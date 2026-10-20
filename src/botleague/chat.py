"""The chat on a member's page: an instruction in their own words ("drop the tech stocks", "make it
more defensive"), a change of rules proposed by Claude, which the member confirms before it is
applied (as an edit: from the next close, keeping the record).

Claude only proposes rules in the bot's format; the code checks them as it checks any bot. There
are no orders and no stock tips: a switch (pause, leave a company out) is the member's to press.
Nothing of the chat is kept: the page sends the last few turns with each message. What goes to
Anthropic is the member's message, those turns and the bot's rules, never who the member is.

It spends on the owner's Anthropic key, so it is off unless BOTLEAGUE_CHAT=1 and a key is set,
with a cap of messages per member a day (in memory, per instance) and a cap of dollars a day for
the whole service (a ledger in bot_meta/chat, which keeps no one's identity).
"""

from __future__ import annotations

import json
import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Protocol

from . import engine
from .config import (CHAT_DAILY_MAX_USD, CHAT_ENABLED, CHAT_MODEL, CHAT_PER_MEMBER_PER_DAY, CHAT_PRICES, CHAT_REQUEST_MAX_USD,
                     DATA_DIR, FIRESTORE_DATABASE)

log = logging.getLogger("botleague.chat")

MESSAGE_MAX = 600
TURNS_KEPT = 6  # earlier turns the page may send back with a message
TURN_MAX = 1200

SCHEMA = {
    "type": "object",
    "properties": {
        "reply": {"type": "string", "description": "What to tell the member, in their language, in at most four short sentences."},
        "bot": {"type": "string", "description": "The whole bot, as JSON in the markethub-bot/1 format, when you propose a change; an empty string when you do not."},
    },
    "required": ["reply", "bot"],
    "additionalProperties": False,
}


def system_prompt() -> str:
    return f"""You help a member of Bot League change the rules of their trading bot, which runs on paper (no money, no broker, no orders) in a competition. The bot is a JSON file in the format "markethub-bot/1". This is what the format allows, as JSON:

{json.dumps(engine.spec(), indent=1)}

Fields: "format" ("markethub-bot/1"), "name" (3 to 40 characters), "about" (up to 280), "universe" ({{"largest": N}} or {{"tickers": [...]}}, and "exclude": [...]), "rebalance", "filters" (each a factor with its settings and "min" and/or "max"), "score" (each a factor with its settings and a "weight" from -5 to 5, not 0; below 0 prefers the lowest), "hold", "weighting", "max_weight", and optionally "market" (a factor of the S&P 500 with "min"/"max" and "cash", the share held in cash when the index is outside those bounds).

How to answer:
- The member writes an instruction about their bot. If it can be done with the format, propose the whole new bot in "bot", changing only what the instruction asks, and say in "reply" what changes, in plain words. Keep "name" and "about" unless asked; update "about" if the idea itself changes.
- If the instruction is unclear, ask one short question and leave "bot" empty.
- The format has no sectors or industries: it chooses among the largest US companies by figures worked out from prices. If asked for something it cannot express (a sector, fundamentals, news), say so and offer the closest rule, or leave "bot" empty.
- Pausing the bot and leaving one company out or letting it back in are switches on the page, not rules: point the member to them instead of changing the rules for that.
- Never tell the member to buy or sell anything with their own money, never promise returns, and never present a change as a forecast. You describe what a rule does; the member decides.
- Answer in the member's language, briefly."""


class Ledger(Protocol):
    def get(self) -> dict | None: ...
    def put(self, doc: dict) -> None: ...


class MemoryLedger:
    def __init__(self):
        self.doc: dict | None = None

    def get(self):
        return json.loads(json.dumps(self.doc)) if self.doc else None

    def put(self, doc):
        self.doc = json.loads(json.dumps(doc))


class FileLedger:
    def __init__(self, path: Path | None = None):
        self.path = Path(path or DATA_DIR / "bots" / "chat.json")

    def get(self):
        return json.loads(self.path.read_text(encoding="utf-8")) if self.path.exists() else None

    def put(self, doc):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(doc), encoding="utf-8")


class FirestoreLedger:
    def __init__(self, database: str = FIRESTORE_DATABASE):
        from google.cloud import firestore

        self.ref = firestore.Client(database=database).collection("bot_meta").document("chat")

    def get(self):
        snap = self.ref.get()
        return snap.to_dict() if snap.exists else None

    def put(self, doc):
        self.ref.set(doc)


class ChatOff(Exception):
    """The chat cannot answer now: switched off, or a cap reached. Its message is for the member."""


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    price_in, price_out = CHAT_PRICES.get(model, max(CHAT_PRICES.values()))
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000


class Chat:
    def __init__(self, ledger: Ledger, client: Callable[[], object] | None = None, enabled: bool = CHAT_ENABLED,
                 model: str = CHAT_MODEL, daily_max: float = CHAT_DAILY_MAX_USD, request_max: float = CHAT_REQUEST_MAX_USD,
                 per_member: int = CHAT_PER_MEMBER_PER_DAY, now: Callable[[], datetime] | None = None):
        self.ledger, self.enabled, self.model = ledger, enabled, model
        self.daily_max, self.request_max, self.per_member = daily_max, request_max, per_member
        self.now = now or (lambda: datetime.now(timezone.utc))
        self._client_factory = client
        self._client = None
        self._asked: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    @property
    def client(self):
        if self._client is None:
            if self._client_factory:
                self._client = self._client_factory()
            else:
                import anthropic

                self._client = anthropic.Anthropic()
        return self._client

    def status(self) -> dict:
        return {"on": self.enabled, "per_member_per_day": self.per_member}

    def _day(self) -> str:
        return self.now().strftime("%Y-%m-%d")

    def _reserve(self, user_id: str) -> None:
        if not self.enabled:
            raise ChatOff("The chat is not switched on yet. Use the editor.")
        with self._lock:
            t, asked = time.monotonic(), self._asked[user_id]
            while asked and t - asked[0] > 86400:
                asked.popleft()
            if len(asked) >= self.per_member:
                raise ChatOff(f"That is {self.per_member} messages today. The editor still works; the chat is back tomorrow.")
            spent = (self.ledger.get() or {}).get("days", {}).get(self._day(), 0.0)
            if spent + self.request_max > self.daily_max:
                raise ChatOff("The chat has reached today's limit for everyone. The editor still works; the chat is back tomorrow.")
            asked.append(t)

    def _book(self, usd: float) -> None:
        with self._lock:
            doc = self.ledger.get() or {"days": {}, "calls": 0, "total_usd": 0.0}
            day = self._day()
            doc["days"][day] = round(doc["days"].get(day, 0.0) + usd, 6)
            doc["days"] = dict(sorted(doc["days"].items())[-60:])
            doc["calls"] = doc.get("calls", 0) + 1
            doc["total_usd"] = round(doc.get("total_usd", 0.0) + usd, 6)
            self.ledger.put(doc)

    def ask(self, user_id: str, bot: dict, message: str, history: list | None = None) -> dict:
        """A proposal for the member's instruction: Claude's reply and, when it proposes one, the new
        bot checked by the code (or the problems the code found in it)."""
        message = " ".join(str(message or "").split())
        if not 1 <= len(message) <= MESSAGE_MAX:
            raise engine.Refused(f"Write an instruction of 1 to {MESSAGE_MAX} characters.")
        turns = []
        for t in (history or [])[-TURNS_KEPT:]:
            if isinstance(t, dict) and t.get("role") in ("user", "assistant") and isinstance(t.get("text"), str) and t["text"].strip():
                turns.append({"role": t["role"], "content": t["text"][:TURN_MAX]})
        while turns and turns[0]["role"] != "user":
            turns.pop(0)
        self._reserve(user_id)
        content = f"My bot now:\n{json.dumps(bot, indent=1)}\n\nMy instruction: {message}"
        params = dict(model=self.model, max_tokens=8000, system=system_prompt(), messages=[*turns, {"role": "user", "content": content}],
                      output_config={"effort": "low", "format": {"type": "json_schema", "schema": SCHEMA}})
        try:
            if self.model.startswith(("claude-opus-5-5", "claude-sonnet-5-5")):
                # On a policy decline the API runs the same request on a fallback model, in the same call.
                response = self.client.beta.messages.create(**params, betas=["server-side-fallback-2026-07-01"], fallbacks="default")
            else:
                response = self.client.messages.create(**params)
        except Exception as exc:  # the SDK's own errors; their text is not shown
            log.warning("chat call failed: %s", type(exc).__name__)
            raise ChatOff("The chat could not answer just now. Try again in a minute.") from None
        usage = getattr(response, "usage", None)
        self._book(cost_usd(self.model, getattr(usage, "input_tokens", 0) or 0, getattr(usage, "output_tokens", 0) or 0))
        if getattr(response, "stop_reason", None) == "refusal":
            return {"reply": "I can't help with that one. Try putting it as a change to the bot's rules.", "proposal": None}
        text = next((b.text for b in response.content if getattr(b, "type", "") == "text"), "")
        try:
            got = json.loads(text)
        except ValueError:
            return {"reply": "I could not put that into rules. Try saying it another way.", "proposal": None}
        reply, raw = str(got.get("reply") or "").strip(), str(got.get("bot") or "").strip()
        if not raw:
            return {"reply": reply, "proposal": None}
        try:
            proposed = engine.check(json.loads(raw))
        except ValueError as exc:  # not JSON, or Refused (a ValueError) with its problems
            problems = exc.problems if isinstance(exc, engine.Refused) else ["The proposal was not valid JSON."]
            return {"reply": reply, "proposal": None, "problems": problems}
        return {"reply": reply, "proposal": proposed}
