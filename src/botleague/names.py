"""The names members show under, and the words nothing is shown with.

The same rules as Market Hub's Community (market-hub-landing: community.py and opinion.py), so a
name is taken or refused the same here as there. A change there is made here too.
"""

from __future__ import annotations

import re

HANDLE = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9_\-]| (?! )){1,18}[A-Za-z0-9]")
RESERVED = {"you", "average", "admin", "markethub", "market hub", "market-hub", "sp500", "s&p 500", "index"}
# The portal's sample members: names nobody can take, so a sample line is never mistaken for one.
SAMPLE_NAMES = ["northwind", "tape_reader", "quiet compounder", "delta nine", "harbour lane", "second derivative", "plainvanilla",
                "long_duration", "copper kettle", "margin of error", "sunday charts", "basis point"]


def handle_key(handle: str) -> str:
    return re.sub(r"[\s_\-]+", "", handle).lower()


# Words a name or a bot's note is not shown with: slurs and the coarsest insults, in English and in
# Spanish, as whole words.
_UNPUBLISHED = re.compile(r"(?<![a-z])(?:" + "|".join((
    "n[i1]gg(?:er|a)s?", "f[a4]gg?[o0]ts?", "k[i1]kes?", "sp[i1]cs?", "ch[i1]nks?", "tr[a4]nn(?:y|ies)", "r[e3]t[a4]rd(?:s|ed)?",
    "c[u*]nts?", "wh[o0]res?", "sl[u*]ts?", "f[u*]ck(?:er|ers|ing|ed|s)?", "m[o0]therf[u*]ck(?:er|ers|ing)?", "b[i1]tch(?:es)?",
    "assh[o0]les?", "kill yourself", "kys",
    "maric[oó]n(?:es)?", "put[ao]s?", "hijo(?:s)? de puta", "hijueputa", "zorras?", "subnormal(?:es)?", "gilipollas", "cabr[oó]n(?:es)?",
    "sudacas?", "panchitos?", "mátate", "matate",
)) + r")(?![a-z])", re.IGNORECASE)


def publishable(text: str) -> bool:
    return not _UNPUBLISHED.search(text)
