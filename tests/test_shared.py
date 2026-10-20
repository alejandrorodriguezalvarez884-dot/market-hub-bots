"""The same data as the portal's: documents written by the portal's own code (fixtures/portal_docs.json,
made by scripts/portal_docs.py) are read, moved on and answered for here exactly as there, and what
this site writes has the same shape."""

import json
from pathlib import Path

import pytest

from botleague.engine import FORMAT, Bots, MemoryBots, Prices, check, run
from conftest import Clock, Market, at

PORTAL = json.loads((Path(__file__).parent / "fixtures" / "portal_docs.json").read_text(encoding="utf-8"))
LONG = PORTAL["sessions"]
NAMES = [f"T{i:02d}" for i in range(30)]
TREND = {"format": FORMAT, "name": "Trend", "about": "Rides what is over its average.", "universe": {"largest": 20}, "rebalance": "weekly",
         "filters": [{"factor": "trend", "days": 50, "min": 0}], "score": [{"factor": "momentum", "days": 63, "weight": 1}], "hold": 5}


def portal_store() -> MemoryBots:
    store = MemoryBots()
    store.bots = json.loads(json.dumps(PORTAL["bots"]))
    store.keys = json.loads(json.dumps(PORTAL["keys"]))
    store.state = json.loads(json.dumps(PORTAL["meta"]))
    return store


def here(store, day: int):
    clock, market = Clock(at(LONG[day], 17)), Market(LONG, LONG[day])
    return Bots(store, market, lambda n: NAMES[:n], now=clock), clock, market


def test_the_portals_bot_reads_the_same_here():
    bots, *_ = here(portal_store(), 385)
    assert bots.mine("portal-user-1") == PORTAL["mine"]
    assert bots.overview("portal-user-1")["rows"] == PORTAL["overview_rows"]


def test_a_key_made_on_the_portal_opens_the_agent_routes_here():
    bots, *_ = here(portal_store(), 385)
    assert bots.who(PORTAL["key"]) == "portal-user-1"
    assert bots.who(PORTAL["key"][:-2] + "xx") is None


def test_a_bot_the_portal_moved_on_goes_on_from_there():
    store = portal_store()
    bots, clock, market = here(store, 385)
    market.upto, clock.when = LONG[390], at(LONG[390], 17)
    assert bots.refresh(force=True)["moved"] == 1
    kept = store.get("portal-user-1")
    whole, held, _ = run(check(TREND), NAMES[:20], Prices(market(set(NAMES) | {"SPY"})), 380, 390)
    assert [d for d, _ in kept["curve"]] == LONG[380:391]
    assert kept["curve"][:6] == PORTAL["bots"]["portal-user-1"]["curve"]
    assert [v for _, v in kept["curve"]] == pytest.approx([v for _, v in whole], abs=2e-6)
    assert kept["weights"] == pytest.approx(held, abs=1e-6)


def test_what_is_written_here_has_the_portals_shape():
    store = MemoryBots()
    bots, clock, market = here(store, 380)
    clock.when = at(LONG[380], 11)
    bots.issue_key("u2", "Bea Ortiz")
    bots.submit("u2", {**TREND, "name": "Other"})
    market.upto, clock.when = LONG[385], at(LONG[385], 17)
    bots.refresh(force=True)
    theirs, mine = PORTAL["bots"]["portal-user-1"], store.get("u2")
    assert set(mine) == set(theirs) and set(mine["spec"]) == set(theirs["spec"])
    assert [type(x) for x in mine["curve"][0]] == [type(x) for x in theirs["curve"][0]]
    assert set(store.keys_of("u2")[0]) == set(next(iter(PORTAL["keys"].values())))
    assert set(store.meta()) == set(PORTAL["meta"])
