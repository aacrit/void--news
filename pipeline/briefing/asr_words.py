"""Word normalisation and alignment for the TTS word-perfect gate.

Pure python: imported by the host (to build each unit's reference words) and
by the GPU worker (to judge each take), so both sides normalise identically.
Numbers are compared as spoken words ("1941" and "nineteen forty-one" agree),
hyphens split, accents fold, case drops.
"""
from __future__ import annotations

import re
import unicodedata

from briefing.spoken_text import number_words, ordinal_words, spoken_numbers


_NUMBER_WORDS = {"one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                 "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
                 "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
                 "hundred", "thousand", "million"}
# Spelling is not speech: an ASR model writes American spellings, a British
# script does not, and the voice said the same word either way. Measured on
# the 2026-10-03 Partition render (programme/program, organisation/organization).
_SPELLING = [(re.compile(r"isation"), "ization"), (re.compile(r"ise(d|s)?$"), r"ize\1"),
             (re.compile(r"^programme(s)?$"), r"program\1"), (re.compile(r"our$"), "or"),
             (re.compile(r"our(s|ed|ing)$"), r"or\1"), (re.compile(r"tre(s)?$"), r"ter\1"),
             (re.compile(r"ogue(s)?$"), r"og\1"), (re.compile(r"dgement(s)?$"), r"dgment\1"),
             (re.compile(r"ising$"), "izing"), (re.compile(r"ence(s)?$"), r"ense\1")]
_TENS_TEENS = {"ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen",
               "eighteen", "nineteen", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty",
               "ninety"}


# A regnal or ordinal numeral is one value written three ways: "Charles the
# Tenth" in the script, "Charles X" or "Charles the 10th" from the ASR model
# (2026-10-06 renders). After a capitalised word, both sides fold to "charles
# tenth"; only the same value can meet (X is tenth, never ninth). One to
# thirty-nine, so "MD", "CD", "DC" and "LA" stay letters. After "War" it is
# a cardinal ("World War II" is "World War Two").
_ROMAN = re.compile(r"^(XXX|XX|X)?(IX|IV|V?I{0,3})$")
_ROMAN_VAL = {"I": 1, "V": 5, "X": 10}
_ORDINALS = {ordinal_words(n): n for n in range(1, 40)}
_ORD_ALT = "|".join(sorted((re.escape(o) for o in _ORDINALS), key=len, reverse=True))
_NAME_THE_ORD = re.compile(r"\b([A-Z][a-z]+) the (" + _ORD_ALT + r")\b", re.I)
_NAME_ROMAN = re.compile(r"\b([A-Z][a-z]+) ([IVX]{1,6})\b")


def _roman(tok: str) -> int:
    if not tok or not _ROMAN.match(tok):
        return 0
    total, prev = 0, 0
    for c in reversed(tok):
        v = _ROMAN_VAL[c]
        total = total - v if v < prev else total + v
        prev = max(prev, v)
    return total if 1 <= total <= 39 else 0


def _regnal(t: str) -> str:
    def roman(m: re.Match) -> str:
        n = _roman(m.group(2))
        if not n:
            return m.group(0)
        if m.group(1).lower() == "war":
            return f"{m.group(1)} {number_words(n)}"
        return f"{m.group(1)} {ordinal_words(n)}"

    def the_ord(m: re.Match) -> str:
        if not m.group(1)[0].isupper():
            return m.group(0)
        return f"{m.group(1)} {m.group(2)}"
    t = _NAME_ROMAN.sub(roman, t)
    return _NAME_THE_ORD.sub(the_ord, t)


# "one and a half million" is said, "1.5 million" is written; both are 1.5.
# Folded to the decimal form only after a number word, so the value is the
# same digit for digit and "an hour and a half" stays words.
_FRACTIONS = {("and", "a", "half"): ["point", "five"],
              ("and", "a", "quarter"): ["point", "two", "five"],
              ("and", "three", "quarters"): ["point", "seven", "five"]}


def _fractions(words: list[str]) -> list[str]:
    out, i = [], 0
    while i < len(words):
        if out and out[-1] in _NUMBER_WORDS:
            hit = next((f for f in _FRACTIONS if tuple(words[i:i + 3]) == f), None)
            if hit:
                out.extend(_FRACTIONS[hit])
                i += 3
                continue
        out.append(words[i])
        i += 1
    return out


def _canon(w: str) -> str:
    # Six letters minimum: "four"/"for", "hour", "your", "rise" must stay
    # themselves, or a real misread would be folded away.
    if len(w) < 6:
        return w
    for pat, rep in _SPELLING:
        w = pat.sub(rep, w)
    return w


def norm_words(text: str) -> list[str]:
    # A digit range ("1975-1979", "1975 to 1979" written with a dash) spells
    # each year out only once the dash is a space; "a hundred" is "one hundred".
    t = re.sub(r"(?<=\d)\s*[-‐-―]\s*(?=\d)", " to ", text or "")
    t = re.sub(r"\ba (hundred|thousand|million)\b", r"one \1", t, flags=re.I)
    # A designator ("U-2", "R-12") is a letter and a number: split it so the
    # number is spelled the way the script spells it ("U two").
    t = re.sub(r"(?<=\b[A-Za-z])[-‐-―](?=\d)", " ", t)
    t = spoken_numbers(t)
    t = _regnal(t)
    t = re.sub(r"[-‐-―]", " ", t)
    t = re.sub(r"\bper cent\b", "percent", t, flags=re.I)
    t = "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")
    words = [_canon(w) for w in re.findall(r"[a-z0-9]+", t.lower())]
    # "nineteen oh four" spells back as "nineteen o four" (Scramble render).
    words = ["oh" if w == "o" else w for w in words]
    words = _fractions(words)
    # "two thousand and ninety four" is the British spoken form of 2,094; an
    # ASR model writes the digits, which spell back without the "and".
    words = [w for i, w in enumerate(words)
             if not (w == "and" and 0 < i < len(words) - 1
                     and words[i - 1] in _NUMBER_WORDS and words[i + 1] in _NUMBER_WORDS)]
    # A year from 2010 is said two ways: the script writes "two thousand
    # thirteen", an ASR model writes 2013, which spells back as "twenty
    # thirteen" (Srebrenica render, 2026-10-04). One form for both; it runs on
    # both sides after the "and" goes, so 2,094 still matches.
    i, folded = 0, []
    while i < len(words):
        if (words[i] == "two" and i + 2 < len(words) and words[i + 1] == "thousand"
                and words[i + 2] in _TENS_TEENS):
            folded.append("twenty")
            i += 2
            continue
        folded.append(words[i])
        i += 1
    return folded


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


# ---------------------------------------------------------------------------
# Proper names the transcriber spells its own way.
#
# An ASR model has never seen "Aldwin" or "Labouchere" and writes the nearest
# spelling it knows ("aldwyn", "la bouchere"); the voice said the name. Each
# failed six takes on 2026-10-06. Such an op goes to the ear log instead of
# failing, and ONLY when all of these hold, so a real misread still fails:
#   - the reference token is capitalised in the script line and is not the
#     first word of a sentence (a capitalised common word opens a sentence);
#   - neither side is a number, an ordinal or a digit (a number defect is
#     never waved through), and the reference is not "void", the brand;
#   - the hypothesis differs from the reference in exactly ONE letter, vowel
#     for vowel (y counts as a vowel), same length, at least four letters;
#     or the hypothesis is the name split in two ("la bouchere") or two
#     capitalised script tokens heard as one, with the letters unchanged.
# ---------------------------------------------------------------------------
_VOWELS = set("aeiouy")
_NEVER_EAR = {"void"}
_SENTENCE_END = re.compile(r"[.!?]['\"’”)\]]*\s*$")


def proper_names(text: str) -> set[str]:
    """Normalised tokens written capitalised mid-sentence in the script line."""
    out: set[str] = set()
    for m in re.finditer(r"[^\W\d_]+(?:['’][^\W\d_]+)?", text or ""):
        w = m.group(0)
        if not w[0].isupper():
            continue
        before = text[: m.start()]
        if not before.strip() or _SENTENCE_END.search(before):
            continue
        toks = norm_words(w)
        if len(toks) == 1:
            out.add(toks[0])
    return out


def _numeric(w: str | None) -> bool:
    return bool(w) and (w in _NUMBER_WORDS or w in _ORDINALS or any(c.isdigit() for c in w)
                        or w in ("point", "half", "quarter", "quarters", "billion", "zero", "oh"))


def _vowel_variant(r: str, h: str) -> bool:
    if len(r) < 4 or len(r) != len(h):
        return False
    diff = [(a, b) for a, b in zip(r, h) if a != b]
    return len(diff) == 1 and diff[0][0] in _VOWELS and diff[0][1] in _VOWELS


def _name_ok(r: str | None, names: set[str]) -> bool:
    return bool(r) and r in names and r not in _NEVER_EAR and not _numeric(r)


def judge_ops(text: str, ops: list[tuple], name_tokens=()) -> tuple[set, set]:
    """Split one decode's non-'=' ops into (defects, names for the ear).

    `ops` is align()'s output in order (the '=' ops may be present). An op on
    a token in `name_tokens` (the episode's cast list) goes to the ear as
    before; a proper-name spelling variant of the script line goes there too,
    under the rules above. Everything else is a defect."""
    listed = set(name_tokens or ())
    caps = proper_names(text)
    ear: set = set()
    seq = list(ops)
    for k, o in enumerate(seq):
        if o[0] != "S" or not _name_ok(o[1], caps) or _numeric(o[2]):
            continue
        if _vowel_variant(o[1], o[2]):
            ear.add(o)
            continue
        # Split: the name heard as two words, the extra one an insertion
        # immediately beside the substitution.
        for lo, hi in ((k - 1, k), (k, k + 1)):
            if lo < 0 or hi >= len(seq):
                continue
            pair = [seq[lo], seq[hi]]
            other = pair[0] if hi == k else pair[1]
            if other[0] != "I" or _numeric(other[2]):
                continue
            joined = "".join(p[2] for p in pair)
            if joined == o[1] or _vowel_variant(o[1], joined):
                ear.update(pair)
                break
        else:
            # Join: two capitalised script tokens heard as one word.
            for lo, hi in ((k - 1, k), (k, k + 1)):
                if lo < 0 or hi >= len(seq):
                    continue
                pair = [seq[lo], seq[hi]]
                other = pair[0] if hi == k else pair[1]
                if other[0] != "D" or not _name_ok(other[1], caps):
                    continue
                if "".join(p[1] for p in pair) == o[2]:
                    ear.update(pair)
                    break
    wrong, heard = set(), set()
    for o in seq:
        if o[0] == "=":
            continue
        if o in ear or o[1] in listed or o[2] in listed:
            heard.add(o)
        else:
            wrong.add(o)
    return wrong, heard
