"""Every bot's face, for the pictures the server draws (card.py).

A copy of the site's ``site/src/lib/robot.ts`` (the iPhone app has another): the same seeded numbers
from the slug and the same markup, character for character, so a bot looks the same on its page, in
the app and on the card it is shared with. A change there is made here too;
``tests/test_card.py`` checks both draw the same faces (``scripts/robot_faces.mjs`` writes them).

JavaScript has only doubles and 32-bit integer tricks: ``_imul``, ``_round`` and ``_num`` stand for
``Math.imul``, ``Math.round`` and the way a number is written into a string, so the output matches.
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_UP, Decimal

LINE = "var(--color-ink-strong)"
DARK = "var(--color-deep)"
PANEL = "var(--color-panel)"
SHELLS = ["var(--color-raised)", "#24272a", "#2f3236", "var(--color-line-strong)", "var(--color-ink)"]
LIGHT_SHELL = len(SHELLS) - 1

M32 = 0xFFFFFFFF


def _imul(a: int, b: int) -> int:
    return ((a & M32) * (b & M32)) & M32


def _seeded(text: str):
    """FNV-1a, then mulberry32: a small, stable stream of numbers from a string."""
    h = 0x811C9DC5
    units = text.encode("utf-16-le")
    for i in range(0, len(units), 2):
        h ^= units[i] | (units[i + 1] << 8)
        h = _imul(h, 0x01000193)
    state = {"a": h & M32}

    def next_number() -> float:
        a = (state["a"] + 0x6D2B79F5) & M32
        state["a"] = a
        t = _imul(a ^ (a >> 15), 1 | a)
        t = ((t + _imul(t ^ (t >> 7), 61 | t)) & M32) ^ t
        return ((t ^ (t >> 14)) & M32) / 4294967296

    return next_number


def _round(x: float) -> int:
    """Math.round: halves go up."""
    return math.floor(x + 0.5)


def _num(x: float | int) -> str:
    """A number as JavaScript writes it into a string."""
    if isinstance(x, int):
        return str(x)
    if x.is_integer():
        return str(int(x))
    return repr(x)


def _fixed2(x: float | int) -> str:
    """``+x.toFixed(2)``, written as a string: two decimals, halves away from zero, no trailing zeros."""
    d = Decimal(x).copy_abs().quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return _num(float(-d if x < 0 else d))


HEADS = ["box", "wide", "round", "tall", "dome", "tv", "octagon", "egg"]
EYES = ["dots", "googly", "visor", "cyclops", "happy", "square", "mismatch", "sleepy", "dashes", "plus"]
MOUTHS = ["smile", "grille", "flat", "o", "zigzag", "smirk", "blep", "grin"]
ANTENNAS = ["none", "ball", "double", "spring", "bent", "bulb", "propeller", "dish"]
EARS = ["none", "bolts", "round", "cones"]
CHESTS = ["none", "dial", "lights", "heart", "slot"]
EXTRAS = ["bowtie", "monocle", "mustache", "headphones", "hat", "brows", "cheeks", "screw", "patch"]


def traits(slug: str) -> dict:
    r = _seeded(f"bot:{slug}")

    def pick(xs):
        return xs[math.floor(r() * len(xs))]

    head = pick(HEADS)
    shell = math.floor(r() * len(SHELLS))
    eyes = pick(EYES)
    look = [_round((r() * 2 - 1) * 1.6 * 10) / 10, _round((r() * 2 - 1) * 1.2 * 10) / 10]
    mouth = pick(MOUTHS)
    antenna = pick(ANTENNAS)
    ears = pick(EARS)
    chest = pick(CHESTS)
    want = 0 if r() < 0.25 else 1 if r() < 0.7 else 2
    extras: list[str] = []
    tries = 0
    while len(extras) < want and tries < 12:
        tries += 1
        x = pick(EXTRAS)
        if x in extras:
            continue
        if x in ("monocle", "patch", "brows") and eyes in ("visor", "cyclops", "mismatch"):
            continue
        if x == "monocle" and "patch" in extras:
            continue
        if x == "patch" and "monocle" in extras:
            continue
        if x == "mustache" and mouth in ("grille", "grin"):
            continue
        if x == "hat" and ("headphones" in extras or head == "dome"):
            continue
        if x == "headphones" and "hat" in extras:
            continue
        extras.append(x)
    if "hat" in extras:
        antenna = "none"
    if "headphones" in extras:
        ears = "none"
    tilt = _round((r() * 2 - 1) * 7) if r() < 0.45 else 0
    return {"head": head, "shell": shell, "eyes": eyes, "look": look, "mouth": mouth, "antenna": antenna, "ears": ears,
            "chest": chest, "extras": extras, "tilt": tilt}


HEAD = {
    "box": {"d": "M20 16H44Q51 16 51 23V39Q51 46 44 46H20Q13 46 13 39V23Q13 16 20 16Z", "top": 16, "bottom": 46, "left": 13, "right": 51},
    "wide": {"d": "M18 19H46Q55 19 55 28V36Q55 45 46 45H18Q9 45 9 36V28Q9 19 18 19Z", "top": 19, "bottom": 45, "left": 9, "right": 55},
    "round": {"d": "M32 14A17 17 0 1 1 31.99 14Z", "top": 14, "bottom": 48, "left": 15, "right": 49},
    "tall": {"d": "M29 12H35Q47 12 47 24V36Q47 48 35 48H29Q17 48 17 36V24Q17 12 29 12Z", "top": 12, "bottom": 48, "left": 17, "right": 47},
    "dome": {"d": "M12 44V31A20 20 0 0 1 52 31V44Q52 47 49 47H15Q12 47 12 44Z", "top": 11, "bottom": 47, "left": 12, "right": 52},
    "tv": {"d": "M15 16H49Q53 16 52.6 20L50 43.5Q49.6 47 46 47H18Q14.4 47 14 43.5L11.4 20Q11 16 15 16Z", "top": 16, "bottom": 47, "left": 12, "right": 52},
    "octagon": {"d": "M23 14H41L51 24V38L41 48H23L13 38V24Z", "top": 14, "bottom": 48, "left": 13, "right": 51},
    "egg": {"d": "M32 15C43 15 51 22 51 31.5S43 47 32 47S13 41 13 31.5S21 15 32 15Z", "top": 15, "bottom": 47, "left": 13, "right": 51},
}


def _tag(name: str, a: dict, inner: str = "") -> str:
    attrs = "".join(f' {k}="{_fixed2(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else v}"' for k, v in a.items())
    return f"<{name}{attrs}>{inner}</{name}>" if inner else f"<{name}{attrs}/>"


def _stroke(color: str, width: float = 2.2) -> dict:
    return {"fill": "none", "stroke": color, "stroke-width": width, "stroke-linecap": "round", "stroke-linejoin": "round"}


def robot_svg(slug: str, size: int = 40, frame: bool = True, label: str | None = None) -> str:
    n = _num
    t = traits(slug)
    box = HEAD[t["head"]]
    shell = SHELLS[t["shell"]]
    light = t["shell"] == LIGHT_SHELL
    fg = "var(--color-page)" if light else LINE
    h = box["bottom"] - box["top"]
    cx = 32
    ey = box["top"] + h * 0.42
    my = box["top"] + h * 0.74
    ex = min(9.5, (box["right"] - box["left"]) * 0.21)
    parts: list[str] = []
    put = parts.append
    tag, stroke = _tag, _stroke

    chest: list[str] = [tag("path", {"d": "M12 66V58Q12 52 19 52H45Q52 52 52 58V66Z", **stroke(LINE), "fill": PANEL})]
    if t["chest"] == "dial":
        chest += [tag("circle", {"cx": cx, "cy": 59, "r": 3, **stroke(LINE, 1.6)}), tag("path", {"d": "M32 59L33.8 57.2", **stroke(LINE, 1.6)})]
    if t["chest"] == "lights":
        for dx in (-5, 0, 5):
            chest.append(tag("circle", {"cx": cx + dx, "cy": 59, "r": 1.3, "fill": LINE if dx == 0 else "var(--color-muted)"}))
    if t["chest"] == "heart":
        chest.append(tag("path", {"d": "M32 62.2L28.9 59.2A1.9 1.9 0 0 1 32 56.9A1.9 1.9 0 0 1 35.1 59.2Z", "fill": LINE}))
    if t["chest"] == "slot":
        chest.append(tag("path", {"d": "M27 59H37", **stroke(LINE, 1.8)}))
    put(f"<g>{''.join(chest)}</g>")
    put(tag("rect", {"x": 27.5, "y": box["bottom"] - 2, "width": 9, "height": 56 - box["bottom"], **stroke(LINE, 2), "fill": "#2a2d30"}))

    head: list[str] = []
    left, right, bottom = box["left"], box["right"], box["bottom"]
    ear_y = ey + 2
    if t["ears"] == "bolts":
        for s in (-1, 1):
            head.append(tag("rect", {"x": left - 4.5 if s < 0 else right - 0.5, "y": ear_y - 4, "width": 5, "height": 8, "rx": 1.5, "fill": PANEL,
                                     "stroke": LINE, "stroke-width": 2}))
    if t["ears"] == "round":
        for s in (-1, 1):
            head.append(tag("circle", {"cx": left - 0.5 if s < 0 else right + 0.5, "cy": ear_y, "r": 4, "fill": PANEL, "stroke": LINE, "stroke-width": 2}))
    if t["ears"] == "cones":
        for s in (-1, 1):
            x0 = left + 1 if s < 0 else right - 1
            head.append(tag("path", {"d": f"M{n(x0)} {n(ear_y - 4)}L{n(x0 + s * 6)} {n(ear_y - 7)}V{n(ear_y + 7)}L{n(x0)} {n(ear_y + 4)}Z", "fill": PANEL,
                                     "stroke": LINE, "stroke-width": 2, "stroke-linejoin": "round"}))

    top = box["top"]

    def ball(x, y, r=2.6):
        return tag("circle", {"cx": x, "cy": y, "r": r, "fill": LINE})

    a = t["antenna"]
    if a == "ball":
        head += [tag("path", {"d": f"M32 {n(top)}V{n(top - 7)}", **stroke(LINE)}), ball(32, top - 8.5)]
    if a == "double":
        for s in (-1, 1):
            head += [tag("path", {"d": f"M{n(32 + s * 6)} {n(top + 1)}L{n(32 + s * 10)} {n(top - 7)}", **stroke(LINE)}), ball(32 + s * 10.6, top - 8.4, 2.2)]
    if a == "spring":
        head += [tag("path", {"d": f"M32 {n(top)}L29.5 {n(top - 2)}L34.5 {n(top - 4)}L29.5 {n(top - 6)}L34.5 {n(top - 8)}L32 {n(top - 9.5)}", **stroke(LINE, 1.8)}),
                 ball(32, top - 11, 2.4)]
    if a == "bent":
        head += [tag("path", {"d": f"M30 {n(top)}V{n(top - 6)}L36 {n(top - 9)}", **stroke(LINE)}), ball(37.5, top - 9.8, 2.3)]
    if a == "bulb":
        head += [tag("path", {"d": f"M32 {n(top)}V{n(top - 4)}", **stroke(LINE)}), tag("circle", {"cx": 32, "cy": top - 8, "r": 4, **stroke(LINE, 2), "fill": PANEL})]
        head.append(tag("path", {"d": f"M26 {n(top - 12)}L24.5 {n(top - 13.5)}M38 {n(top - 12)}L39.5 {n(top - 13.5)}M32 {n(top - 14.5)}V{n(top - 16)}", **stroke(LINE, 1.5)}))
    if a == "propeller":
        head += [tag("path", {"d": f"M32 {n(top)}V{n(top - 6)}", **stroke(LINE)}),
                 tag("path", {"d": f"M23 {n(top - 7.5)}Q27.5 {n(top - 10.5)} 32 {n(top - 7)}Q36.5 {n(top - 3.5)} 41 {n(top - 6.5)}", **stroke(LINE, 2.4)})]
    if a == "dish":
        head += [tag("path", {"d": f"M33 {n(top)}L35 {n(top - 6)}", **stroke(LINE)}),
                 tag("path", {"d": f"M29 {n(top - 9)}Q34 {n(top - 3)} 41 {n(top - 8)}", **stroke(LINE, 2.2)}), ball(35.6, top - 7.4, 1.4)]

    head.append(tag("path", {"d": box["d"], "fill": shell, "stroke": LINE, "stroke-width": 2.4, "stroke-linejoin": "round"}))
    if t["head"] != "octagon":
        head.append(tag("path", {"d": f"M{n(left + 5)} {n(top + 9)}Q{n(left + 5.5)} {n(top + 5)} {n(left + 10)} {n(top + 4.5)}",
                                 **stroke("rgb(255 255 255 / 0.55)" if light else "rgb(242 240 234 / 0.28)", 1.6)}))

    lx, rx = cx - ex, cx + ex
    sclera = "var(--color-ink-strong)"
    pupil = "var(--color-page)"
    dx, dy = t["look"]

    def googly(x, r):
        return "".join([tag("circle", {"cx": x, "cy": ey, "r": r, "fill": sclera, "stroke": pupil if light else "none", "stroke-width": 1.4}),
                        tag("circle", {"cx": x + dx * (r / 5), "cy": ey + dy * (r / 5), "r": r * 0.45, "fill": pupil})])

    face: list[str] = []
    e = t["eyes"]
    if e == "dots":
        face += [tag("circle", {"cx": lx, "cy": ey, "r": 2.7, "fill": fg}), tag("circle", {"cx": rx, "cy": ey, "r": 2.7, "fill": fg})]
    if e == "googly":
        face += [googly(lx, 4.6), googly(rx, 4.6)]
    if e == "visor":
        face.append(tag("rect", {"x": lx - 5.5, "y": ey - 4, "width": rx - lx + 11, "height": 8, "rx": 4, "fill": DARK, "stroke": LINE, "stroke-width": 1.6}))
        face.append(tag("rect", {"x": cx - 6 + dx * 2.5, "y": ey - 1.3, "width": 12, "height": 2.6, "rx": 1.3, "fill": LINE}))
    if e == "cyclops":
        face.append(googly(cx, 6.6))
    if e == "happy":
        for x in (lx, rx):
            face.append(tag("path", {"d": f"M{n(x - 3.6)} {n(ey + 1.6)}Q{n(x)} {n(ey - 4)} {n(x + 3.6)} {n(ey + 1.6)}", **stroke(fg, 2.4)}))
    if e == "square":
        for x in (lx, rx):
            face.append(tag("rect", {"x": x - 2.8, "y": ey - 2.8, "width": 5.6, "height": 5.6, "rx": 1, "fill": fg}))
    if e == "mismatch":
        face += [googly(lx, 5.2), tag("circle", {"cx": rx, "cy": ey, "r": 2.3, "fill": fg})]
    if e == "sleepy":
        for x in (lx, rx):
            face.append(tag("path", {"d": f"M{n(x - 4)} {n(ey)}A4 4 0 0 0 {n(x + 4)} {n(ey)}Z", "fill": sclera, "stroke": pupil if light else "none",
                                     "stroke-width": 1.2}))
            face += [tag("circle", {"cx": x + dx * 0.5, "cy": ey + 1.8, "r": 1.5, "fill": pupil}),
                     tag("path", {"d": f"M{n(x - 4.6)} {n(ey)}H{n(x + 4.6)}", **stroke(fg, 2)})]
    if e == "dashes":
        for x in (lx, rx):
            face.append(tag("path", {"d": f"M{n(x - 3.4)} {n(ey)}H{n(x + 3.4)}", **stroke(fg, 2.6)}))
    if e == "plus":
        for x in (lx, rx):
            face.append(tag("path", {"d": f"M{n(x - 3)} {n(ey)}H{n(x + 3)}M{n(x)} {n(ey - 3)}V{n(ey + 3)}", **stroke(fg, 2.2)}))

    mw = min(7, ex * 0.8)
    m = t["mouth"]
    if m == "smile":
        face.append(tag("path", {"d": f"M{n(cx - mw)} {n(my - 1.5)}Q{n(cx)} {n(my + 4)} {n(cx + mw)} {n(my - 1.5)}", **stroke(fg, 2.2)}))
    if m == "grille":
        face.append(tag("rect", {"x": cx - mw - 1, "y": my - 3, "width": 2 * mw + 2, "height": 6, "rx": 1.6, "fill": DARK, "stroke": fg, "stroke-width": 1.6}))
        face.append(tag("path", {"d": "".join(f"M{n(cx + k * (mw / 1.9))} {n(my - 2.4)}V{n(my + 2.4)}" for k in (-1, 0, 1)), **stroke(LINE, 1.2)}))
    if m == "flat":
        face.append(tag("path", {"d": f"M{n(cx - mw * 0.75)} {n(my)}H{n(cx + mw * 0.75)}", **stroke(fg, 2.2)}))
    if m == "o":
        face.append(tag("ellipse", {"cx": cx, "cy": my, "rx": 2.4, "ry": 2.9, **stroke(fg, 2)}))
    if m == "zigzag":
        face.append(tag("path", {"d": f"M{n(cx - mw)} {n(my)}L{n(cx - mw / 2)} {n(my - 2)}L{n(cx)} {n(my)}L{n(cx + mw / 2)} {n(my - 2)}L{n(cx + mw)} {n(my)}",
                                 **stroke(fg, 1.9)}))
    if m == "smirk":
        face.append(tag("path", {"d": f"M{n(cx - mw * 0.6)} {n(my + 0.5)}Q{n(cx + mw * 0.3)} {n(my + 1.8)} {n(cx + mw)} {n(my - 2.2)}", **stroke(fg, 2.2)}))
    if m == "blep":
        face.append(tag("path", {"d": f"M{n(cx - mw * 0.8)} {n(my - 1)}H{n(cx + mw * 0.8)}", **stroke(fg, 2.2)}))
        face.append(tag("path", {"d": f"M{n(cx - 0.2)} {n(my - 0.8)}V{n(my + 1.4)}A2.2 2.2 0 0 0 {n(cx + 4.2)} {n(my + 1.4)}V{n(my - 0.8)}",
                                 "fill": "var(--color-muted)" if light else "var(--color-ink)", "stroke": fg, "stroke-width": 1.4, "stroke-linejoin": "round"}))
    if m == "grin":
        face.append(tag("path", {"d": f"M{n(cx - mw)} {n(my - 2.4)}H{n(cx + mw)}Q{n(cx + mw)} {n(my + 4)} {n(cx)} {n(my + 4)}Q{n(cx - mw)} {n(my + 4)} {n(cx - mw)} {n(my - 2.4)}Z",
                                 "fill": DARK, "stroke": fg, "stroke-width": 1.8, "stroke-linejoin": "round"}))
        face += [tag("rect", {"x": cx - 3.2, "y": my - 2.4, "width": 2.8, "height": 2.4, "fill": LINE}),
                 tag("rect", {"x": cx + 0.4, "y": my - 2.4, "width": 2.8, "height": 2.4, "fill": LINE})]

    for x in t["extras"]:
        if x == "brows":
            up = 1 if t["look"][1] > 0 else -1
            face.append(tag("path", {"d": f"M{n(lx - 3.5)} {n(ey - 6.5 + up)}L{n(lx + 3)} {n(ey - 6.5 - up)}M{n(rx - 3)} {n(ey - 6.5 - up)}L{n(rx + 3.5)} {n(ey - 6.5 + up)}",
                                     **stroke(fg, 2)}))
        if x == "cheeks":
            for c in (lx - 2.5, rx + 2.5):
                face.append(tag("ellipse", {"cx": c, "cy": my - 2.8, "rx": 2.6, "ry": 1.6, "fill": "rgb(11 12 13 / 0.18)" if light else "rgb(242 240 234 / 0.16)"}))
        if x == "mustache":
            face.append(tag("path", {"d": f"M{n(cx)} {n(my - 4.4)}Q{n(cx - 3)} {n(my - 6.4)} {n(cx - 6)} {n(my - 4.6)}Q{n(cx - 8)} {n(my - 3.4)} {n(cx - 8.6)} {n(my - 5.2)}"
                                          f"Q{n(cx - 7.8)} {n(my - 1.6)} {n(cx - 4.4)} {n(my - 2.4)}Q{n(cx - 2)} {n(my - 3)} {n(cx)} {n(my - 3.4)}"
                                          f"Q{n(cx + 2)} {n(my - 3)} {n(cx + 4.4)} {n(my - 2.4)}Q{n(cx + 7.8)} {n(my - 1.6)} {n(cx + 8.6)} {n(my - 5.2)}"
                                          f"Q{n(cx + 8)} {n(my - 3.4)} {n(cx + 6)} {n(my - 4.6)}Q{n(cx + 3)} {n(my - 6.4)} {n(cx)} {n(my - 4.4)}Z", "fill": fg}))
        if x == "monocle":
            face += [tag("circle", {"cx": rx, "cy": ey, "r": 5.6, **stroke(fg, 1.6)}),
                     tag("path", {"d": f"M{n(rx + 4)} {n(ey + 4)}Q{n(rx + 6)} {n(my + 2)} {n(right - 3)} {n(bottom - 2)}", **stroke(fg, 1.1)})]
        if x == "patch":
            face += [tag("path", {"d": f"M{n(left + 2)} {n(ey - 7)}L{n(right - 4)} {n(ey + 4)}", **stroke(DARK, 1.6)}),
                     tag("ellipse", {"cx": lx, "cy": ey, "rx": 5, "ry": 4.4, "fill": DARK, "stroke": LINE, "stroke-width": 1.2})]
        if x == "screw":
            sx, sy = right - 7, top + 6
            face += [tag("circle", {"cx": sx, "cy": sy, "r": 1.9, "fill": "none", "stroke": fg, "stroke-width": 1.2}),
                     tag("path", {"d": f"M{n(sx - 1.2)} {n(sy - 1.2)}L{n(sx + 1.2)} {n(sy + 1.2)}", **stroke(fg, 1.1)})]
    over: list[str] = []
    for x in t["extras"]:
        if x == "headphones":
            y = ey + 1
            over.append(tag("path", {"d": f"M{n(left - 1)} {n(y)}V{n(y - 6)}A{n((right - left) / 2 + 1)} {n(y - top + 3)} 0 0 1 {n(right + 1)} {n(y - 6)}V{n(y)}",
                                     **stroke(LINE, 2.4)}))
            for s in (-1, 1):
                over.append(tag("rect", {"x": left - 4.5 if s < 0 else right - 1.5, "y": y - 3, "width": 6, "height": 10, "rx": 2.5, "fill": PANEL,
                                         "stroke": LINE, "stroke-width": 2}))
        if x == "hat":
            over.append(tag("path", {"d": f"M{n(cx - 13)} {n(top + 1.5)}H{n(cx + 13)}", **stroke(LINE, 2.6)}))
            over.append(tag("path", {"d": f"M{n(cx - 8)} {n(top + 1)}V{n(top - 10)}Q{n(cx - 8)} {n(top - 12)} {n(cx - 6)} {n(top - 12)}H{n(cx + 6)}"
                                          f"Q{n(cx + 8)} {n(top - 12)} {n(cx + 8)} {n(top - 10)}V{n(top + 1)}Z",
                                     "fill": DARK, "stroke": LINE, "stroke-width": 2.2, "stroke-linejoin": "round"}))
            over.append(tag("path", {"d": f"M{n(cx - 8)} {n(top - 3)}H{n(cx + 8)}", **stroke(LINE, 1.6)}))
    tilt = f' transform="rotate({n(t["tilt"])} 32 {n(bottom)})"' if t["tilt"] else ""
    put(f"<g{tilt}>{''.join(head)}{''.join(face)}{''.join(over)}</g>")
    if "bowtie" in t["extras"]:
        put(tag("path", {"d": "M32 53.5L26 50.5V56.5ZM32 53.5L38 50.5V56.5Z", "fill": LINE, "stroke": LINE, "stroke-width": 1.4, "stroke-linejoin": "round"}))

    bg = "" if frame is False else tag("rect", {"x": 0, "y": 0, "width": 64, "height": 64, "rx": 12, "fill": "var(--color-panel)"})
    if label:
        clean = "".join(ch for ch in label if ch not in '<>&"')
        a11y = f'role="img" aria-label="{clean}"'
    else:
        a11y = 'aria-hidden="true"'
    return f'<svg viewBox="0 0 64 64" width="{size}" height="{size}" {a11y} class="robot-svg">{bg}<g>{"".join(parts)}</g></svg>'
