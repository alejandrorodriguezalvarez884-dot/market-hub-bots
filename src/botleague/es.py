"""What the service says to a page in Spanish (docs/i18n.md).

The page sends ``X-MH-Lang: es`` with every call when it is in Spanish; with no such header (the
kit's mh.py, the mobile app, the portal) everything stays in English. Data never changes, only words.

The engine (engine.py) is a copy of the portal's and writes its messages in English: they are put
into Spanish here, at the edge of the API, with a table of the engine's sentences and the site's
own. A message the table does not know goes out as it came.
"""

from __future__ import annotations

import re

from . import engine
from .config import BOT_COST

LANG_HEADER = "x-mh-lang"


def lang_of(request) -> str:
    """The language a page asked for: "es" only when it says so, "en" otherwise."""
    return "es" if (request.headers.get(LANG_HEADER) or "").strip().lower() == "es" else "en"


# --- The format, for the Rules page -------------------------------------------------------------

FACTOR_NOTES_ES = {
    "momentum": "Rentabilidad en `days` sesiones, hasta hace `skip` sesiones. `0.25` es +25 %.",
    "trend": "Último cierre entre su media de los últimos `days` cierres, menos uno. Por encima de 0: sobre la media.",
    "sma_cross": "Media de los últimos `fast` cierres entre la de los últimos `slow`, menos uno. Por encima de 0: la media corta está sobre la larga.",
    "volatility": "Desviación típica de las rentabilidades diarias en `days` sesiones, anualizada. `0.30` es 30 %.",
    "rsi": "Índice de fuerza relativa de Wilder en `days` sesiones, de 0 a 100.",
    "drawdown": "Último cierre frente al cierre más alto de las últimas `days` sesiones, menos uno. 0 en un máximo, `-0.2` un 20 % por debajo.",
    "beta": "Cuánto se ha movido la acción con el S&P 500 (SPY) en `days` sesiones. 1 se mueve con él.",
}


def spec(lang: str = "en") -> dict:
    """The engine's spec, with what each factor means in the page's language."""
    out = engine.spec()
    if lang == "es":
        for name, f in out["factors"].items():
            f["means"] = FACTOR_NOTES_ES.get(name, f["means"])
    return out


PERIODS_ES = {"1d": "Día", "1w": "Semana", "1m": "Mes", "1y": "Año"}


def periods(items: list[dict], lang: str) -> list[dict]:
    return [{**p, "label": PERIODS_ES.get(p["key"], p["label"])} for p in items] if lang == "es" else items


# --- Messages ------------------------------------------------------------------------------------

# The engine's sentences (engine.py: check, resolve, Bots), league.py's, chat.py's, the API's and
# the market's, each with its Spanish. {name} stands for a value, kept as it is.
_COST = f"{BOT_COST * 100:.2f}"
MESSAGES: list[tuple[str, str]] = [
    # engine.check and its helpers
    ('{where}: each one is an object with a "factor".', '{where}: cada uno es un objeto con un "factor".'),
    ('{where}: "factor" is one of {names}.', '{where}: "factor" es uno de estos: {names}.'),
    ('{where}: {name} has no field "{k}" (it takes {names}).', '{where}: {name} no tiene el campo "{k}" (admite {names}).'),
    ('{where}: {name} needs "{k}", a whole number from {low} to {high}.', '{where}: {name} necesita "{k}", un número entero de {low} a {high}.'),
    ('{where}: {name}\'s "{k}" is a whole number from {low} to {high}.', '{where}: el "{k}" de {name} es un número entero de {low} a {high}.'),
    ('{where}: sma_cross\'s "fast" is shorter than its "slow".', '{where}: el "fast" de sma_cross es más corto que su "slow".'),
    ('{where}: "{k}" is a number.', '{where}: "{k}" es un número.'),
    ('{where}: give a "min", a "max" or both.', '{where}: pon un "min", un "max" o los dos.'),
    ('{where}: "min" is above "max".', '{where}: "min" está por encima de "max".'),
    ("{where} is a list of {low} to {high} tickers.", "{where} es una lista de {low} a {high} tickers."),
    ("{where}: {value} is not a ticker.", "{where}: {value} no es un ticker."),
    ("{where}: {t} is there twice.", "{where}: {t} está dos veces."),
    ("A bot is a JSON object: see SPEC.md in the kit.", "Un bot es un objeto JSON: mira SPEC.md en el kit."),
    ('There is no field "{k}" (a bot takes {names}).', 'No existe el campo "{k}" (un bot admite {names}).'),
    ('"format" is "{format}".', '"format" es "{format}".'),
    ('"name" is the bot\'s name, 3 to 40 characters.', '"name" es el nombre del bot, de 3 a 40 caracteres.'),
    ('That "name" cannot be shown.', 'Ese "name" no se puede mostrar.'),
    ('"about" is at most 280 characters.', '"about" tiene como mucho 280 caracteres.'),
    ('That "about" cannot be shown.', 'Ese "about" no se puede mostrar.'),
    ('"universe" is an object: {"largest": 500} or {"tickers": [...]}.', '"universe" es un objeto: {"largest": 500} o {"tickers": [...]}.'),
    ('"universe" has no field "{k}" (it takes largest, tickers and exclude).', '"universe" no tiene el campo "{k}" (admite largest, tickers y exclude).'),
    ('"universe" takes "largest" or "tickers", one of the two.', '"universe" admite "largest" o "tickers", uno de los dos.'),
    ('"universe.largest" is a whole number from 20 to {high}.', '"universe.largest" es un número entero de 20 a {high}.'),
    ('"rebalance" is one of {names}.', '"rebalance" es uno de estos: {names}.'),
    ('"filters" is a list of at most 8.', '"filters" es una lista de 8 como mucho.'),
    ('"score" is a list of 1 to 8 factors, each with a "weight".', '"score" es una lista de 1 a 8 factores, cada uno con un "weight".'),
    ('score[{n}]: "weight" is a number from -5 to 5, not 0 (below 0 prefers the lowest).',
     'score[{n}]: "weight" es un número de -5 a 5, distinto de 0 (por debajo de 0 prefiere los valores más bajos).'),
    ('"hold" is how many stocks it holds, a whole number from 1 to {high}.', '"hold" es cuántas acciones mantiene, un número entero de 1 a {high}.'),
    ('"weighting" is one of {names}.', '"weighting" es uno de estos: {names}.'),
    ('"max_weight" is the most one stock can be, from 0.02 to 1.', '"max_weight" es el peso máximo de una acción, de 0,02 a 1.'),
    ('"market.cash": the share held in cash when the market is out of its bounds, above 0 and up to 1.',
     '"market.cash": la parte que se mantiene en liquidez cuando el mercado está fuera de sus límites, por encima de 0 y hasta 1.'),
    # engine.resolve
    ("Not among the {high} largest US companies (funds are left out): {names}.",
     "No están entre las {high} mayores empresas de EE. UU. (los fondos no cuentan): {names}."),
    ("The universe leaves fewer than two companies to choose from.", "El universo deja menos de dos empresas entre las que elegir."),
    ('"hold" is {hold}, and the universe has {n} companies.', '"hold" es {hold} y el universo tiene {n} empresas.'),
    # engine.Bots
    ('"years" is a whole number from 1 to {high}.', '"years" es un número entero de 1 a {high}.'),
    ("There are not enough closes to backtest on yet.", "Todavía no hay cierres suficientes para hacer el backtest."),
    ("The competition is full for now.", "La competición está completa por ahora."),
    ("There is no bot to rename: send one in first.", "No hay ningún bot al que cambiar el nombre: envía uno primero."),
    ("There is no bot to change: send one in first.", "No hay ningún bot que cambiar: envía uno primero."),
    ("A bot leaves out at most 100 companies.", "Un bot deja fuera 100 empresas como mucho."),
    ("The rules can change once a day. Try again tomorrow.", "Las reglas se pueden cambiar una vez al día. Vuelve a intentarlo mañana."),
    ("Give the ticker of a company.", "Indica el ticker de una empresa."),
    ("{t} is already left out.", "{t} ya está excluida."),
    ("{t} is not among the companies the bot chooses from.", "{t} no está entre las empresas entre las que elige el bot."),
    ("Without {t} the bot would have too few companies to choose from.", "Sin {t}, el bot tendría muy pocas empresas entre las que elegir."),
    ("{t} is not left out.", "{t} no está excluida."),
    ('The switches are "pause", "resume", "exclude" and "include".', 'Los interruptores son "pause", "resume", "exclude" e "include".'),
    # engine.Bots.backtest's notes
    ("A simulation on past closes: no money, no orders, and nothing it says about the future.",
     "Una simulación sobre cierres pasados: sin dinero, sin órdenes y sin decir nada del futuro."),
    ("It chooses among today's largest companies, which did well to become so: the past looks better than it was.",
     "Elige entre las mayores empresas de hoy, a las que les fue bien para llegar a serlo: el pasado parece mejor de lo que fue."),
    (f"It pays {_COST}% on what it trades. Dividends are left out, as in the competition.",
     f"Paga un {_COST.replace('.', ',')} % sobre lo que negocia. Los dividendos no se cuentan, como en la competición."),
    # league.py
    ("There is no change waiting for the next close.", "No hay ningún cambio esperando al próximo cierre."),
    # chat.py
    ("Unknown chat.", "Chat desconocido."),
    ("Write a message of 1 to {high} characters.", "Escribe un mensaje de 1 a {high} caracteres."),
    ("The proposal was not valid JSON.", "La propuesta no era un JSON válido."),
    # api.py
    ("Cross-site request refused.", "Petición desde otro sitio rechazada."),
    ("Too many requests from this address. Try again later.", "Demasiadas peticiones desde esta dirección. Vuelve a intentarlo más tarde."),
    ("Sign in with your account on The Market Hub.", "Entra con tu cuenta de The Market Hub."),
    ("Members' bots are seen by members: sign in with your account on The Market Hub.",
     "Los bots de los miembros solo los ven los miembros: entra con tu cuenta de The Market Hub."),
    ("There is no such bot.", "Ese bot no existe."),
    ("That is {n} changes today. Try again tomorrow.", "Ya llevas {n} cambios hoy. Vuelve a intentarlo mañana."),
    ("That is {n} previews in an hour. Try again later.", "Ya llevas {n} vistas previas en una hora. Vuelve a intentarlo más tarde."),
    ("That is {n} backtests and previews in an hour. Try again later.",
     "Ya llevas {n} backtests y vistas previas en una hora. Vuelve a intentarlo más tarde."),
    ("That is {n} backtests in an hour. Try again later.", "Ya llevas {n} backtests en una hora. Vuelve a intentarlo más tarde."),
    ("That is {n} bots sent in a day. Try again tomorrow.", "Ya llevas {n} bots enviados en un día. Vuelve a intentarlo mañana."),
    ("No key, or not a good one: make one on your page of Bot League (/me/) and put it in .env.",
     "No hay clave, o no es válida: crea una en tu página de Bot League (/me/) y ponla en .env."),
    # market.py
    ("The SEC company list is not available right now.", "La lista de empresas de la SEC no está disponible ahora mismo."),
    ("The market data provider is not answering for now.", "El proveedor de datos de mercado no responde por ahora."),
    ("The market data provider did not answer.", "El proveedor de datos de mercado no ha respondido."),
    ("The market data provider has no closes for the benchmark.", "El proveedor de datos de mercado no tiene cierres del índice de referencia."),
]

_SLOT = re.compile(r"\{(\w+)\}")


def _pattern(english: str) -> re.Pattern:
    """An English sentence with {slots} as a pattern that matches it whole. A literal "{...}" that
    is not a single word (the JSON in the universe's message) stays literal."""
    out, at = [], 0
    for m in _SLOT.finditer(english):
        out.append(re.escape(english[at:m.start()]) + f"(?P<{m.group(1)}>.+?)")
        at = m.end()
    return re.compile("".join(out) + re.escape(english[at:]), re.DOTALL)


_TABLE = [(_pattern(en), es) for en, es in MESSAGES]


def say(text, lang: str):
    """A message in the page's language: Spanish when the table knows it, as it came otherwise."""
    if lang != "es" or not isinstance(text, str):
        return text
    for pattern, es in _TABLE:
        m = pattern.fullmatch(text)
        if m:
            return _SLOT.sub(lambda s: m.group(s.group(1)) if s.group(1) in m.groupdict() else s.group(0), es)
    return text


def problems(items: list[str], lang: str) -> list[str]:
    return [say(p, lang) for p in items]


# --- Rules in words --------------------------------------------------------------------------------


def rules(out, lang: str):
    """A bot as a page gets it, with its rules in the page's language: they are written again from
    the bot that comes with them ("bot", and the change waiting in "pending"; "you" on the overview).
    Without the universe's list, describe() reads the tickers less those left out, which is what
    the engine's resolve() keeps for a list of tickers, so the words are the same."""
    if lang != "es" or not isinstance(out, dict):
        return out
    if isinstance(out.get("bot"), dict) and "rules" in out:
        out["rules"] = engine.describe(out["bot"], lang=lang)
    for key in ("pending", "you"):
        if isinstance(out.get(key), dict):
            rules(out[key], lang)
    return out
