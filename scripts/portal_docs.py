"""Writes documents with the portal's own code, for Bot League's compatibility test (tests/test_shared.py).

Run from market-hub-landing, with its code: cd ../market-hub-landing && uv run python ../market-hub-bots/scripts/portal_docs.py ../market-hub-bots/tests/fixtures/portal_docs.json
"""
import json, math, sys
from datetime import date, datetime, time, timedelta, timezone
from markethub.bots import Bots, MemoryBots, NEW_YORK, FORMAT

def sessions(n, first=date(2024, 1, 8)):
    out, d = [], first
    while len(out) < n:
        if d.weekday() < 5: out.append(d.isoformat())
        d += timedelta(days=1)
    return out

def walk(ticker, days):
    seed = sum(map(ord, ticker)); price, out = 40.0 + seed % 60, []
    for i, d in enumerate(days):
        price *= 1 + 0.0004 * (seed % 5 - 2) + 0.012 * math.sin(i / (5 + seed % 7) + seed)
        out.append((d, round(price, 4)))
    return out

LONG = sessions(420); NAMES = [f"T{i:02d}" for i in range(30)]
at = lambda day, h: datetime.combine(date.fromisoformat(day), time(h, 0), NEW_YORK).astimezone(timezone.utc)
clock = {"now": at(LONG[380], 11)}
upto = {"d": LONG[380]}
closes = lambda ts: {t: [(d, c) for d, c in walk(t, LONG) if d <= upto["d"]] for t in ts}
store = MemoryBots()
bots = Bots(store, closes, lambda n: NAMES[:n], now=lambda: clock["now"])
TREND = {"format": FORMAT, "name": "Trend", "about": "Rides what is over its average.", "universe": {"largest": 20}, "rebalance": "weekly",
         "filters": [{"factor": "trend", "days": 50, "min": 0}], "score": [{"factor": "momentum", "days": 63, "weight": 1}], "hold": 5}
key = bots.issue_key("portal-user-1", "Ana Torres")
bots.submit("portal-user-1", TREND)
clock["now"], upto["d"] = at(LONG[385], 17), LONG[385]
bots.refresh(force=True)
json.dump({"written_by": "market-hub-landing src/markethub/bots.py", "sessions": LONG, "key": key,
           "bots": store.bots, "keys": store.keys, "meta": store.state,
           "mine": bots.mine("portal-user-1"), "overview_rows": bots.overview("portal-user-1")["rows"]},
          open(sys.argv[1], "w"), indent=1, default=str)
print("ok", len(store.bots["portal-user-1"]["curve"]))
