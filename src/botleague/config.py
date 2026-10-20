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
# Sample closes and a sample list of companies, for a machine with no network (make demo).
SAMPLE = os.environ.get("BOTLEAGUE_SAMPLE", "0").strip() == "1"
SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
# Closes are read once a day: a refresh after the close finds them new again after this long.
CLOSES_TTL_SECONDS = 6 * 3600
