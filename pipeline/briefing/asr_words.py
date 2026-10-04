"""Word normalisation and alignment for the TTS word-perfect gate.

Pure python: imported by the host (to build each unit's reference words) and
by the GPU worker (to judge each take), so both sides normalise identically.
Numbers are compared as spoken words ("1941" and "nineteen forty-one" agree),
hyphens split, accents fold, case drops.
"""
from __future__ import annotations

import re
import unicodedata

from briefing.spoken_text import spoken_numbers


_NUMBER_WORDS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                 "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
                 "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
                 "hundred", "thousand", "million"}
# Spelling is not speech: an ASR model writes American spellings, a British
# script does not, and the voice said the same word either way. Measured on
# the 2026-10-03 Partition render (programme/program, organisation/organization).
_SPELLING = [(re.compile(r"isation"), "ization"), (re.compile(r"ise(d|s)?$"), r"ize\1"),
             (re.compile(r"^programme(s)?$"), r"program\1"), (re.compile(r"our$"), "or"),
             (re.compile(r"our(s|ed|ing)$"), r"or\1"), (re.compile(r"tre$"), "ter")]


def _canon(w: str) -> str:
    # Six letters minimum: "four"/"for", "hour", "your", "rise" must stay
    # themselves, or a real misread would be folded away.
    if len(w) < 6:
        return w
    for pat, rep in _SPELLING:
        w = pat.sub(rep, w)
    return w


def norm_words(text: str) -> list[str]:
    t = spoken_numbers(text or "")
    t = re.sub(r"[-‐-―]", " ", t)
    t = re.sub(r"\bper cent\b", "percent", t, flags=re.I)
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    words = [_canon(w) for w in re.findall(r"[a-z0-9]+", t.lower())]
    # "two thousand and ninety four" is the British spoken form of 2,094; an
    # ASR model writes the digits, which spell back without the "and".
    return [w for i, w in enumerate(words)
            if not (w == "and" and 0 < i < len(words) - 1
                    and words[i - 1] in _NUMBER_WORDS and words[i + 1] in _NUMBER_WORDS)]


def same_when_joined(ref: list[str], hyp: list[str]) -> bool:
    """A compound written open or closed ("hydro electric" / "hydroelectric")
    is the same speech: equal once the spaces go."""
    return "".join(ref) == "".join(hyp)


def align(ref: list[str], hyp: list[str]) -> list[tuple]:
    """Levenshtein on words with backtrace: ("=", r, h), ("S", r, h), ("D", r, None), ("I", None, h)."""
    n, m = len(ref), len(hyp)
    d = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        d[i][0] = i
    for j in range(m + 1):
        d[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            d[i][j] = min(d[i - 1][j] + 1, d[i][j - 1] + 1,
                          d[i - 1][j - 1] + (0 if ref[i - 1] == hyp[j - 1] else 1))
    ops, i, j = [], n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0 and d[i][j] == d[i - 1][j - 1] + (0 if ref[i - 1] == hyp[j - 1] else 1):
            ops.append(("=" if ref[i - 1] == hyp[j - 1] else "S", ref[i - 1], hyp[j - 1]))
            i, j = i - 1, j - 1
        elif i > 0 and d[i][j] == d[i - 1][j] + 1:
            ops.append(("D", ref[i - 1], None))
            i -= 1
        else:
            ops.append(("I", None, hyp[j - 1]))
            j -= 1
    return ops[::-1]
