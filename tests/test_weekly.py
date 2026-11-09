"""Weekly prizes: each market week's winner among the bots that played it whole, kept the first time
a refresh passes the week's last close, and the bots that have won the most weeks."""

from datetime import date

from botleague.league import unrecorded, week_of, weeks, winner
from conftest import at, sessions
from test_api import BOT, DAYS, client, make, send, slug

JAN = sessions(15, date(2024, 1, 8))  # three weeks: 8-12, 15-19 and 22-26 January 2024


def bot(pid: str, start: str, daily: float, days=JAN) -> dict:
    """A bot whose record starts at the close of ``start`` and grows by ``daily`` a session."""
    curve, v = [], 1.0
    for d in days[days.index(start):]:
        curve.append([d, round(v, 6)])
        v *= 1 + daily
    return {"public_id": pid, "curve": curve}


def index(days=JAN, daily=0.001) -> list:
    return [[d, 100 * (1 + daily) ** i] for i, d in enumerate(days)]


def test_a_week_is_monday_to_friday():
    assert week_of("2024-01-08") == week_of("2024-01-12") == "2024-01-08"
    assert week_of("2024-01-15") == "2024-01-15"


def test_only_bots_that_played_the_whole_week_count():
    docs = [bot("aaaaaaaaaa", "2024-01-08", 0.002),  # its first close is a Monday: it plays from the next week
            bot("bbbbbbbbbb", "2024-01-10", 0.003),  # sent in on a Wednesday: from the next week too
            bot("cccccccccc", "2024-01-17", 0.010),  # the best, but it started in the middle of the second week
            {**bot("dddddddddd", "2024-01-08", 0.05), "public_id": None}]  # no public id yet: not shown
    got = weeks(docs, index())
    assert [w["week"] for w in got] == ["2024-01-08", "2024-01-15", "2024-01-22"] and all(w["over"] for w in got)
    assert got[0]["played"] == []
    assert [p["id"] for p in got[1]["played"]] == ["bbbbbbbbbb", "aaaaaaaaaa"]
    assert [p["id"] for p in got[2]["played"]] == ["cccccccccc", "bbbbbbbbbb", "aaaaaaaaaa"]
    # The week's return: the last close of the week over the last close before it.
    assert got[1]["played"][0]["return"] == round(1.003 ** 7, 6) / round(1.003 ** 2, 6) - 1
    assert abs(got[1]["index"] - (1.001 ** 5 - 1)) < 1e-12 and got[0]["index"] is None
    w = winner(got[2])
    assert w["winners"] == [{"id": "cccccccccc", "since": "2024-01-17"}] and w["entrants"] == 3 and w["sessions"] == 5
    assert winner(got[0]) is None


def test_a_bot_behind_the_weeks_last_close_has_not_played_it_whole():
    docs = [bot("aaaaaaaaaa", "2024-01-08", 0.002), bot("bbbbbbbbbb", "2024-01-08", 0.003, days=JAN[:9])]  # stopped on Thursday 18
    assert [p["id"] for p in weeks(docs, index())[1]["played"]] == ["aaaaaaaaaa"]


def test_the_same_return_shares_the_week():
    docs = [bot("bbbbbbbbbb", "2024-01-08", 0.002), bot("aaaaaaaaaa", "2024-01-09", 0.002)]
    w = winner(weeks(docs, index())[1])
    assert [x["id"] for x in w["winners"]] == ["bbbbbbbbbb", "aaaaaaaaaa"]  # the longest playing first


def test_a_week_is_over_on_friday_or_when_a_later_session_has_closed():
    thursday = JAN[:14]  # up to Thursday 25 January
    assert [w["over"] for w in weeks([bot("aaaaaaaaaa", "2024-01-08", 0.002, thursday)], index(thursday))] == [True, True, False]
    # Good Friday 2024: the week of 25 March closes on Thursday; it is over once Monday 1 April has closed.
    easter = ["2024-03-22", "2024-03-25", "2024-03-26", "2024-03-27", "2024-03-28"]
    assert weeks([], index(easter))[-1]["over"] is False
    assert weeks([], index([*easter, "2024-04-01"]))[1]["over"] is True


def test_only_the_weeks_not_kept_yet_are_added():
    got = weeks([bot("aaaaaaaaaa", "2024-01-08", 0.002)], index())
    kept = [winner(got[1])]
    assert [w["week"] for w in unrecorded(got, kept)] == ["2024-01-22"]
    assert unrecorded(got, kept + unrecorded(got, kept)) == []


def test_weekly_prizes_on_the_board_and_on_a_bots_page():
    app = make()
    clock, store = app.state.clock, app.state.store
    friday = max(i for i, d in enumerate(DAYS[:-10]) if date.fromisoformat(d).weekday() == 4)
    w1 = friday - 14  # the Monday two weeks before that Friday
    assert date.fromisoformat(DAYS[w1]).weekday() == 0
    clock.when = at(DAYS[w1], 12)
    send(app, "u1")  # plays from the second week
    clock.when = at(DAYS[w1 + 7], 12)
    send(app, "u2", bot={**BOT, "name": "Other bot", "hold": 3}, name="Luis Gil")  # sent in on a Wednesday: from the third week
    clock.when = at(DAYS[friday], 18)
    assert client(app).post("/api/board/refresh").json()["moved"] == 2
    kept = store.meta()["weeks"]
    assert [k["week"] for k in kept] == [week_of(DAYS[w1 + 5]), week_of(DAYS[friday])]
    assert kept[0]["winners"] == [{"id": slug(app, "u1"), "since": DAYS[w1]}] and kept[0]["entrants"] == 1
    assert set(kept[0]) == {"week", "from", "to", "sessions", "return", "index", "entrants", "winners"}  # no names are kept

    ana = client(app, "u1").get("/api/board").json()
    weekly = ana["weekly"]
    assert weekly["current"] is None  # Friday has closed: the next week starts on Monday
    assert [w["week"] for w in weekly["winners"]] == [kept[1]["week"], kept[0]["week"]]  # newest first
    assert weekly["winners"][1]["bots"] == [{"slug": slug(app, "u1"), "name": "Api bot", "handle": "Ana", "you": True}]
    assert weekly["winners"][0]["entrants"] == 2 and weekly["winners"][0]["index"] is not None
    third = weekly["winners"][0]["bots"][0]["slug"]
    assert sum(t["wins"] for t in weekly["ranking"]) == 2 and weekly["ranking"][0]["wins"] >= weekly["ranking"][-1]["wins"]
    assert {r["slug"]: r["wins"] for r in ana["rows"]}[slug(app, "u1")] == (2 if third == slug(app, "u1") else 1)
    page = client(app, "u2").get(f"/api/board/bot/{slug(app, 'u1')}").json()
    assert page["wins"][-1]["week"] == kept[0]["week"] and not page["wins"][-1]["shared"]
    assert client(app).get("/api/board").json()["weekly"] == {"current": None, "winners": [], "ranking": []}  # not public here

    # A withdrawn winner keeps its week, without its name.
    client(app, "u1").delete("/api/bots/mine")
    luis = client(app, "u2").get("/api/board").json()["weekly"]
    assert luis["winners"][1]["bots"] == [{"gone": True}] and all(t["slug"] == slug(app, "u2") for t in luis["ranking"])
    assert len(store.meta()["weeks"]) == 2

    # The week being played, as it stands after its first two closes.
    clock.when = at(DAYS[friday + 2], 18)
    client(app).post("/api/board/refresh")
    current = client(app, "u2").get("/api/board").json()["weekly"]["current"]
    assert current["week"] == week_of(DAYS[friday + 1]) and current["sessions"] == 2 and current["to"] == DAYS[friday + 2]
    assert current["standing"] == [{"slug": slug(app, "u2"), "name": "Other bot", "handle": "Luis", "you": True, "place": 1,
                                    "return": current["standing"][0]["return"]}]
    assert len(store.meta()["weeks"]) == 2
