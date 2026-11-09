"""The service: the site and the API, from one origin.

Open to everyone:
    GET    /api/health
    GET    /api/me                  who is signed in to Market Hub, and where to sign in
    GET    /api/board               the board: the members' bots (to members, or to all when the
                                    board is public) and the index
    POST   /api/board/refresh       move the bots on to the last close, if they are behind
    GET    /api/board/bot/{slug}    a bot's page: its curve against the index, what it holds
The member's own, with Market Hub's session cookie or, from the Bot League phone app, the hub's app token
(Authorization: Bearer <token>, hubauth.py) (the same routes as the portal's Community):
    GET    /api/bots                the board as the portal gives it, with the member's bot and key
    POST   /api/bots/refresh        as /api/board/refresh
    POST   /api/bots/kit            a new key, and the kit with it in its .env (a zip)
    POST   /api/bots/key            a new key, shown once      DELETE /api/bots/key  take it back
    DELETE /api/bots/mine           withdraw the member's bot
    GET    /api/bots/mine           what is kept of the member's bot and key
    POST   /api/bots/preview        {bot}: its rules in words and what they would hold at the last close
    PUT    /api/bots/mine/rules     {bot}: new rules, from the next close, keeping the record (once a day)
    PUT    /api/bots/mine/name      {name, about?}: rename the bot, at once, keeping the record
    POST   /api/bots/mine/switch    {action, ticker?, min_weight?}: pause, resume, exclude, include, pin (always hold,
                                    at least min_weight of it) or unpin, from the next close
    DELETE /api/bots/mine/pending   drop everything waiting for the next close
    GET    /api/bots/chat           whether the chat is on, and the member's messages left today
    POST   /api/bots/mine/chat      {message, history?}: a change of rules proposed by Claude, to confirm
    POST   /api/bots/draft/chat     {message, history?, draft?, backtest?}: building a bot with Claude, from scratch
    POST   /api/bots/backtest       {bot, years}: what a draft would have done, for its owner
    PUT    /api/bots/mine           {bot}: send in the bot made on the page, in place of the one there was
The routes of the member's agent, with the bot key (Authorization: Bearer mhb_...), never the cookie:
    GET    /api/bot/spec            what a bot can be (no key needed)
    POST   /api/bot/check           {bot}: whether it is a bot, and its rules in words
    POST   /api/bot/backtest        {bot, years}: what it would have done, for its owner
    PUT    /api/bot                 {bot}: send it in, in place of the one there was
    PATCH  /api/bot                 {bot}: change its rules from the next close, keeping its record
    GET    /api/bot                 the member's bot: returns, rank, holdings, rules

Everything else is the static site, when BOTLEAGUE_STATIC_DIR points at its build.
"""

from __future__ import annotations

import logging
import os
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Callable

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles

from . import engine, es, why
from .chat import Chat, ChatOff, FileLedger, FirestoreLedger, MemoryLedger, Scripted
from .config import (BOT_BACKTESTS_PER_USER_PER_HOUR, BOT_SUBMISSIONS_PER_USER_PER_DAY, BOT_UNIVERSE_MAX, CHAT_ENABLED, PER_IP_PER_HOUR, PUBLIC_BOARD,
                     SAMPLE, SWITCHES_PER_USER_PER_DAY)
from .engine import BotStore, Bots
from .hubauth import Hub
from .hubauth import settings as hub_settings
from .league import League, Remembering, cancel_pending
from .market import Directory, MarketUnavailable, Sample, Yahoo

log = logging.getLogger("botleague.api")

UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
SLUG = re.compile(r"[a-z0-9\-]{1,60}")


class RateLimiter:
    def __init__(self, limit: int, window: float = 3600.0):
        self.limit, self.window = limit, window
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, who: str) -> bool:
        now = time.monotonic()
        with self._lock:
            calls = self._calls[who]
            while calls and now - calls[0] > self.window:
                calls.popleft()
            if len(calls) >= self.limit:
                return False
            calls.append(now)
            return True


def _client_address(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    return forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def bearer(header: str | None) -> str | None:
    scheme, _, value = (header or "").partition(" ")
    return value.strip() or None if scheme.lower() == "bearer" else None


def _firestore() -> bool:
    return os.environ.get("MARKETHUB_FIRESTORE") == "1"


def owned(out, lang: str):
    """The member's own bot as their page gets it: its rules in the page's language, and why each of
    its moves was made with every figure behind it (theirs alone)."""
    return why.page(es.rules(out, lang), lang, full=True)


def create_app(bot_store: BotStore | None = None,
               closes: Callable[[set[str]], dict] | None = None, largest: Callable[[int], list[str]] | None = None,
               hub: tuple[str, str] | None | bool = True, public: bool | None = None, sample: bool | None = None,
               clock: Callable[[], datetime] | None = None, static_dir: str | None = None, chat: Chat | None = None) -> FastAPI:
    """App factory. Tests pass their own pieces, so they need no network and no Google.

    ``hub`` is (hub URL, hub session secret); by default it comes from HUB_URL and
    HUB_SESSION_SECRET, and None is a local run where everyone is one local member."""
    logging.basicConfig(level=logging.INFO)
    for noisy in ("httpx", "httpcore", "yfinance"):
        logging.getLogger(noisy).setLevel(logging.CRITICAL if noisy == "yfinance" else logging.WARNING)
    app = FastAPI(title="Bot League", docs_url=None, redoc_url=None, openapi_url=None)

    sample = SAMPLE if sample is None else sample
    named: Callable[[int], list[tuple[str, str]]] | None = None  # the largest companies with their names
    if closes is None or largest is None:
        if sample:
            source = Sample()
            closes, largest, named = closes or source.closes, largest or source.largest, source.names if largest is None else None
        else:
            yahoo, directory = Yahoo(), Directory()
            closes, largest, named = closes or yahoo.closes, largest or directory.largest, directory.names if largest is None else None
    store = Remembering(bot_store or engine.default_bots())
    bots = Bots(store, closes, largest, sample=False, now=clock)
    league = League(bots, store, public=PUBLIC_BOARD if public is None else public, sample=sample, now=clock)
    gate = Hub(hub_settings() if hub is True else hub or None)

    limiter = RateLimiter(PER_IP_PER_HOUR)
    backtesting = RateLimiter(BOT_BACKTESTS_PER_USER_PER_HOUR)
    sending = RateLimiter(BOT_SUBMISSIONS_PER_USER_PER_DAY, window=86400.0)
    changing = RateLimiter(SWITCHES_PER_USER_PER_DAY, window=86400.0)
    if chat is None and sample and not CHAT_ENABLED:
        # `make demo`: a scripted Claude that answers a few instructions by rule and spends nothing.
        chat = Chat(MemoryLedger(), client=Scripted, enabled=True, now=clock)
    chat = chat or Chat(FirestoreLedger() if _firestore() else FileLedger(), now=clock)
    origins = [o.strip() for o in os.environ.get("BOTLEAGUE_ALLOWED_ORIGINS", "").split(",") if o.strip()]

    def agent_route(request: Request) -> bool:
        """The routes of a member's agent: they take the bot key and never read the cookie, so no
        foreign page can use a browser's cookie on them."""
        return request.url.path == "/api/bot" or request.url.path.startswith("/api/bot/")

    def open_route(request: Request) -> bool:
        """Asking for the bots to be moved on reads no cookie and changes nothing of anyone's: it
        is open to any caller, at the competition's pace (the portal asks it from its server)."""
        return request.url.path == "/api/board/refresh"

    @app.middleware("http")
    async def same_site_writes(request: Request, call_next):
        """Writes must come from this site: a foreign page can neither send the hub's cookie on a
        POST (SameSite=Lax) nor pass this check. The agent's writes carry its key instead, and the
        phone app's the hub's app token (hubauth.py)."""
        if (request.method in UNSAFE and request.url.path.startswith("/api/") and not agent_route(request) and not open_route(request)
                and not gate.from_app(request)):
            origin = request.headers.get("origin")
            host = request.headers.get("x-forwarded-host") or request.headers.get("host", "")
            if origin not in {f"{request.url.scheme}://{request.url.netloc}", f"https://{host}", *origins}:
                return JSONResponse({"detail": es.say("Cross-site request refused.", es.lang_of(request))}, status_code=403)
        response = await call_next(request)
        if request.url.path.startswith("/api/") and "cache-control" not in response.headers:
            response.headers["Cache-Control"] = "no-store"
        return response

    if origins:
        app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
                           allow_headers=["*"], allow_credentials=True)

    def allow(request: Request) -> None:
        if not limiter.allow(_client_address(request)):
            raise HTTPException(429, "Too many requests from this address. Try again later.")

    def member(request: Request) -> dict:
        user = gate.user(request)
        if not user:
            raise HTTPException(401, detail={"detail": "Sign in with your account on The Market Hub.", "signin": gate.signin_url(request)})
        return user

    def refused(exc: engine.Refused, request: Request) -> JSONResponse:
        """A bot or a request that cannot be taken: every reason, in the page's language."""
        problems = es.problems(exc.problems, es.lang_of(request))
        return JSONResponse({"detail": " ".join(problems), "problems": problems}, status_code=400)

    def market_down(exc: MarketUnavailable):
        raise HTTPException(503, str(exc)) from None

    @app.exception_handler(HTTPException)
    async def flat_detail(request: Request, exc: HTTPException):
        body = dict(exc.detail) if isinstance(exc.detail, dict) else {"detail": exc.detail}
        body["detail"] = es.say(body.get("detail"), es.lang_of(request))
        return JSONResponse(body, status_code=exc.status_code, headers={"Cache-Control": "no-store"})

    # --- Open to everyone ---

    @app.get("/api/health")
    def health() -> dict:
        return {"ok": True}

    @app.get("/api/me")
    def me(request: Request) -> dict:
        user = gate.user(request)
        return {"user": {"name": user.get("name") or "", "picture": user.get("picture") or ""} if user else None,
                "signin": gate.signin_url(request, "/me/"), "hub": gate.url, "local": gate.secret is None}

    @app.get("/api/board")
    def board(request: Request) -> dict:
        allow(request)
        out = league.board(gate.user(request))
        return {**out, "periods": es.periods(out["periods"], es.lang_of(request))}

    @app.post("/api/board/refresh")
    def refresh_board(request: Request) -> dict:
        """A visit that finds the bots behind the last close asks for this: not more often than the
        competition allows, and not while another refresh runs."""
        allow(request)
        return league.refresh()

    @app.get("/api/board/bot/{slug}")
    def bot_page(request: Request, slug: str) -> dict:
        allow(request)
        user = gate.user(request)
        page = league.bot(slug, user, es.lang_of(request)) if SLUG.fullmatch(slug) else None
        if not page:
            if not league.visible(user):
                raise HTTPException(401, detail={"detail": "Members' bots are seen by members: sign in with your account on The Market Hub.",
                                                 "signin": gate.signin_url(request)})
            raise HTTPException(404, "There is no such bot.")
        return es.rules(page, es.lang_of(request))

    # --- The member's own ---

    @app.get("/api/bots")
    def overview(request: Request) -> dict:
        user = member(request)
        allow(request)
        # The bot is shown under the first name of the account the member signed in with.
        bots.sync_player(user["id"], user.get("name"))
        lang = es.lang_of(request)
        out = owned(bots.overview(user["id"]), lang)
        return {**out, "periods": es.periods(out["periods"], lang)}

    @app.post("/api/bots/refresh")
    def refresh_bots(request: Request) -> dict:
        member(request)
        allow(request)
        return league.refresh()

    @app.post("/api/bots/kit")
    def kit(request: Request) -> Response:
        user = member(request)
        allow(request)
        key = bots.issue_key(user["id"], user.get("name"))
        log.info("bot kit downloaded with a new key")
        return Response(engine.kit(str(request.base_url).rstrip("/"), key), media_type="application/zip",
                        headers={"Content-Disposition": 'attachment; filename="markethub-bot.zip"'})

    @app.post("/api/bots/key")
    def new_key(request: Request) -> dict:
        user = member(request)
        allow(request)
        log.info("bot key issued")
        return {"key": bots.issue_key(user["id"], user.get("name")), "status": bots.key_status(user["id"])}

    @app.delete("/api/bots/key")
    def drop_key(request: Request) -> dict:
        bots.revoke_key(member(request)["id"])
        return {"revoked": True}

    @app.delete("/api/bots/mine")
    def withdraw(request: Request) -> dict:
        bots.withdraw(member(request)["id"])
        log.info("bot withdrawn")
        return {"withdrawn": True}

    @app.get("/api/bots/mine")
    def kept(request: Request) -> dict:
        return bots.kept(member(request)["id"])

    def changes_allowed(user_id: str) -> None:
        if not changing.allow(user_id):
            raise HTTPException(429, f"That is {SWITCHES_PER_USER_PER_DAY} changes today. Try again tomorrow.")

    @app.post("/api/bots/preview")
    def preview(request: Request, bot: dict = Body(embed=True)):
        user_id = member(request)["id"]
        allow(request)
        if not backtesting.allow(user_id):
            raise HTTPException(429, f"That is {BOT_BACKTESTS_PER_USER_PER_HOUR} previews in an hour. Try again later.")
        try:
            return es.rules(bots.preview(bot), es.lang_of(request))
        except engine.Refused as exc:
            return refused(exc, request)
        except MarketUnavailable as exc:
            market_down(exc)

    @app.put("/api/bots/mine/rules")
    def new_rules(request: Request, bot: dict = Body(embed=True)):
        user_id = member(request)["id"]
        allow(request)
        changes_allowed(user_id)
        try:
            mine = bots.edit(user_id, bot)
        except engine.Refused as exc:
            return refused(exc, request)
        except MarketUnavailable as exc:
            market_down(exc)
        log.info("bot rules changed")
        return owned(mine, es.lang_of(request))

    @app.put("/api/bots/mine/name")
    def rename(request: Request, name: str = Body(embed=True, max_length=200), about: str | None = Body(None, embed=True, max_length=1000)):
        user_id = member(request)["id"]
        allow(request)
        changes_allowed(user_id)
        try:
            mine = bots.rename(user_id, name, about)
        except engine.Refused as exc:
            return refused(exc, request)
        log.info("bot renamed")
        return owned(mine, es.lang_of(request))

    @app.post("/api/bots/mine/switch")
    def switch(request: Request, action: str = Body(embed=True, max_length=10), ticker: str | None = Body(None, embed=True, max_length=12),
               min_weight: float | None = Body(None, embed=True, ge=0, le=1)):
        user_id = member(request)["id"]
        allow(request)
        changes_allowed(user_id)
        try:
            mine = bots.switch(user_id, action, ticker, min_weight)
        except engine.Refused as exc:
            return refused(exc, request)
        except MarketUnavailable as exc:
            market_down(exc)
        log.info("bot switch: %s", action if action in ("pause", "resume", "exclude", "include", "pin", "unpin") else "?")
        return owned(mine, es.lang_of(request))

    @app.delete("/api/bots/mine/pending")
    def cancel(request: Request):
        user_id = member(request)["id"]
        allow(request)
        changes_allowed(user_id)
        try:
            mine = cancel_pending(bots, user_id)
        except engine.Refused as exc:
            return refused(exc, request)
        except MarketUnavailable as exc:
            market_down(exc)
        log.info("bot change cancelled")
        return owned(mine, es.lang_of(request))

    def companies() -> list[tuple[str, str]] | None:
        """The companies a bot can choose among, for Claude to pick a theme's from: none if the list
        cannot be read now (the chat still answers)."""
        try:
            return named(BOT_UNIVERSE_MAX) if named else [(t, "") for t in largest(BOT_UNIVERSE_MAX)]
        except MarketUnavailable:
            return None

    def checked(raw) -> dict:
        """A bot Claude proposed, checked as one sent in is: its rules and its universe."""
        return bots.check(raw)["bot"]

    def spoken(got: dict, lang: str, user_id: str) -> dict:
        """The chat's answer for the page: the problems the code found, in the page's language."""
        if got.get("problems"):
            got["problems"] = es.problems(got["problems"], lang)
        return {**got, "left": chat.left(user_id)}

    @app.get("/api/bots/chat")
    def chat_status(request: Request) -> dict:
        return chat.status(member(request)["id"])

    # Creating a bot on the page, by talking to Claude: as the kit does with the member's own agent.

    @app.post("/api/bots/draft/chat")
    def draft_chat(request: Request, message: str = Body(embed=True, max_length=2000), history: list = Body([], embed=True),
                   draft: dict | None = Body(None, embed=True), backtest: dict | None = Body(None, embed=True)):
        user_id = member(request)["id"]
        allow(request)
        lang = es.lang_of(request)
        try:
            current = engine.check(draft) if draft else None
            got = chat.ask(user_id, current, message, history, mode="create", backtest=backtest, checker=checked, lang=lang,
                           companies=companies())
        except engine.Refused as exc:
            return refused(exc, request)
        except ChatOff as exc:
            raise HTTPException(503, str(exc)) from None
        except MarketUnavailable as exc:
            market_down(exc)
        if got.get("proposal"):
            # Its rules in words now; what it would hold is asked for by the page next (/api/bots/preview), so
            # the reply is not kept waiting while the closes of its companies are read.
            try:
                got["rules"] = bots.check(got["proposal"])["rules"]
            except MarketUnavailable:
                got["rules"] = engine.describe(got["proposal"])
            if lang == "es":
                got["rules"] = engine.describe(got["proposal"], lang=lang)
        return spoken(got, lang, user_id)

    @app.post("/api/bots/backtest")
    def page_backtest(request: Request, bot: dict = Body(embed=True), years: int = Body(1, embed=True)):
        """The agent's backtest, for the member's own draft on the page: a simulation of the past."""
        user_id = member(request)["id"]
        allow(request)
        if not backtesting.allow(user_id):
            raise HTTPException(429, f"That is {BOT_BACKTESTS_PER_USER_PER_HOUR} backtests and previews in an hour. Try again later.")
        try:
            out = bots.backtest(bot, years)
        except engine.Refused as exc:
            return refused(exc, request)
        except MarketUnavailable as exc:
            market_down(exc)
        lang = es.lang_of(request)
        if lang == "es":
            out.update(rules=engine.describe(engine.check(bot), lang=lang), notes=[es.say(n, lang) for n in out["notes"]])
        return out

    @app.put("/api/bots/mine")
    def send_in(request: Request, bot: dict = Body(embed=True)):
        """Send in the bot made on the page, as the agent does with its key: it replaces any bot the
        member had, and its record starts at the next close."""
        user = member(request)
        allow(request)
        if not sending.allow(user["id"]):
            raise HTTPException(429, f"That is {BOT_SUBMISSIONS_PER_USER_PER_DAY} bots sent in a day. Try again tomorrow.")
        try:
            mine = bots.submit(user["id"], bot, user.get("name"))
        except engine.Refused as exc:
            return refused(exc, request)
        except MarketUnavailable as exc:
            market_down(exc)
        log.info("bot sent in from the page")
        return owned(mine, es.lang_of(request))

    @app.post("/api/bots/mine/chat")
    def chat_message(request: Request, message: str = Body(embed=True, max_length=2000), history: list = Body([], embed=True)):
        user_id = member(request)["id"]
        allow(request)
        doc = bots.store.get(user_id)
        if not doc:
            raise HTTPException(400, "There is no bot to change: send one in first.")
        current = {**doc, **(doc.get("pending") or {})}["spec"]
        lang = es.lang_of(request)
        try:
            got = chat.ask(user_id, current, message, history, checker=checked, lang=lang, companies=companies())
        except engine.Refused as exc:
            return refused(exc, request)
        except ChatOff as exc:
            raise HTTPException(503, str(exc)) from None
        except MarketUnavailable as exc:
            market_down(exc)
        if got.get("proposal"):
            got["rules"] = engine.describe(got["proposal"], lang=lang)
        return spoken(got, lang, user_id)

    # --- The member's agent ---

    def agent(request: Request) -> str:
        """The member a bot key belongs to. The cookie is never looked at here."""
        allow(request)
        user_id = bots.who(bearer(request.headers.get("authorization")))
        if not user_id:
            raise HTTPException(401, "No key, or not a good one: make one on your page of Bot League (/me/) and put it in .env.")
        return user_id

    @app.get("/api/bot/spec")
    def spec(request: Request) -> dict:
        allow(request)
        # The kit's agent sends no language and gets the engine's own; the Rules page asks in its own.
        return es.spec(es.lang_of(request))

    @app.post("/api/bot/check")
    def check(request: Request, bot: dict = Body(embed=True)):
        agent(request)
        try:
            return bots.check(bot)
        except engine.Refused as exc:
            return refused(exc, request)
        except MarketUnavailable as exc:
            market_down(exc)

    @app.post("/api/bot/backtest")
    def backtest(request: Request, bot: dict = Body(embed=True), years: int = Body(1, embed=True)):
        user_id = agent(request)
        if not backtesting.allow(user_id):
            raise HTTPException(429, f"That is {BOT_BACKTESTS_PER_USER_PER_HOUR} backtests in an hour. Try again later.")
        try:
            return bots.backtest(bot, years)
        except engine.Refused as exc:
            return refused(exc, request)
        except MarketUnavailable as exc:
            market_down(exc)

    @app.put("/api/bot")
    def submit(request: Request, bot: dict = Body(embed=True)):
        user_id = agent(request)
        if not sending.allow(user_id):
            raise HTTPException(429, f"That is {BOT_SUBMISSIONS_PER_USER_PER_DAY} bots sent in a day. Try again tomorrow.")
        try:
            mine = bots.submit(user_id, bot)
        except engine.Refused as exc:
            return refused(exc, request)
        except MarketUnavailable as exc:
            market_down(exc)
        log.info("bot sent in")
        return mine

    @app.patch("/api/bot")
    def change_bot(request: Request, bot: dict = Body(embed=True)):
        user_id = agent(request)
        changes_allowed(user_id)
        try:
            mine = bots.edit(user_id, bot)
        except engine.Refused as exc:
            return refused(exc, request)
        except MarketUnavailable as exc:
            market_down(exc)
        log.info("bot rules changed by the agent")
        return mine

    @app.get("/api/bot")
    def my_bot(request: Request) -> dict:
        user_id = agent(request)
        return {"bot": bots.mine(user_id), "name": bots.overview(user_id)["name"]}

    app.state.bots, app.state.league, app.state.chat = bots, league, chat
    static_dir = static_dir or os.environ.get("BOTLEAGUE_STATIC_DIR", "")
    if static_dir and Path(static_dir).is_dir():
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="site")
    return app
