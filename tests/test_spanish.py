"""The service in Spanish: what a page that sends X-MH-Lang: es gets, and that everything else (the
kit's agent, the portal, the mobile app) still gets English."""

import ast
import io
import zipfile
from pathlib import Path

import pytest

from botleague import es
from botleague.chat import Chat, MemoryLedger, Scripted
from botleague.engine import check, describe, examples
from test_api import BOT, client, make, send

ES = {"x-mh-lang": "es"}
SRC = Path(__file__).parent.parent / "src" / "botleague"


def spanish(app, user_id=None):
    c = client(app, user_id)
    c.headers.update(ES)
    return c


def test_the_language_comes_from_the_page_header_only():
    class R:
        def __init__(self, headers):
            self.headers = headers
    assert es.lang_of(R({"x-mh-lang": "es"})) == "es" and es.lang_of(R({"x-mh-lang": " ES "})) == "es"
    assert es.lang_of(R({})) == "en" and es.lang_of(R({"x-mh-lang": "fr"})) == "en"
    assert es.lang_of(R({"accept-language": "es-ES"})) == "en"  # the browser's own header is not the page's choice


def _sentences(path: Path) -> list[str]:
    """Every message a module raises or reports, with each value as "Q1"."""
    def text(node) -> str | None:
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            return "".join(v.value if isinstance(v, ast.Constant) else "Q1" for v in node.values)
        return None

    out = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        name = f.id if isinstance(f, ast.Name) else f.attr if isinstance(f, ast.Attribute) else ""
        if name in ("Refused", "MarketUnavailable") or (name == "append" and isinstance(f.value, ast.Name) and f.value.id == "problems"):
            args = node.args[:1]
        elif name == "HTTPException":
            args = node.args[1:2] + [k.value.values[0] for k in node.keywords if k.arg == "detail" and isinstance(k.value, ast.Dict)]
        else:
            continue
        out += [t for t in map(text, args) if t]
    return out


@pytest.mark.parametrize("module", ["engine.py", "league.py", "chat.py", "api.py", "market.py"])
def test_every_message_a_page_can_see_has_its_spanish(module):
    found = _sentences(SRC / module)
    assert found
    for sentence in found:
        assert es.say(sentence, "es") != sentence, sentence
        assert es.say(sentence, "en") == sentence


def test_the_values_of_a_message_stay_as_they_were():
    assert es.say("NVDA is already left out.", "es") == "NVDA ya está excluida."
    assert es.say('score[2]: "weight" is a number from -5 to 5, not 0 (below 0 prefers the lowest).', "es").startswith('score[2]: "weight" es un número')
    assert es.say('"universe" is an object: {"largest": 500} or {"tickers": [...]}.', "es") == '"universe" es un objeto: {"largest": 500} o {"tickers": [...]}.'
    assert es.say("Something the table does not know.", "es") == "Something the table does not know."


def test_the_rules_in_words_in_spanish():
    words = describe(check(next(r for r in examples() if r["name"] == "Trend follower")), lang="es")
    assert words[0] == "Mira las 300 mayores empresas de EE. UU."
    assert "Se queda con aquellas en las que su cierre frente a su media de 200 sesiones es al menos 0 %." in words
    assert words[-1] == "Cuando, para el S&P 500, su cierre frente a su media de 200 sesiones no es al menos 0 %, mantiene el 100 % en liquidez."
    one = describe(check({**BOT, "hold": 1, "max_weight": 0.25, "universe": {"largest": 30, "exclude": ["AAPL", "MSFT"]},
                          "score": [{"factor": "beta", "days": 63, "weight": -0.5}], "filters": [{"factor": "momentum", "days": 63, "skip": 5, "min": -0.2, "max": 0.25}]}),
                   lang="es")
    assert one == ["Mira las 30 mayores empresas de EE. UU., sin contar AAPL, MSFT.",
                   "Se queda con aquellas en las que su rentabilidad en 63 sesiones, sin contar las últimas 5 es entre −20 % y +25 %.",
                   "Las puntúa por su beta al S&P 500 en 63 sesiones (mejor cuanto más bajo, peso 0,5).",
                   "Mantiene la mejor, a partes iguales, ninguna por encima del 25 %.",
                   "Revisa la cartera en el primer cierre de cada mes."]


def test_a_spanish_page_gets_spanish_words_and_the_same_figures():
    app = make(public=True)
    send(app, "u1")
    en, sp = client(app, "u1").get("/api/bots").json(), spanish(app, "u1").get("/api/bots").json()
    assert en["you"]["rules"][0] == "Looks at the 30 largest US companies."
    assert sp["you"]["rules"][0] == "Mira las 30 mayores empresas de EE. UU." and sp["you"]["rules"][-1].startswith("Revisa la cartera")
    assert [p["label"] for p in sp["periods"]] == ["Día", "Semana", "Mes", "Año"] and en["periods"][0]["label"] == "Day"
    assert {**sp, "you": None, "periods": None} == {**en, "you": None, "periods": None}
    assert {**sp["you"], "rules": None} == {**en["you"], "rules": None}
    slug = app.state.store.get("u1")["public_id"]
    assert spanish(app, "u1").get(f"/api/board/bot/{slug}").json()["rules"][0].startswith("Mira las")
    assert client(app, "u1").get(f"/api/board/bot/{slug}").json()["rules"][0].startswith("Looks at")
    # A change waiting for the next close, in words, and the codes of what changed as they are.
    got = spanish(app, "u1").post("/api/bots/mine/switch", json={"action": "exclude", "ticker": "AAPL"}).json()
    assert got["rules"][0] == "Mira las 30 mayores empresas de EE. UU., sin contar AAPL." and got["exclude"] == ["AAPL"]
    shown = es.rules({"rules": ["x"], "bot": check(BOT), "pending": {"what": ["excluded AAPL"], "rules": ["y"], "bot": check({**BOT, "hold": 3})}}, "es")
    assert shown["rules"][0] == "Mira las 30 mayores empresas de EE. UU." and shown["pending"]["rules"][2].startswith("Mantiene las 3 mejores")
    assert shown["pending"]["what"] == ["excluded AAPL"]  # the codes of what changed stay as they are: the page words them


def test_errors_on_a_page_route_follow_the_page():
    app = make()
    send(app, "u1")
    bad = {**BOT, "hold": 0, "rebalance": "hourly"}
    got = spanish(app, "u1").post("/api/bots/preview", json={"bot": bad})
    assert got.status_code == 400 and '"rebalance" es uno de estos: daily, weekly, monthly.' in got.json()["problems"]
    assert got.json()["detail"] == " ".join(got.json()["problems"])
    assert '"rebalance" is one of daily, weekly, monthly.' in client(app, "u1").post("/api/bots/preview", json={"bot": bad}).json()["problems"]
    assert spanish(app, "u1").post("/api/bots/mine/switch", json={"action": "exclude", "ticker": "ZZZZ"}).json()["detail"] == \
        "ZZZZ no está entre las empresas entre las que elige el bot."
    assert spanish(app).get("/api/bots").json()["detail"] == "Entra con tu cuenta de The Market Hub."
    assert "signin" in spanish(app).get("/api/bots").json()
    assert spanish(app, "u1").get("/api/board/bot/nope").json()["detail"] == "Ese bot no existe."
    foreign = spanish(app, "u1")
    foreign.headers.update({"origin": "https://elsewhere.example"})
    assert foreign.put("/api/bots/mine", json={"bot": BOT}).json()["detail"] == "Petición desde otro sitio rechazada."


def test_a_backtest_on_a_spanish_page_is_told_in_spanish():
    app = make()
    got = spanish(app, "u1").post("/api/bots/backtest", json={"bot": BOT, "years": 1}).json()
    english = client(app, "u1").post("/api/bots/backtest", json={"bot": BOT, "years": 1}).json()
    assert got["rules"][0] == "Mira las 30 mayores empresas de EE. UU." and got["notes"][0].startswith("Una simulación sobre cierres pasados")
    assert got["notes"][2] == "Paga un 0,10 % sobre lo que negocia. Los dividendos no se cuentan, como en la competición."
    assert english["notes"][0].startswith("A simulation on past closes") and english["bot"] == got["bot"]


def test_the_rules_page_reads_the_format_in_its_language_and_the_kit_in_english():
    app = make()
    assert client(app).get("/api/bot/spec").json()["factors"]["momentum"]["means"].startswith("Return over")
    sp = spanish(app).get("/api/bot/spec").json()
    assert sp["factors"]["momentum"]["means"].startswith("Rentabilidad en") and set(sp["factors"]) == set(es.FACTOR_NOTES_ES)
    assert {k: v for k, v in sp.items() if k != "factors"} == {k: v for k, v in client(app).get("/api/bot/spec").json().items() if k != "factors"}
    # The kit is the agent's: the same files whatever the page's language.
    with zipfile.ZipFile(io.BytesIO(spanish(app, "u1").post("/api/bots/kit").content)) as z:
        assert "markethub-bot/SPEC.md" in z.namelist() or any(n.endswith(".md") for n in z.namelist())


def test_the_agents_routes_stay_english():
    app = make()
    key = send(app, "u1")
    from fastapi.testclient import TestClient
    agent = TestClient(app)
    agent.headers.update({"authorization": f"Bearer {key}"})
    assert agent.post("/api/bot/check", json={"bot": BOT}).json()["rules"][0] == "Looks at the 30 largest US companies."
    assert agent.get("/api/bot").json()["bot"]["rules"][0].startswith("Looks at")
    assert '"hold" is how many stocks it holds, a whole number from 1 to 50.' in agent.post("/api/bot/check", json={"bot": {**BOT, "hold": 0}}).json()["problems"]


def test_the_demo_chat_answers_in_spanish_on_a_spanish_page():
    app = make(chat=Chat(MemoryLedger(), client=Scripted, enabled=True, per_member=30, daily_max=None))
    owner = spanish(app, "u1")
    got = owner.post("/api/bots/draft/chat", json={"message": "Hola, quiero un bot"}).json()
    assert got["proposal"] is None and got["reply"].startswith("Encantado")
    got = owner.post("/api/bots/draft/chat", json={"message": "Lo que más ha subido"}).json()
    draft = got["proposal"]
    assert draft["name"] == "Momentum de doce meses" and got["reply"].startswith("Aquí tienes") and got["rules"][0].startswith("Mira las")
    got = owner.post("/api/bots/draft/chat", json={"message": "Menos acciones", "draft": draft}).json()
    assert got["proposal"]["hold"] == 12 and got["reply"] == "Menos acciones: mantiene las 12 mejores en vez de 20."
    owner.put("/api/bots/mine", json={"bot": got["proposal"]})
    got = owner.post("/api/bots/mine/chat", json={"message": "Hazlo más defensivo"}).json()
    assert got["reply"].startswith("Más defensivo") and got["rules"][-1].startswith("Cuando, para el S&P 500")
    assert owner.post("/api/bots/mine/chat", json={"message": "Que mire cada semana"}).json()["proposal"]["rebalance"] == "weekly"
    assert owner.post("/api/bots/mine/chat", json={"message": "Ponlo en pausa"}).json()["reply"].startswith("Pausar es un interruptor")
    # The same instruction on an English page, in English.
    assert client(app, "u1").post("/api/bots/mine/chat", json={"message": "more stocks"}).json()["reply"].startswith("More stocks")


def test_the_chat_is_told_the_page_is_in_spanish_and_its_limits_are_in_spanish():
    from test_api import Claude
    claude = Claude({"reply": "Vale.", "bot": ""})
    app = make(chat=Chat(MemoryLedger(), client=lambda: claude, enabled=True, per_member=1, daily_max=None))
    owner = spanish(app, "u1")
    owner.post("/api/bots/draft/chat", json={"message": "hola"})
    assert "Spanish of Spain" in claude.calls[0]["system"]
    capped = owner.post("/api/bots/draft/chat", json={"message": "otra"})
    assert capped.status_code == 503 and "mensajes" in capped.json()["detail"]
    client(app, "u2").post("/api/bots/draft/chat", json={"message": "hi"})
    assert "Spanish" not in claude.calls[1]["system"]
    off = make()
    send(off, "u1")
    assert spanish(off, "u1").post("/api/bots/mine/chat", json={"message": "x"}).json()["detail"] == "El chat aún no está activado. Usa el editor."
