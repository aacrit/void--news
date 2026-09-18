"""Text normalisation for the ear: what the TTS engine must never see.

Broadcast copy is written for a reader who will SAY it, so numerals, currency
symbols, percent signs and print-style initialisms are converted to spoken
words before synthesis. Kokoro/espeak and edge-tts each guess differently at
"$1.2bn", "3.75%" or "ICE"; the pipeline decides instead, deterministically.

Pure functions, stdlib only, shared by the radio script validators (which
report what the model wrote) and the audio producer (which fixes it anyway).

Order of application (``normalize_for_speech``):
  1. ``apply_say``          model-supplied respellings from the ``## SAY`` block
  2. ``spoken_numbers``     currency, percent, ordinals, decimals, years, ints
  3. ``expand_initialisms`` U-S, E-U, F-B-I ... (words like NATO stay words)
"""

from __future__ import annotations

import re
from datetime import date, datetime

# ---------------------------------------------------------------------------
# Number words
# ---------------------------------------------------------------------------

_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
         "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
         "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]
_SCALES = [(10 ** 12, "trillion"), (10 ** 9, "billion"), (10 ** 6, "million"),
           (10 ** 3, "thousand")]

_ORDINAL_IRREGULAR = {
    "one": "first", "two": "second", "three": "third", "five": "fifth",
    "eight": "eighth", "nine": "ninth", "twelve": "twelfth",
}


def _below_thousand(n: int) -> str:
    parts = []
    if n >= 100:
        parts.append(f"{_ONES[n // 100]} hundred")
        n %= 100
    if n >= 20:
        tens = _TENS[n // 10]
        parts.append(f"{tens}-{_ONES[n % 10]}" if n % 10 else tens)
    elif n > 0 or not parts:
        parts.append(_ONES[n])
    return " ".join(parts)


def number_words(n: int) -> str:
    """``1234`` -> ``one thousand two hundred thirty-four``."""
    if n < 0:
        return "minus " + number_words(-n)
    if n < 1000:
        return _below_thousand(n)
    parts = []
    for value, name in _SCALES:
        if n >= value:
            parts.append(f"{_below_thousand(n // value) if n // value < 1000 else number_words(n // value)} {name}")
            n %= value
    if n:
        parts.append(_below_thousand(n))
    return " ".join(parts)


def ordinal_words(n: int) -> str:
    """``18`` -> ``eighteenth``, ``21`` -> ``twenty-first``."""
    words = number_words(n)
    head, sep, last = words.rpartition(" ")
    if "-" in last:
        tens, _, unit = last.rpartition("-")
        last = f"{tens}-{ordinal_words_single(unit)}"
    else:
        last = ordinal_words_single(last)
    return f"{head}{sep}{last}"


def ordinal_words_single(word: str) -> str:
    if word in _ORDINAL_IRREGULAR:
        return _ORDINAL_IRREGULAR[word]
    if word.endswith("y"):
        return word[:-1] + "ieth"
    return word + "th"


def year_words(n: int) -> str:
    """``1979`` -> ``nineteen seventy-nine``; ``2026`` -> ``twenty twenty-six``;
    ``2000`` -> ``two thousand``; ``2005`` -> ``two thousand five``."""
    if 1100 <= n <= 1999 or 2100 <= n <= 9999:
        hi, lo = divmod(n, 100)
        if lo == 0:
            return f"{_below_thousand(hi)} hundred"
        if lo < 10:
            return f"{_below_thousand(hi)} oh {_ONES[lo]}"
        return f"{_below_thousand(hi)} {_below_thousand(lo)}"
    if 2000 <= n <= 2099:
        lo = n - 2000
        if lo == 0:
            return "two thousand"
        if lo < 10:
            return f"two thousand {_ONES[lo]}"
        return f"twenty {_below_thousand(lo)}"
    return number_words(n)


def spoken_date(d: date | datetime) -> str:
    """``2026-09-18`` -> ``Friday, September eighteenth``."""
    return f"{d.strftime('%A')}, {d.strftime('%B')} {ordinal_words(d.day)}"


# ---------------------------------------------------------------------------
# Numerals inside prose
# ---------------------------------------------------------------------------

_CURRENCY = {"$": ("dollar", "dollars"), "£": ("pound", "pounds"),
             "€": ("euro", "euros"), "¥": ("yen", "yen"), "₹": ("rupee", "rupees")}
_MAGNITUDE = {"k": "thousand", "m": "million", "mn": "million", "bn": "billion",
              "b": "billion", "tn": "trillion", "t": "trillion"}

_NUM = r"(\d{1,3}(?:,\d{3})+|\d+)(?:\.(\d+))?"
_CURRENCY_RE = re.compile(
    r"(?<![\w.])([$£€¥₹])\s?" + _NUM + r"\s?(trillion|billion|million|thousand|tn|bn|mn|k|m|b|t)?(?![\w])",
    re.IGNORECASE,
)
_PERCENT_RE = re.compile(_NUM + r"\s?(?:%|percent(?:age points?)?)(?![\w])", re.IGNORECASE)
_ORDINAL_RE = re.compile(r"(?<![\w.])(\d+)(st|nd|rd|th)(?![\w])")
_MAG_RE = re.compile(_NUM + r"\s?(trillion|billion|million|thousand|tn|bn|mn|k|m|b)(?![\w])", re.IGNORECASE)
_PLAIN_RE = re.compile(r"(?<![\w.\-/:])" + _NUM + r"(?![\w/:])")
_TIME_RE = re.compile(r"(?<![\w.])(\d{1,2}):(\d{2})(?![\w:])")


def _int_of(s: str) -> int:
    return int(s.replace(",", ""))


def _decimal_words(int_part: str, frac: str | None) -> str:
    words = number_words(_int_of(int_part))
    if frac:
        words += " point " + " ".join(_ONES[int(ch)] for ch in frac)
    return words


def _magnitude(word: str | None) -> str:
    if not word:
        return ""
    w = word.lower()
    return _MAGNITUDE.get(w, w)


def spoken_numbers(text: str) -> str:
    """Convert numerals, currency, percentages, ordinals and years to words."""
    def currency(m: re.Match) -> str:
        sym, ip, frac, mag = m.group(1), m.group(2), m.group(3), m.group(4)
        singular, plural = _CURRENCY[sym]
        magw = _magnitude(mag)
        if magw:
            return f"{_decimal_words(ip, frac)} {magw} {plural}"
        n = _int_of(ip)
        if frac and len(frac) == 2 and n < 1000:
            # $1.50 -> one dollar fifty
            cents = int(frac)
            unit = singular if n == 1 else plural
            if cents:
                return f"{number_words(n)} {unit} {number_words(cents)}"
            return f"{number_words(n)} {unit}"
        unit = singular if n == 1 and not frac else plural
        return f"{_decimal_words(ip, frac)} {unit}"

    def percent(m: re.Match) -> str:
        return f"{_decimal_words(m.group(1), m.group(2))} percent"

    def ordinal(m: re.Match) -> str:
        return ordinal_words(int(m.group(1)))

    def magnitude(m: re.Match) -> str:
        return f"{_decimal_words(m.group(1), m.group(2))} {_magnitude(m.group(3))}"

    def clock(m: re.Match) -> str:
        h, mm = int(m.group(1)), int(m.group(2))
        if h > 24:
            return m.group(0)
        if mm == 0:
            return f"{number_words(h)} o'clock"
        return f"{number_words(h)} {'oh ' if mm < 10 else ''}{number_words(mm)}"

    def plain(m: re.Match) -> str:
        ip, frac = m.group(1), m.group(2)
        if frac:
            return _decimal_words(ip, frac)
        n = _int_of(ip)
        if "," not in ip and 1100 <= n <= 2099 and len(ip) == 4:
            return year_words(n)
        return number_words(n)

    text = _CURRENCY_RE.sub(currency, text)
    text = _PERCENT_RE.sub(percent, text)
    text = _ORDINAL_RE.sub(ordinal, text)
    text = _TIME_RE.sub(clock, text)
    text = _MAG_RE.sub(magnitude, text)
    text = _PLAIN_RE.sub(plain, text)
    return text


# ---------------------------------------------------------------------------
# Initialisms and respellings
# ---------------------------------------------------------------------------

# Read letter by letter. Everything NOT listed here is left alone, so acronyms
# pronounced as words (NATO, OPEC, UNESCO, NASA, ISIS, AUKUS) stay words.
BUILTIN_INITIALISMS: dict[str, str] = {
    "US": "U-S", "U.S.": "U-S", "USA": "U-S-A", "UK": "U-K", "U.K.": "U-K",
    "EU": "E-U", "E.U.": "E-U", "UN": "U-N", "U.N.": "U-N", "UAE": "U-A-E",
    "AI": "A-I", "ECB": "E-C-B", "GDP": "G-D-P", "CPI": "C-P-I", "IMF": "I-M-F",
    "WHO": "W-H-O", "WTO": "W-T-O", "FBI": "F-B-I", "CIA": "C-I-A", "NSA": "N-S-A",
    "DOJ": "D-O-J", "DHS": "D-H-S", "ICE": "I-C-E", "IRS": "I-R-S", "SEC": "S-E-C",
    "FDA": "F-D-A", "EPA": "E-P-A", "CDC": "C-D-C", "NIH": "N-I-H", "FAA": "F-A-A",
    "CEO": "C-E-O", "CFO": "C-F-O", "GOP": "G-O-P", "MP": "M-P", "MPs": "M-Ps",
    "PM": "P-M", "EV": "E-V", "EVs": "E-Vs", "IPO": "I-P-O", "ETF": "E-T-F",
    "BBC": "B-B-C", "CNN": "C-N-N", "NBC": "N-B-C", "ABC": "A-B-C", "CBS": "C-B-S",
    "NYC": "N-Y-C", "LA": "L-A", "DC": "D-C", "D.C.": "D-C", "GMT": "G-M-T",
    "UTC": "U-T-C", "IDF": "I-D-F", "PLA": "P-L-A", "SBU": "S-B-U", "ANC": "A-N-C",
    "BJP": "B-J-P", "AfD": "A-F-D", "SPD": "S-P-D", "CDU": "C-D-U", "LNG": "L-N-G",
    "GPS": "G-P-S", "HIV": "H-I-V", "TB": "T-B", "ER": "E-R", "PhD": "P-H-D",
    "vs.": "versus", "vs": "versus", "Mr.": "Mister", "Mrs.": "Missus",
    "Dr.": "Doctor", "St.": "Saint", "Gen.": "General", "Sen.": "Senator",
    "Rep.": "Representative", "Gov.": "Governor", "Lt.": "Lieutenant",
    "km": "kilometres", "kg": "kilograms", "mph": "miles an hour",
}

# Tokens that look like initialisms but are ordinary words in caps.
_KEEP_AS_WORD = {"NATO", "OPEC", "UNESCO", "NASA", "ISIS", "AUKUS", "ASEAN",
                 "NAFTA", "OSHA", "FEMA", "SWAT", "AIDS", "COVID", "UNICEF",
                 "OPEC+", "BRICS", "PISA", "NASDAQ", "SCOTUS"}


def _token_pattern(token: str) -> str:
    # Word boundaries do not work around a trailing period ("U.S.") so build
    # the lookarounds by hand: not preceded by a word char, not followed by one.
    return r"(?<![\w-])" + re.escape(token) + r"(?![\w-])"


def expand_initialisms(text: str, table: dict[str, str] | None = None) -> str:
    """Spell listed initialisms letter by letter (``US`` -> ``U-S``)."""
    merged = dict(BUILTIN_INITIALISMS)
    if table:
        merged.update(table)
    for token in sorted(merged, key=len, reverse=True):
        if token in _KEEP_AS_WORD:
            continue
        text = re.sub(_token_pattern(token), merged[token], text)
    return text


def apply_say(text: str, say: dict[str, str] | None) -> str:
    """Apply ``## SAY`` respellings (``Hormuz = hor-MOOZ``), longest key first."""
    if not say:
        return text
    for key in sorted(say, key=len, reverse=True):
        val = say[key].strip()
        if not key.strip() or not val:
            continue
        text = re.sub(_token_pattern(key.strip()), val, text)
    return text


_DASHES_RE = re.compile(r"\s*[—–]\s*")


def normalize_for_speech(text: str, say: dict[str, str] | None = None) -> str:
    """Everything the TTS should get: respellings, spoken numbers, initialisms.

    Em/en dashes become a comma-pause (engines read them inconsistently; a
    comma is the one pause every engine honours). Double spaces collapse.
    """
    text = apply_say(text, say)
    text = spoken_numbers(text)
    text = expand_initialisms(text, say)
    text = _DASHES_RE.sub(", ", text)
    text = re.sub(r"\s*,\s*,", ",", text)
    return re.sub(r"[ \t]{2,}", " ", text).strip()


# ---------------------------------------------------------------------------
# Detection helpers for the validators (report, do not fix)
# ---------------------------------------------------------------------------

_DIGIT_RE = re.compile(r"\d")
_QUOTE_RE = re.compile(r"[\"“”„‟]|(?<!\w)['‘’](?=\w)|(?<=\w)['‘’](?!\w)")


def has_numerals(text: str) -> bool:
    return bool(_DIGIT_RE.search(text))


def has_quotation_marks(text: str) -> bool:
    """Double quotes, or single quotes used as quotation marks (not apostrophes)."""
    if re.search(r"[\"“”„‟]", text):
        return True
    # ‘word ... word’ pairs: an opening single quote after a non-word char.
    return bool(re.search(r"(?<![\w])[‘'](?=\w)[^‘’']{3,}[’'](?![\w])", text))
