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


def norm_words(text: str) -> list[str]:
    t = spoken_numbers(text or "")
    t = re.sub(r"[-‐-―]", " ", t)
    t = re.sub(r"\bper cent\b", "percent", t, flags=re.I)
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    return re.findall(r"[a-z0-9]+", t.lower())


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
