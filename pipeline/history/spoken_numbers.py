"""Numbers as a History script speaks them, and as the event record writes them.

H-18 (script_format.validate_script) needs one question answered: is every
number this episode says aloud a number its event record carries? The scripts
spell numbers for the synthesiser ("nineteen seventy five", "one and a half
million", "December the twenty fifth"); the record writes them in digits
("1975", "1.5-2 million", "December 25, 1978") and sometimes in words ("three
days"). Both sides are reduced to VALUES here and compared as values.

The card pipeline has a spoken-number reader (`editorial.derived_grounding`),
but it reads "nineteen seventy five" as 94, which is right for a radio
headline and wrong for a History script where most spoken numbers are years.
This one reads the year form first.

Pure: no I/O. Tested in tests/test_history_script.py (H-18).
"""
from __future__ import annotations

import re
from typing import NamedTuple

UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine".split())}
TEENS = {w: 10 + i for i, w in enumerate(
    "ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate(
    "twenty thirty forty fifty sixty seventy eighty ninety".split())}
DECADES = {w[:-1] + "ies": v for w, v in TENS.items()}           # "sixties" -> 60
SCALES = {"thousand": 1_000, "million": 1_000_000, "billion": 1_000_000_000,
          "trillion": 1_000_000_000_000}
ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6,
    "seventh": 7, "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11,
    "twelfth": 12, "thirteenth": 13, "fourteenth": 14, "fifteenth": 15,
    "sixteenth": 16, "seventeenth": 17, "eighteenth": 18, "nineteenth": 19,
    "twentieth": 20, "thirtieth": 30, "fortieth": 40, "fiftieth": 50,
    "sixtieth": 60, "seventieth": 70, "eightieth": 80, "ninetieth": 90,
    "hundredth": 100, "thousandth": 1000,
}
HEDGES = frozenset("about almost nearly roughly around some approximately over "
                   "under more than less fewer perhaps estimated close up".split())
_CARD = {**UNITS, **TEENS, **TENS}


class Num(NamedTuple):
    value: float
    text: str        # the words it was read from, for the finding
    hedged: bool     # "about", "nearly", "more than": a rounded figure is honest
    start: int = 0   # token span, for pairing a range's two ends
    end: int = 0
    alts: tuple = () # the other reading of an ambiguous phrase, all of it sourced or none
    yearish: bool = False  # "in sixty four": a year said without its century
    after: str = ""        # the words that follow ("years later"), for intervals


_ORD_NAMES = "|".join(w.capitalize() for w in ORDINALS)
# "Jayavarman the Seventh", "Constantine the First": a regnal number is part of
# a name, and names are H-10's question.
_REGNAL = re.compile(rf"\bthe ({_ORD_NAMES})\b")
_FRACTION_OF_SCALE = [
    (re.compile(r"\b(?:a|one) quarter of a (million|billion)\b"), r"zero point two five \1"),
    (re.compile(r"\bthree quarters of a (million|billion)\b"), r"zero point seven five \1"),
    (re.compile(r"\bhalf a (million|billion)\b"), r"zero point five \1"),
]
_PUNCT = ",.;:!?()\""


def _tokens(text: str) -> list[str]:
    t = _REGNAL.sub(" ", (text or "").replace("’", "'"))
    t = t.lower()
    for rx, rep in _FRACTION_OF_SCALE:
        t = rx.sub(rep, t)
    t = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", t)
    return re.findall(r"[a-z]+|\d(?:[\d,]*\d)?(?:\.\d+)?|[,.;:!?()\"]", t)


def _two_digit(toks: list[str], i: int) -> tuple[int, int] | None:
    """A value 0..99 starting at toks[i], spoken as the back half of a year:
    "seventy five", "forty", "twelve", "oh five", "sixties". Returns (value,
    tokens used)."""
    if i >= len(toks):
        return None
    w = toks[i]
    if w == "oh" and i + 1 < len(toks) and toks[i + 1] in UNITS:
        return UNITS[toks[i + 1]], 2
    if w in TEENS:
        return TEENS[w], 1
    if w in TENS:
        if i + 1 < len(toks) and toks[i + 1] in UNITS and toks[i + 1] != "zero":
            return TENS[w] + UNITS[toks[i + 1]], 2
        if i + 1 < len(toks) and toks[i + 1] in ORDINALS and ORDINALS[toks[i + 1]] < 10:
            return TENS[w] + ORDINALS[toks[i + 1]], 2
        return TENS[w], 1
    if w in DECADES:
        return DECADES[w], 1
    return None


def _year_form(toks: list[str], i: int) -> tuple[int, int] | None:
    """A number spoken in the hundreds-pair form, which no cardinal can be:
    "nineteen seventy five" 1975, "thirteen forty nine" 1349, "nineteen oh
    five" 1905, "the nineteen sixties" 1960, "ten eighty two" 1082, "twenty
    twelve" 2012, "four seventy six" 476, "six fifty five" 655. A unit or a
    teen followed by "five" is a cardinal list, not this form, so the back half
    must itself be a teen, a tens word, a decade or "oh"."""
    w = toks[i]
    if w in TEENS and i + 1 < len(toks) and toks[i + 1] == "hundreds":
        return TEENS[w] * 100, 2            # "the late seventeen hundreds"
    if w in TEENS:
        head = TEENS[w]
    elif w in UNITS and w != "zero":
        head = UNITS[w]
    elif w == "twenty" and i + 1 < len(toks) and (toks[i + 1] in TEENS or toks[i + 1] in TENS):
        head = 20
    else:
        return None
    back = _two_digit(toks, i + 1)
    if back is None or toks[i + 1] in UNITS:
        return None
    end = i + 1 + back[1]
    # "nineteen fifty thousand" is not a year.
    if end < len(toks) and (toks[end] == "hundred" or toks[end] in SCALES):
        return None
    return head * 100 + back[0], 1 + back[1]


def _scales_ahead(toks: list[str], j: int) -> list[int]:
    """The scale words of the number that starts at toks[j], up to and
    including its first thousand-or-larger scale: "seven hundred and fifty
    thousand" -> [100, 1000]."""
    out: list[int] = []
    while j < len(toks) and (toks[j] in _CARD or toks[j] in ("hundred", "and", "a", *SCALES)):
        # "seventy and two hundred": an "and" after a plain count ends it.
        if toks[j] == "and" and toks[j - 1] not in ("hundred", *SCALES):
            break
        if toks[j] == "hundred":
            out.append(100)
        elif toks[j] in SCALES:
            out.append(SCALES[toks[j]])
            break
        j += 1
    return out


def _parse(toks: list[str], split_ambiguous: bool) -> list[Num]:
    out: list[Num] = []
    i = 0
    n = len(toks)
    while i < n:
        w = toks[i]
        prev = toks[i - 1] if i > 0 else ""
        hedged = prev in HEDGES or (i > 1 and toks[i - 2] in ("more", "less", "fewer") and prev == "than")

        yf = _year_form(toks, i)
        if yf is not None:
            v, used = yf
            out.append(Num(float(v), " ".join(toks[i:i + used]), hedged, i, i + used))
            i += used
            continue

        nxt1 = toks[i + 1] if i + 1 < n else ""
        nxt2 = toks[i + 2] if i + 2 < n else ""
        start_ok = (w in _CARD or w in ORDINALS
                    or (w in ("a", "the") and nxt1 in ("hundred", "dozen", *SCALES)
                        and not (w == "a" and nxt1 == "hundred" and prev == "in"))
                    # "the same hundred and twenty three years"
                    or (w == "hundred" and (nxt1 in _CARD or (nxt1 == "and" and nxt2 in _CARD))))
        if not start_ok:
            i += 1
            continue

        seg_start = i
        total = 0.0
        cur = 0.0
        last = None           # "unit" | "teen" | "tens" | "hundred" | "scale"
        teen_hundred = False  # "eighteen hundred": a year-like hundred
        last_scale = 0
        big_scale = 0         # the last thousand-or-larger scale in this number
        pieces: list[tuple[float, int, int]] = []

        def flush(at: int) -> None:
            nonlocal total, cur, last, teen_hundred, last_scale, big_scale, seg_start
            if last is not None:
                pieces.append((total + cur, seg_start, at))
            total, cur, last, teen_hundred, last_scale, big_scale = 0.0, 0.0, None, False, 0, 0
            seg_start = at

        while i < n:
            w = toks[i]
            nxt = toks[i + 1] if i + 1 < n else ""
            if w in ("a", "the") and nxt in ("hundred", "dozen", *SCALES) and last is None:
                cur, last = 1.0, "unit"
            elif w in UNITS:
                if last in ("unit", "teen"):
                    flush(i)
                cur += UNITS[w]
                last = "unit"
            elif w in TEENS:
                if last in ("unit", "teen", "tens"):
                    flush(i)
                cur += TEENS[w]
                last = "teen"
            elif w in TENS:
                if last in ("unit", "teen", "tens"):
                    flush(i)
                cur += TENS[w]
                last = "tens"
            elif w in ORDINALS:
                v = ORDINALS[w]
                if v == 100:
                    cur = (cur or 1) * 100
                elif v == 1000:
                    total += (cur or 1) * 1000
                    cur = 0.0
                else:
                    if last in ("unit", "teen") or (last == "tens" and v >= 10):
                        flush(i)
                    cur += v
                last = "unit"
                i += 1
                break                      # an ordinal ends the number
            elif w == "dozen" and last is not None:
                cur = (cur or 1) * 12
                last = "unit"
            elif w == "hundred" and last is None:
                cur, last, last_scale = 100.0, "hundred", 100
            elif w == "hundred" and last is not None and last != "hundred":
                teen_hundred = last == "teen" or cur >= 10
                cur = (cur or 1) * 100
                last = "hundred"
                last_scale = 100
            elif w in SCALES and last is not None:
                total += (cur or 1) * SCALES[w]
                cur = 0.0
                last = "scale"
                last_scale = big_scale = SCALES[w]
            elif w == "point" and last is not None and nxt in UNITS:
                j = i + 1
                digits = ""
                while j < n and toks[j] in UNITS:
                    digits += str(UNITS[toks[j]])
                    j += 1
                cur += float("0." + digits)
                i = j
                if i < n and toks[i] in SCALES:
                    total += cur * SCALES[toks[i]]
                    cur = 0.0
                    i += 1
                break
            elif (w == "and" and nxt == "a" and i + 2 < n and toks[i + 2] == "half"
                  and last is not None):
                cur += 0.5
                i += 3
                if i < n and toks[i] in SCALES:
                    total += cur * SCALES[toks[i]]
                    cur = 0.0
                    i += 1
                break
            elif w in ("and", ",") and last in ("hundred", "scale") and (nxt in _CARD or nxt in ORDINALS):
                # Continue one number, or start the next? "two hundred and
                # fifty", "eleven hundred and twenty three" and "four hundred
                # and ninety eight thousand" are one; "seven hundred thousand
                # and seven hundred and fifty thousand" and "eighteen hundred
                # and two thousand" are two. What follows must be smaller than
                # the scale it would sit under. "five hundred and four
                # thousand" is genuinely both (504,000, or 500 and 4,000), so
                # it is read both ways and either reading may be sourced.
                ahead = _scales_ahead(toks, i + 1)
                if _year_form(toks, i + 1) is not None:
                    # "between fifteen hundred and eighteen fifty": the next
                    # number is a year, read on its own.
                    break
                if last == "scale":
                    cont = all(x < last_scale for x in ahead)
                else:
                    big_ahead = [x for x in ahead if x >= 1000]
                    cont = (100 not in ahead
                            and all(x < (big_scale or float("inf")) for x in ahead)
                            and not (teen_hundred and big_ahead))
                    if cont and big_ahead and big_scale == 0 and split_ambiguous:
                        cont = False
                if not cont:
                    if w == ",":
                        break
                    flush(i + 1)
            else:
                break
            i += 1
        flush(i)
        for v, a, b in pieces:
            out.append(Num(v, " ".join(toks[a:b]).strip(" ,"), hedged, a, b))
        if i == seg_start and not pieces:
            i += 1

    # A range shares its scale: "between sixty and ninety thousand" is 60,000
    # to 90,000, "twelve to thirty thousand" is 12,000 to 30,000.
    fixed: list[Num] = []
    for k, x in enumerate(out):
        nxt = out[k + 1] if k + 1 < len(out) else None
        if nxt is not None and x.value < 1000 and not any(t in SCALES for t in toks[x.start:x.end]):
            joint = toks[x.end:nxt.start]
            scale = next((SCALES[t] for t in toks[nxt.start:nxt.end] if t in SCALES), 0)
            ranged = joint in (["to"], ["or"]) or (
                joint == ["and"] and x.start > 0 and toks[x.start - 1] == "between")
            if ranged and scale >= 1000 and x.value * scale <= nxt.value:
                x = x._replace(value=x.value * scale)
        fixed.append(x)
    return [x for x in fixed if x.value != 1 or x.text not in ("one", "a", "first")]


def spoken_numbers(text: str) -> list[Num]:
    """Every number spoken in words, as a value.

    The hundreds-pair form first (`_year_form`). Then cardinals with scales
    ("one hundred fifty thousand", "two hundred and fifty", "one and a half
    million", "one point five million", "a million", "a quarter of a
    million"), and ordinals ("the twenty fifth", "the ninth century"). Plural
    scales ("hundreds of thousands") are not a number. "one", "a" and "first"
    standing alone are not read: they are pronouns, articles and sequence far
    more often than counts.

    A phrase that reads two ways ("five hundred and four thousand") carries
    its second reading in `alts`.
    """
    toks = _tokens(text)
    a = _parse(toks, split_ambiguous=False)
    b = _parse(toks, split_ambiguous=True)
    out: list[Num] = []
    for x in a:
        inside = [y for y in b if y.start >= x.start and y.end <= x.end]
        if inside and [y.value for y in inside] != [x.value]:
            x = x._replace(alts=tuple(y.value for y in inside))
        # A year without its century: "in sixty four, sixty five and sixty
        # eight", "returned in fifty seven". Only a two-digit count, only after
        # a word that takes a year, and the list it heads.
        if 10 <= x.value < 100 and x.value == int(x.value) and x.start > 0:
            before = toks[x.start - 1]
            chained = (out and (out[-1].yearish or 1000 <= out[-1].value <= 2100)
                       and out[-1].end <= x.start
                       and all(t in (",", "and") for t in toks[out[-1].end:x.start]))
            if before in ("in", "since", "until") or chained:
                x = x._replace(yearish=True)
        x = x._replace(after=" ".join(toks[x.end:x.end + 2]))
        out.append(x)
    return out


_DIGITS = re.compile(
    r"(?<![\d.])(\d(?:[\d,]*\d)?(?:\.\d+)?)(?:st|nd|rd|th|s)?(?![\d])"
    r"(?:\s*(?:-|–|to|and|or)\s*(\d(?:[\d,]*\d)?(?:\.\d+)?))?"
    r"\s*(thousand|million|billion|trillion)?", re.I)


_KILOTONS = re.compile(r"(\d+(?:\.\d+)?)\s*kilotons?", re.I)


def digit_numbers(text: str) -> list[float]:
    """Numbers written in digits, with a scale applied, both ends of a range,
    and a year range's short end expanded ("1975-79" also yields 1979)."""
    out: list[float] = []
    for m in _DIGITS.finditer(text or ""):
        a_raw, b_raw, scale = m.group(1), m.group(2), (m.group(3) or "").lower()
        mult = SCALES.get(scale, 1)
        for raw in (a_raw, b_raw):
            if not raw:
                continue
            try:
                v = float(raw.replace(",", ""))
            except ValueError:
                continue
            out.append(v)
            if mult != 1:
                out.append(v * mult)
            # "$21,685,135,571.48": a script says the dollars and the cents.
            whole, _, frac = raw.replace(",", "").partition(".")
            if len(frac) == 2:
                out.extend((float(whole), float(frac)))
        if b_raw and len(a_raw) == 4 and len(b_raw) == 2 and a_raw.isdigit() and b_raw.isdigit():
            out.append(float(a_raw[:2] + b_raw))
    # "15 kilotons" is said "fifteen thousand tonnes".
    out.extend(float(k) * 1000 for k in _KILOTONS.findall(text or ""))
    # "9/11" is spoken "nine eleven".
    out.extend(float(a + b) for a, b in re.findall(r"\b(\d{1,2})/(\d{1,2})\b", text or ""))
    # A clock time ("11:30") is spoken "eleven thirty".
    out.extend(float(h + m) for h, m in re.findall(r"\b(\d{1,2}):(\d{2})\b", text or ""))
    return out


def record_values(text: str) -> set[float]:
    """Every number the record carries, in digits or in words."""
    vals = set(digit_numbers(text))
    vals.update(x.value for x in spoken_numbers(text))
    return vals


def _one(value: float, hedged: bool, values: set[float]) -> bool:
    if value in values:
        return True
    if hedged:
        return any(v and abs(v - value) <= 0.1 * abs(v) for v in values)
    return False


def supported(num: Num, values: set[float]) -> bool:
    """Exactly in the record; or, for a hedged figure, within a tenth of one.
    An ambiguous phrase is sourced when either whole reading is."""
    if _one(num.value, num.hedged, values):
        return True
    if num.yearish and any(v >= 1000 and v == int(v) and int(v) % 100 == num.value for v in values):
        return True
    return bool(num.alts) and all(_one(v, num.hedged, values) for v in num.alts)
