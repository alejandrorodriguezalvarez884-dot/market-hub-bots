"""Puts a few made-up members' bots, and the house bots, in the local store (data/bots), on the
made-up closes of BOTLEAGUE_SAMPLE=1, each sent in on a different day of the past, and moves them
all on to the last close. For `make demo` only: it writes the local files, never Firestore.

    BOTLEAGUE_SAMPLE=1 uv run python scripts/seed_local.py
"""

from __future__ import annotations

import os
import shutil
from datetime import date, datetime, time, timedelta, timezone

from botleague.config import DATA_DIR
from botleague.engine import FORMAT, NEW_YORK, Bots, FileBots
from botleague.league import FileHouse, League, Remembering
from botleague.market import Sample

if os.environ.get("MARKETHUB_FIRESTORE") == "1":
    raise SystemExit("This writes the local store only: unset MARKETHUB_FIRESTORE.")

# (account, name shown, sessions ago it was sent in, bot)
BOTS = [
    ("seed-1", "tape_and_trend", 180, {"name": "Trend with a seatbelt", "about": "The strongest of the 80 largest over their 100-session average; cash when the index is under its own.",
                                       "universe": {"largest": 80}, "rebalance": "weekly", "filters": [{"factor": "trend", "days": 100, "min": 0}],
                                       "score": [{"factor": "momentum", "days": 126, "skip": 5, "weight": 1}], "hold": 10,
                                       "market": {"factor": "trend", "days": 100, "min": 0, "cash": 1}}),
    ("seed-2", "lowvol lucy", 150, {"name": "Sleep well", "about": "The 15 calmest large caps, the calmest with more.", "universe": {"largest": 80},
                                    "rebalance": "monthly", "score": [{"factor": "volatility", "days": 63, "weight": -1}], "hold": 15,
                                    "weighting": "inverse_volatility", "max_weight": 0.12}),
    ("seed-3", "quant-curious", 90, {"name": "Dip buyer", "about": "Short-term losers inside long uptrends, looked at every day.", "universe": {"largest": 80},
                                     "rebalance": "daily", "filters": [{"factor": "trend", "days": 150, "min": 0}],
                                     "score": [{"factor": "rsi", "days": 3, "weight": -1}], "hold": 8}),
    ("seed-4", "the drift", 60, {"name": "Six-month winners", "about": "What rose the most over six months, monthly.", "universe": {"largest": 60},
                                 "rebalance": "monthly", "score": [{"factor": "momentum", "days": 126, "weight": 1}], "hold": 12}),
    ("seed-5", "nine to five", 25, {"name": "Megacap trio", "about": "Three of a dozen giants, by their three-month move.",
                                    "universe": {"tickers": ["AAPL", "MSFT", "NVDA", "AMZN", "META", "AVGO", "TSLA", "JPM", "LLY", "V", "WMT", "ORCL"]},
                                    "rebalance": "weekly", "score": [{"factor": "momentum", "days": 63, "weight": 1}], "hold": 3, "weighting": "score"}),
    ("seed-6", "mean reverter", 8, {"name": "Rubber band", "about": "The furthest under their 50-session high, among the calmer half.", "universe": {"largest": 80},
                                    "rebalance": "weekly", "filters": [{"factor": "volatility", "days": 63, "max": 0.3}],
                                    "score": [{"factor": "drawdown", "days": 50, "weight": -1}], "hold": 10}),
    ("local", "local member", 40, {"name": "My first bot", "about": "Near the highs, with the short average over the long one.", "universe": {"largest": 80},
                                   "rebalance": "weekly", "filters": [{"factor": "sma_cross", "fast": 20, "slow": 100, "min": 0}],
                                   "score": [{"factor": "drawdown", "days": 252, "weight": 1}], "hold": 10}),
]


def sessions_back(n: int) -> datetime:
    d, left = date.today(), n
    while left:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            left -= 1
    return datetime.combine(d, time(11, 0), NEW_YORK).astimezone(timezone.utc)


def main() -> None:
    root = DATA_DIR / "bots"
    shutil.rmtree(root, ignore_errors=True)
    source = Sample()
    clock = {"now": sessions_back(200)}
    store = Remembering(FileBots(root))
    bots = Bots(store, source.closes, source.largest, now=lambda: clock["now"])
    league = League(bots, store, FileHouse(root), source.closes, source.largest, sample=True, now=lambda: clock["now"])
    league._move_house()  # the house bots start 200 sessions ago
    for user_id, handle, back, raw in BOTS:
        clock["now"] = sessions_back(back)
        bots.submit(user_id, {"format": FORMAT, **raw}, handle=handle)
    clock["now"] = datetime.now(timezone.utc)
    print(league.refresh(force=True))
    print(f"{len(BOTS)} bots and the house bots in {root}")


if __name__ == "__main__":
    main()
