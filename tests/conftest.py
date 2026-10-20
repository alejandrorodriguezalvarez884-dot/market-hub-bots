"""Helpers shared by the tests: sessions, made-up closes, a clock, a market that moves on, and a
Market Hub session cookie signed as the hub signs it."""

import json
import math
import sys
from base64 import b64encode
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

import itsdangerous

sys.path.insert(0, str(Path(__file__).parent))

from botleague.engine import NEW_YORK  # noqa: E402

SECRET = "test-hub-secret"
HUB = "https://hub.test"
ORIGIN = "http://testserver"


def sessions(n: int, first: date = date(2024, 1, 8)) -> list[str]:
    out, d = [], first
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def at(day: str, hour: int, minute: int = 0) -> datetime:
    """A moment of a session's day, in New York, as the clock gives it (UTC)."""
    return datetime.combine(date.fromisoformat(day), time(hour, minute), NEW_YORK).astimezone(timezone.utc)


def walk(ticker: str, days: list[str]) -> list[tuple[str, float]]:
    seed = sum(map(ord, ticker))
    price, out = 40.0 + seed % 60, []
    for i, d in enumerate(days):
        price *= 1 + 0.0004 * (seed % 5 - 2) + 0.012 * math.sin(i / (5 + seed % 7) + seed)
        out.append((d, round(price, 4)))
    return out


def steady(days: list[str], daily: float, start: float = 100.0) -> list[tuple[str, float]]:
    return [(d, start * (1 + daily) ** i) for i, d in enumerate(days)]


class Clock:
    def __init__(self, when: datetime):
        self.when = when

    def __call__(self):
        return self.when


class Market:
    """Closes for any ticker, up to a session the test moves on."""

    def __init__(self, days: list[str], upto: str):
        self.days, self.upto, self.gone, self.asked = days, upto, set(), 0

    def __call__(self, tickers):
        self.asked += 1
        return {t: [] if t in self.gone else [(d, c) for d, c in walk(t, self.days) if d <= self.upto] for t in tickers}


def hub_cookie(user_id: str, name: str = "Ana", secret: str = SECRET) -> str:
    """A session cookie as Market Hub's portal writes it (Starlette's signed session)."""
    data = b64encode(json.dumps({"user": {"id": user_id, "email": f"{user_id}@example.com", "name": name, "picture": ""}}).encode())
    return itsdangerous.TimestampSigner(secret).sign(data).decode()
