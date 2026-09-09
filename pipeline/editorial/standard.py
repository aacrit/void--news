"""The editorial standard: one implementation, two consumers.

Every rule in docs/EDITORIAL-STANDARD.md lives here as a pure function with a
stable ID. The PIPELINE calls it before a summary is stored, and the
SERVED-OUTPUT GATE (scripts/verify_production.py) calls the same functions
against the HTML production actually serves. Before this module the two sides
had drifted: the gate's orphan-clause regex used a lookbehind and the
pipeline's was anchored, the gate vendored a copy of the clusterer's title
stemmer with a hand-sync note, and the pipeline REPAIRED silently where the
gate FAILED loudly, so nothing counted how often a repair fired.

CONSTRAINTS, all load-bearing:

  * stdlib only. .github/workflows/verify-production.yml installs nothing but
    nltk, so this module must not import cluster_summarizer (which pulls the
    Gemini client) or story_cluster (spaCy). nltk is used when present and
    falls back to a suffix stripper when it is not.
  * importable both ways. main.py puts pipeline/ on sys.path and imports
    `editorial.standard`; the gate and the tests put the repo root on sys.path
    and import `pipeline.editorial.standard`.
  * pure. No I/O, no network, no DB, no model. Same text in, same findings out.

Statuses: ENFORCED rules fail the build. ADVISORY rules are implemented and
reported but do not fail, pending CEO review of the standard; --strict promotes
them. L-* rules need the model and are declared here, not implemented.
"""
from __future__ import annotations

import re
from typing import Callable, Iterable, NamedTuple

# ---------------------------------------------------------------------------
# Finding
# ---------------------------------------------------------------------------


class Finding(NamedTuple):
    id: str
    message: str

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"{self.id} {self.message}"


ENFORCED = "enforced"
ADVISORY = "advisory"


# ---------------------------------------------------------------------------
# Title stemming. Moved here from scripts/verify_production.py, which carried a
# vendored copy plus a comment asking the next person to keep it in sync with
# clustering/story_cluster.py by hand.
# ---------------------------------------------------------------------------
TITLE_STOPWORDS = frozenset({
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "are", "was", "were", "be", "been",
    "has", "have", "had", "its", "it", "as", "after", "over", "up", "that",
    "this", "not", "no", "says", "said", "new", "amid", "more", "than",
    "about", "how", "what", "why", "who", "when", "where", "which",
    "will", "would", "could", "should", "may", "might", "can",
    "reports", "report", "sources", "according", "also", "first",
    "two", "one", "three", "us", "announces", "while",
})

try:  # Porter when available (CI installs nltk); a stripper otherwise.
    from nltk.stem import PorterStemmer as _PorterStemmer

    _STEMMER = _PorterStemmer()

    def _stem(word: str) -> str:
        try:
            return _STEMMER.stem(word)
        except Exception:
            return word
except Exception:  # pragma: no cover - nltk missing

    def _stem(word: str) -> str:
        for suf in ("ations", "ation", "ing", "ies", "edly", "ed", "es", "s"):
            if len(word) > len(suf) + 2 and word.endswith(suf):
                return word[: -len(suf)]
        return word


# A possessive is the same word. The token regex keeps the apostrophe inside
# the word, so "Germany's" stems to "germany'" and never matches "German" or
# "Germany"; "Iran's" never matches "Iran". Strip it before stemming.
#
# This is the same defect the daily brief's continuing-story matcher had in
# rev 57 ("iran's"/"leader's" never matched "iran"/"leader", so every brief
# reported 0 continuing stories). It was fixed there and reintroduced here,
# which is the argument for one tokenizer rather than three.
_POSSESSIVE = re.compile(r"['\u2019]s?$")


def title_word_stems(title: str) -> set[str]:
    """Content-word stems of a headline (stopwords removed, Porter-stemmed)."""
    out: set[str] = set()
    for w in re.findall(r"[a-z0-9](?:[a-z0-9'\u2019-]*[a-z0-9])?",
                        (title or "").lower().replace("\u2019", "'")):
        w = _POSSESSIVE.sub("", w)
        if w in TITLE_STOPWORDS or len(w) < 2:
            continue
        out.add(_stem(w))
    return out


# ---------------------------------------------------------------------------
# Shared text helpers
# ---------------------------------------------------------------------------
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“‘'])")
_QUOTED_SPAN = re.compile(r'["“][^"”“]*["”]|[‘][^’]*[’]')


def sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split((text or "").strip()) if s.strip()]


def outside_quote_spans(text: str) -> list[str]:
    """The parts of `text` that sit OUTSIDE any quotation.

    Tracks straight and curly double quotes and curly single quotes. Straight
    apostrophes are deliberately not treated as quotation marks: "Zambia's"
    would open a span that never closes.
    """
    out: list[str] = []
    last = 0
    for m in _QUOTED_SPAN.finditer(text or ""):
        out.append(text[last:m.start()])
        last = m.end()
    out.append((text or "")[last:])
    return out


def _ctx(text: str, needle: str, width: int = 55) -> str:
    i = text.find(needle)
    if i < 0:
        return text[:width]
    return "..." + text[max(0, i - width // 2): i + len(needle) + width // 2] + "..."


# ---------------------------------------------------------------------------
# S: structural
# ---------------------------------------------------------------------------
MIN_SUMMARY_CHARS = 300
STORY_HREF_RE = re.compile(
    r"^(?:/void--news)?/story/"
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/$"
)
_TERMINAL = ('.', '!', '?', '”', '"', '’', "'", ')')
_DOUBLED_WORD = re.compile(r"\b([A-Z][a-z]+)\1\b")
_ABBREV_SPACING = re.compile(r"\bU\. S\.|\bU\. K\.|\bU\. N\.|\bE\. U\.|\d\. \d|\. [”’]")


def s01_href_shape(href: str) -> list[Finding]:
    if not href:
        return [Finding("S-01", "card has no story link")]
    if not STORY_HREF_RE.match(href):
        return [Finding("S-01", f'link is not /story/<uuid>/: "{href}"')]
    return []


def s02_summary_length(summary: str) -> list[Finding]:
    n = len(summary or "")
    if 0 < n < MIN_SUMMARY_CHARS:
        return [Finding("S-02", f'summary is {n} chars (min {MIN_SUMMARY_CHARS}): "{summary[:90]}"')]
    return []


def s03_terminal_punctuation(summary: str) -> list[Finding]:
    s = (summary or "").strip()
    if s and not s.endswith(_TERMINAL):
        return [Finding("S-03", f'summary does not end in terminal punctuation: "...{s[-60:]}"')]
    return []


def s04_quote_balance(summary: str) -> list[Finding]:
    text = summary or ""
    straight = text.count('"')
    if straight % 2:
        return [Finding("S-04", f'unbalanced straight quote ({straight} marks): "{text[:90]}"')]
    if text.count("“") != text.count("”"):
        return [Finding("S-04",
                        f'unbalanced curly quotes ({text.count(chr(0x201c))} open, '
                        f'{text.count(chr(0x201d))} close): "{text[:90]}"')]
    return []


def s05_doubled_words(text: str) -> list[Finding]:
    return [Finding("S-05", f'doubled word "{m.group(0)}": "{_ctx(text, m.group(0))}"')
            for m in _DOUBLED_WORD.finditer(text or "")]


def s06_abbrev_spacing(text: str) -> list[Finding]:
    return [Finding("S-06", f'broken spacing "{m.group(0)}": "{_ctx(text, m.group(0))}"')
            for m in _ABBREV_SPACING.finditer(text or "")]


# ---------------------------------------------------------------------------
# E: editorial
# ---------------------------------------------------------------------------
_FIRST_PERSON = [
    re.compile(r"\b(?:we|our|ours|ourselves|my|mine|myself)\b", re.I),
    re.compile(r"\bus\b"),                       # lowercase only: "US" is a country
    re.compile(r"\b(?:we|I)'(?:m|re|ve|ll|d)\b", re.I),
]
_SECOND_PERSON = re.compile(r"\b(?:your|yours|yourself|yourselves)\b", re.I)
# Scanned over the RAW text, not per sentence: `sentences()` splits only before
# a capital letter, so a lowercase orphan clause stays glued to the sentence
# before it and a per-sentence anchored match can never see it. That is exactly
# the defect shape (the tail of a sentence whose head was dropped), so the
# lookbehind is the rule, matching the gate's original semantics.
_SUBORDINATING = re.compile(
    r"(?<=[.!?]\s)(?:when|where|which|while|although|though|because|since|"
    r"unless|whereas|wherein|whereby|if|after|before|as)\b"
)
_SUBORDINATING_START = re.compile(
    r"^(?:when|where|which|while|although|though|because|since|"
    r"unless|whereas|wherein|whereby|if|after|before|as)\b"
)


def e03_first_person_outside_quotes(summary: str) -> list[Finding]:
    out: list[Finding] = []
    for gap in outside_quote_spans(summary or ""):
        for rx in _FIRST_PERSON:
            m = rx.search(gap)
            if m:
                out.append(Finding(
                    "E-03",
                    f'first-person "{m.group(0)}" outside quotes: "{_ctx(gap, m.group(0))}"'))
                break
    return out


def e04_orphan_subordinate(summary: str) -> list[Finding]:
    text = summary or ""
    out = [Finding("E-04",
                   f'clause opens on "{m.group(0)}" after a full stop: '
                   f'"{_ctx(text, m.group(0))}"')
           for m in _SUBORDINATING.finditer(text)]
    m0 = _SUBORDINATING_START.match(text.strip())
    if m0:
        out.append(Finding("E-04",
                           f'summary opens on "{m0.group(0)}": "{text[:80]}"'))
    return out


def e11_second_person_outside_quotes(summary: str) -> list[Finding]:
    out: list[Finding] = []
    for gap in outside_quote_spans(summary or ""):
        m = _SECOND_PERSON.search(gap)
        if m:
            out.append(Finding(
                "E-11",
                f'second-person "{m.group(0)}" outside quotes: "{_ctx(gap, m.group(0))}"'))
    return out


# --- E-05: reputational claims -------------------------------------------
_REPUTATIONAL = re.compile(
    r"\b(?:is|was|are|were)\s+(?:a\s+|an\s+|the\s+)?(?:convicted\s+|alleged\s+|suspected\s+)?"
    r"(terrorist|rapist|p(?:a?e)dophile|murderer|fraudster|abuser|molester|criminal|extremist)\b",
    re.I,
)
_CRIMINAL_ALLEGATION = re.compile(
    r"\b(accused of|charged with|indicted (?:for|on)|convicted of|found guilty of|"
    r"pleaded guilty|pled guilty|arrested for|perpetrat(?:ed|or))\b", re.I,
)
_ATTRIBUTION_CUE = re.compile(
    r"\b(accord(?:ing)? to|reported by|as reported|reportedly|said|says|stated|stating|"
    r"told\s+[A-Z]|per\s+[A-Z]|alleged by|prosecutors|indictment|police said|"
    r"court (?:documents|filings|records)|lawsuit|complaint|wrote|posted|announced)\b", re.I,
)
_QUOTE_PRESENT = re.compile(r'["“][^"”]{3,}["”]')


def e05_reputational_attribution(summary: str) -> list[Finding]:
    out: list[Finding] = []
    for sent in sentences(summary or ""):
        if not (_REPUTATIONAL.search(sent) or _CRIMINAL_ALLEGATION.search(sent)):
            continue
        if _ATTRIBUTION_CUE.search(sent) or _QUOTE_PRESENT.search(sent):
            continue
        out.append(Finding("E-05",
                           f'reputational or criminal claim with no attribution: "{sent[:110]}"'))
    return out


# --- E-07: contested terminology -----------------------------------------
# Symmetric by design: it neutralises loaded phrasing from either direction,
# the same principle as the clusterer's contested-headline lexicon. Each entry
# is (pattern, neutral construction). Word boundaries throughout: "regime"
# must not match "Foot Regiment", and the migrant sense of "invasion" is
# distinguished from the military one by the words around it.
CONTESTED_TERMS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bterror regime\b", re.I), "government"),
    (re.compile(r"\bIslamic terror\b", re.I), "the attacks, named plainly"),
    (re.compile(r"\bterrorists?\b", re.I), "fighters, militants, or the charge as filed"),
    (re.compile(r"\billegal aliens?\b|\billegals\b", re.I), "undocumented migrants"),
    (re.compile(r"\bopen borders\b", re.I), "the border policy, described"),
    (re.compile(r"\bpro-abortion\b", re.I), "abortion-rights"),
    (re.compile(r"\bpro-life\b", re.I), "anti-abortion"),
    (re.compile(r"\bforced birth\b", re.I), "the abortion restriction, described"),
    (re.compile(r"\bgender ideology\b", re.I), "the policy, named"),
    (re.compile(r"\btrans genocide\b", re.I), "the legislation, described"),
    (re.compile(r"\bthugs?\b", re.I), "the people, described"),
    (re.compile(r"\bfreedom fighters?\b", re.I), "fighters"),
    (re.compile(r"\binvasion\b(?=[^.]{0,60}\b(?:migrant|immigrant|border|caravan)s?\b)", re.I),
     "the arrivals, counted"),
    (re.compile(r"\b(?:migrant|immigrant)s?\b(?=[^.]{0,60}\binvasion\b)", re.I),
     "the arrivals, counted"),
]
_NAMED_SPEAKER = re.compile(
    r"\b(?:said|says|stated|told|called|posted|wrote|argued|claimed|described|"
    r"accord(?:ing)? to|denounced|condemned|labell?ed|referred to|reported)\b", re.I,
)


def e07_contested_terminology(summary: str) -> list[Finding]:
    """Flag a contested term in Void's own voice: outside quotation marks AND
    with no attribution cue anywhere in its sentence."""
    out: list[Finding] = []
    for sent in sentences(summary or ""):
        if _NAMED_SPEAKER.search(sent):
            continue
        unquoted = " ".join(outside_quote_spans(sent))
        for rx, neutral in CONTESTED_TERMS:
            m = rx.search(unquoted)
            if m:
                out.append(Finding(
                    "E-07",
                    f'"{m.group(0)}" in Void\'s voice, unquoted and unattributed '
                    f'(neutral: {neutral}): "{sent[:90]}"'))
                break
    return out


# --- E-08: unattributed passive evaluation --------------------------------
_PASSIVE_EVAL = re.compile(
    r"\b(?:is|are|was|were)\s+(?:described|seen|viewed|regarded|considered|"
    r"characteri[sz]ed|portrayed|painted)\s+as\b", re.I,
)


def e08_passive_evaluation(summary: str) -> list[Finding]:
    out: list[Finding] = []
    for sent in sentences(summary or ""):
        m = _PASSIVE_EVAL.search(" ".join(outside_quote_spans(sent)))
        if m and not re.search(r"\bby\s+[A-Z]", sent):
            out.append(Finding("E-08",
                               f'"{m.group(0)}" with no one doing the describing: "{sent[:90]}"'))
    return out


# --- E-09: absence of information -----------------------------------------
# The strict phrase list misses the real shape entirely: the 09-06 Bolivia card
# scored 0 of 8 on it while saying "have not been immediately released",
# "remains under investigation", "still being evaluated" and "based on initial
# reports". This vocabulary is the summarizer's own _UNKNOWN_PADDING_RE set.
ABSENCE_RE = re.compile(
    r"\b(?:"
    r"ha(?:s|ve) not been (?:immediately )?(?:released|disclosed|confirmed|identified|determined)"
    r"|not yet (?:been )?(?:released|known|confirmed|clear|determined|identified)"
    r"|remains? (?:under investigation|unclear|unknown)"
    r"|investigations? (?:is|are|remain|remains|continue|continues) (?:ongoing|underway)"
    r"|investigations? are ongoing"
    r"|still being (?:evaluated|assessed|determined|investigated)"
    r"|(?:is|are) based on initial reports"
    r"|no (?:further )?(?:details|information|comment|word|explanation)"
    r"|did not (?:say|specify|disclose|provide|respond)"
    r"|could not be (?:confirmed|verified|reached|determined)"
    r"|not immediately (?:available|clear|known)"
    r"|the (?:exact )?cause .{0,30}(?:remains|is) (?:under investigation|unclear|unknown)"
    r"|yet to be (?:determined|released|confirmed)"
    r"|unclear|unknown"
    r")\b", re.I,
)
ABSENCE_MAX_SENTENCES = 3
ABSENCE_MAX_RATIO = 0.25
ABSENCE_MIN_SENTENCES_FOR_RATIO = 6


def e09_absence_of_information(summary: str) -> list[Finding]:
    sents = sentences(summary or "")
    if not sents:
        return []
    hits = [s for s in sents if ABSENCE_RE.search(s)]
    n, total = len(hits), len(sents)
    ratio = n / total
    if n >= ABSENCE_MAX_SENTENCES or (
        total >= ABSENCE_MIN_SENTENCES_FOR_RATIO and ratio >= ABSENCE_MAX_RATIO
    ):
        return [Finding(
            "E-09",
            f"{n} of {total} sentences assert absence of information "
            f"({ratio:.0%}): \"{hits[0][:80]}\"")]
    return []


# E-10 (a location named in the headline appears in the summary) is NOT
# implemented here. A regex cannot tell a place from any other capitalised
# opener: the first draft flagged "Mudslides Kill Dozens..." as a headline
# whose location the summary omitted. Distinguishing a place from a plural
# noun needs either a gazetteer this module may not carry (stdlib only) or the
# model, so the rule lives in the critique pass as L-07 instead. Shipping a
# low-precision check would train the operator to ignore findings, which is
# how the tracking issue accumulated 26 unread comments.


# ---------------------------------------------------------------------------
# F: feed level
# ---------------------------------------------------------------------------
DUP_STEM_OVERLAP = 4


def f02_duplicate_headlines(titles: Iterable[str]) -> list[Finding]:
    titles = list(titles)
    stems = [title_word_stems(t) for t in titles]
    out: list[Finding] = []
    for i in range(len(titles)):
        for j in range(i + 1, len(titles)):
            shared = stems[i] & stems[j]
            if len(shared) >= DUP_STEM_OVERLAP:
                out.append(Finding(
                    "F-02",
                    f"duplicate story ({len(shared)} shared stems "
                    f"{sorted(shared)}): \"{titles[i][:60]}\" / \"{titles[j][:60]}\""))
    return out


def f04_count_match(header_count: int | None, rendered: int,
                    expected: int | None = None) -> list[Finding]:
    out: list[Finding] = []
    if header_count is None:
        out.append(Finding("F-04", 'no "N stories loaded" header count found'))
    elif header_count != rendered:
        out.append(Finding("F-04",
                           f"header says {header_count} stories but {rendered} cards rendered"))
    if expected is not None and rendered != expected:
        out.append(Finding("F-04",
                           f"{rendered} cards rendered but the configured feed size is {expected}"))
    return out


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
class Validator(NamedTuple):
    id: str
    name: str
    status: str
    fn: Callable
    scope: str  # "summary", "text", "title+summary", "href", "feed"


VALIDATORS: list[Validator] = [
    Validator("S-01", "card links to /story/<uuid>/", ENFORCED, s01_href_shape, "href"),
    Validator("S-02", "summary min length", ENFORCED, s02_summary_length, "summary"),
    Validator("S-03", "summary ends in terminal punctuation", ENFORCED, s03_terminal_punctuation, "summary"),
    Validator("S-04", "quotes are balanced", ENFORCED, s04_quote_balance, "summary"),
    Validator("S-05", "no doubled word", ENFORCED, s05_doubled_words, "text"),
    Validator("S-06", "no broken abbreviation or decimal spacing", ENFORCED, s06_abbrev_spacing, "text"),
    Validator("E-03", "no first-person pronoun outside quotes", ENFORCED, e03_first_person_outside_quotes, "summary"),
    Validator("E-04", "no orphan subordinate clause", ENFORCED, e04_orphan_subordinate, "summary"),
    Validator("E-05", "reputational claims carry attribution", ENFORCED, e05_reputational_attribution, "summary"),
    Validator("E-07", "no contested terminology in Void's voice", ADVISORY, e07_contested_terminology, "summary"),
    Validator("E-08", "no unattributed passive evaluation", ADVISORY, e08_passive_evaluation, "summary"),
    Validator("E-09", "not mostly absence of information", ADVISORY, e09_absence_of_information, "summary"),
    Validator("E-11", "no second-person pronoun outside quotes", ADVISORY, e11_second_person_outside_quotes, "summary"),
]

VALIDATORS_BY_ID = {v.id: v for v in VALIDATORS}

# Declared, implemented in the Block 2 critique pass (see the standard doc).
LLM_RULES = {
    "L-01": "the first sentence states the event, not a reaction",
    "L-02": "every quotation is verbatim, pronouns included",
    "L-03": "the card describes one event",
    "L-04": "the card is news, not opinion, satire or commerce",
    "L-05": "no internal contradiction; ages, titles and numbers are sourced",
    "L-06": "criticism of a named living person carries their response",
    "L-07": "a location named in the headline is not contradicted by the summary",
}


def validate_candidate(candidate: dict, include_advisory: bool = True) -> list[Finding]:
    """Every per-card rule, against one candidate.

    Keys read: title, summary, href (optional). A missing key is skipped, so
    the pipeline can call this before a permalink exists.
    """
    title = candidate.get("title") or ""
    summary = candidate.get("summary") or ""
    href = candidate.get("href")
    out: list[Finding] = []
    for v in VALIDATORS:
        if v.status == ADVISORY and not include_advisory:
            continue
        if v.scope == "href":
            if href is not None:
                out.extend(v.fn(href))
        elif v.scope == "summary":
            out.extend(v.fn(summary))
        elif v.scope == "title+summary":
            out.extend(v.fn(title, summary))
        elif v.scope == "text":
            out.extend(v.fn(f"{title} {summary}"))
    return out


def validate_feed(cards: list[dict], expected_count: int | None = None,
                  header_count: int | None = None) -> list[Finding]:
    """Feed-level rules, against the whole displayed set."""
    out: list[Finding] = []
    out.extend(f02_duplicate_headlines(c.get("title") or "" for c in cards))
    if header_count is not None or expected_count is not None:
        out.extend(f04_count_match(header_count, len(cards), expected_count))
    return out


def summarize(findings: Iterable[Finding]) -> dict[str, int]:
    """Failures per ID, for pipeline_runs.llm_metrics["editorial"]["by_id"]."""
    counts: dict[str, int] = {}
    for f in findings:
        counts[f.id] = counts.get(f.id, 0) + 1
    return counts
