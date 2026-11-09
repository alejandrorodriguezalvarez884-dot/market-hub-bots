"""Why a bot made each move, in words, from what the engine kept when it rebalanced (engine.reasons).

Each logged rebalance since 2026-11-10 keeps, for every stock it bought, sold, raised or cut, its
place in the bot's ranking, every figure of its filters and score at that close, and what kept it or
left it out; and, for the move, how many companies passed and how many places it fills, the market
rule's figure and the rules it read. Older moves have none of it and read as before.

Two readers. The bot's owner gets everything: the figures, the filters' thresholds, the market
rule's figure, the weighting and the cap. Everyone else gets what the rules did without what the
rules are: the kind of reason ("did not pass one of its filters", "placed 12th by its score, under
the best 10 it holds", "left out by its owner") and the place in its ranking, never a figure, a
factor, a threshold or a setting. Holdings, weights, cash, a pause and the changes of its rules
(excluded, pinned) are public already, so they may be named.

It describes what the rules did; never that a stock is good, bad or worth anything.
"""

from __future__ import annotations

from . import engine

TEXT = {
    "en": {
        "ranked": "At this close {passed} of the {of} companies it looks at passed its filters; it holds the best {slots} by its score.",
        "ranked_one": "At this close {passed} of the {of} companies it looks at passed its filters; it holds the best one by its score.",
        "scored": "At this close it scored {passed} of the {of} companies it looks at; it holds the best {slots}.",
        "scored_one": "At this close it scored {passed} of the {of} companies it looks at; it holds the best one.",
        "holds": "It holds the best {slots} by its score.",
        "holds_one": "It holds the best one by its score.",
        "always_only": "It holds only the companies it always holds.",
        "count": "It now holds {n}; before, {m}.",
        "market_out": "Its market rule: for the S&P 500, {what} was {value}, not {range}, so it holds {cash}% in cash.",
        "market_in": "Its market rule: for the S&P 500, {what} was {value}, {range} again, so it is invested again.",
        "market_out_public": "Its market rule moved part of the portfolio to cash.",
        "market_all_public": "Its market rule moved the portfolio to cash.",
        "market_in_public": "Its market rule let it back out of cash.",
        "paused": "Paused by its owner: it moved to cash.",
        "equal": "Equal parts: each one it picks by its score gets the same share{cap}.",
        "score": "The better placed by its score get more{cap}.",
        "inverse_volatility": "The calmer get more: each by one over its volatility over 63 sessions{cap}.",
        "cap": ", none above {x}%",
        "rank": "Placed {nth} by its score.",
        "always": "Always held, whatever its other rules say.",
        "always_least": "Always held, whatever its other rules say, with at least {x}%.",
        "at_cap": "At its cap of {x}%.",
        "below": "Placed {nth} by its score, under the best {slots} it holds.",
        "below_one": "Placed {nth} by its score, under the best one it holds.",
        "filter": "Did not pass one of its filters.",
        "filter_full": "Did not pass its filter: {what} was {value}, not {range}.",
        "missing": "No close or no figure for it at this close.",
        "excluded": "Left out by its owner.",
        "left": "No longer among the companies it looks at: its rules changed.",
        "paused_one": "Paused: it holds cash.",
        "cash": "Its market rule moved the portfolio to cash.",
        "drift": "Back to the share it got at the last rebalance, {x}%: prices had moved it.",
        "figure": "{what}: {value}",
        "figure_filter": "{what}: {value} (needs {range})",
        "volatility": "Its volatility over 63 sessions: {value}",
    },
    "es": {
        "ranked": "En este cierre, {passed} de las {of} empresas que mira pasaron sus filtros; mantiene las {slots} mejores por su puntuación.",
        "ranked_one": "En este cierre, {passed} de las {of} empresas que mira pasaron sus filtros; mantiene la mejor por su puntuación.",
        "scored": "En este cierre puntuó {passed} de las {of} empresas que mira; mantiene las {slots} mejores.",
        "scored_one": "En este cierre puntuó {passed} de las {of} empresas que mira; mantiene la mejor.",
        "holds": "Mantiene las {slots} mejores por su puntuación.",
        "holds_one": "Mantiene la mejor por su puntuación.",
        "always_only": "Solo tiene las empresas que mantiene siempre.",
        "count": "Ahora tiene {n}; antes, {m}.",
        "market_out": "Su regla de mercado: para el S&P 500, {what} era {value}, no {range}, así que mantiene el {cash} % en liquidez.",
        "market_in": "Su regla de mercado: para el S&P 500, {what} era {value}, otra vez {range}, así que vuelve a invertir.",
        "market_out_public": "Su regla de mercado pasó parte de la cartera a liquidez.",
        "market_all_public": "Su regla de mercado pasó la cartera a liquidez.",
        "market_in_public": "Su regla de mercado le dejó volver a invertir.",
        "paused": "En pausa por decisión de su dueño: pasó a liquidez.",
        "equal": "A partes iguales: cada una de las que elige por su puntuación recibe lo mismo{cap}.",
        "score": "Las mejor puntuadas reciben más{cap}.",
        "inverse_volatility": "Las más tranquilas reciben más: cada una según la inversa de su volatilidad en 63 sesiones{cap}.",
        "cap": ", ninguna por encima del {x} %",
        "rank": "Puesto {nth} por su puntuación.",
        "always": "La mantiene siempre, digan lo que digan sus otras reglas.",
        "always_least": "La mantiene siempre, digan lo que digan sus otras reglas, con al menos el {x} %.",
        "at_cap": "En su máximo del {x} %.",
        "below": "Puesto {nth} por su puntuación, fuera de las {slots} mejores que mantiene.",
        "below_one": "Puesto {nth} por su puntuación, fuera de la mejor, que es la que mantiene.",
        "filter": "No pasó uno de sus filtros.",
        "filter_full": "No pasó su filtro: {what} era {value}, no {range}.",
        "missing": "Sin cierre o sin cifra en este cierre.",
        "excluded": "Excluida por su dueño.",
        "left": "Ya no está entre las empresas que mira: cambiaron sus reglas.",
        "paused_one": "En pausa: está en liquidez.",
        "cash": "Su regla de mercado pasó la cartera a liquidez.",
        "drift": "Vuelve al peso que tenía en el último rebalanceo, el {x} %: los precios lo habían movido.",
        "figure": "{what}: {value}",
        "figure_filter": "{what}: {value} (pide {range})",
        "volatility": "Su volatilidad en 63 sesiones: {value}",
    },
}


def _nth(n: int, lang: str) -> str:
    if lang == "es":
        return str(n)
    end = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{end}"


def _pct(x: float, lang: str) -> str:
    out = f"{x * 100:.4g}"
    return out.replace(".", ",") if lang == "es" else out


def _value(name: str, v: float, lang: str) -> str:
    """A figure as its owner reads it: a percentage with one decimal under 10% (never "−0%"), a
    volatility without a sign, an RSI or a beta as a number."""
    if name in engine.PERCENT:
        x = v * 100
        out = "0" if abs(x) < 0.05 else f"{x:.1f}" if abs(x) < 9.95 else f"{x:.0f}"
        if name != "volatility" and out != "0" and x > 0:
            out = "+" + out
        out = out.replace("-", "−")
        return (out.replace(".", ",") + " %") if lang == "es" else out + "%"
    out = f"{v:.3g}".replace("-", "−")
    return out.replace(".", ",") if lang == "es" else out


def _cap(s: str) -> str:
    return s[:1].upper() + s[1:]


def _figures(e: dict, rules: dict, lang: str) -> list[str]:
    """Every figure its rules read for one stock at that close, each with what it is."""
    t, out = TEXT[lang], []
    for f, v in zip(rules.get("score") or [], e.get("s") or []):
        if v is not None:
            out.append(t["figure"].format(what=_cap(engine._what(f, lang)), value=_value(f["factor"], v, lang)))
    for f, v in zip(rules.get("filters") or [], e.get("f") or []):
        if v is not None:
            out.append(t["figure_filter"].format(what=_cap(engine._what(f, lang)), value=_value(f["factor"], v, lang),
                                                 range=engine._range(f, lang)))
    if e.get("vol") is not None:
        out.append(t["volatility"].format(value=_value("volatility", e["vol"], lang)))
    return out


def _one(e: dict, why: dict, before: float, after: float, last: float | None, lang: str, full: bool) -> dict:
    """Why one stock moved: a sentence, and for the owner the figures behind it."""
    t, rules, slots = TEXT[lang], why.get("rules") or {}, why.get("slots", 0)
    nth = _nth(e["rank"], lang) if e.get("rank") else ""
    kind = e.get("why")
    said: list[str] = []
    if kind == "rank":
        said.append(t["rank"].format(nth=nth) if nth else "")
    elif kind == "always":
        least = e.get("least") or 0
        said.append(t["always_least"].format(x=_pct(least, lang)) if full and least > 0 else t["always"])
    elif kind == "below":
        said.append(t["below_one" if slots == 1 else "below"].format(nth=nth, slots=slots))
    elif kind == "filter":
        k, filters = e.get("fail", 0), rules.get("filters") or []
        values = e.get("f") or []
        if full and k < len(filters) and k < len(values) and values[k] is not None:
            f = filters[k]
            said.append(t["filter_full"].format(what=engine._what(f, lang), value=_value(f["factor"], values[k], lang),
                                                range=engine._range(f, lang)))
        else:
            said.append(t["filter"])
    elif kind in ("missing", "excluded", "left", "cash"):
        said.append(t[kind])
    elif kind == "paused":
        said.append(t["paused_one"])
    if full and e.get("cap") and rules.get("max_weight", 1) < 1:
        said.append(t["at_cap"].format(x=_pct(rules["max_weight"], lang)))
    if before and after and last is not None and abs(after - last) < engine.MOVED:
        said.append(t["drift"].format(x=_pct(last, lang)))
    out = {"why": " ".join(s for s in said if s)}
    if full:
        out["figures"] = _figures(e, rules, lang)
    return out


def _move(m: dict, why: dict, prev: dict | None, lang: str, full: bool) -> dict:
    """Why one rebalance moved what it moved: a few sentences for the move, and one for each stock."""
    t, rules = TEXT[lang], why.get("rules") or {}
    lines: list[str] = []
    after, before = m.get("after") or {}, {}
    for x in m.get("sold", []):
        before[x["ticker"]] = x["weight"]
    for x in m.get("raised", []) + m.get("cut", []):
        before[x["ticker"]] = x["before"]
    if why.get("paused"):
        lines.append(t["paused"])
    else:
        slots = why.get("slots", 0)
        if not slots:
            lines.append(t["always_only"])
        elif full:
            key = ("ranked" if rules.get("filters") else "scored") + ("_one" if slots == 1 else "")
            lines.append(t[key].format(passed=why.get("passed", 0), of=why.get("of", 0), slots=slots))
        else:
            lines.append(t["holds_one" if slots == 1 else "holds"].format(slots=slots))
        market, was = why.get("market"), ((prev or {}).get("why") or {}).get("market")
        m_rule = rules.get("market")
        if market and (market.get("out") or (was and was.get("out"))):
            out = bool(market.get("out"))
            if full and m_rule and market.get("value") is not None:
                lines.append(t["market_out" if out else "market_in"].format(
                    what=engine._what(m_rule, lang), value=_value(m_rule["factor"], market["value"], lang),
                    range=engine._range(m_rule, lang), cash=_pct(m_rule.get("cash", 1), lang)))
            elif out:
                lines.append(t["market_all_public" if m_rule and m_rule.get("cash", 1) >= 1 else "market_out_public"])
            else:
                lines.append(t["market_in_public"])
        if full and after and (m.get("bought") or m.get("raised") or m.get("cut")) and rules.get("weighting") in ("equal", "score", "inverse_volatility"):
            cap = t["cap"].format(x=_pct(rules["max_weight"], lang)) if rules.get("max_weight", 1) < 1 else ""
            lines.append(t[rules["weighting"]].format(cap=cap))
    if prev is not None and len(prev.get("after") or {}) != len(after) and after and prev.get("after"):
        lines.append(t["count"].format(n=len(after), m=len(prev["after"])))
    last = (prev or {}).get("after") if prev is not None else None
    names = {}
    for tk, e in (why.get("names") or {}).items():
        names[tk] = _one(e, why, before.get(tk, 0.0), after.get(tk, 0.0), (last or {}).get(tk) if last is not None else None, lang, full)
    return {"full": full, "lines": lines, "names": names}


def told(log: list[dict] | None, lang: str = "en", full: bool = False) -> list[dict]:
    """A bot's moves as engine.activity() gives them (latest first), each move's "why" put in words
    as "reasons": everything for the owner (``full``), what the rules did without what they are for
    everyone else. A move with no "why" is left as it is."""
    lang = "es" if lang == "es" else "en"
    log = log or []
    out = []
    for k, m in enumerate(log):
        raw = m.get("why")
        shown = {key: v for key, v in m.items() if key != "why"}
        if isinstance(raw, dict):
            shown["reasons"] = _move(m, raw, log[k + 1] if k + 1 < len(log) else None, lang, full)
        out.append(shown)
    return out


def page(out, lang: str, full: bool):
    """A page with a bot's moves ("log", and "you" on the overview), with their reasons in words."""
    if not isinstance(out, dict):
        return out
    if isinstance(out.get("log"), list):
        out["log"] = told(out["log"], lang, full)
    if isinstance(out.get("you"), dict):
        page(out["you"], lang, full)
    return out
