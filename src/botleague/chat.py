"""The chat on a member's page, in two modes. Creating: a member with no bot talks their idea through
with Claude, as with the kit in their own agent, and Claude proposes a whole bot, which the member
sees in words, with what it would hold and, if they ask, a backtest, and sends in when they say so.
Changing: an instruction in their own words ("make it more defensive"), a change of rules proposed
by Claude, which the member confirms before it is applied (from the next close, keeping the record).

Claude only proposes rules in the bot's format; the code checks them as it checks any bot, and a
proposal the code refuses goes back to Claude once, with the problems, in the same message. There
are no orders and no stock tips: a switch (pause, leave a company out) is the member's to press.
Nothing of the chat is kept: the page sends the last few turns, the draft and the figures of the
backtest it shows with each message. What goes to Anthropic is that, never who the member is.

It spends on the owner's Anthropic key, so it is off unless BOTLEAGUE_CHAT=1 and a key is set,
with a cap of messages per member a day (in memory, per instance) and, if the owner sets one, a cap
of dollars a day for the whole service. A ledger in bot_meta/chat, which keeps no one's identity,
counts what it spends either way.
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
from .config import (CHAT_DAILY_MAX_USD, CHAT_EFFORT, CHAT_ENABLED, CHAT_MODEL, CHAT_PER_MEMBER_PER_DAY, CHAT_PRICES,
                     CHAT_REQUEST_MAX_USD, DATA_DIR, FIRESTORE_DATABASE)

log = logging.getLogger("botleague.chat")

MESSAGE_MAX = 600
TURNS_KEPT = 10  # earlier turns the page may send back with a message
TURN_MAX = 1200
MODES = ("change", "create")

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


def create_prompt() -> str:
    examples = "\n".join(json.dumps(b) for b in engine.examples())
    return f"""You help a member of Bot League build their trading bot from scratch, in a chat on its website, as their own AI agent would with Bot League's kit. The bot runs on paper (no money, no broker, no orders) in a public competition, ranked from the close after it is sent in, over the day, week, month, year and since it started. It is a JSON file in the format "markethub-bot/1". This is what the format allows, as JSON:

{json.dumps(engine.spec(), indent=1)}

Fields: "format" ("markethub-bot/1"), "name" (3 to 40 characters), "about" (up to 280), "universe" ({{"largest": N}} or {{"tickers": [...]}}, and "exclude": [...]), "rebalance", "filters" (each a factor with its settings and "min" and/or "max"), "score" (each a factor with its settings and a "weight" from -5 to 5, not 0; below 0 prefers the lowest), "hold", "weighting", "max_weight", and optionally "market" (a factor of the S&P 500 with "min"/"max" and "cash", the share held in cash when the index is outside those bounds).

Valid bots to start from, one per line:
{examples}

How to go about it:
- The member may not know what momentum or an RSI is: plain words, short answers, no jargon without saying what it means.
- Find the idea first. If they have none, offer three or four in a line each (momentum, trend following with a market filter, calm stocks, buying pullbacks in an uptrend, near the highs, a few megacaps rotated) and ask which one sounds like them.
- Then ask, one or two questions at a time, what matters to them: how many stocks (concentrated or spread), how often it looks again (each trade costs 0.10%), and whether it should step into cash when the whole market falls. Do not ask what you can choose sensibly yourself.
- As soon as you know enough, propose the whole bot in "bot", starting from the closest example, and say in "reply" what it does in two or three plain sentences. Give it a "name" and an "about" that say the idea (the board is public: nothing offensive, no promises), and keep the "about" true to the rules when a change makes it wrong (a number of stocks, how often it looks again). From then on, each answer that changes something proposes the whole bot again; one that only answers a question leaves "bot" empty.
- The page shows the member each proposal in words and what it would hold at the last close, and a button for a backtest. When the member has run one, its figures come with their message: you may describe them (the total and yearly return, the volatility and the worst fall, against the S&P 500), always as a simulation of the past among today's largest companies, which flatters it, and never as what will happen. After a few rounds of changes, warn once that tuning to the past makes a bot good at the past only.
- The format has no sectors, fundamentals or news: it chooses among the largest US companies by figures worked out from prices. If asked for something it cannot express, say so and offer the closest rule.
- The member sends the bot in with a button on the page, when they decide; you cannot send it. When they seem happy, tell them that the button is there, that the public board shows the bot with the first name of their account, that its rules stay theirs alone, and that it starts at the next close.
- Never tell the member to buy or sell anything with their own money, never promise returns, and never present a bot or a backtest as a forecast or a recommendation. You describe what a rule does; the member decides.
- Answer in the member's language, briefly: at most five short sentences in "reply"."""


FIX = "The code refused that bot: {problems} Send the whole bot again, fixed, in \"bot\", and keep the reply."


def figures(backtest) -> str | None:
    """The backtest the page shows, as a few figures for Claude: only numbers and dates are kept."""
    if not isinstance(backtest, dict):
        return None

    def pct(v):
        return f"{v * 100:+.1f}%" if isinstance(v, (int, float)) and not isinstance(v, bool) and abs(v) < 100 else "n/a"

    def side(d):
        d = d if isinstance(d, dict) else {}
        return (f"total {pct(d.get('total_return'))}, yearly {pct(d.get('annual_return'))}, "
                f"volatility {pct(d.get('volatility'))}, worst fall {pct(d.get('max_drawdown'))}")

    years = backtest.get("years")
    span = f"{years} year{'s' if years != 1 else ''}" if isinstance(years, int) and 1 <= years <= 10 else "the last years"
    out = [f"Over {span}: the bot {side(backtest.get('bot'))}; the S&P 500 {side(backtest.get('benchmark'))}."]
    if isinstance(backtest.get("turnover_per_year"), (int, float)):
        out.append(f"It traded {backtest['turnover_per_year'] * 100:.0f}% of the portfolio a year.")
    return " ".join(out)


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
                 model: str = CHAT_MODEL, daily_max: float | None = CHAT_DAILY_MAX_USD, request_max: float = CHAT_REQUEST_MAX_USD,
                 per_member: int = CHAT_PER_MEMBER_PER_DAY, effort: str = CHAT_EFFORT, now: Callable[[], datetime] | None = None):
        self.ledger, self.enabled, self.model, self.effort = ledger, enabled, model, effort
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

    def status(self, user_id: str | None = None) -> dict:
        out = {"on": self.enabled, "per_member_per_day": self.per_member}
        return {**out, "left": self.left(user_id)} if user_id else out

    def _recent(self, user_id: str) -> deque[float]:
        """The member's messages of the last 24 hours (call with the lock held)."""
        t, asked = time.monotonic(), self._asked[user_id]
        while asked and t - asked[0] > 86400:
            asked.popleft()
        return asked

    def left(self, user_id: str) -> int:
        """How many messages the member has left in the last 24 hours."""
        with self._lock:
            return max(0, self.per_member - len(self._recent(user_id)))

    def _day(self) -> str:
        return self.now().strftime("%Y-%m-%d")

    def _reserve(self, user_id: str) -> None:
        if not self.enabled:
            raise ChatOff("The chat is not switched on yet. Use the editor.")
        with self._lock:
            asked = self._recent(user_id)
            if len(asked) >= self.per_member:
                raise ChatOff(f"That is {self.per_member} messages today. The editor still works; the chat is back tomorrow.")
            if self.daily_max is not None:
                spent = (self.ledger.get() or {}).get("days", {}).get(self._day(), 0.0)
                if spent + self.request_max > self.daily_max:
                    raise ChatOff("The chat has reached today's limit for everyone. The editor still works; the chat is back tomorrow.")
            asked.append(time.monotonic())

    def _book(self, usd: float) -> None:
        with self._lock:
            doc = self.ledger.get() or {"days": {}, "calls": 0, "total_usd": 0.0}
            day = self._day()
            doc["days"][day] = round(doc["days"].get(day, 0.0) + usd, 6)
            doc["days"] = dict(sorted(doc["days"].items())[-60:])
            doc["calls"] = doc.get("calls", 0) + 1
            doc["total_usd"] = round(doc.get("total_usd", 0.0) + usd, 6)
            self.ledger.put(doc)

    def ask(self, user_id: str, bot: dict | None, message: str, history: list | None = None, mode: str = "change",
            backtest: dict | None = None, checker: Callable[[object], dict] = engine.check) -> dict:
        """Claude's reply to the member and, when it proposes one, the bot checked by the code (or the
        problems the code still found in it after Claude had one go at fixing them). ``bot`` is the
        member's bot when changing it, and the draft so far (or None) when creating one. ``checker``
        returns the checked bot or raises Refused; the site's also checks the bot's universe."""
        if mode not in MODES:
            raise engine.Refused("Unknown chat.")
        message = " ".join(str(message or "").split())
        if not 1 <= len(message) <= MESSAGE_MAX:
            raise engine.Refused(f"Write a message of 1 to {MESSAGE_MAX} characters.")
        turns = []
        for t in (history or [])[-TURNS_KEPT:]:
            if isinstance(t, dict) and t.get("role") in ("user", "assistant") and isinstance(t.get("text"), str) and t["text"].strip():
                turns.append({"role": t["role"], "content": t["text"][:TURN_MAX]})
        while turns and turns[0]["role"] != "user":
            turns.pop(0)
        self._reserve(user_id)
        if mode == "change":
            content, system = f"My bot now:\n{json.dumps(bot, indent=1)}\n\nMy instruction: {message}", system_prompt()
        else:
            draft = f"My draft so far:\n{json.dumps(bot, indent=1)}" if bot else "I have no draft yet."
            seen = figures(backtest) if bot else None
            content = draft + (f"\n\nThe backtest of this draft I see on the page: {seen}" if seen else "") + f"\n\nI say: {message}"
            system = create_prompt()
        messages = [*turns, {"role": "user", "content": content}]
        got = self._call(system, messages)
        if got is None or isinstance(got, str):
            return {"reply": got or "I could not put that into rules. Try saying it another way.", "proposal": None}
        reply, raw = got
        if not raw:
            return {"reply": reply, "proposal": None}
        proposed, problems = self._checked(raw, checker)
        if problems:
            # One go at fixing it, as an agent does after `check`: the member sees a bot that passed, or the problems.
            again = self._call(system, [*messages, {"role": "assistant", "content": json.dumps({"reply": reply, "bot": raw})},
                                        {"role": "user", "content": FIX.format(problems=" ".join(problems))}])
            if isinstance(again, tuple) and again[1]:
                fixed, still = self._checked(again[1], checker)
                if not still:
                    return {"reply": again[0] or reply, "proposal": fixed}
            return {"reply": reply, "proposal": None, "problems": problems}
        return {"reply": reply, "proposal": proposed}

    @staticmethod
    def _checked(raw: str, checker: Callable[[object], dict]) -> tuple[dict | None, list[str]]:
        try:
            return checker(json.loads(raw)), []
        except ValueError as exc:  # not JSON, or Refused (a ValueError) with its problems
            return None, exc.problems if isinstance(exc, engine.Refused) else ["The proposal was not valid JSON."]

    def _call(self, system: str, messages: list[dict]) -> tuple[str, str] | str | None:
        """One call to Claude, booked: (reply, bot as JSON or "") or, when it gives no such answer, a
        reply for the member (a refusal) or None (no answer that can be read)."""
        params = dict(model=self.model, max_tokens=8000, system=system, messages=messages,
                      output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": SCHEMA}})
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
            return "I can't help with that one. Try putting it as a rule for the bot."
        text = next((b.text for b in response.content if getattr(b, "type", "") == "text"), "")
        try:
            got = json.loads(text)
        except ValueError:
            return None
        return str(got.get("reply") or "").strip(), str(got.get("bot") or "").strip()


class Scripted:
    """Anthropic's API as `make demo` answers it: a few instructions done by rule, nothing spent, no
    network. It sees what the real one sees (the bot and the instruction) and answers in the same
    shape. Only for BOTLEAGUE_SAMPLE=1 with the real chat off."""

    def __init__(self):
        self.messages = self

    def create(self, **params):
        from types import SimpleNamespace as NS

        last = params["messages"][-1]["content"]
        if "\n\nI say: " in last:  # creating a bot
            head, _, said = last.partition("\n\nI say: ")
            draft = head.partition("\n\nThe backtest")[0]
            bot = json.loads(draft.removeprefix("My draft so far:\n")) if draft.startswith("My draft") else None
            reply, changed = self.build(bot, said.lower(), "\n\nThe backtest" in head)
        else:
            head, _, said = last.partition("\n\nMy instruction: ")
            bot = json.loads(head.removeprefix("My bot now:\n"))
            reply, changed = self.answer(bot, said.lower())
        text = json.dumps({"reply": reply, "bot": json.dumps(changed) if changed else ""})
        return NS(stop_reason="end_turn", usage=NS(input_tokens=0, output_tokens=0), content=[NS(type="text", text=text)])

    IDEAS = (("momentum", "Twelve-month momentum"), ("rose the most", "Twelve-month momentum"), ("trend", "Trend follower"),
             ("calm", "Calm compounders"), ("volatil", "Calm compounders"), ("quiet", "Calm compounders"),
             ("pullback", "Pullbacks in uptrends"), ("dip", "Pullbacks in uptrends"), ("high", "Near the highs"),
             ("megacap", "Megacap rotation"), ("biggest", "Megacap rotation"))

    @classmethod
    def build(cls, draft: dict | None, said: str, tested: bool) -> tuple[str, dict | None]:
        """Creating a bot: an idea picks the closest example; then it changes as `answer` does."""
        if draft is None:
            name = next((n for w, n in cls.IDEAS if w in said), None)
            if not name:
                return ("Happy to build it with you. How would you like it to pick stocks: what has risen the most "
                        "(momentum), only what is in an uptrend, the calmest ones, or the ones that just dipped in an uptrend?"), None
            bot = next(b for b in engine.examples() if b["name"] == name)
            return (f"Here is a first go: {bot['about']} Look at what it would hold, run a backtest if you like, "
                    "and tell me what to change: fewer or more stocks, how often it looks again, or calmer."), bot
        if tested and any(w in said for w in ("backtest", "how did", "think", "result")):
            return ("That is a simulation of the past among today's largest companies, which flatters it. Compare its worst "
                    "fall with the S&P 500's: if it is deeper than you would sit through, ask me to make it calmer."), None
        if any(w in said for w in ("send", "ready", "done", "happy", "good")):
            return ("When you are ready, press Send it in. The board shows it with the first name of your account, its rules "
                    "stay yours, and it starts at the next close."), None
        return cls.answer(draft, said)

    @staticmethod
    def answer(bot: dict, said: str) -> tuple[str, dict | None]:
        new = json.loads(json.dumps(bot))
        if any(w in said for w in ("defensive", "safer", "calm", "risk")):
            if not any(s["factor"] == "volatility" for s in new["score"]):
                new["score"].append({"factor": "volatility", "days": 63, "weight": -1})
            new.setdefault("market", {"factor": "trend", "days": 200, "min": 0, "cash": 1})
            new["weighting"] = "inverse_volatility"
            return ("More defensive: it also prefers the calmer stocks, gives the calmer ones more, and holds cash "
                    "while the S&P 500 is under its 200-session average."), new
        if "fewer" in said or "less stocks" in said:
            new["hold"] = max(1, round(new["hold"] * 0.6))
            new["max_weight"] = max(new["max_weight"], round(1 / new["hold"] + 0.05, 2)) if new["max_weight"] < 1 else 1
            return f"Fewer stocks: it holds the best {new['hold']} instead of {bot['hold']}.", new
        if "more stocks" in said or "spread" in said:
            new["hold"] = min(engine.BOT_HOLD_MAX, new["hold"] + 5)
            return f"More stocks: it holds the best {new['hold']} instead of {bot['hold']}.", new
        for word in ("monthly", "weekly", "daily"):
            if word in said:
                new["rebalance"] = word
                return f"It looks again {'at every close' if word == 'daily' else 'once a ' + word[:-2]} from now on.", new
        if any(w in said for w in ("sector", "tech", "bank", "energy", "health")):
            return ("The rules have no sectors: the bot chooses by figures worked out from prices. You can leave single "
                    "companies out with the switch below, or choose from a list of tickers in the advanced editor."), None
        return "What would you like to change: how many stocks it holds, how calm they are, or how often it looks again?", None
