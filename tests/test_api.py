"""The site's routes: the board and the bots' pages as visitors and members see them, the member's
own routes with Market Hub's cookie, and the agent's with its key."""

import io
import json
import zipfile
from datetime import date

import pytest
from fastapi.testclient import TestClient

from botleague.api import create_app
from botleague.chat import Chat, MemoryLedger
from botleague.engine import FORMAT, MemoryBots
from botleague.market import SAMPLE_TICKERS
from conftest import HUB, ORIGIN, SECRET, Clock, at, hub_cookie, sessions, walk

DAYS = sessions(700, date(2023, 11, 6))
BOT = {"format": FORMAT, "name": "Api bot", "about": "Momentum, monthly.", "universe": {"largest": 30},
       "score": [{"factor": "momentum", "days": 126, "skip": 21, "weight": 1}], "hold": 8, "rebalance": "monthly"}


def make(public=False, hub=(HUB, SECRET), chat=None):
    clock = Clock(at(DAYS[-1], 18))
    store = MemoryBots()
    app = create_app(bot_store=store, closes=lambda ts: {t: walk(t, DAYS) for t in ts},
                     largest=lambda n: list(SAMPLE_TICKERS[:n]), hub=hub, public=public, clock=clock,
                     chat=chat or Chat(MemoryLedger(), enabled=False, now=clock))
    app.state.clock, app.state.store = clock, store
    return app


@pytest.fixture
def app():
    return make()


def client(app, user_id: str | None = None, name: str = "Ana Torres") -> TestClient:
    c = TestClient(app)
    c.headers.update({"origin": ORIGIN})
    if user_id:
        c.cookies.set("mh_session", hub_cookie(user_id, name))
    return c


def send(app, user_id: str, bot=BOT, name: str = "Ana Torres") -> str:
    page = client(app, user_id, name)
    key = page.post("/api/bots/key").json()["key"]
    got = TestClient(app).put("/api/bot", json={"bot": bot}, headers={"authorization": f"Bearer {key}"})
    assert got.status_code == 200, got.json()
    return key


def slug(app, user_id: str) -> str:
    return app.state.store.get(user_id)["public_id"]


def test_who_is_signed_in(app):
    assert client(app).get("/api/me").json()["user"] is None
    me = client(app).get("/api/me").json()
    assert me["signin"] == f"{HUB}/signin/?next=https%3A%2F%2Ftestserver%2Fme%2F" and not me["local"]
    assert client(app, "u1").get("/api/me").json()["user"]["name"] == "Ana Torres"
    forged = TestClient(app)
    forged.cookies.set("mh_session", hub_cookie("u1", secret="another"))
    assert forged.get("/api/me").json()["user"] is None


def test_the_board_is_the_members_bots_and_the_index(app):
    clock = app.state.clock
    clock.when = at(DAYS[-6], 12)
    send(app, "u1")
    clock.when = at(DAYS[-1], 18)
    visitor = client(app)
    assert visitor.get("/api/board").json()["stale"] is True
    assert visitor.post("/api/board/refresh").json()["moved"] == 1
    board = client(app, "u2").get("/api/board").json()
    assert board["stale"] is False and board["as_of"] == DAYS[-1] and "house" not in board
    row = board["rows"][0]
    assert row["handle"] == "Ana" and row["slug"] == slug(app, "u1") and row["since"] == DAYS[-6] and len(row["spark"]) == 7
    assert board["benchmark"]["returns"]["1y"] is not None and board["index"][0]["value"] == 1.0
    page = client(app, "u2").get(f"/api/board/bot/{slug(app, 'u1')}").json()
    assert [p["date"] for p in page["curve"]] == DAYS[-6:] and page["curve"][0]["index"] is not None


def test_visitors_and_members_and_the_bots_page_by_its_id(app):
    send(app, "u1")
    send(app, "u2", name="Ana López")  # two players with the same first name
    visitor, ana = client(app).get("/api/board").json(), client(app, "u1").get("/api/board").json()
    assert visitor["rows"] == [] and visitor["entrants"] == 2 and not visitor["visible"]
    assert ana["visible"] and {r["handle"] for r in ana["rows"]} == {"Ana"} and len({r["slug"] for r in ana["rows"]}) == 2
    mine = next(r for r in ana["rows"] if r["you"])
    assert mine["slug"] == slug(app, "u1") and "user_id" not in mine and "submitted_utc" not in mine
    assert client(app).get(f"/api/board/bot/{slug(app, 'u1')}").status_code == 401
    other = client(app, "u2").get(f"/api/board/bot/{slug(app, 'u1')}").json()
    assert other["name"] == "Api bot" and "rules" not in other and "bot" not in other and not other["you"]
    own = client(app, "u1").get(f"/api/board/bot/{slug(app, 'u1')}").json()
    assert own["you"] and own["rules"][0] == "Looks at the 30 largest US companies."
    assert client(app, "u2").get("/api/board/bot/0000000000").status_code == 404
    assert client(app, "u2").get("/api/board/bot/Not_A_Slug!").status_code == 404
    public = make(public=True)
    send(public, "u1")
    assert client(public).get("/api/board").json()["rows"][0]["handle"] == "Ana"


def test_a_visit_moves_the_members_bots_on(app):
    clock = app.state.clock
    clock.when = at(DAYS[-6], 12)
    send(app, "u1")
    clock.when = at(DAYS[-1], 18)
    page = client(app, "u1")
    assert page.get("/api/bots").json()["stale"] is True
    assert page.post("/api/bots/refresh").json()["moved"] == 1
    me = page.get("/api/bots").json()["you"]
    assert me["since"] == DAYS[-6] and me["sessions"] == 6 and me["ranks"]["1w"] == 1
    row = page.get("/api/board").json()["rows"][0]
    assert len(row["spark"]) == 7 and row["returns"]["1w"] == pytest.approx(me["returns"]["1w"])


def test_the_player_follows_the_account_and_the_old_bots_move_over(app):
    send(app, "u1")
    store = app.state.store
    old = store.get("u1")
    old.pop("public_id")
    store.put({**old, "handle": "alejandros portfolio", "handle_key": "alejandrosportfolio"})  # a bot from before
    assert client(app).post("/api/board/refresh").status_code == 200 and store.get("u1")["public_id"]
    page = client(app, "u1", name="Alejandro Rodríguez Álvarez")
    assert page.get("/api/bots").json()["you"]["handle"] == "Alejandro"
    assert store.get("u1")["handle"] == "Alejandro" and "Rodríguez" not in json.dumps(store.get("u1"))


def test_renaming_from_the_page(app):
    send(app, "u1")
    page = client(app, "u1")
    got = page.put("/api/bots/mine/name", json={"name": "Momentum dip buyer", "about": "Buys the dips of the strongest."}).json()
    assert got["name"] == "Momentum dip buyer" and got["about"] == "Buys the dips of the strongest."
    assert page.put("/api/bots/mine/name", json={"name": "x"}).status_code == 400
    assert page.put("/api/bots/mine/rules", json={"bot": {**BOT, "hold": 5}}).status_code == 200  # renaming was not the day's change
    assert client(app, "u2").put("/api/bots/mine/name", json={"name": "Nope"}).status_code == 400  # no bot


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
    # Asking for the bots to be moved on is open: the portal asks it from its server, with no Origin.
    assert TestClient(app).post("/api/board/refresh").status_code == 200


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
    # A name sent with the bot is not taken: the player is the account the key was made in.
    sent = agent.put("/api/bot", json={"bot": BOT, "handle": "someone else"}, headers=with_key).json()
    assert sent["name"] == "Api bot" and sent["handle"] == "Ana" and sent["since"] is None
    newer = page.post("/api/bots/key").json()["key"]
    assert agent.get("/api/bot", headers=with_key).status_code == 401
    assert page.delete("/api/bots/key").json() == {"revoked": True}
    assert agent.get("/api/bot", headers={"authorization": f"Bearer {newer}"}).status_code == 401


def test_withdrawing(app):
    send(app, "u1")
    page = client(app, "u1")
    assert page.get("/api/bots/mine").json()["bot"]["handle"] == "Ana"
    assert page.delete("/api/bots/mine").json() == {"withdrawn": True} and app.state.store.bots == {}
    assert page.get("/api/bots/mine").json()["bot"] is None


def test_a_local_run_is_one_local_member_unless_it_asks_to_be_a_visitor():
    app = make(hub=None)
    assert client(app).get("/api/me").json()["user"]["name"] == "Local member"
    assert client(app).get("/api/me?visitor=1").json()["user"] is None
    assert client(app).get("/api/bots").status_code == 200


# --- What a bot does, and changing it from the page -------------------------------------------------


def test_a_bot_that_has_not_started_says_when_it_starts_and_what_it_would_hold(app):
    send(app, "u1")
    page = client(app, "u2").get(f"/api/board/bot/{slug(app, 'u1')}").json()
    assert page["starts"] == "2026-07-13" and page["log"] == [] and page["versions"] == [] and not page["paused"]  # sent in after the close of a Friday
    assert page["preview"]["as_of"] == DAYS[-1] and len(page["preview"]["weights"]) == 8


def test_a_bots_page_shows_what_it_did_and_when_its_rules_changed(app):
    clock = app.state.clock
    clock.when = at(DAYS[-30], 12)
    key = send(app, "u1")
    clock.when = at(DAYS[-20], 18)
    client(app).post("/api/board/refresh")
    owner = client(app, "u1")
    clock.when = at(DAYS[-19], 10)
    got = owner.put("/api/bots/mine/rules", json={"bot": {**BOT, "hold": 4}}).json()
    assert got["pending"]["what"] == ["rules"] and got["pending"]["bot"]["hold"] == 4
    assert owner.put("/api/bots/mine/rules", json={"bot": {**BOT, "hold": 5}}).status_code == 400  # once a day
    assert owner.post("/api/bots/mine/switch", json={"action": "pause"}).json()["pending"]["paused"]
    assert owner.post("/api/bots/mine/switch", json={"action": "jump"}).status_code == 400
    clock.when = at(DAYS[-1], 18)
    app.state.bots.refresh(force=True)
    page = client(app, "u2").get(f"/api/board/bot/{slug(app, 'u1')}").json()
    assert page["paused"] and page["versions"] == [{"from": DAYS[-19], "what": ["rules", "paused"]}]
    assert page["log"][0]["sold"] and page["log"][-1]["bought"] and "after" in page["log"][0]
    assert "rules" not in page and "bot" not in page and page["starts"] is None and page["preview"] is None
    # The agent changes it too, keeping the record (a new day).
    clock.when = at(DAYS[-1], 19)
    agent = TestClient(app)
    assert agent.patch("/api/bot", json={"bot": {**BOT, "hold": 6}}, headers={"authorization": f"Bearer {key}"}).json()["pending"]["bot"]["hold"] == 6


def test_a_preview_of_rules_before_applying_them(app):
    owner = client(app, "u1")
    got = owner.post("/api/bots/preview", json={"bot": {**BOT, "hold": 3}}).json()
    assert got["rules"][0] == "Looks at the 30 largest US companies." and len(got["holds"]["weights"]) == 3
    assert owner.post("/api/bots/preview", json={"bot": {**BOT, "hold": 0}}).status_code == 400
    assert client(app).post("/api/bots/preview", json={"bot": BOT}).status_code == 401


class Claude:
    """Anthropic's API, as the chat calls it: it answers with what the test set."""

    def __init__(self, answer: dict):
        self.answer, self.calls = answer, []
        self.messages = self.beta = self
        self.beta.messages = self

    def create(self, **params):
        from types import SimpleNamespace as NS
        self.calls.append(params)
        return NS(stop_reason="end_turn", usage=NS(input_tokens=3000, output_tokens=800),
                  content=[NS(type="text", text=json.dumps(self.answer))])


def test_the_chat_is_off_until_switched_on(app):
    send(app, "u1")
    got = client(app, "u1").post("/api/bots/mine/chat", json={"message": "make it more defensive"})
    assert got.status_code == 503 and "not switched on" in got.json()["detail"]


def test_the_chat_proposes_rules_the_code_checks_and_counts_what_it_spends():
    claude = Claude({"reply": "Fewer stocks, and cash when the index falls.", "bot": json.dumps({**BOT, "hold": 5})})
    ledger = MemoryLedger()
    app = make(chat=Chat(ledger, client=lambda: claude, enabled=True, model="claude-haiku-5-5", per_member=2, daily_max=None, effort="high"))
    send(app, "u1")
    owner = client(app, "u1")
    got = owner.post("/api/bots/mine/chat", json={"message": "hold fewer", "history": [{"role": "assistant", "text": "hi"}, {"role": "user", "text": "x"}]}).json()
    assert got["proposal"]["hold"] == 5 and got["rules"][2].startswith("Holds the best 5") and got["reply"].startswith("Fewer")
    assert claude.calls[0]["messages"][0] == {"role": "user", "content": "x"} and '"hold": 8' in claude.calls[0]["messages"][-1]["content"]
    assert claude.calls[0]["model"] == "claude-haiku-5-5" and claude.calls[0]["output_config"]["effort"] == "high" and "fallbacks" not in claude.calls[0]
    assert ledger.get()["calls"] == 1 and ledger.get()["total_usd"] == pytest.approx((3000 * 0.10 + 800 * 0.50) / 1e6)
    claude.answer = {"reply": "Here.", "bot": json.dumps({**BOT, "hold": 999})}
    assert owner.post("/api/bots/mine/chat", json={"message": "hold all"}).json()["problems"]
    assert owner.post("/api/bots/mine/chat", json={"message": "again"}).status_code == 503  # two a day for this member
