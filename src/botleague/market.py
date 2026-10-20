"""Where the closes and the list of companies come from.

``Directory`` is the SEC's list of companies, which the SEC orders by market value: the largest US
companies are its first lines, each counted once (a company with several share classes, under its
first ticker). ``Yahoo`` reads five years of daily closes of many tickers at once with the yfinance
library, a hundred at a time, and keeps them in memory for a while. Neither takes a key, and
nothing is sent to either but tickers. ``Sample`` stands in for both on a machine with no network.

The same sources, read the same way, as the portal's (market-hub-landing: market.py, yahoo.py).
"""

from __future__ import annotations

import logging
import math
import os
import threading
import time
from datetime import date, timedelta
from typing import Any, Callable

import httpx

from .config import CLOSES_TTL_SECONDS, SEC_TICKERS_URL

log = logging.getLogger("botleague.market")

BENCHMARK = "SPY"
# After Yahoo refuses a request nothing is asked for this long; after any other failure, a while.
REFUSED_SECONDS = 300
FAILED_SECONDS = 60


class MarketUnavailable(RuntimeError):
    """The provider did not answer. Its message is safe to show."""


class TTLCache:
    def __init__(self):
        self._items: dict[str, tuple[float, Any]] = {}
        self._lock = threading.Lock()

    def get(self, key: str, ttl: float) -> Any | None:
        with self._lock:
            hit = self._items.get(key)
            if hit and time.monotonic() - hit[0] < ttl:
                return hit[1]
            return None

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            self._items[key] = (time.monotonic(), value)


def sec_loader(client: httpx.Client | None = None) -> list[tuple[str, int]]:
    """The SEC's companies as (ticker, id), largest first."""
    agent = os.environ.get("SEC_USER_AGENT", "").strip() or "market-hub contact@example.com"
    c = client or httpx.Client(timeout=30)
    try:
        resp = c.get(SEC_TICKERS_URL, headers={"User-Agent": agent})
        resp.raise_for_status()
    except httpx.HTTPError:
        raise MarketUnavailable("The SEC company list is not available right now.") from None
    out, seen = [], set()
    for row in resp.json().values():
        t = str(row["ticker"]).upper()
        if t not in seen:
            seen.add(t)
            out.append((t, int(row.get("cik_str") or 0)))
    return out


class Directory:
    def __init__(self, loader: Callable[[], list[tuple[str, int]]] = sec_loader, ttl: float = 86400):
        self._loader, self._ttl = loader, ttl
        self._companies: list[tuple[str, int]] | None = None
        self._at = 0.0
        self._lock = threading.Lock()

    def largest(self, n: int) -> list[str]:
        """The tickers of the ``n`` largest companies."""
        with self._lock:
            if self._companies is None or time.monotonic() - self._at > self._ttl:
                self._companies, self._at = self._loader(), time.monotonic()
            companies = self._companies
        out: dict[int, str] = {}
        for ticker, cik in companies:
            if len(out) >= n:
                break
            if cik:
                out.setdefault(cik, ticker)
        return list(out.values())


class Yahoo:
    def __init__(self, yf=None):
        self._yf = yf  # the yfinance module; tests pass a stand-in
        self._closes = TTLCache()
        self._quiet_until = 0.0
        self._lock = threading.Lock()

    @property
    def yf(self):
        with self._lock:
            if self._yf is None:
                import yfinance  # slow to import (pandas): only when the first close is asked for

                try:
                    yfinance.config.debug.hide_exceptions = False
                except AttributeError:
                    pass
                self._yf = yfinance
            return self._yf

    def _download(self, symbols: list[str]):
        if time.monotonic() < self._quiet_until:
            raise MarketUnavailable("The market data provider is not answering for now.")
        try:
            frame = self.yf.download(symbols, period="5y", interval="1d", auto_adjust=False, actions=False, group_by="column",
                                     threads=True, progress=False)
        except Exception as exc:  # yfinance raises its own errors and those of the HTTP library under it
            kind = type(exc).__name__
            self._quiet_until = time.monotonic() + (REFUSED_SECONDS if "RateLimit" in kind else FAILED_SECONDS)
            # The error's name only: its text can carry the address that was asked.
            log.warning("yahoo closes of %d -> %s", len(symbols), kind)
            raise MarketUnavailable("The market data provider did not answer.") from None
        log.info("yahoo closes of %d -> ok", len(symbols))
        return frame

    def closes(self, tickers: set[str] | list[str]) -> dict[str, list[tuple[str, float]]]:
        """Five years of daily closes of many tickers, oldest first: one download for each hundred
        of those not already kept. A ticker Yahoo does not answer for has none."""
        out: dict[str, list[tuple[str, float]]] = {}
        missing = []
        for t in dict.fromkeys(x.upper() for x in sorted(tickers)):
            hit = self._closes.get(t, CLOSES_TTL_SECONDS)
            if hit is None:
                missing.append(t)
            else:
                out[t] = hit
        for n in range(0, len(missing), 100):
            chunk = missing[n:n + 100]
            frame = self._download(chunk)
            close = frame["Close"] if frame is not None and not getattr(frame, "empty", True) and "Close" in frame else None
            for t in chunk:
                column = close[t] if close is not None and t in getattr(close, "columns", []) else None
                rows = [(ts.strftime("%Y-%m-%d"), float(c)) for ts, c in column.items() if c == c and c > 0] if column is not None else []
                self._closes.put(t, rows)
                out[t] = rows
        if not out.get(BENCHMARK) and BENCHMARK in {t.upper() for t in tickers}:
            raise MarketUnavailable("The market data provider is not answering for now.")
        return out


# --- Sample figures, for a machine with no network -------------------------------------------------

SAMPLE_TICKERS = (
    "NVDA MSFT AAPL GOOGL AMZN META AVGO TSLA BRK-B JPM WMT LLY V ORCL MA NFLX XOM COST JNJ HD PG ABBV BAC PLTR KO "
    "UNH GE CVX CSCO TMUS WFC AMD PM IBM MS ABT CRM GS LIN MCD AXP DIS INTU T MRK NOW RTX CAT PEP UBER VZ TMO BKNG "
    "BLK ISRG SCHW C QCOM ANET GILD SPGI TXN BA AMGN ADBE PGR BSX NEE SYK HON DHR UNP ETN PFE LOW AMAT DE TJX COF"
).split()


def _sessions(n: int, last: date) -> list[str]:
    out, d = [], last
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d -= timedelta(days=1)
    return out[::-1]


def sample_walk(ticker: str, days: list[str]) -> list[tuple[str, float]]:
    """A made-up price path, the same every time for the same ticker: a drift, waves and noise."""
    seed = sum(ord(ch) * (k + 1) for k, ch in enumerate(ticker))
    price, out = 30.0 + seed % 270, []
    drift = 0.00045 * ((seed % 9) - 3)
    for i, d in enumerate(days):
        noise = math.sin(i * 12.9898 + seed * 78.233) * 43758.5453
        noise = (noise - math.floor(noise)) - 0.5
        price *= 1 + drift + 0.006 * math.sin(i / (9 + seed % 23) + seed) + 0.024 * noise
        out.append((d, round(max(price, 1.0), 4)))
    return out


class Sample:
    """Made-up closes for 80 of the largest companies and the index, up to yesterday."""

    def __init__(self, today: Callable[[], date] = date.today):
        self.today = today

    def largest(self, n: int) -> list[str]:
        return list(SAMPLE_TICKERS[:n])

    def closes(self, tickers) -> dict[str, list[tuple[str, float]]]:
        days = _sessions(1260, self.today())
        return {t: sample_walk(t, days) for t in tickers}
