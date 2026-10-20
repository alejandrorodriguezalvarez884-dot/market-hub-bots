"""The competition's engine, the same tests as the portal's (market-hub-landing: tests/test_bots.py):
what a bot file can be, how a bot is run on paper and measured from the close after it is sent in,
and its key. engine.py is a copy of the portal's bots.py, so these keep the two in step."""

import json
import math

import pytest

from botleague.config import BOT_COST
from botleague.engine import (FORMAT, Bots, MemoryBots, Prices, Refused, check, decide, describe, examples, first_session, last_settled,
                              resolve, run)
from conftest import Clock, Market, at, sessions, steady


def bot(**over) -> dict:
    raw = {"format": FORMAT, "name": "Test bot", "about": "A bot for the tests.", "universe": {"tickers": ["AAA", "BBB", "CCC"]},
           "rebalance": "daily", "score": [{"factor": "momentum", "days": 5, "weight": 1}], "hold": 1}
    return check({**raw, **over})


# --- The file ------------------------------------------------------------------------------------


def test_a_file_gets_every_default_filled_in():
    b = bot()
    assert (b["filters"], b["weighting"], b["max_weight"], b["universe"]["exclude"]) == ([], "equal", 1.0, [])
    assert b["score"] == [{"factor": "momentum", "days": 5, "skip": 0, "weight": 1.0}]
    assert "market" not in b


def test_a_file_that_is_not_a_bot_is_refused_with_every_problem():
    with pytest.raises(Refused) as exc:
        check({"format": "other", "name": "x", "universe": {"largest": 5, "sector": "Tech"}, "score": [{"factor": "magic"}],
               "hold": 0, "weighting": "random", "colour": "red", "filters": [{"factor": "rsi", "days": 14}],
               "market": {"factor": "sma_cross", "fast": 50, "slow": 20, "min": 0, "cash": 2}})
    problems = " | ".join(exc.value.problems)
    for words in ('no field "colour"', '"format" is', '"name"', 'no field "sector"', "universe.largest", '"factor" is one of',
                  '"hold"', '"weighting"', 'give a "min", a "max"', '"fast" is shorter', '"market.cash"'):
        assert words in problems, words
    assert len(exc.value.problems) >= 11


@pytest.mark.parametrize("raw", examples(), ids=lambda r: r["name"])
def test_every_example_of_the_kit_is_a_bot(raw):
    b = check(raw)
    assert describe(b)[0].startswith("Looks at")


def test_the_rules_in_words():
    words = describe(check(next(r for r in examples() if r["name"] == "Trend follower")))
    assert words[0] == "Looks at the 300 largest US companies."
    assert "Keeps those where its close against its 200-session average is at least 0%." in words
    assert words[-1] == "When, for the S&P 500, its close against its 200-session average is not at least 0%, holds 100% in cash."


def test_the_universe_is_among_the_largest_companies():
    largest = lambda n: ["AAA", "BBB", "CCC", "DDD"][:n]  # noqa: E731
    assert resolve(bot(universe={"largest": 20, "exclude": ["BBB"]}), largest) == ["AAA", "CCC", "DDD"]
    with pytest.raises(Refused, match="ZZZ"):
        resolve(bot(universe={"tickers": ["AAA", "ZZZ"]}), largest)
    with pytest.raises(Refused, match='"hold" is 3'):
        resolve(bot(universe={"tickers": ["AAA", "BBB"]}, hold=3), largest)


# --- Running it ------------------------------------------------------------------------------------

DAYS = sessions(40)


def prices(**extra) -> Prices:
    closes = {"SPY": steady(DAYS, 0.001), "AAA": steady(DAYS, 0.01), "BBB": steady(DAYS, 0.0), "CCC": steady(DAYS, -0.01)}
    return Prices({**closes, **extra})


def test_it_holds_the_best_scored_and_pays_on_what_it_trades():
    curve, held, traded = run(bot(), ["AAA", "BBB", "CCC"], prices(), 10, 30)
    assert held == {"AAA": 1.0} and traded == 1.0  # bought once, then nothing to trade
    assert curve[0] == (DAYS[10], pytest.approx(1 - BOT_COST))
    assert curve[-1][1] == pytest.approx((1 - BOT_COST) * 1.01 ** 20)


def test_weights_drift_between_closes_and_a_rebalance_trades_them_back():
    b = bot(hold=2, universe={"tickers": ["AAA", "BBB"]})
    curve, held, _ = run(b, ["AAA", "BBB"], prices(), 10, 11)
    after = (1 - BOT_COST) * (0.5 * 1.01 + 0.5)
    drift = abs(0.5 - 0.505 / 1.005) + abs(0.5 - 0.5 / 1.005)
    assert curve[1][1] == pytest.approx(after * (1 - BOT_COST * drift))
    assert held == {"AAA": 0.5, "BBB": 0.5}
    weekly = bot(hold=2, universe={"tickers": ["AAA", "BBB"]}, rebalance="weekly")
    _, held, _ = run(weekly, ["AAA", "BBB"], prices(), 10, 11)  # a Monday, then a Tuesday: no rebalance
    assert held["AAA"] == pytest.approx(0.505 / 1.005)


def test_filters_caps_and_the_market_switch():
    p = prices()
    trending = bot(hold=3, filters=[{"factor": "trend", "days": 10, "min": 0}])
    assert set(decide(trending, ["AAA", "BBB", "CCC"], p, 20)) == {"AAA", "BBB"}  # BBB sits on its average, CCC under it
    capped = bot(hold=2, universe={"tickers": ["AAA", "BBB"]}, max_weight=0.4)
    assert decide(capped, ["AAA", "BBB"], p, 20) == {"AAA": 0.4, "BBB": 0.4}  # the rest in cash
    falling = Prices({"SPY": steady(DAYS, -0.005), "AAA": steady(DAYS, 0.01), "BBB": steady(DAYS, 0.0)})
    careful = bot(hold=1, market={"factor": "trend", "days": 10, "min": 0, "cash": 0.5})
    assert decide(careful, ["AAA", "BBB"], falling, 20) == {"AAA": 0.5}
    assert decide(careful, ["AAA", "BBB"], p, 20) == {"AAA": 1.0}


def test_lower_is_better_with_a_negative_weight():
    calm = bot(score=[{"factor": "momentum", "days": 5, "weight": -1}])
    assert decide(calm, ["AAA", "BBB", "CCC"], prices(), 20) == {"CCC": 1.0}


def test_a_stock_with_no_close_keeps_its_last_one():
    gappy = [(d, c) for d, c in steady(DAYS, 0.01) if d not in DAYS[15:25]]
    p = prices(AAA=gappy)
    curve, _, _ = run(bot(), ["AAA", "BBB", "CCC"], p, 10, 30)
    assert all(not math.isnan(v) for _, v in curve)


def test_a_record_starts_at_the_close_after_it_is_sent_in():
    assert DAYS[first_session(DAYS, at(DAYS[3], 11))] == DAYS[3]
    assert DAYS[first_session(DAYS, at(DAYS[3], 16, 5))] == DAYS[4]
    assert first_session(DAYS, at(DAYS[-1], 17)) is None
    assert DAYS[last_settled(DAYS, at(DAYS[-1], 15))] == DAYS[-2]  # today's bar is not a close yet
    assert DAYS[last_settled(DAYS, at(DAYS[-1], 16, 45))] == DAYS[-1]


# --- The competition ---------------------------------------------------------------------------

LONG = sessions(420)
NAMES = [f"T{i:02d}" for i in range(30)]


def competition(day: int, hour: int = 17, names=None):
    clock, market = Clock(at(LONG[day], hour)), Market(LONG, LONG[day])
    store = MemoryBots()
    bots = Bots(store, market, lambda n: NAMES[:n], member_name=names or (lambda user_id: ""), now=clock)
    return bots, store, clock, market


TREND = {"format": FORMAT, "name": "Trend", "universe": {"largest": 20}, "rebalance": "weekly",
         "filters": [{"factor": "trend", "days": 50, "min": 0}], "score": [{"factor": "momentum", "days": 63, "weight": 1}], "hold": 5}


def test_a_bot_is_measured_from_its_first_close_and_moved_on_session_by_session():
    bots, store, clock, market = competition(380, hour=11)
    bots.submit("u1", TREND, handle="ana bots")
    assert bots.mine("u1")["since"] is None and bots.mine("u1")["returns"] is None
    clock.when = at(LONG[380], 17)
    assert bots.behind() is True
    assert bots.refresh()["moved"] == 1
    assert store.get("u1")["curve"][0][0] == LONG[380] and len(store.get("u1")["curve"]) == 1
    assert bots.behind() is False and bots.refresh() == {"moved": 0}  # asked again too soon
    # Five sessions later, moved on from where it was: the same as running it in one go.
    market.upto, clock.when = LONG[385], at(LONG[385], 17)
    assert bots.refresh()["moved"] == 1
    kept = store.get("u1")
    whole, held, _ = run(check(TREND), NAMES[:20], Prices(market(set(NAMES) | {"SPY"})), 380, 385)
    assert [d for d, _ in kept["curve"]] == LONG[380:386]
    assert [v for _, v in kept["curve"]] == pytest.approx([v for _, v in whole], abs=2e-6)
    assert kept["weights"] == pytest.approx(held, abs=1e-6)
    # The record is kept: a stock the provider stops answering for does not change the past.
    past = kept["curve"]
    market.gone, market.upto, clock.when = {"T03", "T07"}, LONG[386], at(LONG[386], 17)
    bots.refresh()
    assert store.get("u1")["curve"][:6] == past and len(store.get("u1")["curve"]) == 7


def test_sending_in_another_bot_starts_the_record_again():
    bots, store, clock, market = competition(380)
    bots.submit("u1", TREND, handle="ana bots")
    market.upto, clock.when = LONG[383], at(LONG[383], 17)
    bots.refresh()
    assert len(store.get("u1")["curve"]) == 3
    bots.submit("u1", {**TREND, "name": "Trend two"})  # the name it showed under stays
    assert store.get("u1")["curve"] == [] and store.get("u1")["handle"] == "ana bots"


def test_a_refresh_does_not_bring_back_a_bot_withdrawn_meanwhile():
    bots, store, clock, market = competition(380)
    bots.submit("u1", TREND, handle="ana bots")
    market.upto, clock.when = LONG[381], at(LONG[381], 17)
    real = store.get
    store.get = lambda user_id: None  # withdrawn while the refresh ran
    bots.refresh()
    store.get = real
    assert store.get("u1")["curve"] == []


def test_the_name_a_bot_shows_under():
    bots, *_ = competition(380, names=lambda user_id: "plays already" if user_id == "u2" else "")
    with pytest.raises(Refused, match="Pick a name"):
        bots.submit("u1", TREND)
    for bad in ("x", "admin", "northwind"):
        with pytest.raises(Refused):
            bots.submit("u1", TREND, handle=bad)
    bots.submit("u1", TREND, handle="ana bots")
    with pytest.raises(Refused, match="Someone else"):
        bots.submit("u3", TREND, handle="Ana-Bots")
    assert bots.submit("u2", TREND)["handle"] == "plays already"  # the name they already show under


def test_the_board_ranks_each_period_among_the_bots_that_ran_it():
    bots, store, clock, market = competition(300)
    bots.submit("u1", TREND, handle="early bird")
    market.upto, clock.when = LONG[330], at(LONG[330], 17)
    bots.refresh()
    bots.submit("u2", {**TREND, "name": "Late", "hold": 10}, handle="late comer")
    market.upto, clock.when = LONG[333], at(LONG[333], 17)
    bots.refresh(force=True)
    o = bots.overview("u2")
    rows = {r["handle"]: r for r in o["rows"]}
    assert set(rows) == {"early bird", "late comer"} and all("user_id" not in r for r in o["rows"])
    assert rows["late comer"]["you"] and not rows["early bird"]["you"]
    assert rows["late comer"]["returns"]["1m"] is None and "1m" not in rows["late comer"]["ranks"]
    assert rows["early bird"]["ranks"]["1m"] == 1 and rows["early bird"]["sessions"] == 33
    assert {rows[h]["ranks"]["1d"] for h in rows} == {1, 2}
    assert o["benchmark"]["returns"]["1d"] is not None and o["benchmark"]["returns"]["all"] is None
    assert o["you"]["rules"][0] == "Looks at the 20 largest US companies." and o["you"]["bot"]["hold"] == 10


def test_a_backtest_is_measured_against_the_index():
    bots, *_ = competition(410)
    got = bots.backtest(TREND, 1)
    assert got["sessions"] == 252 and got["end"] == LONG[410]
    assert set(got["bot"]) >= {"total_return", "annual_return", "volatility", "max_drawdown"} and got["benchmark"]["ticker"] == "SPY"
    assert got["months"][-1]["benchmark"] is not None and len(got["notes"]) == 3
    with pytest.raises(Refused, match="years"):
        bots.backtest(TREND, 9)
    with pytest.raises(Refused, match="not enough closes"):
        competition(60)[0].backtest(TREND, 1)


def test_the_key_is_kept_hashed_and_a_new_one_replaces_it():
    bots, store, *_ = competition(380)
    key = bots.issue_key("u1")
    assert key.startswith("mhb_") and bots.who(key) == "u1"
    assert key not in json.dumps(store.keys) and store.keys_of("u1")[0]["used_utc"]
    second = bots.issue_key("u1")
    assert bots.who(key) is None and bots.who(second) == "u1"
    assert bots.who("mhb_nothing") is None and bots.who(None) is None and bots.who("other") is None
    bots.submit("u1", TREND, handle="ana bots")
    bots.forget("u1")
    assert bots.who(second) is None and store.get("u1") is None
