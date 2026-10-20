"""Constants of the service. Nothing here costs money: closes come from Yahoo Finance and the list
of the largest companies from the SEC, neither of which takes a key."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")

DATA_DIR = Path(os.environ.get("BOTLEAGUE_DATA_DIR", ROOT / "data"))

# Market Hub's own database: the bots, their keys and the board's state live there, shared with
# the portal's Community section (collections bots, bot_keys and bot_meta).
FIRESTORE_DATABASE = os.environ.get("MARKETHUB_FIRESTORE_DATABASE", "market-hub").strip()

# --- The competition (engine.py, the same figures as the portal's config) ----------------------

BOT_UNIVERSE_MAX = 500  # a bot chooses among the largest US companies, at most this many
BOT_HOLD_MAX = 50
BOT_COST = 0.001  # paid on each unit of the portfolio traded at a rebalance (0.10%)
BOTS_MAX = 500  # bots the competition takes
BOT_BACKTEST_YEARS_MAX = 3
# Backtests a member's key can ask for in an hour, and bots it can send in a day.
BOT_BACKTESTS_PER_USER_PER_HOUR = 30
BOT_SUBMISSIONS_PER_USER_PER_DAY = 10
# The board is worked out from the kept curves and held in memory this long. A visit that finds
# the bots behind the last close asks for them to be moved on, at most this often.
BOTS_CACHE_SECONDS = 120
BOTS_REFRESH_SECONDS = 1800
# A refresh taken to be still running elsewhere, if it started less than this ago.
BOTS_LOCK_SECONDS = 300

# --- This site ---------------------------------------------------------------------------------

# Requests one address can make in an hour to the routes that read prices or the store.
PER_IP_PER_HOUR = int(os.environ.get("BOTLEAGUE_PER_IP_PER_HOUR", "600"))
# Whether visitors who are not signed in see the members' bots on the board. On: the user opened
# the board to everyone (2026-10-20), and Market Hub's privacy page says so. 0 shows them to
# signed-in members only; visitors always see the house bots and the index.
PUBLIC_BOARD = os.environ.get("BOTLEAGUE_PUBLIC_BOARD", "1").strip() != "0"
# Rules changes and switches a member can make from the page or their agent in a day.
SWITCHES_PER_USER_PER_DAY = 30

# --- The chat on a member's page (chat.py) -------------------------------------------------------
# It spends on the owner's Anthropic key: off unless BOTLEAGUE_CHAT=1 and the key is set, and
# capped. The model and the caps are the owner's choice; nothing is spent until they say so.
CHAT_ENABLED = os.environ.get("BOTLEAGUE_CHAT", "0").strip() == "1" and bool(os.environ.get("ANTHROPIC_API_KEY", "").strip())
CHAT_MODEL = os.environ.get("BOTLEAGUE_CHAT_MODEL", "claude-opus-5-5").strip()
CHAT_PER_MEMBER_PER_DAY = int(os.environ.get("BOTLEAGUE_CHAT_PER_MEMBER_PER_DAY", "15"))
CHAT_DAILY_MAX_USD = float(os.environ.get("BOTLEAGUE_CHAT_DAILY_MAX_USD", "2.00"))
# The most one message can cost, reserved before it is sent: 8,000 tokens out at the dearest price.
CHAT_REQUEST_MAX_USD = float(os.environ.get("BOTLEAGUE_CHAT_REQUEST_MAX_USD", "0.20"))
# Dollars per million tokens, in and out.
CHAT_PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00), "claude-haiku-5-5": (0.10, 0.50)}

# Sample closes and a sample list of companies, for a machine with no network (make demo).
SAMPLE = os.environ.get("BOTLEAGUE_SAMPLE", "0").strip() == "1"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
# Closes are read once a day: a refresh after the close finds them new again after this long.
CLOSES_TTL_SECONDS = 6 * 3600
