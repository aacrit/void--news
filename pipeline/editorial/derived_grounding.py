"""Ground the derived products against the cards they were written from.

WHY. The TL;DR, the Opinion and the On Air script are written AFTER every card
check has run, by a model handed the finished cards, and nothing read them
against those cards. The edition of 2026-10-01 shipped, in those three
products alone (audit 1, items 1, 2, 4, 5 and 9):

  * "a 20 percent reduction ... This follows 10 percent cuts last year,
    totaling a 20 percent reduction": the brief stacked a consensus point onto
    the card's sentence and a listener heard thirty;
  * "would cost Scottish pensioners £1,000 per year": no source carries it
    (the card says £4 billion, nearly £2,000 a pensioner);
  * "released on police bail just two days later": the source says a day
    earlier;
  * "those who clung to the woke department would be purged": the speaker
    said "no longer work here";
  * a Renee Good paragraph that ended on another card's story.

E-13 and E-14 never saw any of it, because they run on cards.

WHAT THIS DOES. A deterministic pass, per paragraph, mapped to the cluster the
paragraph is about. Every number, quotation, multi-word proper name, weekday,
date and interval phrase must appear in THAT cluster's text (title, summary,
consensus and divergence points: what the writer was handed). A sentence that
fails is CUT, never regenerated: the flash tier is capped at 20 requests a
day, and a cut is silence where a rewrite is another unverified sentence.
Every cut is logged with its reason.

Also cut, because each is a class that shipped:
  * a figure that contradicts its own sentence: a total that is not the sum
    of the parts it names (the stacked 20 percent);
  * reported speech that starts by lifting a quotation and ends somewhere the
    quotation never went (the "purged" kicker);
  * a hedge standing in for attribution on a reputational claim (E-15, which
    is advisory on cards and BLOCKING here);
  * in the TL;DR, a sentence about a different cluster's story inside a
    paragraph (one story per paragraph): moved to its own paragraph when that
    story has none, cut when it does.

Radio numbers are words ("twenty percent", "almost four billion dollars"), so
spoken numbers are read as values, and a hedged or spoken figure may round.

Pure: no I/O, no model, no network. Imported by the brief and radio
generators, tested in tests/test_brief_grounding.py.
"""
from __future__ import annotations

import re
from typing import Any, Iterable, NamedTuple

try:
    from . import grounding as G
    from . import standard as std
except ImportError:  # pragma: no cover - loaded as top-level modules
    import grounding as G  # type: ignore[no-redef]
    import standard as std  # type: ignore[no-redef]


class Cut(NamedTuple):
    product: str
    sentence: str
    reason: str

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"[{self.product}] cut ({self.reason}): {self.sentence[:110]}"


# ---------------------------------------------------------------------------
# Spoken numbers
# ---------------------------------------------------------------------------
_UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve "
    "thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split())}
_TENS = {w: 10 * (i + 2) for i, w in enumerate(
    "twenty thirty forty fifty sixty seventy eighty ninety".split())}
_SCALES = {"hundred": 100, "thousand": 1_000, "million": 1_000_000,
           "billion": 1_000_000_000, "trillion": 1_000_000_000_000}
_FRACTIONS = {"half": 0.5, "quarter": 0.25, "three-quarter": 0.75,
              "three-quarters": 0.75, "quarters": 0.25}
_HEDGES = frozenset("about almost nearly roughly around some approximately "
                    "over under than just close".split())
_SUFFIX_SCALE = {"bn": 1e9, "b": 1e9, "m": 1e6, "mn": 1e6, "k": 1e3, "tn": 1e12,
                 "trn": 1e12}


class Value(NamedTuple):
    value: float
    text: str
    hedged: bool
    spoken: bool


def _word_tokens(text: str) -> list[str]:
    t = (text or "").lower().replace("’", "'")
    t = t.replace("three-quarters", "threequarters").replace("three-quarter", "threequarter")
    t = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", t)
    t = t.replace("threequarters", "three-quarters").replace("threequarter", "three-quarter")
    return re.findall(r"[a-z][a-z'-]*|\d[\d,]*(?:\.\d+)?|[%$£€]", t)


def spoken_values(text: str) -> list[Value]:
    """Numbers written as words, as values: "twenty-seven" 27, "four billion"
    4e9, "three and three-quarter percent" 3.75, "four point two" 4.2."""
    toks = _word_tokens(text)
    out: list[Value] = []
    i = 0
    while i < len(toks):
        t = toks[i]
        if t not in _UNITS and t not in _TENS:
            i += 1
            continue
        start = i
        total, current = 0.0, 0.0
        seen_any = False
        while i < len(toks):
            w = toks[i]
            if w in _UNITS:
                current += _UNITS[w]
            elif w in _TENS:
                current += _TENS[w]
            elif w == "hundred" and seen_any:
                current = (current or 1) * 100
            elif w in ("thousand", "million", "billion", "trillion") and seen_any:
                total += (current or 1) * _SCALES[w]
                current = 0.0
            elif w == "and" and seen_any and i + 1 < len(toks) and (
                    toks[i + 1] in _UNITS or toks[i + 1] in _TENS
                    or toks[i + 1] in ("a", "one", "three-quarter", "three-quarters")):
                # "three and three-quarter", "a hundred and twelve"
                if i + 1 < len(toks) and toks[i + 1] in ("a",) and i + 2 < len(toks) \
                        and toks[i + 2] in _FRACTIONS:
                    current += _FRACTIONS[toks[i + 2]]
                    i += 3
                    break
                if toks[i + 1] in ("three-quarter", "three-quarters"):
                    current += 0.75
                    i += 2
                    break
                if i + 2 < len(toks) and toks[i + 1] in _UNITS and toks[i + 2] in _FRACTIONS:
                    current += _UNITS[toks[i + 1]] * _FRACTIONS[toks[i + 2]] \
                        if toks[i + 2] != "half" else 0.5
                    i += 3
                    break
            elif w == "point" and seen_any and i + 1 < len(toks) and toks[i + 1] in _UNITS:
                digits = ""
                j = i + 1
                while j < len(toks) and toks[j] in _UNITS and _UNITS[toks[j]] < 10:
                    digits += str(_UNITS[toks[j]])
                    j += 1
                current += float("0." + digits) if digits else 0
                i = j
                break
            else:
                break
            seen_any = True
            i += 1
        value = total + current
        # A scale word after a decimal: "four point two billion".
        if i < len(toks) and toks[i] in ("thousand", "million", "billion", "trillion"):
            value *= _SCALES[toks[i]]
            i += 1
        prev = toks[start - 1] if start > 0 else ""
        out.append(Value(value, " ".join(toks[start:i]), prev in _HEDGES, True))
    return out


_DIGIT_VALUE_RE = re.compile(
    r"(?P<num>\b\d[\d,]*(?:\.\d+)?)(?P<suf>bn|b|mn|m|k|tn|trn)?\b\s*"
    r"(?P<scale>thousand|million|billion|trillion)?", re.I)


def digit_values(text: str) -> list[Value]:
    """Numbers written in digits, with a scale word or suffix applied."""
    out: list[Value] = []
    toks = (text or "").lower().split()
    for m in _DIGIT_VALUE_RE.finditer(text or ""):
        raw = m.group("num").replace(",", "")
        try:
            v = float(raw)
        except ValueError:
            continue
        suf = (m.group("suf") or "").lower()
        scale = (m.group("scale") or "").lower()
        if suf in _SUFFIX_SCALE:
            v *= _SUFFIX_SCALE[suf]
        if scale:
            v *= _SCALES[scale]
        before = (text or "")[:m.start()].lower().split()
        prev = before[-1] if before else ""
        out.append(Value(v, m.group(0).strip(), prev in _HEDGES or prev in
                         ("than",), False))
    del toks
    return out


def _in_scope(v: Value) -> bool:
    """The same scope as E-13: two digits or more, a decimal, or a scale."""
    if v.value != int(v.value):
        return True
    return abs(v.value) >= 10


def values_of(text: str) -> list[Value]:
    return [v for v in digit_values(text) + spoken_values(text) if _in_scope(v)]


# ---------------------------------------------------------------------------
# The cluster's evidence
# ---------------------------------------------------------------------------
def cluster_text(cluster: dict[str, Any] | str) -> str:
    """What the writer was handed for one story, one passage per line.

    The points read here are the ones that PASSED. Stage 2 (8d.3, rev 86) runs
    E-13, E-14 and E-16 on every consensus and divergence point against the
    card's own evidence and writes back only the survivors, and the brief and
    radio read their rows after that write. So a point is evidence here only
    once a check has had the chance to drop it: before rev 86 an unsourced
    number in a point became an anchor that let the same number through the
    TL;DR. E-16 needs no evidence, so it is also re-run here, and a point that
    opens on another story is never evidence for this one.
    """
    if isinstance(cluster, str):
        return cluster
    parts = [cluster.get("title"), cluster.get("summary")]
    for k in std.POINT_FIELDS:
        for p in std.as_points(cluster.get(k)):
            text = std.point_text(p)
            if text.strip() and not std.e16_topic_shift(text.strip()):
                parts.append(text)
    if cluster.get("_source_text"):
        parts.append(str(cluster["_source_text"]))
    return "\n".join(str(p).strip() for p in parts if p and str(p).strip())


class Evidence:
    """One cluster's text, answering the questions this pass asks."""

    def __init__(self, cluster: dict[str, Any] | str):
        self.text = cluster_text(cluster)
        self.index = G.TextIndex(self.text)
        self.folded = _norm_names(self.text)
        self.values = [v.value for v in digit_values(self.text) + spoken_values(self.text)]
        self.sentences = [s for p in self.text.split("\n") for s in _sentences(p)]
        self.quotes = [_fold_words(q) for q in std._QUOTE_RE.findall(self.text)]
        self.stems = std.title_word_stems(self.text)
        self.entities = _entities(self.text)
        self.cid = None if isinstance(cluster, str) else (
            cluster.get("id") or cluster.get("_db_id"))

    def has_value(self, v: Value) -> bool:
        for s in self.values:
            if abs(s - v.value) <= 1e-9 * max(1.0, abs(s)):
                return True
        if v.hedged or v.spoken:
            # A spoken or hedged figure rounds: "almost four billion" for 3.9bn.
            for s in self.values:
                if s and abs(s - v.value) <= 0.1 * abs(s):
                    return True
        return False


def _fold_words(text: str) -> list[str]:
    return G.words_of(text)


def _norm_names(text: str) -> str:
    t = (text or "").replace("’", "'")
    t = re.sub(r"\b([A-Z])-(?=[A-Z]\b)", r"\1", t)   # spoken "F-B-I" -> "FBI"
    t = re.sub(r"'s\b", "", t.lower())
    t = t.replace(".", "")
    return re.sub(r"\s+", " ", t)


# ---------------------------------------------------------------------------
# Checks, each returning a reason or None
# ---------------------------------------------------------------------------
def _collapse_spelled(text: str) -> str:
    """"the U-S", "N-A-T-O" -> "the US", "NATO" (radio's spoken initialisms)."""
    return re.sub(r"\b(?:[A-Z]-)+[A-Z]\b", lambda m: m.group(0).replace("-", ""), text)


def check_numbers(sent: str, ev: Evidence) -> str | None:
    for v in values_of(sent):
        if not ev.has_value(v):
            return f"number {v.text!r} is not in this story's text"
    return None


_TOTAL_CUE = re.compile(
    r"\b(?:totall?ing|in total|a total of|bringing the total to|for a total of|"
    r"for a combined|combined total of|altogether)\b", re.I)
_ANAPHOR = re.compile(r"^\W*(?:this|that|it|these|the move|the cut)\b", re.I)
_PCT = re.compile(r"(?:%|\bper ?cent\b)", re.I)


def _unit_values(sent: str) -> list[tuple[float, str]]:
    """(value, unit) for each number; unit is 'pct' or ''."""
    out = []
    for v in digit_values(sent) + spoken_values(sent):
        end = sent.lower().find(v.text.split()[-1]) if v.text else -1
        tail = sent[end:end + len(v.text) + 12] if end >= 0 else ""
        out.append((v.value, "pct" if _PCT.search(tail) else ""))
    return out


def check_total(sent: str, prev: str | None) -> str | None:
    """A stated total must be the sum of the parts the sentence stacks on it."""
    m = _TOTAL_CUE.search(sent)
    if not m:
        return None
    after = sent[m.end():]
    totals = _unit_values(after)
    if not totals:
        return None
    total, unit = totals[0]
    parts = [v for v, u in _unit_values(sent[:m.start()]) if u == unit]
    if prev and _ANAPHOR.match(sent):
        parts = [v for v, u in _unit_values(prev) if u == unit] + parts
    if len(parts) < 2:
        return None
    if abs(sum(parts) - total) > 1e-6 * max(1.0, abs(total)):
        return (f"states a total of {total:g} after parts that sum to "
                f"{sum(parts):g}")
    return None


_NUMBER_WORDS = {w: str(v) for w, v in list(_UNITS.items()) + list(_TENS.items())}
# A name made only of these is a title or a body ("U.S. Defense Secretary" for
# "Secretary of Defense"), not a name the writer could have invented.
_TITLE_WORDS = frozenset("""
us uk eu un usa us-led british american european russian chinese defense
defence secretary minister prime president vice deputy foreign state
department ministry office general attorney chief army navy air force
house senate congress parliament government federal national supreme court
senator senators lawmaker governor mayor ambassador spokesperson spokesman
spokeswoman official officials
""".split())
# Long and short forms of the same name.
_ALIASES = (("united kingdom", "uk"), ("united states", "us"),
            ("european union", "eu"), ("united nations", "un"))


def _name_variants(key: str) -> list[str]:
    """The name as written, with number words as digits ("Falcon Nine"), with
    a hyphenated modifier dropped ("Iran-backed Houthi"), and in its long or
    short form ("United Kingdom", "UK")."""
    key = " ".join(t for t in key.split() if t not in ("mr", "mrs", "ms", "dr"))
    out = [key]
    digits = " ".join(_NUMBER_WORDS.get(t, t) for t in key.split())
    out.append(digits)
    bare = " ".join(t for t in key.split() if not re.search(r"-[a-z]", t))
    if bare and bare != key:
        out.append(bare)
    for long, short in _ALIASES:
        for v in list(out):
            if long in v:
                out.append(v.replace(long, short))
            if re.search(rf"\b{short}\b", v):
                out.append(re.sub(rf"\b{short}\b", long, v))
    return list(dict.fromkeys(v for v in out if v))


def check_names(sent: str, ev: Evidence) -> str | None:
    for nm in G.proper_names(_collapse_spelled(sent)):
        key = _norm_names(nm)
        toks = [t for t in key.split() if t not in ("mr", "mrs", "ms", "dr")]
        if all(t in _TITLE_WORDS for t in toks):
            continue
        # A title in front of a name is the writer's ("Secretary Hegseth" for
        # "Secretary of Defense Pete Hegseth"): the name is what must be sourced.
        core = " ".join(toks[next((i for i, t in enumerate(toks)
                                   if t not in _TITLE_WORDS), 0):])
        if any(re.search(r"\b" + re.escape(v) + r"\b", ev.folded)
               for v in _name_variants(key) + _name_variants(core)):
            continue
        if len(toks) < 2:
            continue
        toks = key.split()
        # The weekly rule: the last two words as a phrase and every word on its
        # own ("United States President Donald Trump" against a record that
        # says "President Donald Trump" and "United States").
        tail = " ".join(toks[-2:])
        if tail in ev.folded and all(re.search(r"\b" + re.escape(t) + r"\b", ev.folded)
                                     for t in toks):
            continue
        return f"name {nm!r} is not in this story's text"
    return None


_WEEKDAY = re.compile(r"\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I)
_MONTHS = ("january february march april may june july august september october "
           "november december").split()
_MONTH_DAY = re.compile(r"\b(" + "|".join(_MONTHS) + r")\s+(\d{1,2})\b", re.I)
_INTERVAL = re.compile(
    r"\b(a|an|one|two|three|four|five|six|seven|eight|nine|ten|\d+|several|a few)\s+"
    r"(hours?|days?|weeks?|months?|years?)\s+(later|earlier|before|after|ago|"
    r"previously|beforehand)\b", re.I)
_NUM_WORD = {"a": "1", "an": "1", "one": "1", "two": "2", "three": "3", "four": "4",
             "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
             "ten": "10"}


def _interval_key(m: re.Match) -> str:
    n = _NUM_WORD.get(m.group(1).lower(), m.group(1).lower())
    unit = m.group(2).lower().rstrip("s")
    return f"{n} {unit} {m.group(3).lower()}"


def _weekdays_of_dates(text: str) -> set[str]:
    """Weekdays of the month-day dates a text states, in the year it names
    (or the current year), so "on Thursday" is read as "on October 1"."""
    import datetime as _dt
    years = [int(y) for y in re.findall(r"\b(20\d\d)\b", text or "")]
    year = max(years) if years else _dt.datetime.now(_dt.timezone.utc).year
    out = set()
    for m in _MONTH_DAY.finditer(text or ""):
        try:
            d = _dt.date(year, _MONTHS.index(m.group(1).lower()) + 1, int(m.group(2)))
        except ValueError:
            continue
        out.add(d.strftime("%A").lower())
    return out


def check_dates(sent: str, ev: Evidence) -> str | None:
    low = ev.text.lower()
    implied = None
    for m in _WEEKDAY.finditer(sent):
        if m.group(1).lower() in low:
            continue
        if implied is None:
            implied = _weekdays_of_dates(ev.text)
        if m.group(1).lower() not in implied:
            return f"weekday {m.group(1)!r} is not in this story's text"
    for m in _MONTH_DAY.finditer(sent):
        month, day = m.group(1).lower(), m.group(2)
        if not re.search(rf"\b{month}\s+{day}\b|\b{day}\s+{month}\b", low):
            return f"date {m.group(0)!r} is not in this story's text"
    have = {_interval_key(m) for m in _INTERVAL.finditer(ev.text)}
    for m in _INTERVAL.finditer(sent):
        if _interval_key(m) not in have:
            return f"interval {m.group(0)!r} is not in this story's text"
    return None


def check_quotes(sent: str, ev: Evidence) -> str | None:
    found = std.e14_quotes_are_verbatim("", sent, ev.index)
    return f"quotation not verbatim in this story's text ({found[0].message[:80]})" \
        if found else None


_SPEECH = re.compile(
    r"\b(?:said|says|told|warned|vowed|declared|stated|added|insisted|"
    r"claimed|argued|announced|promised|threatened)\b", re.I)


def check_lifted_quote(sent: str, ev: Evidence) -> str | None:
    """Reported speech that lifts a quotation must not end somewhere it never went.

    When a sentence reporting speech shares a run of three or more consecutive
    words with a quotation in the story's text, every content word after that
    run must be in the quotation's own sentence. "Those who clung to the woke
    department would be purged" lifts "clung to the woke department" from a
    quotation that ends "no longer work here", and "purged" is not in it.
    """
    if not _SPEECH.search(sent) or not ev.quotes:
        return None
    words = _fold_words(sent)
    for q in ev.quotes:
        if len(q) < 3:
            continue
        qset = {" ".join(q[i:i + 3]) for i in range(len(q) - 2)}
        run_end, run = None, ""
        for i in range(len(words) - 2):
            if " ".join(words[i:i + 3]) in qset:
                run_end, run = i + 3, " ".join(words[i:i + 3])
        if run_end is None:
            continue
        rest = " ".join(words[run_end:])
        # Every sentence of the story that carries the lifted words is a
        # legitimate home for what follows them.
        homes = [s for s in ev.sentences
                 if run in " ".join(_fold_words(s))] or [" ".join(q)]
        allowed: set[str] = set()
        for home in homes:
            allowed |= std.title_word_stems(home)
        stray = sorted(std.title_word_stems(rest) - allowed)
        if stray:
            return (f"reported speech lifts a quotation and ends on words it "
                    f"never said ({', '.join(stray[:3])})")
    return None


def check_hedge(sent: str) -> str | None:
    found = std.e15_hedge_is_not_attribution(sent)
    return "a hedge stands in for attribution (E-15)" if found else None


def sentence_problem(sent: str, ev: Evidence, prev: str | None = None) -> str | None:
    """The first reason this sentence cannot ship against this story, or None."""
    for fn in (check_numbers, check_names, check_dates, check_quotes,
               check_lifted_quote):
        why = fn(sent, ev)
        if why:
            return why
    return check_total(sent, prev) or check_hedge(sent)


# ---------------------------------------------------------------------------
# Paragraphs and products
# ---------------------------------------------------------------------------
def _open_quote(text: str) -> bool:
    return (text.count("\u201c") > text.count("\u201d")) or text.count('"') % 2 == 1


def _sentences(text: str) -> list[str]:
    """Sentences, never split inside an open quotation: a quotation that spans a
    full stop is one claim and is judged whole."""
    out: list[str] = []
    for piece in G.sentences_of(text):
        if out and _open_quote(out[-1]):
            out[-1] = f"{out[-1]} {piece}"
        else:
            out.append(piece)
    return out


def ground_text(text: str, cluster: dict[str, Any] | str | Evidence, *,
                product: str = "text",
                formulas: Iterable[str] = ()) -> tuple[str, list[Cut]]:
    """`text` with every sentence that fails against ONE story cut.

    Paragraph breaks are kept; a paragraph emptied by the cut is dropped.
    A sentence that opens with one of `formulas` (the programme's own fixed
    lines, "One more before Void Opinion.") is the house speaking, not the
    story, and is kept.
    """
    formulas = tuple(f for f in formulas if f)
    if not text:
        return text, []
    ev = cluster if isinstance(cluster, Evidence) else Evidence(cluster)
    cuts: list[Cut] = []
    paras = []
    for para in re.split(r"\n\s*\n", text):
        kept: list[str] = []
        prev = None
        for line in para.split("\n"):
            for sent in _sentences(line):
                if formulas and sent.startswith(formulas):
                    kept.append(sent)
                    prev = sent
                    continue
                why = sentence_problem(sent, ev, prev)
                if why:
                    cuts.append(Cut(product, sent, why))
                else:
                    kept.append(sent)
                prev = sent
        if kept:
            paras.append(" ".join(kept))
    return "\n\n".join(paras), cuts


# --- one story per paragraph ------------------------------------------------
_CAP_TOKEN = re.compile(r"\b[A-Z][A-Za-z'’&-]+")
_GENERIC_CAPS = frozenset("""
the a an in on at it he she they this that these those but and for with as
mr mrs ms dr president prime minister secretary general chief officials
official government department court police state states national federal
monday tuesday wednesday thursday friday saturday sunday january february
march april may june july august september october november december
""".split())


def _entities(text: str) -> set[str]:
    """Capitalised words that are not a sentence's first word, folded."""
    out: set[str] = set()
    for line in (text or "").split("\n"):
        for sent in G.sentences_of(line):
            for i, m in enumerate(_CAP_TOKEN.finditer(_collapse_spelled(sent))):
                if m.start() == 0 or (i == 0 and not sent[:m.start()].strip(" \"'“")):
                    continue
                w = re.sub(r"['’]s$", "", m.group(0)).lower()
                if len(w) >= 3 and w not in _GENERIC_CAPS:
                    out.add(w)
            out.update(G.proper_names(sent))
    return out


def map_sentence(sent: str, evs: list[Evidence]) -> list[int]:
    """Clusters whose DISTINCT entities this sentence names, best first."""
    ents = _entities(sent)
    if not ents:
        return []
    scores = []
    for i, ev in enumerate(evs):
        others: set[str] = set()
        for j, o in enumerate(evs):
            if j != i:
                others |= o.entities
        distinct = (ev.entities - others) & ents
        if distinct:
            scores.append((len(distinct), i))
    return [i for _, i in sorted(scores, key=lambda x: (-x[0], x[1]))]


def ground_brief(text: str, clusters: list[dict[str, Any]],
                 product: str = "tldr") -> tuple[str, list[Cut]]:
    """The TL;DR: each paragraph mapped to its story, one story per paragraph,
    each paragraph grounded against that story alone."""
    if not text or not clusters:
        return text, []
    evs = [Evidence(c) for c in clusters]
    union = Evidence("\n".join(e.text for e in evs))
    paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    sents_by_para = [[s for line in p.split("\n") for s in _sentences(line)]
                     for p in paras]
    # The paragraph's story: the cluster its sentences name most distinctly.
    owner: list[int | None] = []
    for sents in sents_by_para:
        votes: dict[int, int] = {}
        for k, s in enumerate(sents):
            ranked = map_sentence(s, evs)
            if ranked:
                votes[ranked[0]] = votes.get(ranked[0], 0) + (3 if k == 0 else 1)
        owner.append(max(votes, key=lambda i: (votes[i], -i)) if votes else None)
    owned = {o for o in owner if o is not None}

    cuts: list[Cut] = []
    out_paras: list[str] = []
    for sents, own in zip(sents_by_para, owner):
        keep: list[str] = []
        moved: dict[int, list[str]] = {}
        for s in sents:
            ranked = map_sentence(s, evs)
            if own is not None and ranked and own not in ranked:
                other = ranked[0]
                if other in owned:
                    cuts.append(Cut(product, s, "names another story that has its "
                                                "own paragraph (one story per paragraph)"))
                else:
                    moved.setdefault(other, []).append(s)
                continue
            keep.append(s)
        for para_sents, idx in [(keep, own)] + [(v, k) for k, v in moved.items()]:
            if not para_sents:
                continue
            ev = evs[idx] if idx is not None else union
            kept, more = ground_text(" ".join(para_sents), ev, product=product)
            cuts.extend(more)
            if kept:
                out_paras.append(kept)
            if idx is not None:
                owned.add(idx)
    return "\n\n".join(out_paras), cuts


def log_cuts(cuts: Iterable[Cut], prefix: str = "  [grounding]") -> None:
    for c in cuts:
        print(f"{prefix} {c}")


# ---------------------------------------------------------------------------
# The card itself, at write time (Stage 2, 8d.3)
# ---------------------------------------------------------------------------
_REPAIRABLE = ("E-13", "E-14", "E-16")


def repair_card(summary: str, sources=None, *, title: str = "",
                removed_text: str | None = None,
                kept_text: str | None = None) -> tuple[str, list[Cut]]:
    """A card summary with every sentence E-13, E-14 or E-16 fails CUT.

    A sentence goes when it opens by changing the subject ("Separately,"),
    with the sentences after it until one names something the card named
    before the shift. With `sources` (the text the card was WRITTEN from, or a
    grounding index), a sentence also goes when it states a number no source
    carries or one the sources attach to another name, or quotes words no
    source says (or punctuates). Pass `sources` only when it is complete: a
    card cached from an earlier run was written from bodies step 10 has since
    cut, and an absence there means "cannot confirm", never "invented". With
    `removed_text` (the members a coherence pass removed) and `kept_text`, a
    sentence whose names appear in the removed members and in none of the
    kept ones goes too: the Kanye West paragraph on the Putin card. That is
    positive evidence of where the sentence came from, so it holds however
    much of the kept bodies survives.

    Deterministic, so a failing card costs no model call: regeneration is the
    fallback for what a cut cannot fix (a headline), never the first resort.
    """
    if not summary:
        return summary, []
    ev = std._evidence(sources) if sources else None
    decimals = getattr(ev, "decimals", True)
    removed = _norm_names(removed_text) if removed_text else None
    kept_folded = _norm_names(kept_text) if kept_text else ""
    seen: list[str] = list(G.proper_names(title or ""))
    before = _entities(title or "")
    shifted = False
    kept: list[str] = []
    cuts: list[Cut] = []
    for sent in _sentences(summary):
        names = list(G.proper_names(sent))
        for m in std._DEFINITE.finditer(sent):
            for nm in reversed(seen):
                if nm.split(" ")[0] == m.group(1) and nm not in names:
                    names.append(nm)
                    break
        why = None
        if std.TOPIC_SHIFT_RE.match(sent):
            why, shifted = "E-16 opens on another story", True
        elif shifted:
            if _entities(sent) & before:
                shifted = False
            else:
                why = "E-16 continues the other story"
        if not why and ev is not None:
            for n in sorted(std._numbers(sent)):
                if not ev.has_number(n):
                    if "." in n and not decimals:
                        continue
                    why = f"E-13 {n} is in no source"
                    break
                rival = std._misattached(ev, n, names)
                if rival:
                    why = f"E-13 {n} is attached to {rival!r} in no source"
                    break
        if not why and ev is not None:
            found = std.e14_quotes_are_verbatim("", sent, ev)
            if found:
                why = "E-14 " + found[0].message[:80]
        if not why and removed:
            multi = [" ".join(_norm_names(n).split()[-2:]) for n in G.proper_names(sent)
                     if not all(t in _TITLE_WORDS for t in n.split())]
            # A name counts on its last two words ("NATO Secretary General
            # Mark Rutte" for "Mark Rutte").
            if multi and any(m in removed for m in multi) \
                    and not any(m in kept_folded for m in multi):
                why = "names only members the coherence pass removed"
        if why:
            cuts.append(Cut("card", sent, why))
        else:
            kept.append(sent)
            if not shifted:
                before |= _entities(sent)
        seen.extend(G.proper_names(sent))
    return " ".join(kept), cuts
