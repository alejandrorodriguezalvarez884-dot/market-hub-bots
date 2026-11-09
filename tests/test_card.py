"""A bot's card: the face is the site's, the figures are the page's, the picture is a PNG of the
right size, and a link to a bot on the public board shows its card."""

import json
import struct
from pathlib import Path

from fastapi.testclient import TestClient

from botleague import card
from botleague.robot import robot_svg, traits
from test_api import DAYS, client, make, send, slug
from conftest import at

FACES = json.loads((Path(__file__).parent / "fixtures" / "robot_faces.json").read_text())


def size_of(png: bytes) -> tuple[int, int]:
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    return struct.unpack(">II", png[16:24])


def test_the_face_is_the_one_the_site_draws():
    """robot.py is a copy of site/src/lib/robot.ts: the same traits and the same markup, character
    for character (scripts/robot_faces.mjs writes what the site draws)."""
    for face in FACES:
        assert traits(face["slug"]) == face["traits"], face["slug"]
        assert robot_svg(face["slug"], 96) == face["svg"], face["slug"]
        if "bare" in face:
            assert robot_svg(face["slug"], 300, frame=False, label="A & <b>") == face["bare"], face["slug"]


def page(**over):
    curve = [{"date": d, "bot": 1 + 0.002 * i, "index": 1 + 0.001 * i} for i, d in enumerate(DAYS[-30:], 1)]
    return {"slug": "bag-holder", "name": "Bag holder", "handle": "Ana", "returns": {"1d": 0.002, "1w": 0.01, "1m": 0.04, "1y": None, "all": curve[-1]["bot"] - 1},
            "ranks": {"1d": 2, "1w": 1, "1m": 3, "all": 2}, "entrants": 7, "curve": curve, "starts": DAYS[-30], **over}


def test_what_a_card_says():
    p = page()
    f = card.facts(p, "1m", {"1m": 5})
    assert f["period"] == "1m" and f["rank"] == 3 and f["of"] == 5 and f["last"] == DAYS[-1] and f["first"] == DAYS[-21]
    assert len(f["bot"]) == 22 and f["bot"][0] == 1 and abs(f["bot"][-1] - p["curve"][-1]["bot"] / p["curve"][-22]["bot"]) < 1e-12
    assert abs(f["index"] - (p["curve"][-1]["index"] / p["curve"][-22]["index"] - 1)) < 1e-12
    # Since the start: from 1 the session before the first, as the board counts it.
    f = card.facts(p, "all")
    assert f["first"] == DAYS[-30] and f["bot"][0] == 1 and abs(f["index"] - 0.03) < 1e-9 and f["of"] == 7
    # A period it has no figure for falls back to since the start.
    assert card.facts(p, "1y")["period"] == "all" and card.facts(p, "nonsense")["period"] == "all"
    # In words, in each language.
    en, es = card.svg(p, "1m", "story", "en"), card.svg(p, "1m", "story", "es")
    assert "+4.0%" in en and "3rd of 7 bots" in en and "a paper game, no real money" in en and "bots.themarkethub.app" in en
    assert "+4,0 %" in es and "3.º de 7 bots" in es and "sin dinero real" in es and "de Ana" in es
    # Nothing that reads as advice, in any format.
    for fmt in card.SIZES:
        for lang in ("en", "es"):
            text = card.svg(p, "all", fmt, lang).lower()
            assert not any(w in text for w in ("buy", "sell", "compra", "vende", "invest", "invierte", "target", "objetivo"))


def test_a_card_before_its_first_close_and_with_a_name_to_escape():
    p = page(curve=[], returns={k: None for k in card.PERIOD_KEYS}, ranks={}, starts="2026-11-10", name='Tom & "Jerry" <3')
    text = card.svg(p, "all", "story", "en")
    assert "Starts playing at the close of Nov 10, 2026" in text and "Tom &amp; &quot;Jerry&quot; &lt;3" in text and "<3" not in text
    assert "Empieza a jugar en el cierre del 10 nov 2026" in card.svg(p, "1w", "square", "es")


def test_the_pictures_are_pngs_of_each_size():
    for fmt, (w, h) in card.SIZES.items():
        assert size_of(card.png(card.svg(page(), "1w", fmt, "es"))) == (w, h)


def test_long_names_fit():
    lines, size = card.fit("A name long enough to need more than one line of the card", 92, 888)
    assert len(lines) <= 2 and all(card.width(x, size, card.SANS_BOLD) <= 888 for x in lines)
    lines, size = card.fit("W" * 40, 92, 500)
    assert all(card.width(x, size, card.SANS_BOLD) <= 500 for x in lines) and lines[-1].endswith("…")


def test_the_card_route_and_the_link_preview(tmp_path):
    site = tmp_path / "site"
    for sub in ("bot", "es/bot"):
        (site / sub).mkdir(parents=True)
        (site / sub / "index.html").write_text('<html><head><meta name="description" content="A bot" /><title>Bot · Bot League</title>'
                                               '<meta property="og:title" content="Bot" /><meta property="og:image" content="https://x/share.png" />'
                                               '<meta property="og:image:width" content="1200" /><meta name="twitter:card" content="summary" /></head></html>')
    app = make(public=True)
    app.state.clock.when = at(DAYS[-6], 12)
    send(app, "u1")
    app.state.clock.when = at(DAYS[-1], 18)
    client(app).post("/api/board/refresh")
    s = slug(app, "u1")
    got = client(app).get(f"/api/board/bot/{s}/card.png?format=square&period=1w&lang=es")
    assert got.status_code == 200 and got.headers["content-type"] == "image/png" and size_of(got.content) == (1080, 1080)
    assert got.headers["cache-control"] == "public, max-age=900"
    assert size_of(client(app).get(f"/api/board/bot/{s}/card.png").content) == (1080, 1920)
    assert client(app).get("/api/board/bot/0000000000/card.png").status_code == 404

    # The bot's page carries its card as its link preview; any other page of the site is as built.
    served = _with_site(app, site)
    html = served.get(f"/bot/?b={s}").text
    assert f"/api/board/bot/{s}/card.png?format=link&amp;lang=en" in html and "https://x/share.png" not in html
    assert html.count('property="og:image"') == 1 and html.count('name="twitter:card"') == 1 and html.count("og:image:width") == 1
    assert "<title>Api bot · Bot League</title>" in html and "By Ana" in html and "a paper game, with no real money" in html
    es = served.get(f"/es/bot/?b={s}").text
    assert "lang=es" in es and "De Ana" in es and "sin dinero real" in es
    assert "https://x/share.png" in served.get("/bot/?b=0000000000").text


def _with_site(app, site) -> TestClient:
    """The same app's store and clock, served with a built site."""
    from botleague.api import create_app
    from botleague.chat import Chat, MemoryLedger
    from botleague.market import SAMPLE_TICKERS
    from conftest import HUB, SECRET, walk
    other = create_app(bot_store=app.state.store, closes=lambda ts: {t: walk(t, DAYS) for t in ts},
                       largest=lambda n: list(SAMPLE_TICKERS[:n]), hub=(HUB, SECRET), public=True, clock=app.state.clock,
                       chat=Chat(MemoryLedger(), enabled=False, now=app.state.clock), static_dir=str(site))
    return TestClient(other)


def test_a_private_board_keeps_its_cards_to_members():
    app = make(public=False)
    send(app, "u1")
    s = slug(app, "u1")
    assert client(app).get(f"/api/board/bot/{s}/card.png").status_code == 404
    got = client(app, "u2").get(f"/api/board/bot/{s}/card.png?format=link")
    assert got.status_code == 200 and got.headers["cache-control"] == "private, max-age=300" and size_of(got.content) == (1200, 630)
