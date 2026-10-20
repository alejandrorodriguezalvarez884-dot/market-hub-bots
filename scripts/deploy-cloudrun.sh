#!/usr/bin/env bash
# Deploys the production image (site + API in one container) to Google Cloud Run. Cloud Build
# builds the Dockerfile remotely, so Docker is not needed locally. The bots, their keys and the
# board's state live in Market Hub's own Firestore database (collections bots, bot_keys and
# bot_meta), which the hub's deploy creates and the hub's Community section reads too. The
# service scales to zero: it costs nothing while nobody uses it, and it calls no paid API.
#
# Requirements: the gcloud CLI logged in on a project with billing enabled, and .env with HUB_URL.
# HUB_URL (the Market Hub address) is where members sign in: the service reads the hub's session
# cookie with the hub's secret (Secret Manager: market-hub-session-secret). The cookie is shared
# on the hub's parent domain, so the site has to be served under it (a subdomain of
# themarkethub.app) for members to arrive signed in.
#
# Optional overrides: GCP_PROJECT, GCP_REGION, SERVICE_NAME, MAX_INSTANCES.
set -euo pipefail

cd "$(dirname "$0")/.."

fail() {
  echo "error: $*" >&2
  exit 1
}

command -v gcloud >/dev/null || fail "gcloud is not installed."

GCP_PROJECT="${GCP_PROJECT:-$(gcloud config get-value project 2>/dev/null || true)}"
GCP_REGION="${GCP_REGION:-europe-west1}"
SERVICE_NAME="${SERVICE_NAME:-bot-league}"
FIRESTORE_DATABASE="${MARKETHUB_FIRESTORE_DATABASE:-market-hub}"
MAX_INSTANCES="${MAX_INSTANCES:-2}"
ENV_FILE=".env"

[[ -n "$GCP_PROJECT" ]] || fail "No GCP project selected. Run 'gcloud init' or set GCP_PROJECT."
[[ -f "$ENV_FILE" ]] || fail "$ENV_FILE not found."

# Read single values instead of sourcing the file, and drop the quotes around them.
env_value() { grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2- | sed -e 's/^"//' -e 's/"$//' || true; }
HUB_URL="$(env_value HUB_URL)"
SEC_USER_AGENT="$(env_value SEC_USER_AGENT)"
PUBLIC_BOARD="$(env_value BOTLEAGUE_PUBLIC_BOARD)"
# The chat on a member's page: on with BOTLEAGUE_CHAT=1, with the owner's Anthropic key from Secret
# Manager (the secret ANTHROPIC_API_KEY, the one the portal reads). Its model and caps are the owner's.
CHAT="$(env_value BOTLEAGUE_CHAT)"
CHAT_MODEL="$(env_value BOTLEAGUE_CHAT_MODEL)"
CHAT_EFFORT="$(env_value BOTLEAGUE_CHAT_EFFORT)"
CHAT_PER_MEMBER="$(env_value BOTLEAGUE_CHAT_PER_MEMBER_PER_DAY)"
CHAT_DAILY_MAX="$(env_value BOTLEAGUE_CHAT_DAILY_MAX_USD)"

[[ -n "$HUB_URL" ]] || fail "HUB_URL is not set: members sign in with their Market Hub account."
[[ "$SEC_USER_AGENT" == *@* ]] || fail "SEC_USER_AGENT in $ENV_FILE needs a contact email."

gcp() { gcloud --project "$GCP_PROJECT" --quiet "$@"; }

# Give the service's account a role on something, only if it does not have it yet (a policy
# written by two deploys at once collides).
grant() {
  local kind="$1" resource="$2" role="$3" member="serviceAccount:$SERVICE_ACCOUNT"
  shift 3
  if gcp $kind get-iam-policy "$resource" --flatten='bindings[].members' --format='value(bindings.role,bindings.members)' 2>/dev/null \
      | tr -d '\r' | grep -xF "$role"$'\t'"$member" >/dev/null; then
    return 0
  fi
  gcp $kind add-iam-policy-binding "$resource" --member "$member" --role "$role" "$@" >/dev/null
}

echo "→ Enabling APIs in $GCP_PROJECT"
gcp services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com \
  secretmanager.googleapis.com firestore.googleapis.com

PROJECT_NUMBER="$(gcp projects describe "$GCP_PROJECT" --format='value(projectNumber)')"
SERVICE_ACCOUNT="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
grant projects "$GCP_PROJECT" roles/run.builder --condition=None
grant projects "$GCP_PROJECT" roles/datastore.user --condition=None

gcp firestore databases describe --database="$FIRESTORE_DATABASE" >/dev/null 2>&1 \
  || fail "Market Hub's Firestore database '$FIRESTORE_DATABASE' does not exist. Deploy the hub first."
gcp secrets describe market-hub-session-secret >/dev/null 2>&1 \
  || fail "Market Hub's secret market-hub-session-secret does not exist. Deploy the hub first."
grant secrets market-hub-session-secret roles/secretmanager.secretAccessor
SECRETS="HUB_SESSION_SECRET=market-hub-session-secret:latest"
CHAT_ENV=""
if [[ "$CHAT" == "1" ]]; then
  gcp secrets describe ANTHROPIC_API_KEY >/dev/null 2>&1 || fail "BOTLEAGUE_CHAT=1 but the secret ANTHROPIC_API_KEY does not exist."
  grant secrets ANTHROPIC_API_KEY roles/secretmanager.secretAccessor
  SECRETS="$SECRETS,ANTHROPIC_API_KEY=ANTHROPIC_API_KEY:latest"
  CHAT_ENV="|BOTLEAGUE_CHAT=1|BOTLEAGUE_CHAT_MODEL=${CHAT_MODEL:-claude-haiku-5-5}|BOTLEAGUE_CHAT_EFFORT=${CHAT_EFFORT:-high}|BOTLEAGUE_CHAT_PER_MEMBER_PER_DAY=${CHAT_PER_MEMBER:-15}|BOTLEAGUE_CHAT_DAILY_MAX_USD=$CHAT_DAILY_MAX"
  echo "→ With the chat on (${CHAT_MODEL:-claude-haiku-5-5})"
fi

echo "→ Building with Cloud Build and deploying '$SERVICE_NAME' to $GCP_REGION (a few minutes)"
# Memory and time for a refresh: five years of closes of the 500 largest companies, read and run.
gcp run deploy "$SERVICE_NAME" \
  --source . \
  --region "$GCP_REGION" \
  --allow-unauthenticated \
  --port 8080 \
  --cpu 1 \
  --memory 2Gi \
  --min-instances 0 \
  --max-instances "$MAX_INSTANCES" \
  --timeout 300 \
  --set-secrets "$SECRETS" \
  --set-env-vars "^|^MARKETHUB_FIRESTORE=1|MARKETHUB_FIRESTORE_DATABASE=$FIRESTORE_DATABASE|HUB_URL=$HUB_URL|SEC_USER_AGENT=$SEC_USER_AGENT|BOTLEAGUE_PUBLIC_BOARD=${PUBLIC_BOARD:-1}$CHAT_ENV"

URL="$(gcp run services describe "$SERVICE_NAME" --region "$GCP_REGION" --format 'value(status.url)')"
if curl -fsS "$URL/api/health" >/dev/null 2>&1; then
  echo "✓ Deployed: $URL"
else
  fail "Deployed, but $URL/api/health failed. Logs: gcloud run services logs read $SERVICE_NAME --region $GCP_REGION"
fi
