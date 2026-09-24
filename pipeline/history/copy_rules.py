"""The History catalogue's reader-facing copy rules, in one place.

`tests/test_history_copy.py` wrote these for the event YAML (the dash ban, the
time-relative gate, the prose-attribution gate) and documents why each shape is
here. The thesis checks (T-06) apply the same gates to the thesis Markdown, and
two copies of a regex drift, so both import from here.

Nothing in this module reads a file or exits; it is regexes and two helpers.
"""
from __future__ import annotations

import re

EM, EN = "—", "–"

# A quoted span anywhere is exempt from the prose gates: the words are as the
# source printed them (see test_history_copy.py for the Rock Edict XIII case).
QUOTED_SPAN = re.compile(r"[“\"]([^“”\"]{2,600})[”\"]")


def outside_quotations(text: str) -> str:
    """The text with every quoted span blanked, so only our own prose is judged."""
    return QUOTED_SPAN.sub(lambda m: " " * len(m.group(0)), text or "")


# ------------------------------------------------------ time-relative gate
# Every entry measures from the moment somebody reads the page. The allowed
# rewrites and the two carve-outs are documented in tests/test_history_copy.py.
TIME_RELATIVE = [
    ("a near year used as now",
     re.compile(r"\b(?:in|as of|since) 20(?:2[4-9]|3\d)\b"
                r"(?!\s+(?:dollars|values|prices|terms|money))", re.I)),
    ("to this day", re.compile(r"\bto this day\b", re.I)),
    ("a state asserted as continuing",
     re.compile(r"\bstill (?:open|governs|leads|stands|in force|the)\b", re.I)),
    ("a state asserted as still holding",
     re.compile(r"\b(?:remains?|persists?)\b[^.!?]*?"
                r"\b(?:in force|today|the (?:most|largest|only|world's))\b",
                re.I)),
    ("an interval measured from now",
     re.compile(r"\b\w+(?:-\w+)? years "
                r"(?:ago\b|later\b|on\b(?=\s*[,.;:]|$))"
                r"(?!\s+in\s+\d{4})", re.I)),
    ("the present decade", re.compile(r"\bin the 2020s\b", re.I)),
    ("currently", re.compile(r"\bcurrently\b", re.I)),
    ("today", re.compile(r"\btoday\b", re.I)),
]

# ------------------------------------------------- prose-attribution gate
# A hedge noun standing where a name belongs.
HEDGED_ATTRIBUTION = re.compile(
    r"\b(?:analysts|experts|critics|observers|some|many|sources) "
    r"(?:say|says|said|argue|argues|argued|believe|believes|believed"
    r"|note|notes|noted)\b", re.I)

# What rescues it: a full name, or an institution that can hold a position.
NAMED = re.compile(
    r"\b[A-Z][a-z]+(?:\s+(?:de|van|von|al|ibn|bin|da|di|of|the))?"
    r"\s+[A-Z][\w'’-]+|\b[A-Z]{2,}\b")

_SENTENCE = re.compile(r"[^.!?]*[.!?]|[^.!?]+$")


def sentence_around(text: str, index: int) -> str:
    """The sentence containing `index`, or the whole text if it has none."""
    for m in _SENTENCE.finditer(text):
        if m.start() <= index < m.end():
            return m.group(0)
    return text


def time_relative_hits(prose: str) -> list[tuple[str, str]]:
    """(label, snippet) for every scheduled error in our own prose."""
    out = []
    for label, rx in TIME_RELATIVE:
        for m in rx.finditer(prose):
            out.append((label, " ".join(prose[max(0, m.start() - 40):m.end() + 40].split())))
    return out


def hedge_hits(prose: str) -> list[str]:
    """Every hedge whose sentence names nobody."""
    out = []
    for m in HEDGED_ATTRIBUTION.finditer(prose):
        if NAMED.search(sentence_around(prose, m.start())):
            continue
        out.append(m.group(0))
    return out
