"""A bot's card: the picture a player shares (a story, a square) and its link preview.

Drawn here, on the server, so the site, the iPhone app and the preview a shared link shows are the
same picture: an SVG written from the bot's page (``League.bot``), turned into a PNG by resvg with
the site's own fonts (``fonts/``, IBM Plex, OFL). It describes what the bot did over one period and
nothing else: its face, its name, its player's first name, its place, its return and its line
against the S&P 500, and that this is a paper game.

The face is ``robot.py`` (a copy of the site's ``robot.ts``); the colours are the site's
(``site/src/styles/global.css``).
"""

from __future__ import annotations

import re
from collections import OrderedDict
from datetime import date
from functools import lru_cache
from pathlib import Path
from threading import Lock
from xml.sax.saxutils import escape

from .robot import robot_svg

FONTS = Path(__file__).parent / "fonts"
SANS = FONTS / "IBMPlexSans_400Regular.ttf"
SANS_BOLD = FONTS / "IBMPlexSans_600SemiBold.ttf"
MONO = FONTS / "IBMPlexMono_400Regular.ttf"

COLORS = {
    "page": "#0b0c0d", "deep": "#070808", "panel": "#101213", "raised": "#191b1d", "line": "#222528", "line-strong": "#3a3e42",
    "ink": "#c9c7c1", "ink-strong": "#f2f0ea", "muted": "#8c8b86", "faint": "#5f5f5b", "up": "#35c98f", "down": "#ff6b57",
}
SITE = "bots.themarkethub.app"

# The formats: a story (9:16), a square, and the link preview (Open Graph, 1.91:1).
SIZES = {"story": (1080, 1920), "square": (1080, 1080), "link": (1200, 630)}
PERIOD_KEYS = ["1d", "1w", "1m", "1y", "all"]
SESSIONS = {"1d": 1, "1w": 5, "1m": 21, "1y": 252}

WORDS = {
    "en": {
        "periods": {"1d": "Day", "1w": "Week", "1m": "Month", "1y": "Year", "all": "Since start"},
        "by": "by {handle}",
        "of": "{rank} of {n} bots",
        "index": "S&P 500",
        "starts": "Starts playing at the close of {day}",
        "joined": "Just joined the game",
        "paper": "Bot League · a paper game, no real money",
        "months": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    },
    "es": {
        "periods": {"1d": "Día", "1w": "Semana", "1m": "Mes", "1y": "Año", "all": "Desde el inicio"},
        "by": "de {handle}",
        "of": "{rank} de {n} bots",
        "index": "S&P 500",
        "starts": "Empieza a jugar en el cierre del {day}",
        "joined": "Acaba de entrar en el juego",
        "paper": "Bot League · un juego en papel, sin dinero real",
        "months": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"],
    },
}


# --- Words and numbers ---------------------------------------------------------------------------

def pct(v: float, digits: int, lang: str) -> str:
    """+12.4% or +12,4 % (the space does not break), with a true minus."""
    s = f"{v * 100:.{digits}f}"
    if float(s) == 0:
        s = s.lstrip("-")
    shown = f"{s.replace('.', ',')} %" if lang == "es" else f"{s}%"
    return ("+" if float(s) > 0 else "") + shown.replace("-", "−")


def ordinal(n: int, lang: str) -> str:
    if lang == "es":
        return f"{n}.º"
    v = n % 100
    suffix = "th" if 10 <= v % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(v % 10, "th")
    return f"{n}{suffix}"


def day(iso: str, lang: str, year: bool = True) -> str:
    d = date.fromisoformat(iso[:10])
    m = WORDS[lang]["months"][d.month - 1]
    if lang == "es":
        return f"{d.day} {m}" + (f" {d.year}" if year else "")
    return f"{m} {d.day}" + (f", {d.year}" if year else "")


def span(first: str, last: str, lang: str) -> str:
    """Oct 10 – Nov 7, 2026 / 10 oct – 7 nov 2026; one day alone when they are the same."""
    if first[:10] == last[:10]:
        return day(last, lang)
    return f"{day(first, lang, year=first[:4] != last[:4])} – {day(last, lang)}"


# --- Measuring text ------------------------------------------------------------------------------

@lru_cache(maxsize=4)
def _metrics(path: str) -> tuple[dict, dict, int]:
    from fontTools.ttLib import TTFont
    font = TTFont(path, lazy=True)
    return font.getBestCmap(), {k: v[0] for k, v in font["hmtx"].metrics.items()}, font["head"].unitsPerEm


def width(text: str, size: float, font: Path = SANS) -> float:
    """How wide a line is in a font, from its advances (no kerning: a little wider than drawn)."""
    cmap, advances, em = _metrics(str(font))
    fallback = advances.get(cmap.get(ord("M"), ""), em * 0.6)
    return sum(advances.get(cmap.get(ord(ch), ""), fallback) for ch in text) * size / em


def fit(text: str, size: float, room: float, font: Path = SANS_BOLD, lines: int = 2, smallest: float = 0.6) -> tuple[list[str], float]:
    """Words broken over up to ``lines`` lines of ``room`` pixels, the size made smaller (down to
    ``smallest`` of it) until they fit; a word too long for a line is cut with an ellipsis."""
    words = text.split() or [""]
    floor = size * smallest
    while True:
        out: list[str] = []
        for w in words:
            if out and width(f"{out[-1]} {w}", size, font) <= room:
                out[-1] = f"{out[-1]} {w}"
            else:
                out.append(w)
        if (len(out) <= lines and all(width(line, size, font) <= room for line in out)) or size <= floor:
            break
        size = max(floor, size * 0.92)
    if len(out) > lines:
        out = out[: lines - 1] + [" ".join(out[lines - 1:])]
    cut = []
    for line in out:
        while width(line, size, font) > room and len(line) > 1:
            line = line[:-2].rstrip() + "…"
        cut.append(line)
    return cut, size


def _clean(text: str) -> str:
    return escape("".join(ch for ch in (text or "") if ch >= " " or ch == "\t"), {'"': "&quot;"})


# --- The drawing ---------------------------------------------------------------------------------

def facts(page: dict, period: str, ranked: dict | None = None) -> dict:
    """What a card says for a bot and a period: the period actually used (since start when it has no
    figure for the one asked), its return, its place, the S&P 500 over the same sessions, the dates
    and the two lines from 1."""
    curve = page.get("curve") or []
    returns = page.get("returns") or {}
    if period not in PERIOD_KEYS or returns.get(period) is None:
        period = "all"
    out = {"period": period, "return": returns.get(period), "rank": (page.get("ranks") or {}).get(period),
           "of": (ranked or {}).get(period) or page.get("entrants"), "index": None, "first": None, "last": None, "bot": [], "ref": []}
    if not curve or out["return"] is None:
        return out
    if period == "all":
        window = [{"date": None, "bot": 1.0, "index": 1.0}] + curve
    else:
        window = curve[-1 - SESSIONS[period]:]
    base, end = window[0], window[-1]
    out["first"], out["last"] = window[1]["date"] if len(window) > 1 else end["date"], end["date"]
    out["bot"] = [p["bot"] / base["bot"] for p in window] if base["bot"] else []
    if base.get("index"):
        out["ref"] = [p["index"] / base["index"] if p.get("index") else None for p in window]
        if end.get("index"):
            out["index"] = end["index"] / base["index"] - 1
    return out


def _chart(x: float, y: float, w: float, h: float, bot: list[float], ref: list[float | None], stroke: float) -> str:
    """The two lines from 1, the bot's in the ink and the S&P 500's in grey, over a hairline at 1."""
    values = [v for v in bot + ref if v is not None] + [1.0]
    lo, hi = min(values), max(values)
    pad = (hi - lo) * 0.08 or 0.01
    lo, hi = lo - pad, hi + pad
    n = max(len(bot), len(ref), 2)

    def px(i: int, v: float) -> str:
        return f"{x + w * i / (n - 1):.1f},{y + h - (v - lo) / (hi - lo) * h:.1f}"

    def path(vals: list[float | None]) -> str:
        d, pen = [], "M"
        for i, v in enumerate(vals):
            if v is None:
                pen = "M"
                continue
            d.append(f"{pen}{px(i, v)}")
            pen = "L"
        return "".join(d)

    one = y + h - (1.0 - lo) / (hi - lo) * h
    parts = [f'<path d="M{x:.1f},{one:.1f}H{x + w:.1f}" stroke="{COLORS["line-strong"]}" stroke-width="{stroke * 0.4:.1f}" stroke-dasharray="{stroke * 1.4:.0f} {stroke * 1.4:.0f}"/>']
    if any(v is not None for v in ref):
        parts.append(f'<path d="{path(ref)}" fill="none" stroke="{COLORS["muted"]}" stroke-width="{stroke * 0.7:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
    if bot:
        parts.append(f'<path d="{path(bot)}" fill="none" stroke="{COLORS["ink-strong"]}" stroke-width="{stroke:.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
        last = bot[-1]
        cx, cy = px(len(bot) - 1, last).split(",")
        parts.append(f'<circle cx="{cx}" cy="{cy}" r="{stroke * 1.6:.1f}" fill="{COLORS["ink-strong"]}"/>')
    return "".join(parts)


def _robot(slug: str, x: float, y: float, size: float) -> str:
    return f'<g transform="translate({x:.1f} {y:.1f})">{robot_svg(slug, round(size))}</g>'


def _mark(x: float, y: float, size: float) -> str:
    """Bot League's mark (site/src/components/Mark.astro), ``size`` pixels high."""
    k = size / 20
    return (f'<g transform="translate({x:.1f} {y:.1f}) scale({k:.3f})" fill="none" stroke="{COLORS["ink-strong"]}" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round"><path d="M3.5 2v16M3.5 2h4l3 3v1.5L7 10M7.5 10l4 4v.5L8 18H3.5M3.5 10h10"/>'
            f'<circle cx="16.25" cy="10" r="2.5" fill="{COLORS["ink-strong"]}" stroke="none"/></g>')


def _text(x: float, y: float, text: str, size: float, color: str = COLORS["ink-strong"], weight: int = 400, anchor: str = "start",
          mono: bool = False) -> str:
    family = "IBM Plex Mono" if mono else "IBM Plex Sans"
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{family}" font-size="{size:.1f}" font-weight="{weight}" fill="{color}" '
            f'text-anchor="{anchor}">{_clean(text)}</text>')


def _legend(x: float, y: float, w: float, name: str, size: float) -> str:
    """Which line is which: the bot's in the ink, the S&P 500's in grey."""
    sw = size * 1.3
    ref = "S&P 500"
    rw = width(ref, size) + sw + size * 0.5
    room = w - rw - size * 2 - sw - size * 0.5
    label = fit(name, size, room, font=SANS, lines=1, smallest=1)[0][0]
    mid = y - size * 0.34
    return "".join([
        f'<path d="M{x:.1f} {mid:.1f}h{sw:.1f}" stroke="{COLORS["ink-strong"]}" stroke-width="{size * 0.2:.1f}" stroke-linecap="round"/>',
        _text(x + sw + size * 0.5, y, label, size, COLORS["ink"]),
        f'<path d="M{x + w - rw:.1f} {mid:.1f}h{sw:.1f}" stroke="{COLORS["muted"]}" stroke-width="{size * 0.16:.1f}" stroke-linecap="round"/>',
        _text(x + w, y, ref, size, COLORS["muted"], anchor="end"),
    ])


def _tone(v: float | None) -> str:
    return COLORS["faint"] if v is None else COLORS["up"] if v > 0 else COLORS["down"] if v < 0 else COLORS["ink"]


def svg(page: dict, period: str = "all", fmt: str = "story", lang: str = "en", ranked: dict | None = None) -> str:
    """The card as SVG markup."""
    lang = "es" if lang == "es" else "en"
    fmt = fmt if fmt in SIZES else "story"
    t = WORDS[lang]
    W, H = SIZES[fmt]
    f = facts(page, period, ranked)
    digits = 2 if f["period"] == "1d" else 1
    name, handle = page.get("name") or "", page.get("handle") or ""
    started = f["return"] is not None
    ret = pct(f["return"], digits, lang) if started else ""
    place = t["of"].format(rank=ordinal(f["rank"], lang), n=f["of"]) if started and f["rank"] else ""
    idx = f"{t['index']} {pct(f['index'], digits, lang)}" if f["index"] is not None else ""
    when = f"{t['periods'][f['period']]} · {span(f['first'], f['last'], lang)}" if started and f["first"] else ""
    waiting = t["starts"].format(day=day(page["starts"], lang)) if page.get("starts") else t["joined"]
    out: list[str] = [f'<rect width="{W}" height="{H}" fill="{COLORS["page"]}"/>']
    put = out.append

    if fmt == "story":
        m = 96
        room = W - 2 * m
        put(_mark(W / 2 - 150, 132, 52))
        put(_text(W / 2 - 80, 174, "Bot League", 46, weight=600))
        robot = 440 if started else 520
        head = 250 if started else 420
        put(_robot(page["slug"], (W - robot) / 2, head, robot))
        y = head + robot + 120
        lines, size = fit(name, 92, room)
        for line in lines:
            put(_text(W / 2, y, line, size, weight=600, anchor="middle"))
            y += size * 1.12
        put(_text(W / 2, y + 6, t["by"].format(handle=handle), 44, COLORS["muted"], anchor="middle"))
        y += 6 + 44
        if started:
            y += 92
            put(_text(W / 2, y, when, 36, COLORS["muted"], anchor="middle"))
            y += 196
            put(_text(W / 2, y, ret, 196, _tone(f["return"]), 600, "middle"))
            y += 84
            sub = "   ·   ".join(s for s in (place, idx) if s)
            put(_text(W / 2, y, sub, 44, COLORS["ink"], anchor="middle"))
            top = y + 80
            bottom = H - 290
            if f["bot"] and bottom - top > 120:
                put(_chart(m, top, room, bottom - top, f["bot"], f["ref"], 7))
                put(_legend(m, bottom + 58, room, name, 30))
        else:
            put(_text(W / 2, y + 120, waiting, 42, COLORS["ink"], anchor="middle"))
        put(f'<path d="M{m} {H - 168}H{W - m}" stroke="{COLORS["line"]}" stroke-width="2"/>')
        put(_text(W / 2, H - 104, t["paper"], 36, COLORS["muted"], anchor="middle"))
        put(_text(W / 2, H - 52, SITE, 34, COLORS["ink"], anchor="middle", mono=True))

    elif fmt == "square":
        m = 80
        put(_mark(m, 70, 40))
        put(_text(m + 56, 103, "Bot League", 36, weight=600))
        robot = 260
        put(_robot(page["slug"], m, 150, robot))
        x = m + robot + 44
        room = W - m - x
        lines, size = fit(name, 66, room)
        block = len(lines) * size * 1.12 + 50
        y = 150 + (robot - block) / 2 + size * 0.85
        for line in lines:
            put(_text(x, y, line, size, weight=600))
            y += size * 1.12
        put(_text(x, y + 4, t["by"].format(handle=handle), 36, COLORS["muted"]))
        y = 150 + robot + 90
        if started:
            put(_text(m, y, when, 32, COLORS["muted"]))
            put(_text(m, y + 140, ret, 140, _tone(f["return"]), 600))
            sub = "  ·  ".join(s for s in (place, idx) if s)
            put(_text(m, y + 206, sub, 38, COLORS["ink"]))
            top, bottom = y + 250, H - 196
            if f["bot"] and bottom - top > 60:
                put(_chart(m, top, W - 2 * m, bottom - top, f["bot"], f["ref"], 6))
                put(_legend(m, bottom + 46, W - 2 * m, name, 26))
        else:
            put(_text(m, y + 40, waiting, 40, COLORS["ink"]))
        put(f'<path d="M{m} {H - 128}H{W - m}" stroke="{COLORS["line"]}" stroke-width="2"/>')
        put(_text(m, H - 76, t["paper"], 28, COLORS["muted"]))
        put(_text(m, H - 36, SITE, 28, COLORS["ink"], mono=True))

    else:  # link
        m = 64
        robot = 300
        put(_robot(page["slug"], m, 110, robot))
        put(_mark(m, 40, 32))
        put(_text(m + 46, 66, "Bot League", 30, weight=600))
        x = m + robot + 56
        room = W - m - x
        lines, size = fit(name, 56, room, smallest=0.7)
        y = 158 if len(lines) == 1 else 140
        for line in lines:
            put(_text(x, y, line, size, weight=600))
            y += size * 1.1
        put(_text(x, y, t["by"].format(handle=handle), 30, COLORS["muted"]))
        if started:
            put(_text(x, y + 58, when, 26, COLORS["muted"]))
            put(_text(x, y + 160, ret, 100, _tone(f["return"]), 600))
            sub = "  ·  ".join(s for s in (place, idx) if s)
            sx = x + width(ret, 100, SANS_BOLD) + 36
            if sub and sx + width(sub, 30) <= W - m:
                put(_text(sx, y + 150, sub, 30, COLORS["ink"]))
                top = y + 196
            else:
                put(_text(x, y + 206, sub, 30, COLORS["ink"])) if sub else None
                top = y + 236
            if f["bot"] and H - 96 - top > 40:
                put(_chart(x, top, room, H - 96 - top, f["bot"], f["ref"], 4))
        else:
            put(_text(x, y + 80, waiting, 32, COLORS["ink"]))
        put(f'<path d="M{m} {H - 72}H{W - m}" stroke="{COLORS["line"]}" stroke-width="1.5"/>')
        put(_text(m, H - 30, t["paper"], 24, COLORS["muted"]))
        put(_text(W - m, H - 30, SITE, 24, COLORS["ink"], anchor="end", mono=True))

    body = "".join(out)
    body = re.sub(r"var\(--color-([a-z-]+)\)", lambda mt: COLORS.get(mt.group(1), COLORS["ink"]), body)
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">{body}</svg>'


# --- The link preview ---------------------------------------------------------------------------

PREVIEW_WORDS = {
    "en": {"title": "{name} · Bot League", "alt": "{name}, a bot of {handle} in Bot League, against the S&P 500",
           "paper": "Bot League is a paper game, with no real money.", "starts": "It starts playing at the close of {day}."},
    "es": {"title": "{name} · Bot League", "alt": "{name}, un bot de {handle} en Bot League, frente al S&P 500",
           "paper": "Bot League es un juego en papel, sin dinero real.", "starts": "Empieza a jugar en el cierre del {day}."},
}
_OWN = re.compile(r'\s*<meta\s+(?:property="og:(?:title|description|image(?::[a-z]+)?)"|name="twitter:card"|name="description")[^>]*>')


def preview(html: str, page: dict, image: str, lang: str, ranked: dict | None = None) -> str:
    """A bot's page with the link preview of its own: its name, what it did since it started and
    its card (``image``, the link format) in place of the site's picture."""
    lang = "es" if lang == "es" else "en"
    t, w = PREVIEW_WORDS[lang], WORDS[lang]
    f = facts(page, "all", ranked)
    name, handle = page.get("name") or "", page.get("handle") or ""
    by = w["by"].format(handle=handle)
    said = [by[:1].upper() + by[1:]]
    if f["return"] is not None:
        said.append(f"{pct(f['return'], 1, lang)} {w['periods']['all'].lower()}")
        if f["rank"]:
            said.append(w["of"].format(rank=ordinal(f["rank"], lang), n=f["of"]))
        if f["index"] is not None:
            said.append(f"{w['index']} {pct(f['index'], 1, lang)}")
        text = " · ".join(said) + ". " + t["paper"]
    else:
        text = " · ".join(said) + ". " + (t["starts"].format(day=day(page["starts"], lang)) + " " if page.get("starts") else "") + t["paper"]
    attr = lambda v: escape(v, {'"': "&quot;"})  # noqa: E731
    tags = "".join([
        f'<meta name="description" content="{attr(text)}" />',
        f'<meta property="og:title" content="{attr(t["title"].format(name=name))}" />',
        f'<meta property="og:description" content="{attr(text)}" />',
        f'<meta property="og:image" content="{attr(image)}" />',
        '<meta property="og:image:type" content="image/png" />',
        f'<meta property="og:image:width" content="{SIZES["link"][0]}" /><meta property="og:image:height" content="{SIZES["link"][1]}" />',
        f'<meta property="og:image:alt" content="{attr(t["alt"].format(name=name, handle=handle))}" />',
        '<meta name="twitter:card" content="summary_large_image" />',
    ])
    html = _OWN.sub("", html)
    html = re.sub(r"<title>[^<]*</title>", lambda _: f"<title>{escape(t['title'].format(name=name))}</title>", html, count=1)
    return html.replace("</head>", f"{tags}</head>", 1)


# --- The picture ---------------------------------------------------------------------------------

_done: OrderedDict[str, bytes] = OrderedDict()
_lock = Lock()


def png(markup: str) -> bytes:
    """The SVG as a PNG, with the fonts above and no others (the same picture on any machine). The
    last few are kept: a card changes once a close."""
    with _lock:
        if markup in _done:
            _done.move_to_end(markup)
            return _done[markup]
    import resvg_py
    data = bytes(resvg_py.svg_to_bytes(svg_string=markup, skip_system_fonts=True, font_files=[str(SANS), str(SANS_BOLD), str(MONO)],
                                       font_family="IBM Plex Sans", sans_serif_family="IBM Plex Sans", monospace_family="IBM Plex Mono"))
    with _lock:
        _done[markup] = data
        while len(_done) > 48:
            _done.popitem(last=False)
    return data
