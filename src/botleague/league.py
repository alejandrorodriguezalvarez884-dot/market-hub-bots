"""What Bot League adds to the competition: the board as the site shows it and each bot's own page.

The competition itself (the format, the paper engine, the members' bots and their keys) is
engine.py, the same as the portal's, on the same collections. This module only reads it.

On the board there are the members' bots and the S&P 500 as the line of reference (from the
closes the refresh keeps in bot_meta/board). Each bot is found by its random public id, and shown
under the first name of its owner's account.

The members' bots are seen by everyone while PUBLIC_BOARD is on (the default, and what Market
Hub's privacy page says), or by signed-in members alone when it is off. Rules are their owner's alone.

Bot League is the only service that moves the curves (refresh): the portal's Community section
reads the same documents and, when it finds them behind, asks this site to move them.

Until 2026-10-20 the site also ran six house bots, kept in bot_meta/house; the owner removed them,
and that document is no longer read or written.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable

from . import engine
from .config import BOT_UNIVERSE_MAX
from .engine import BELL, NEW_YORK, PERIODS, YEAR, Bots, activity, describe, returns
from .market import BENCHMARK

SPARK_POINTS = 64
LOG_SHOWN = 120  # rebalances on a bot's page


def start_day(submitted_utc: str) -> str:
    """The session whose close a bot sent in at this moment starts at (weekdays; holidays are not known)."""
    local = engine._when(submitted_utc).astimezone(NEW_YORK)
    day = local.date() if local.time() < BELL else local.date() + timedelta(days=1)
    while day.weekday() >= 5:
        day += timedelta(days=1)
    return day.isoformat()


def doings(doc: dict) -> dict:
    """What a bot has done, for everyone: its rebalances (what it bought, sold, raised and cut), when
    its rules changed (never what they became), whether it is paused, and, before its first close,
    when it starts and what its rules would hold at the last close."""
    started = bool(doc.get("curve"))
    return {"log": activity(doc.get("log") or [], LOG_SHOWN), "paused": bool(doc.get("paused")),
            "versions": [{"from": v.get("from"), "what": v.get("what")} for v in doc.get("versions") or []],
            "starts": None if started or not doc.get("submitted_utc") else start_day(doc["submitted_utc"]),
            "preview": None if started else doc.get("preview")}


def spark(curve: list, points: int = SPARK_POINTS) -> list[float]:
    """A curve thinned to a few points, from 1 (the session before its first close)."""
    values = [1.0] + [float(v) for _, v in curve]
    if len(values) <= points:
        return [round(v, 5) for v in values]
    step = (len(values) - 1) / (points - 1)
    return [round(values[round(k * step)], 5) for k in range(points)]


class Remembering:
    """A store of bots that keeps the last list of bots it read, so the site can draw each line's
    curve from the read the board was worked out from, with no second read."""

    def __init__(self, store: engine.BotStore):
        self.inner = store
        self.last: list[dict] = []

    def all(self):
        self.last = self.inner.all()
        return [dict(d) for d in self.last]

    def __getattr__(self, name):
        return getattr(self.inner, name)


# --- The league -----------------------------------------------------------------------------------


class League:
    def __init__(self, bots: Bots, store: Remembering, public: bool = False, sample: bool = False,
                 now: Callable[[], datetime] | None = None):
        self.bots, self.store, self.public, self.sample = bots, store, public, sample
        self.now = now or bots.now

    def refresh(self, force: bool = False) -> dict:
        """Move the members' bots on: the engine's refresh, which keeps its own pace and lock. A bot
        sent in before bots had a public id gets one."""
        self.bots.ensure_ids()
        return self.bots.refresh(force=force)

    # --- Reading ---

    def _index(self) -> list[list]:
        """The S&P 500's closes the refresh keeps, the last year's."""
        return self.bots.store.meta().get("benchmark") or []

    def visible(self, user: dict | None) -> bool:
        """Whether the members' bots are shown: to members, or to everyone when the board is public."""
        return bool(user) or self.public

    def board(self, user: dict | None) -> dict:
        user_id = user["id"] if user else ""
        state = self.bots._state()
        curves = {(d.get("user_id"), d.get("submitted_utc")): d.get("curve") or [] for d in self.store.last}
        rows = []
        if self.visible(user):
            for r in state["rows"][:engine.SHOWN]:
                line = Bots._line(r, user_id)
                rows.append({**line, "slug": r["id"], "spark": spark(curves.get((r["user_id"], r.get("submitted_utc")), []))})
        index = self._index()
        start = index[0][1] if index else None
        return {"sample": self.sample, "as_of": state["as_of"], "stale": self.bots.behind(), "periods": [{"key": k, "label": label} for k, label, _ in PERIODS],
                "visible": self.visible(user), "signed_in": bool(user), "rows": rows, "entrants": len(state["rows"]), "benchmark": state["benchmark"],
                "index": [{"date": d, "value": round(c / start, 5)} for d, c in index] if start else [],
                "rules": {"cost": engine.BOT_COST, "universe": BOT_UNIVERSE_MAX, "hold": engine.BOT_HOLD_MAX}}

    def _against_index(self, curve: list, index: list) -> list[dict]:
        """A curve, and the index over the same sessions, both from 1 the session before its first."""
        if not curve:
            return []
        closes = dict((d, c) for d, c in index)
        days = [d for d, _ in index]
        first = curve[0][0]
        before = [d for d in days if d < first]
        base = closes.get(before[-1]) if before else closes.get(first)
        return [{"date": d, "bot": round(v, 6), "index": round(closes[d] / base, 6) if base and d in closes else None} for d, v in curve]

    def bot(self, slug: str, user: dict | None) -> dict | None:
        """A bot's own page, by its public id: its line, its curve against the index, everything it
        holds and what it did. Its rules are its owner's."""
        if not self.visible(user):
            return None
        user_id = user["id"] if user else ""
        state = self.bots._state()
        row = next((r for r in state["rows"] if not r["stand_in"] and r["id"] and r["id"] == slug), None)
        if not row:
            return None
        doc = self.store.get(row["user_id"]) or {}
        mine = bool(user_id) and row["user_id"] == user_id
        held = sorted((doc.get("weights") or {}).items(), key=lambda x: -x[1])
        out = {**Bots._line(row, user_id), "slug": slug, "spark": spark(doc.get("curve") or []),
               "holdings": [{"ticker": t, "weight": w} for t, w in held], "curve": self._against_index(doc.get("curve") or [], self._index()),
               "entrants": len(state["rows"]), **doings(doc)}
        if mine:
            out.update(rules=describe(doc["spec"], doc["universe"]), bot=doc["spec"], universe=len(doc["universe"]))
        return out
