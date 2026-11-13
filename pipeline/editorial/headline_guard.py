"""Headline and place guards: three Rule 1 controls added 2026-11-02.

Found on the served page of 2026-11-02, once Gemini was writing again:

1. The Brief's headline said "Kherson Truce Collapses" over text that said the
   ceasefire "expired ... without an extension". The head made a stronger claim
   than the words under it. `overreach` lists the escalation verbs a headline
   uses that its own text never does; `guard_headline` cuts the clause that
   carries one, or falls back to a head that does not.
2. A card placed the Kherson truce in "the eastern Kherson region"; every
   other text that day, the Brief included, said southern. E-13 checks numbers
   and E-14 quotations, and nothing checked a compass word. `drop_unsourced_
   directions` removes a direction adjective in front of a place when no source
   puts that direction beside that place. The sentence stays true without it.
3. Heads were written in three styles ("Tens Of Thousands Protest In Delhi",
   "Over Three Hundred Protesters"). `house_case` lower-cases the short joining
   words of a Title Case head and writes a spelled number of ten or more as
   digits, the newspaper convention, so every head reads alike.

All three are deterministic and run at write time; nothing here calls a model.
"""
from __future__ import annotations

import re

# --------------------------------------------------------------------------- 1
# Escalation verbs: each asserts that something broke, burst or moved sharply.
# Matched by stem, so "collapses" in a head is answered by "collapsed" in text.
_ESCALATION_STEMS = (
    "collaps", "crumbl", "implod", "erupt", "explod", "shatter", "plung",
    "plummet", "soar", "skyrocket", "slam", "blast", "decimat", "devastat",
    "meltdown", "unravel", "spiral",
)
_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")


def _stem_of(word: str) -> str | None:
    w = word.lower()
    for stem in _ESCALATION_STEMS:
        if w.startswith(stem):
            return stem
    return None


def overreach(headline: str, text: str) -> list[str]:
    """Escalation words in `headline` whose stem appears nowhere in `text`."""
    body = (text or "").lower()
    out = []
    for w in _WORD_RE.findall(headline or ""):
        stem = _stem_of(w)
        if stem and stem not in body:
            out.append(w)
    return out


_CLAUSE_SPLIT = re.compile(r"\s+(?:as|amid|while|after|and)\s+|;\s+|,\s+|:\s+", re.I)


def guard_headline(headline: str, text: str, fallback: str = "") -> str:
    """The head with no claim stronger than its text, in house style.

    Cuts the clause holding the overreaching word when what is left before it
    is a head of four words or more; otherwise uses `fallback` (a head that
    passes), and failing that the head as written, so a head is never blank.
    """
    head = (headline or "").strip()
    if not head:
        return head
    bad = overreach(head, text)
    if bad:
        first = min(head.lower().find(w.lower()) for w in bad)
        cuts = [m.start() for m in _CLAUSE_SPLIT.finditer(head) if m.start() < first]
        kept = head[:cuts[-1]].rstrip(" ,;:") if cuts else ""
        if len(kept.split()) >= 4 and not overreach(kept, text):
            print(f"  [headline-guard] cut {head[len(kept):].strip()!r}: "
                  f"{', '.join(bad)} is not in the text")
            head = kept
        elif fallback and not overreach(fallback, text):
            print(f"  [headline-guard] {head!r} -> fallback: {', '.join(bad)} is not in the text")
            head = fallback.strip()
    return house_case(head)


# --------------------------------------------------------------------------- 2
_DIRECTION = (r"(?:north|south|east|west|north-?east|north-?west|south-?east|"
              r"south-?west|central)(?:ern)?")
_DIRECTED_PLACE = re.compile(rf"\b({_DIRECTION})\s+((?:[A-Z][\w'-]+)(?:\s+[A-Z][\w'-]+)?)")


def _root(direction: str) -> str:
    d = direction.lower().replace("-", "")
    return d[:-3] if d.endswith("ern") else d


def drop_unsourced_directions(summary: str, source_text: str) -> str:
    """Remove a compass word before a place unless a source pairs them.

    "the eastern Kherson region" -> "the Kherson region" when no source sentence
    that names Kherson also carries east/eastern. A source that pairs them in
    any order ("Kherson, in the east") keeps it. Without source text, nothing
    is changed: absence of evidence is not checked against nothing.
    """
    if not summary or not source_text:
        return summary
    sentences = re.split(r"(?<=[.!?])\s+", source_text)

    def supported(direction: str, place: str) -> bool:
        root = _root(direction)
        name = place.split()[0].lower()
        for s in sentences:
            low = s.lower()
            if name in low and re.search(rf"\b{root}(?:ern)?\b", low.replace("-", "")):
                return True
        return False

    def repl(m: "re.Match[str]") -> str:
        direction, place = m.group(1), m.group(2)
        if supported(direction, place):
            return m.group(0)
        print(f"  [place-guard] dropped {direction!r} before {place!r}: no source pairs them")
        return place

    out = _DIRECTED_PLACE.sub(repl, summary)
    # "the eastern Kherson region" -> "the Kherson region": an article left
    # before a capitalised name stays grammatical; tidy doubled spaces only.
    return re.sub(r"\s{2,}", " ", out)


# --------------------------------------------------------------------------- 3
_SMALL = frozenset({"a", "an", "the", "and", "but", "or", "nor", "for", "as",
                    "at", "by", "in", "of", "on", "to", "via", "vs", "per"})
_UNITS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
          "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
          "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
          "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19}
_TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
         "seventy": 70, "eighty": 80, "ninety": 90}
_SCALES = {"hundred": 100, "thousand": 1000, "million": 1_000_000}
_NUM_WORDS = set(_UNITS) | set(_TENS) | set(_SCALES)


def _parse_number(words: list[str]) -> int | None:
    total, current = 0, 0
    for w in words:
        parts = w.lower().split("-")
        for p in parts:
            if p in _UNITS:
                current += _UNITS[p]
            elif p in _TENS:
                current += _TENS[p]
            elif p == "hundred":
                current = max(current, 1) * 100
            elif p in ("thousand", "million"):
                total += max(current, 1) * _SCALES[p]
                current = 0
            else:
                return None
    return total + current


def _digits_for_spelled_numbers(head: str) -> str:
    tokens = head.split(" ")
    out, i = [], 0
    while i < len(tokens):
        j = i
        while j < len(tokens) and all(p.lower() in _NUM_WORDS
                                      for p in tokens[j].strip(",").split("-")):
            j += 1
        run = tokens[i:j]
        value = _parse_number([t.strip(",") for t in run]) if run else None
        big = any(t.lower().strip(",") in _SCALES for t in run)
        if run and value is not None and (value >= 10 or big):
            out.append(f"{value:,}" + ("," if run[-1].endswith(",") else ""))
            i = j
        else:
            out.append(tokens[i])
            i += 1
    return " ".join(out)


def house_case(head: str) -> str:
    """One headline style. A Title Case head keeps its capitals except the
    short joining words (first word and the word after a colon excepted); a
    sentence-case head is left as written. A spelled number of ten or more,
    or one with hundred/thousand/million, becomes digits."""
    head = _digits_for_spelled_numbers((head or "").strip())
    words = head.split(" ")
    long_words = [w for w in words if len(re.sub(r"\W", "", w)) >= 4]
    if not long_words:
        return head
    title_case = sum(w[:1].isupper() for w in long_words) / len(long_words) >= 0.6
    if not title_case:
        return head
    out = []
    for i, w in enumerate(words):
        core = w.strip("'\"‘’“”(")
        after_colon = i > 0 and words[i - 1].endswith(":")
        if i > 0 and not after_colon and core.lower() in _SMALL and core[:1].isupper() \
                and not core.isupper():
            w = w.replace(core, core.lower(), 1)
        out.append(w)
    return " ".join(out)


__all__ = ["overreach", "guard_headline", "drop_unsourced_directions", "house_case"]
