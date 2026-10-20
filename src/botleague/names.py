"""The words nothing is shown with: the same floor as Market Hub's (market-hub-landing: opinion.py).
A player is shown under the first name of their account (engine.first_name), refused if it has one
of these words. A change there is made here too.
"""

from __future__ import annotations

import re

# The portal's sample members, for its sample stand-ins (bots.py runs them on sample figures).
SAMPLE_NAMES = ["northwind", "tape_reader", "quiet compounder", "delta nine", "harbour lane", "second derivative", "plainvanilla",
                "long_duration", "copper kettle", "margin of error", "sunday charts", "basis point"]


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
