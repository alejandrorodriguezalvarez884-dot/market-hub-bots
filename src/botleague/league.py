"""What Bot League adds to the competition: the house bots, the board as the site shows it and each
bot's own page.

The competition itself (the format, the paper engine, the members' bots and their keys) is
engine.py, the same as the portal's, on the same collections. This module only reads it, but for
one document of its own, ``bot_meta/house``:

- **The house bots.** The kit's examples, run on paper by the site itself from the close after
  they were first started, exactly as a member's bot is (never a backtest). They are lines of
  reference on the board, like the index: never ranked, never counted as entrants, and their rules
  are public, because they are the kit's. Visitors who are not signed in see them; they are not
  anyone's.
- **The index** over the last three years (SPY's closes), so a bot's page can draw it under the
  bot from the bot's first close.

The members' bots are seen by everyone while PUBLIC_BOARD is on (the default, and what Market
Hub's privacy page says), or by signed-in members alone when it is off. Rules are their owner's alone.

Bot League is the only service that moves the curves (refresh): the portal's Community section
reads the same documents and, when it finds them behind, asks this site to move them.
"""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Protocol

from . import engine
from .config import BOT_UNIVERSE_MAX, BOTS_CACHE_SECONDS, BOTS_REFRESH_SECONDS, DATA_DIR, FIRESTORE_DATABASE
from .engine import BELL, KIT, NEW_YORK, PERIODS, SETTLED, YEAR, Bots, Prices, check, describe, last_settled, resolve, returns
from .market import BENCHMARK, MarketUnavailable
from .names import handle_key

HOUSE = "house-"  # the id of a house bot: this, then the name of its example's file
HOUSE_NAME = "Bot League"  # what a house bot shows under
INDEX_SESSIONS = 3 * YEAR + 1
SPARK_POINTS = 64


def _iso(at: datetime) -> str:
    return engine._iso(at)


def house_examples() -> list[tuple[str, dict]]:
    """The kit's examples, each with its id: the house bots."""
    return [(HOUSE + p.stem, json.loads(p.read_text(encoding="utf-8"))) for p in sorted((KIT / "examples").glob("*.json"))]


def expected_close(now: datetime) -> str:
    """The last session whose close there should be by ``now`` (weekdays; holidays are not known)."""
    local = now.astimezone(NEW_YORK)
    day = local.date() if local.time() >= SETTLED else local.date() - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day.isoformat()


def spark(curve: list, points: int = SPARK_POINTS) -> list[float]:
    """A curve thinned to a few points, from 1 (the session before its first close)."""
    values = [1.0] + [float(v) for _, v in curve]
    if len(values) <= points:
        return [round(v, 5) for v in values]
    step = (len(values) - 1) / (points - 1)
    return [round(values[round(k * step)], 5) for k in range(points)]


# --- The site's document --------------------------------------------------------------------------


class HouseStore(Protocol):
    def get(self) -> dict | None: ...
    def put(self, doc: dict) -> None: ...


class MemoryHouse:
    def __init__(self):
        self.doc: dict | None = None

    def get(self):
        return json.loads(json.dumps(self.doc)) if self.doc else None

    def put(self, doc):
        self.doc = json.loads(json.dumps(doc))


class FileHouse:
    """For local development only: house.json next to the portal's files of bots."""

    def __init__(self, root: Path | None = None):
        self.path = Path(root or DATA_DIR / "bots") / "house.json"

    def get(self):
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else None

    def put(self, doc):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(doc), encoding="utf-8")


class FirestoreHouse:
    def __init__(self, database: str = FIRESTORE_DATABASE):
        from google.cloud import firestore

        self.ref = firestore.Client(database=database).collection("bot_meta").document("house")

    def get(self):
        snap = self.ref.get()
        return engine.unpacked(snap.to_dict()) if snap.exists else None

    def put(self, doc):
        self.ref.set(engine.packed(doc))


# --- Who else shows under a name in Market Hub's community -----------------------------------------


class Members(Protocol):
    def taken(self, key: str, user_id: str) -> bool: ...
    def name(self, user_id: str) -> str: ...


class NoMembers:
    """No community besides the bots: a local run, or the tests."""

    def taken(self, key, user_id):
        return False

    def name(self, user_id):
        return ""


class FirestoreMembers:
    """Reads, and only reads, the portal's community: the name a member shares their portfolio
    under (shared_portfolios) and the one they play the monthly competition under
    (competition_entries). A bot's name cannot be one somebody else already shows under there, and
    a member who shows under one already is shown under it here too: the same rule as the portal's."""

    def __init__(self, database: str = FIRESTORE_DATABASE):
        from google.cloud import firestore
        from google.cloud.firestore_v1.base_query import FieldFilter

        client = firestore.Client(database=database)
        self.where = lambda field, value: FieldFilter(field, "==", value)
        self.shared = client.collection("shared_portfolios")
        self.entries = client.collection("competition_entries")

    def taken(self, key, user_id):
        return any(s.to_dict().get("user_id") != user_id for s in self.shared.where(filter=self.where("handle_key", key)).limit(5).stream())

    def name(self, user_id):
        entries = sorted((s.to_dict() for s in self.entries.where(filter=self.where("user_id", user_id)).stream()),
                         key=lambda e: e.get("month", ""), reverse=True)
        if entries:
            return entries[0].get("handle") or ""
        snap = self.shared.document(user_id).get()
        return (snap.to_dict() or {}).get("handle", "") if snap.exists else ""


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
    def __init__(self, bots: Bots, store: Remembering, house: HouseStore, closes: Callable[[set[str]], dict],
                 largest: Callable[[int], list[str]], public: bool = False, sample: bool = False,
                 now: Callable[[], datetime] | None = None):
        self.bots, self.store, self.house_store = bots, store, house
        self.closes, self.largest, self.public, self.sample = closes, largest, public, sample
        self.now = now or bots.now
        self._house: tuple[float, dict | None] | None = None
        self._refreshing = threading.Lock()

    # --- Moving the house bots on ---

    def _read_house(self) -> dict | None:
        hit = self._house
        if hit and time.monotonic() - hit[0] < BOTS_CACHE_SECONDS:
            return hit[1]
        doc = self.house_store.get()
        self._house = (time.monotonic(), doc)
        return doc

    def house_behind(self) -> bool:
        doc, now = self._read_house(), self.now()
        if not doc:
            return True
        if doc.get("checked_utc") and now - engine._when(doc["checked_utc"]) < timedelta(seconds=BOTS_REFRESH_SECONDS):
            return False
        if {h for h, _ in house_examples()} - set(doc.get("bots") or {}):
            return True
        expected = expected_close(now)
        for b in doc["bots"].values():
            if b.get("as_of") and b["as_of"] < expected:
                return True
            if not b.get("as_of") and engine._when(b["submitted_utc"]) < datetime.combine(datetime.fromisoformat(expected).date(), BELL, NEW_YORK):
                return True
        return False

    def _move_house(self) -> int:
        now = self.now()
        doc = self.house_store.get() or {"created_utc": _iso(now), "bots": {}}
        pool = self.largest(BOT_UNIVERSE_MAX)
        kept = doc.get("bots") or {}
        bots: dict[str, dict] = {}
        for hid, raw in house_examples():
            spec = check(raw)
            b = kept.get(hid)
            if b is None or b.get("spec") != spec:  # new, or its example changed: it starts again
                try:
                    universe = resolve(spec, lambda k: pool[:k])
                except engine.Refused:  # a company of its own list is no longer among the largest
                    continue
                b = {"id": hid, "spec": spec, "universe": universe, "submitted_utc": _iso(now), "curve": [], "weights": {}, "as_of": None}
            bots[hid] = b
        tickers = {t for b in bots.values() for t in b["universe"]} | {t for b in bots.values() for t in b["weights"]} | {BENCHMARK}
        prices = Prices(self.closes(tickers))
        end = last_settled(prices.days, now)
        moved = 0
        if end is not None:
            for b in bots.values():
                moved += bool(self.bots._advance(b, prices, end))
            j = prices.col[BENCHMARK]
            doc["index"] = [[prices.days[i], round(float(prices.close[i, j]), 4)] for i in range(max(0, end - INDEX_SESSIONS + 1), end + 1)]
            doc["as_of"] = prices.days[end]
        doc.update(bots=bots, checked_utc=_iso(now))
        self.house_store.put(doc)
        self._house = (time.monotonic(), doc)
        return moved

    def refresh(self, force: bool = False) -> dict:
        """Move the members' bots on (the engine's refresh, which keeps its own pace and lock), then
        the house bots, if they are behind the last close."""
        out = self.bots.refresh(force=force)
        if not self._refreshing.acquire(blocking=False):
            return {**out, "house": 0, "busy": True}
        try:
            house = self._move_house() if force or self.house_behind() else 0
        except MarketUnavailable:
            house = 0
        finally:
            self._refreshing.release()
        return {**out, "house": house}

    # --- Reading ---

    def _house_lines(self) -> tuple[list[dict], list[list]]:
        doc = self._read_house() or {}
        lines = []
        for hid, raw in house_examples():
            b = (doc.get("bots") or {}).get(hid)
            if not b:
                continue
            values = [v for _, v in b.get("curve") or []]
            held = sorted((b.get("weights") or {}).items(), key=lambda x: -x[1])
            lines.append({"slug": hid, "house": True, "you": False, "handle": HOUSE_NAME, "name": b["spec"]["name"], "about": b["spec"]["about"],
                          "since": b["curve"][0][0] if b.get("curve") else None, "as_of": b.get("as_of"), "sessions": len(values),
                          "returns": returns(values) if values else {k: None for k in [*(p[0] for p in PERIODS), "all"]}, "ranks": {},
                          "holdings": [{"ticker": t, "weight": w} for t, w in held[:engine.SHOWN_HOLDINGS]], "holding": len(held),
                          "cash": max(0.0, 1 - sum(w for _, w in held)) if values else None, "spark": spark(b.get("curve") or [])})
        return lines, doc.get("index") or []

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
                rows.append({**line, "slug": handle_key(r["handle"]), "house": False, "spark": spark(curves.get((r["user_id"], r.get("submitted_utc")), []))})
        house, index = self._house_lines()
        bench = state["benchmark"]
        if index:
            closes = [c for _, c in index[-(YEAR + 1):]]
            bench = {"ticker": BENCHMARK, "returns": {**returns([c / closes[0] for c in closes]), "all": None}}
        as_of = max([x for x in (state["as_of"], *(h["as_of"] for h in house)) if x], default=None)
        stale = self.bots.behind() or self.house_behind()
        return {"sample": self.sample, "as_of": as_of, "stale": stale, "periods": [{"key": k, "label": label} for k, label, _ in PERIODS],
                "visible": self.visible(user), "signed_in": bool(user), "rows": rows, "house": house,
                "entrants": len(state["rows"]), "benchmark": bench,
                "index": [{"date": d, "value": round(c / index[max(0, len(index) - YEAR - 1)][1], 5)} for d, c in index[-(YEAR + 1):]] if index else [],
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
        out = [{"date": d, "bot": round(v, 6), "index": round(closes[d] / base, 6) if base and d in closes else None} for d, v in curve]
        return out

    def bot(self, slug: str, user: dict | None) -> dict | None:
        """A bot's own page: its line, its curve against the index and everything it holds. A house
        bot's rules are public; a member's are their own."""
        house, index = self._house_lines()
        if slug.startswith(HOUSE):
            line = next((h for h in house if h["slug"] == slug), None)
            if not line:
                return None
            doc = (self._read_house() or {})["bots"][slug]
            return {**line, "holdings": [{"ticker": t, "weight": w} for t, w in sorted(doc["weights"].items(), key=lambda x: -x[1])],
                    "curve": self._against_index(doc.get("curve") or [], index), "rules": describe(doc["spec"], doc["universe"]),
                    "bot": doc["spec"], "universe": len(doc["universe"]), "entrants": len(self.bots._state()["rows"])}
        if not self.visible(user):
            return None
        user_id = user["id"] if user else ""
        state = self.bots._state()
        row = next((r for r in state["rows"] if not r["stand_in"] and handle_key(r["handle"]) == slug), None)
        if not row:
            return None
        doc = self.store.get(row["user_id"]) or {}
        mine = bool(user_id) and row["user_id"] == user_id
        held = sorted((doc.get("weights") or {}).items(), key=lambda x: -x[1])
        out = {**Bots._line(row, user_id), "slug": slug, "house": False, "spark": spark(doc.get("curve") or []),
               "holdings": [{"ticker": t, "weight": w} for t, w in held], "curve": self._against_index(doc.get("curve") or [], index),
               "entrants": len(state["rows"])}
        if mine:
            out.update(rules=describe(doc["spec"], doc["universe"]), bot=doc["spec"], universe=len(doc["universe"]))
        return out
