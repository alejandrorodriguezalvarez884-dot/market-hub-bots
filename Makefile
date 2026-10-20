# Everything is started from here, by hand. Nothing runs on a timer.
#
#   make            list the targets
#   make demo       the whole site on made-up figures, with a few made-up bots, at :8080
#   make deploy     build and deploy the service to Cloud Run
#
# The service (site + API) runs on Cloud Run and only works when a visitor asks. The bots are moved
# on when a visit finds them behind the last close, never on a schedule.

SHELL := /bin/bash
.DEFAULT_GOAL := help
.PHONY: help install test check site api dev serve demo seed icons share deploy

help: ## List the targets
	@grep -E '^[a-z]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  make %-9s %s\n", $$1, $$2}'

install: ## Install the Python and site dependencies
	uv sync
	cd site && npm ci

test: ## Run the tests
	uv run pytest

check: test ## Tests plus the site's type check and build
	cd site && npx astro check && npm run build

site: ## Build the site into site/dist
	cd site && npm run build

api: ## Run the API alone at http://localhost:8000, with reload (pair it with `make dev`)
	HUB_URL= BOTLEAGUE_ALLOWED_ORIGINS=http://localhost:4321 uv run uvicorn botleague.api:create_app --factory --reload --port 8000

dev: ## Run the site at http://localhost:4321 with reload (it calls the API on port 8000)
	cd site && PUBLIC_API_URL=http://localhost:8000 npm run dev

serve: site ## Site and API together at http://localhost:8080 on real closes, as in production but signed in as a local member
	HUB_URL= BOTLEAGUE_STATIC_DIR=site/dist uv run uvicorn botleague.api:create_app --factory --port 8080

seed: ## Put a few made-up members' bots in the local store (data/bots), on made-up figures
	BOTLEAGUE_SAMPLE=1 uv run python scripts/seed_local.py

demo: site seed ## The whole site on made-up figures, with the bots of `make seed`, at http://localhost:8080
	HUB_URL= BOTLEAGUE_SAMPLE=1 BOTLEAGUE_STATIC_DIR=site/dist uv run uvicorn botleague.api:create_app --factory --port 8080

icons: ## Draw favicon.ico, the PNG icons and logo.png from site/public/favicon.svg (uses this machine's Chrome)
	cd brand && npm ci && node icons.mjs

share: ## Draw the picture a shared link shows (site/public/share.png, uses this machine's Chrome)
	cd brand && npm ci && node share.mjs

deploy: ## Build and deploy the service to Cloud Run (see scripts/deploy-cloudrun.sh)
	./scripts/deploy-cloudrun.sh
