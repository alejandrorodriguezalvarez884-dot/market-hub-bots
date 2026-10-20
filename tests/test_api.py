"""The site's routes: the board and the bots' pages as visitors and members see them, the house bots,
the member's own routes with Market Hub's cookie, and the agent's with its key."""

import io
import zipfile
from datetime import date

import pytest
from fastapi.testclient import TestClient

from botleague.api import create_app
from botleague.engine import FORMAT, MemoryBots
from botleague.league import HOUSE, MemoryHouse, house_examples
from botleague.market import SAMPLE_TICKERS
from conftest import HUB, ORIGIN, SECRET, Clock, at, hub_cookie, sessions, walk

DAYS = sessions(700, date(2023, 11, 6))
BOT = {"format": FORMAT, "name": "Api bot", "about": "Momentum, monthly.", "universe": {"largest": 30},
       "score": [{"factor": "momentum", "days": 126, "skip": 21, "weight": 1}], "hold": 8, "rebalance": "monthly"}


class Names:
    """Market Hub's community: who already shows under a name there."""

    def __init__(self):
        self.shown = {"cara": "u9"}

    def taken(self, key, user_id):
        return self.shown.get(key, user_id) != user_id

    def name(self, user_id):
        return next((k for k, v in self.shown.items() if v == user_id), "")


def make(public=False, hub=(HUB, SECRET)):
    clock = Clock(at(DAYS[-1], 18))
    store, house = MemoryBots(), MemoryHouse()
    app = create_app(bot_store=store, house_store=house, members=Names(), closes=lambda ts: {t: walk(t, DAYS) for t in ts},
                     largest=lambda n: list(SAMPLE_TICKERS[:n]), hub=hub, public=public, clock=clock)
    app.state.clock, app.state.store, app.state.house = clock, store, house
    return app


@pytest.fixture
def app():
    return make()


def client(app, user_id: str | None = None) -> TestClient:
    c = TestClient(app)
    c.headers.update({"origin": ORIGIN})
    if user_id:
        c.cookies.set("mh_session", hub_cookie(user_id))
    return c


def send(app, user_id: str, bot=BOT, handle="ana bots") -> str:
    page = client(app, user_id)
    key = page.post("/api/bots/key").json()["key"]
    got = TestClient(app).put("/api/bot", json={"bot": bot, "handle": handle}, headers={"authorization": f"Bearer {key}"})
    assert got.status_code == 200, got.json()
    return key


def test_who_is_signed_in(app):
    assert client(app).get("/api/me").json()["user"] is None
    me = client(app).get("/api/me").json()
    assert me["signin"] == f"{HUB}/signin/?next=https%3A%2F%2Ftestserver%2Fme%2F" and not me["local"]
    assert client(app, "u1").get("/api/me").json()["user"]["name"] == "Ana"
    forged = TestClient(app)
    forged.cookies.set("mh_session", hub_cookie("u1", secret="another"))
    assert forged.get("/api/me").json()["user"] is None


def test_the_house_bots_run_from_the_close_after_they_start(app):
    visitor = client(app)
    clock = app.state.clock
    clock.when = at(DAYS[-6], 12)
    assert visitor.get("/api/board").json()["stale"] is True
    assert visitor.post("/api/board/refresh").json()["house"] == 0  # started: their record begins at this day's close
    doc = app.state.house.get()
    assert set(doc["bots"]) == {h for h, _ in house_examples()} and all(b["curve"] == [] for b in doc["bots"].values())
    clock.when = at(DAYS[-1], 18)
    assert visitor.post("/api/board/refresh").json()["house"] == len(house_examples())
    board = visitor.get("/api/board").json()
    assert board["stale"] is False and board["as_of"] == DAYS[-1]
    lines = {h["slug"]: h for h in board["house"]}
    momentum = lines[HOUSE + "momentum"]
    assert momentum["since"] == DAYS[-6] and momentum["sessions"] == 6 and momentum["ranks"] == {} and momentum["house"]
    assert len(momentum["spark"]) == 7 and momentum["spark"][0] == 1.0
    assert board["benchmark"]["returns"]["1y"] is not None and board["index"][0]["value"] == 1.0
    page = visitor.get(f"/api/board/bot/{HOUSE}momentum").json()
    assert page["rules"][0] == "Looks at the 500 largest US companies." and page["bot"]["format"] == FORMAT
    assert [p["date"] for p in page["curve"]] == DAYS[-6:] and page["curve"][0]["index"] is not None


def test_visitors_see_the_house_and_members_see_the_members(app):
    send(app, "u1")
    clock = app.state.clock
    app.state.clock.when = at(DAYS[-1], 18)
    client(app).post("/api/board/refresh")
    visitor, ana = client(app).get("/api/board").json(), client(app, "u1").get("/api/board").json()
    assert visitor["rows"] == [] and visitor["entrants"] == 1 and not visitor["visible"] and visitor["house"]
    assert ana["visible"] and ana["rows"][0]["handle"] == "ana bots" and ana["rows"][0]["you"] and ana["rows"][0]["slug"] == "anabots"
    assert "user_id" not in ana["rows"][0] and "submitted_utc" not in ana["rows"][0]
    assert client(app).get("/api/board/bot/anabots").status_code == 401
    bea = client(app, "u2").get("/api/board/bot/anabots").json()
    assert bea["name"] == "Api bot" and "rules" not in bea and "bot" not in bea and not bea["you"]
    own = client(app, "u1").get("/api/board/bot/anabots").json()
    assert own["you"] and own["rules"][0] == "Looks at the 30 largest US companies."
    assert client(app, "u2").get("/api/board/bot/nobody").status_code == 404
    assert client(app, "u2").get("/api/board/bot/Not_A_Slug!").status_code == 404
    public = make(public=True)
    send(public, "u1")
    assert client(public).get("/api/board").json()["rows"][0]["handle"] == "ana bots"
    assert clock is app.state.clock


def test_a_visit_moves_the_members_bots_on(app):
    clock = app.state.clock
    clock.when = at(DAYS[-6], 12)
    send(app, "u1")
    clock.when = at(DAYS[-1], 18)
    page = client(app, "u1")
    assert page.get("/api/bots").json()["stale"] is True
    moved = page.post("/api/bots/refresh").json()
    assert moved["moved"] == 1 and moved["house"] == 0  # the house bots start now, from the next close
    me = page.get("/api/bots").json()["you"]
    assert me["since"] == DAYS[-6] and me["sessions"] == 6 and me["ranks"]["1w"] == 1
    row = page.get("/api/board").json()["rows"][0]
    assert len(row["spark"]) == 7 and row["returns"]["1w"] == pytest.approx(me["returns"]["1w"])


def test_the_kit_comes_with_a_key_pointing_here(app):
    page = client(app, "u1")
    got = page.post("/api/bots/kit")
    assert got.status_code == 200 and got.headers["content-type"] == "application/zip"
    files = zipfile.ZipFile(io.BytesIO(got.content))
    names = set(files.namelist())
    assert {"markethub-bot/AGENTS.md", "markethub-bot/CLAUDE.md", "markethub-bot/SPEC.md", "markethub-bot/tools/mh.py",
            "markethub-bot/.claude/skills/build-bot/SKILL.md", "markethub-bot/examples/momentum.json", "markethub-bot/.env"} <= names
    env = files.read("markethub-bot/.env").decode()
    assert "MARKETHUB_URL=http://testserver" in env
    assert all("{{SITE}}" not in files.read(n).decode() for n in names if not n.endswith("/"))
    key = env.split("MARKETHUB_BOT_KEY=")[1].strip()
    agent = TestClient(app)
    assert agent.get("/api/bot", headers={"authorization": f"Bearer {key}"}).json() == {"bot": None, "name": ""}


def test_the_member_routes_need_market_hubs_session(app):
    visitor = client(app)
    got = visitor.get("/api/bots")
    assert got.status_code == 401 and got.json()["signin"].startswith(f"{HUB}/signin/?next=")
    assert visitor.post("/api/bots/kit").status_code == 401
    assert TestClient(app).post("/api/bots/key").status_code == 403  # no Origin: refused before anything
    assert TestClient(app).post("/api/board/refresh").status_code == 403


def test_the_agent_routes_take_the_key_and_never_the_cookie(app):
    page = client(app, "u1")
    assert page.post("/api/bot/check", json={"bot": BOT}).status_code == 401  # signed in, but no key
    key = page.post("/api/bots/key").json()["key"]
    agent, with_key = TestClient(app), {"authorization": f"Bearer {key}"}
    assert agent.get("/api/bot/spec").json()["format"] == FORMAT
    ok = agent.post("/api/bot/check", json={"bot": BOT}, headers=with_key).json()
    assert ok["ok"] and ok["universe"] == 30
    bad = agent.post("/api/bot/check", json={"bot": {**BOT, "hold": 99, "extra": 1}}, headers=with_key)
    assert bad.status_code == 400 and len(bad.json()["problems"]) == 2
    test = agent.post("/api/bot/backtest", json={"bot": BOT, "years": 2}, headers=with_key).json()
    assert test["sessions"] == 504 and test["holdings"]
    assert "Pick a name" in agent.put("/api/bot", json={"bot": BOT}, headers=with_key).json()["detail"]
    assert "Someone else" in agent.put("/api/bot", json={"bot": BOT, "handle": "Cara"}, headers=with_key).json()["detail"]
    sent = agent.put("/api/bot", json={"bot": BOT, "handle": "ana bots"}, headers=with_key).json()
    assert sent["name"] == "Api bot" and sent["handle"] == "ana bots" and sent["since"] is None
    newer = page.post("/api/bots/key").json()["key"]
    assert agent.get("/api/bot", headers=with_key).status_code == 401
    assert page.delete("/api/bots/key").json() == {"revoked": True}
    assert agent.get("/api/bot", headers={"authorization": f"Bearer {newer}"}).status_code == 401


def test_a_member_who_shows_under_a_name_in_the_community_keeps_it(app):
    page = client(app, "u9")
    key = page.post("/api/bots/key").json()["key"]
    sent = TestClient(app).put("/api/bot", json={"bot": BOT}, headers={"authorization": f"Bearer {key}"}).json()
    assert sent["handle"] == "cara"


def test_withdrawing(app):
    send(app, "u1")
    page = client(app, "u1")
    assert page.get("/api/bots/mine").json()["bot"]["handle"] == "ana bots"
    assert page.delete("/api/bots/mine").json() == {"withdrawn": True} and app.state.store.bots == {}
    assert page.get("/api/bots/mine").json()["bot"] is None


def test_a_local_run_is_one_local_member_unless_it_asks_to_be_a_visitor():
    app = make(hub=None)
    assert client(app).get("/api/me").json()["user"]["name"] == "Local member"
    assert client(app).get("/api/me?visitor=1").json()["user"] is None
    assert client(app).get("/api/bots").status_code == 200
