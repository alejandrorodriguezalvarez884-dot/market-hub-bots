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
and that document was deleted.

Each market week (the closes of Monday to Friday, New York) has a winner: the bot with the best return
over the week among those that played it whole (see weeks()). A prize is recognition, never money.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Callable

from . import engine
from .config import BOT_UNIVERSE_MAX
from .engine import BELL, NEW_YORK, PERIODS, YEAR, Bots, activity, describe, returns
from .market import BENCHMARK

SPARK_POINTS = 64
LOG_SHOWN = 120  # rebalances on a bot's page
WEEKS_KEPT = 520  # weekly winners kept in bot_meta/board, the latest
STANDING_SHOWN = 3  # bots shown in the week that is being played


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


def cancel_pending(bots: Bots, user_id: str) -> dict:
    """Drop everything a member's bot is waiting to do at its next close: new rules, a pause or a
    resume, companies left out or let back in. The bot goes on as it is. New rules that never
    reached the bot do not count as the day's change, so that change is free again."""
    doc = bots.store.get(user_id)
    if not doc:
        raise engine.Refused("There is no bot to change: send one in first.")
    pending = doc.get("pending")
    if not pending:
        raise engine.Refused("There is no change waiting for the next close.")
    if "rules" in engine.changes(doc, pending):
        applied = [v for v in doc.get("versions") or [] if "rules" in (v.get("what") or [])]
        doc["rules_changed_utc"] = applied[-1].get("changed_utc") if applied else None
    doc.pop("pending")
    bots.store.put(doc)
    bots._cached = None
    return bots.mine(user_id)


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


# --- Weekly winners ------------------------------------------------------------------------------
#
# A week is the sessions of one calendar week, Monday to Friday, in New York. A bot plays a week
# whole when it already held its stocks before the week's first close (its record starts in an
# earlier week) and it was moved on to the week's last close: its return over the week is its value
# at that close over its value at the last close before the week. Changing rules or pausing during
# the week does not take a bot out (its record goes on, as on the board); a bot sent in during the
# week plays from the next one. The best return wins; bots with the same return, to the sixth
# decimal of the curve, share the week.
#
# A week is over when its Friday has closed, or when a later session has (a holiday on Friday).
# Nothing is scheduled: when a refresh has moved the bots past a week's last close, record() keeps
# that week's winner in bot_meta/board ("weeks"), so the prize stays put if the bot is later
# withdrawn or replaced. Only the bot's random public id and the date of its first close are kept,
# never a name: names are read from the bots there are, and a winner that is no longer playing is
# shown as such, without its name. A week that is over and not recorded yet (between the close and
# the next refresh) is worked out the same way when the board is read.


def week_of(day: str) -> str:
    """The Monday of a session's week."""
    d = date.fromisoformat(day)
    return (d - timedelta(days=d.weekday())).isoformat()


def weeks(docs: list[dict], index: list) -> list[dict]:
    """Every week there are closes for, oldest first: its sessions, whether it is over, the index over
    it and each bot that played it whole with its return. Read in one pass over each curve."""
    calendar = sorted({d for d, _ in index} | {d for doc in docs for d, _ in doc.get("curve") or []})
    if not calendar:
        return []
    days: dict[str, list[str]] = {}
    for d in calendar:
        days.setdefault(week_of(d), []).append(d)
    played: dict[str, list[dict]] = {w: [] for w in days}
    for doc in docs:
        curve = doc.get("curve") or []
        if not curve or not doc.get("public_id"):
            continue
        since, first = curve[0][0], week_of(curve[0][0])
        base, ends = None, {}
        for (d, v), prev in zip(curve, [None, *curve[:-1]]):
            w = week_of(d)
            if prev is not None and week_of(prev[0]) != w:
                ends[w] = [prev[1], None]
            if w in ends:
                ends[w][1] = (d, v)
        for w, (base, (last, v)) in ends.items():
            if w > first and base and last == days[w][-1]:
                played[w].append({"id": doc["public_id"], "since": since, "return": v / base - 1})
    closes = dict((d, c) for d, c in index)
    out, before = [], None
    for w, ds in days.items():
        last = ds[-1]
        over = date.fromisoformat(last).weekday() == 4 or last != calendar[-1]
        a, b = closes.get(before) if before else None, closes.get(last)
        out.append({"week": w, "from": ds[0], "to": last, "sessions": len(ds), "over": over,
                    "index": b / a - 1 if a and b else None,
                    "played": sorted(played[w], key=lambda p: (-round(p["return"], 6), p["since"], p["id"]))})
        before = last
    return out


def winner(week: dict) -> dict | None:
    """A week as it is kept: its winners (sharing it on the same return) and its figures."""
    if not week["played"]:
        return None
    best = round(week["played"][0]["return"], 6)
    won = [p for p in week["played"] if round(p["return"], 6) == best]
    return {"week": week["week"], "from": week["from"], "to": week["to"], "sessions": week["sessions"], "return": round(best, 6),
            "index": None if week["index"] is None else round(week["index"], 6), "entrants": len(week["played"]),
            "winners": [{"id": p["id"], "since": p["since"]} for p in won]}


def unrecorded(played: list[dict], kept: list[dict]) -> list[dict]:
    """The winners of the weeks that are over and not kept yet, oldest first."""
    have = {k["week"] for k in kept}
    return [x for x in (winner(w) for w in played if w["over"] and w["week"] not in have) if x]


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
        out = self.bots.refresh(force=force)
        self.record()
        return out

    def record(self) -> int:
        """Keep the winner of every week that is over and not kept yet, in bot_meta/board. Called after
        each refresh; it writes only when there is a new week to keep."""
        self.bots._state()  # the bots as the refresh left them, read once into self.store.last
        meta = self.bots.store.meta()
        kept = meta.get("weeks") or []
        new = unrecorded(weeks(self.store.last, meta.get("benchmark") or []), kept)
        if not new:
            return 0
        meta = self.bots.store.meta()  # read again just before writing: the refresh writes this document too
        have = {k["week"] for k in meta.get("weeks") or []}
        kept = sorted((meta.get("weeks") or []) + [w for w in new if w["week"] not in have], key=lambda k: k["week"])[-WEEKS_KEPT:]
        self.bots.store.put_meta({**meta, "weeks": kept})
        return len(new)

    # --- Reading ---

    def visible(self, user: dict | None) -> bool:
        """Whether the members' bots are shown: to members, or to everyone when the board is public."""
        return bool(user) or self.public

    def _weekly(self, state: dict, meta: dict, user_id: str) -> dict:
        """The weekly prizes: the week being played as it stands, every week's winners (newest first,
        with the index over the week for reference) and the bots that have won the most weeks. The
        winners are matched to the bots there are by their public id and first close; one that is no
        longer playing is "gone", with no name."""
        played = weeks(self.store.last, meta.get("benchmark") or [])
        kept = meta.get("weeks") or []
        won = sorted(kept + unrecorded(played, kept), key=lambda k: k["week"], reverse=True)
        bots = {(r["id"], r["since"]): r for r in state["rows"] if r["id"] and r["since"] and not r["stand_in"]}

        def who(w: dict) -> dict:
            r = bots.get((w["id"], w["since"]))
            if not r:
                return {"gone": True}
            return {"slug": r["id"], "name": r["name"], "handle": r["handle"], "you": bool(user_id) and r["user_id"] == user_id}

        winners = [{k: w[k] for k in ("week", "from", "to", "sessions", "return", "index", "entrants")} | {"bots": [who(x) for x in w["winners"]]}
                   for w in won]
        tally: dict[tuple, dict] = {}
        for w in won:
            for x in w["winners"]:
                key = (x["id"], x["since"])
                if key in bots:
                    t = tally.setdefault(key, {**who(x), "wins": 0, "last": w["week"]})
                    t["wins"] += 1
        ranking = sorted(tally.values(), key=lambda t: (-t["wins"], -date.fromisoformat(t["last"]).toordinal(), t["name"].lower(), t["slug"]))
        now = played[-1] if played and not played[-1]["over"] else None
        current = None
        if now:
            standing = []
            for n, p in enumerate(now["played"], 1):
                r = bots.get((p["id"], p["since"]))
                if r and (len(standing) < STANDING_SHOWN or (user_id and r["user_id"] == user_id)):
                    standing.append({**who(p), "place": n, "return": round(p["return"], 6)})
            current = {"week": now["week"], "from": now["from"], "to": now["to"], "sessions": now["sessions"],
                       "index": None if now["index"] is None else round(now["index"], 6), "entrants": len(now["played"]), "standing": standing}
        return {"current": current, "winners": winners, "ranking": ranking}

    def wins(self, slug: str, since: str | None, meta: dict) -> list[dict]:
        """The weeks a bot has won, newest first, with how many played them and the index over them."""
        if not since:
            return []
        kept = meta.get("weeks") or []
        won = kept + unrecorded(weeks(self.store.last, meta.get("benchmark") or []), kept)
        return sorted(({k: w[k] for k in ("week", "from", "to", "return", "index", "entrants")} | {"shared": len(w["winners"]) > 1}
                       for w in won if any(x["id"] == slug and x["since"] == since for x in w["winners"])), key=lambda w: w["week"], reverse=True)

    def board(self, user: dict | None) -> dict:
        user_id = user["id"] if user else ""
        state = self.bots._state()
        meta = self.bots.store.meta()
        curves = {(d.get("user_id"), d.get("submitted_utc")): d.get("curve") or [] for d in self.store.last}
        rows, weekly = [], {"current": None, "winners": [], "ranking": []}
        if self.visible(user):
            weekly = self._weekly(state, meta, user_id)
            count = {t["slug"]: t["wins"] for t in weekly["ranking"]}
            for r in state["rows"][:engine.SHOWN]:
                line = Bots._line(r, user_id)
                rows.append({**line, "slug": r["id"], "spark": spark(curves.get((r["user_id"], r.get("submitted_utc")), [])),
                             "wins": count.get(r["id"], 0)})
        index = meta.get("benchmark") or []  # the S&P 500's closes the refresh keeps, the last year's
        start = index[0][1] if index else None
        return {"sample": self.sample, "as_of": state["as_of"], "stale": self.bots.behind(), "periods": [{"key": k, "label": label} for k, label, _ in PERIODS],
                "visible": self.visible(user), "signed_in": bool(user), "rows": rows, "entrants": len(state["rows"]), "benchmark": state["benchmark"],
                "index": [{"date": d, "value": round(c / start, 5)} for d, c in index] if start else [], "weekly": weekly,
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
        meta = self.bots.store.meta()
        mine = bool(user_id) and row["user_id"] == user_id
        held = sorted((doc.get("weights") or {}).items(), key=lambda x: -x[1])
        out = {**Bots._line(row, user_id), "slug": slug, "spark": spark(doc.get("curve") or []),
               "holdings": [{"ticker": t, "weight": w} for t, w in held], "curve": self._against_index(doc.get("curve") or [], meta.get("benchmark") or []),
               "entrants": len(state["rows"]), "wins": self.wins(slug, row["since"], meta), **doings(doc)}
        if mine:
            out.update(rules=describe(doc["spec"], doc["universe"]), bot=doc["spec"], universe=len(doc["universe"]))
        return out
