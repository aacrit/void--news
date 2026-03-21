"""
Opinion vs. reporting classifier for the void --news bias engine.

Scores each article on a 0-100 opinion-fact spectrum:
    0   = purely factual reporting
    100 = purely opinion/editorial

Uses rule-based NLP heuristics (no LLM API calls):
    - First-person pronoun usage
    - TextBlob subjectivity per sentence
    - Modal verbs and imperatives
    - Hedging language
    - Attribution density
    - Section/tag/URL metadata
    - Rhetorical questions
    - Value judgments without attribution
"""

import re

from textblob import TextBlob

# ---------------------------------------------------------------------------
# First-person pronouns (signal opinion / personal perspective)
# ---------------------------------------------------------------------------
FIRST_PERSON_PRONOUNS = {
    "i", "me", "my", "mine", "myself",
    "we", "us", "our", "ours", "ourselves",
}

# ---------------------------------------------------------------------------
# Modal verbs and prescriptive language (signal opinion)
# ---------------------------------------------------------------------------
MODAL_PRESCRIPTIVE: list[str] = [
    "should", "must", "need to", "ought to", "have to",
    "has to", "needs to", "it is time to", "it's time to",
    "we must", "we should", "we need to", "we ought to",
    "it is essential that", "it is imperative that",
    "it is crucial that", "it is vital that",
    "the time has come", "enough is enough",
    "cannot afford to", "can't afford to",
    "it is wrong to", "it is right to",
]

# ---------------------------------------------------------------------------
# Hedging language (signals subjective interpretation)
# ---------------------------------------------------------------------------
HEDGING_PHRASES: list[str] = [
    "arguably", "perhaps", "it seems", "one might say",
    "one could argue", "it could be said", "it appears that",
    "in my view", "in my opinion", "i believe", "i think",
    "i would argue", "i contend", "from my perspective",
    "some would say", "it is tempting to", "it is fair to say",
    "to be fair", "to be sure", "admittedly", "granted",
    "on balance", "all things considered",
    "the question is", "the real question is",
    # Ironic / sarcastic hedging markers — these signal interpretive voice even
    # without explicit "I" statements. "surely" in journalistic prose is almost
    # always ironic or editorializing; "any day now" marks sarcastic skepticism.
    # "needless to say" and "of course" are rhetorical devices that presuppose
    # a shared editorial stance. (bias-auditor final cycle fix)
    "surely", "any day now", "needless to say", "of course",
    "because nothing says", "just as they have",
]

# ---------------------------------------------------------------------------
# Attribution phrases (signal factual reporting)
# ---------------------------------------------------------------------------
ATTRIBUTION_PHRASES: list[str] = [
    "according to", "said", "told", "stated",
    "reported", "confirmed", "announced", "declined to comment",
    "in a statement", "the spokesperson said", "the official said",
    "the department said", "a source said", "sources say",
    "the company said", "the agency said", "officials said",
    "the report found", "the study found", "researchers found",
    "data shows", "statistics show", "figures show",
    "the document states", "the filing shows", "court records show",
    "testified", "wrote in", "published in",
]

# ---------------------------------------------------------------------------
# Absolutist / certainty assertions (opinion signal for state media and
# declarative editorial pieces that avoid first-person pronouns)
#
# State media (CGTN, RT, Sputnik, Global Times) and ideological op-eds
# frequently use absolutist declarations that signal opinion without "I":
#   "historical inevitability", "no force can prevent", "firmly opposes"
# These are unhedged categorical claims that function as editorial positions.
# Each hit contributes to an absolutist density score; added at 10% weight.
# ---------------------------------------------------------------------------
ABSOLUTIST_PHRASES: list[str] = [
    # Certainty / inevitability
    "historical inevitability", "is inevitable", "is an undeniable fact",
    "there is no doubt", "it is clear that", "without question",
    "is beyond question", "is undeniable", "is irrefutable",
    "is an indisputable fact", "is a proven fact",
    # Categorical prohibition
    "no force can", "no separatist force", "nothing will change",
    "will never allow", "can never be", "cannot be tolerated",
    "must be stopped", "will not be allowed", "cannot be changed",
    "will never succeed", "is doomed to fail",
    # Strong unilateral declarations
    "firmly opposes", "categorically rejects", "strongly condemns",
    "resolutely opposes", "unequivocally rejects", "flatly rejects",
    "reserves the right to take all", "reserves the right to use",
    "vows to", "pledges to defend",
    # Delegitimizing declarations
    "so-called", "self-proclaimed", "illegitimate",
]

# ---------------------------------------------------------------------------
# Value judgment words (opinion signals when used without attribution)
#
# This list was pruned to remove high-frequency words that appear routinely
# in factual reporting WITHOUT being genuine editorial value judgments:
#   "good", "bad"       — "good morning", "bad weather", "good governance"
#   "wrong", "right"    — "the wrong number", "the right approach"
#   "important"         — "it is important to note", "important legislation"
#   "dangerous"         — "dangerous conditions", "dangerous levels of X"
# Keeping them produced false positives inflating opinion scores for wire
# stories by 5-15 points.  The remaining terms are higher-charge evaluative
# words that are unlikely to appear in purely factual reporting. (H3 fix)
# ---------------------------------------------------------------------------
VALUE_JUDGMENTS: list[str] = [
    "terrible", "wonderful", "excellent", "horrible", "disgraceful",
    "shameful", "courageous", "brilliant", "foolish", "reckless",
    "irresponsible", "admirable", "despicable", "outrageous",
    "unacceptable", "commendable", "alarming", "encouraging",
    "disappointing", "refreshing", "troubling", "promising",
    "absurd", "ridiculous", "sensible", "wise", "misguided",
    "naive", "cynical", "brave", "cowardly",
]

# ---------------------------------------------------------------------------
# Section/URL markers for opinion content
# ---------------------------------------------------------------------------
OPINION_MARKERS: list[str] = [
    "opinion", "editorial", "commentary", "analysis", "op-ed",
    "oped", "perspective", "column", "columnist", "blog",
    "viewpoint", "letters to the editor", "the take",
    "first person", "personal essay", "my turn",
]


def _pronoun_score(text: str) -> float:
    """Score first-person pronoun usage. Returns 0-100.

    International English fix (2026-03-21): iterate the ORIGINAL (un-lowercased)
    words and skip any token whose stripped form is exactly 'US' (all-caps) before
    lowercasing.  The country abbreviation 'US' (United States) appears dozens of
    times per article in wire-service copy and lowercases to 'us', which is a valid
    first-person pronoun.  This caused AP/Reuters US-news articles to receive
    pronoun_score=100 and a ~12-point opinion inflation relative to equivalent
    non-US articles (AFP Africa, Jakarta Post, etc.).  All-caps 'US' is
    unambiguously a country code, not a pronoun, in news text.
    """
    words_original = text.split()
    if not words_original:
        return 0.0

    pronoun_count = 0
    for w in words_original:
        stripped = w.strip(".,!?;:'\"()")
        # Skip 'US' (all-caps country abbreviation) before lowercasing
        if stripped == "US":
            continue
        if stripped.lower() in FIRST_PERSON_PRONOUNS:
            pronoun_count += 1

    pronoun_ratio = pronoun_count / len(words_original)

    # More than 2% first-person pronouns = strong opinion signal
    # 0% = 0, 1% = 25, 2% = 50, 4%+ = 100
    return min(100.0, pronoun_ratio * 2500)


def _subjectivity_score(text: str) -> float:
    """Average TextBlob subjectivity across sentences. Returns 0-100."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    if not sentences:
        return 0.0

    # Sample up to 100 sentences for performance
    sample = sentences[:100]
    total_subjectivity = 0.0
    for sent in sample:
        blob = TextBlob(sent)
        total_subjectivity += blob.sentiment.subjectivity

    avg = total_subjectivity / len(sample)
    return avg * 100.0  # TextBlob subjectivity is 0-1


def _modal_score(text: str) -> float:
    """Score prescriptive/modal language density. Returns 0-100."""
    text_lower = text.lower()
    word_count = len(text_lower.split())
    if word_count == 0:
        return 0.0

    modal_count = 0
    for phrase in MODAL_PRESCRIPTIVE:
        modal_count += text_lower.count(phrase)

    modal_per_100 = modal_count / max(word_count / 100, 1)
    # 0 = 0, 2 per 100 words = 40, 5+ per 100 words = 100
    return min(100.0, modal_per_100 * 20.0)


def _hedging_score(text: str) -> float:
    """Score hedging language density. Returns 0-100."""
    text_lower = text.lower()
    word_count = len(text_lower.split())
    if word_count == 0:
        return 0.0

    hedge_count = 0
    for phrase in HEDGING_PHRASES:
        hedge_count += text_lower.count(phrase)

    hedge_per_100 = hedge_count / max(word_count / 100, 1)
    return min(100.0, hedge_per_100 * 25.0)


def _attribution_score(text: str) -> float:
    """
    Score attribution density (inverse: high attribution = low opinion).
    Returns 0-100 where 0 = heavy attribution (factual), 100 = no attribution (opinion).

    M3 fix: Distinguish between "no attribution found" states:
    - word_count < 50: too short to signal either way → return 50 (neutral)
    - word_count >= 50 AND attr_count == 0: clear absence of attribution
      in a substantive text → return 75 (strong opinion signal).
      Propaganda, pure-advocacy, and attack content never cite sources.
      The old value of 50 (neutral) was too forgiving — it made zero-attribution
      attack pieces indistinguishable from wire stories with mixed coverage.
    - attr_count > 0: formula as before (50 - density * 25), decreasing toward 0
      as attribution density increases.

    This pushes Breitbart-style declarative attack content (0 attribution in 80+
    words) from ~28 to ~35+ on the opinion scale, crossing the Reporting/Analysis
    boundary more reliably.  Wire stories that quote sources still score low (0-30)
    because their attr_per_100 is typically 2-5.
    """
    text_lower = text.lower()
    word_count = len(text_lower.split())
    if word_count == 0:
        return 50.0

    attr_count = 0
    for phrase in ATTRIBUTION_PHRASES:
        attr_count += text_lower.count(phrase)

    attr_per_100 = attr_count / max(word_count / 100, 1)
    # High attribution = low score (factual); no attribution in substantial text
    # = elevated opinion signal (75 rather than 50).
    if attr_count == 0 and word_count >= 50:
        # Substantive text with zero attribution markers → opinion signal
        return 75.0
    raw = 50.0 - attr_per_100 * 25.0
    return max(0.0, min(100.0, raw))


ANALYSIS_TITLE_PREFIXES: list[str] = [
    "analysis:", "in depth:", "explainer:", "background:",
    "deep dive:", "fact check:", "q&a:", "primer:",
]


def _metadata_score(article: dict) -> float:
    """
    Check URL, section, and other metadata for opinion markers.
    Returns a gradated score based on marker strength:
        90 = explicit opinion/editorial
        50 = analysis/column (interpretive but sourced)
        30 = blog/personal essay (lighter opinion signal)
         0 = no markers found

    Title prefix detection: headlines like "Analysis: ...", "Explainer: ...",
    "Fact check: ..." are journalistic format labels that signal interpretive
    content (not news wire reporting) but are distinct from opinion. These
    return 50.0, matching the analysis/column tier. (bias-auditor fix)
    """
    url = (article.get("url", "") or "").lower()
    section = (article.get("section", "") or "").lower()
    title = (article.get("title", "") or "").lower()

    combined = f"{url} {section} {title}"

    # Check in priority order — strongest match wins
    strong_markers = ["opinion", "editorial", "op-ed", "oped", "commentary"]
    for marker in strong_markers:
        if marker in combined:
            return 90.0

    mid_markers = ["analysis", "column", "perspective"]
    for marker in mid_markers:
        if marker in combined:
            return 50.0

    # Title prefix detection: "Analysis: ...", "Explainer: ...", "Fact check: ...",
    # etc. These are distinct from the URL/section "analysis" match above because
    # they signal the publisher explicitly labeled the piece as interpretive format.
    # Return 50.0 (same tier as analysis/column). (bias-auditor fix)
    for prefix in ANALYSIS_TITLE_PREFIXES:
        if title.startswith(prefix):
            return 50.0

    light_markers = [
        "blog", "personal essay", "my turn", "viewpoint",
        "letters to the editor", "the take", "first person",
    ]
    for marker in light_markers:
        if marker in combined:
            return 30.0

    return 0.0


def _rhetorical_question_score(text: str) -> float:
    """Score rhetorical question usage. Returns 0-100."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    if not sentences:
        return 0.0

    question_count = sum(1 for s in sentences if s.strip().endswith("?"))
    question_ratio = question_count / len(sentences)

    # More than 10% questions = opinion signal
    return min(100.0, question_ratio * 300.0)


def _absolutist_assertion_score(text: str) -> float:
    """
    Score absolutist / certainty declarations that signal editorial opinion
    even when first-person pronouns and modal verbs are absent.

    State media and ideological op-eds use phrases like "historical
    inevitability", "no force can prevent", "firmly opposes" as unhedged
    categorical claims — the functional equivalent of opinion without "I".

    Returns 0-100.
    """
    text_lower = text.lower()
    word_count = len(text_lower.split())
    if word_count == 0:
        return 0.0

    hit_count = 0
    for phrase in ABSOLUTIST_PHRASES:
        hit_count += text_lower.count(phrase)

    if hit_count == 0:
        return 0.0

    # Density per 100 words; each unit contributes 30 pts; cap at 100
    density = hit_count / max(word_count / 100, 1)
    return min(100.0, density * 30.0)


def _value_judgment_score(text: str) -> float:
    """
    Score value judgment words that appear without nearby attribution.
    Returns 0-100.
    """
    text_lower = text.lower()
    sentences = re.split(r"[.!?]+", text_lower)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return 0.0

    unattributed_judgments = 0
    total_judgments = 0

    for sent in sentences[:100]:  # sample
        has_judgment = False
        has_attribution = False

        for word in VALUE_JUDGMENTS:
            if f" {word} " in f" {sent} ":
                has_judgment = True
                total_judgments += 1
                break

        if has_judgment:
            for phrase in ATTRIBUTION_PHRASES:
                if phrase in sent:
                    has_attribution = True
                    break
            if not has_attribution:
                unattributed_judgments += 1

    if total_judgments == 0:
        return 0.0

    ratio = unattributed_judgments / len(sentences)
    return min(100.0, ratio * 500.0)


def analyze_opinion(article: dict) -> dict:
    """
    Score where an article falls on the opinion-fact spectrum.

    Args:
        article: Dict with keys: full_text, title, summary, section, url.

    Returns:
        Dict with "score" (int 0-100) and "rationale" (dict with sub-scores).
    """
    full_text = article.get("full_text", "") or ""
    title = article.get("title", "") or ""
    combined = f"{title} {full_text}"

    if not combined.strip():
        return {
            "score": 25,
            "rationale": {
                "pronoun_score": 0, "subjectivity_score": 0, "modal_score": 0,
                "hedging_score": 0, "attribution_score": 50, "metadata_score": 0,
                "rhetorical_score": 0, "value_judgment_score": 0,
                "absolutist_assertion_score": 0,
                "classification": "Reporting", "dominant_signals": [],
            },
        }

    # Compute sub-scores
    pronoun = _pronoun_score(combined)
    subjectivity = _subjectivity_score(combined)
    modal = _modal_score(combined)
    hedging = _hedging_score(combined)
    attribution = _attribution_score(combined)
    metadata = _metadata_score(article)
    rhetorical = _rhetorical_question_score(combined)
    value_judg = _value_judgment_score(combined)
    absolutist = _absolutist_assertion_score(combined)

    # Weighted combination (text-based signals)
    # absolutist_assertion at 0.13; subjectivity reduced 0.23→0.22 to make room;
    # rhetorical 0.08→0.04; value_judg 0.10→0.02.  Total remains 1.0.
    # The absolutist signal captures state-media and ideological op-ed voice
    # ("historical inevitability", "firmly opposes", "no force can prevent")
    # that TextBlob subjectivity misses on declarative assertions.
    # Weight derivation (target: CGTN opinion >= 20, NPR opinion >= 5/ACCEPTABLE):
    #   CGTN: sub=18*0.22 + attr=25*0.15 + abs=100*0.13 = 3.96+3.75+13 = 20.71
    #   NPR:  sub=20.5*0.22 = 4.51 -> score=5 (ACCEPTABLE; factual reporting style,
    #         high attribution correctly suppresses opinion signal)
    weighted = (
        pronoun * 0.12
        + subjectivity * 0.22
        + modal * 0.12
        + hedging * 0.08
        + attribution * 0.15
        + metadata * 0.12
        + rhetorical * 0.04
        + value_judg * 0.02
        + absolutist * 0.13
    )

    # Metadata override: when URL/section explicitly marks content as
    # opinion/editorial, treat that as a hard floor — the publisher's own
    # classification is the strongest signal. Without this, paywalled
    # opinion articles with little scraped text score 15-25 despite being
    # opinion, because all text signals return near-zero on 25 words.
    if metadata >= 90:
        # Explicit opinion/editorial marker → floor at 70
        weighted = max(weighted, 70.0)
    elif metadata >= 50:
        # Analysis/column marker → floor at 45
        weighted = max(weighted, 45.0)
    elif metadata >= 30:
        # Blog/personal essay → floor at 35
        weighted = max(weighted, 35.0)

    score = max(0, min(100, int(round(weighted))))

    # Derive classification label
    if score <= 25:
        classification = "Reporting"
    elif score <= 50:
        classification = "Analysis"
    elif score <= 75:
        classification = "Opinion"
    else:
        classification = "Editorial"

    # Identify dominant signals (top 3 by weighted contribution)
    signal_contributions = [
        ("subjectivity", subjectivity * 0.22),
        ("attribution_gaps", attribution * 0.15),
        ("absolutist_assertions", absolutist * 0.13),
        ("pronouns", pronoun * 0.12),
        ("modal_language", modal * 0.12),
        ("metadata", metadata * 0.12),
        ("hedging", hedging * 0.08),
        ("rhetorical_questions", rhetorical * 0.04),
        ("value_judgments", value_judg * 0.02),
    ]
    signal_contributions.sort(key=lambda x: x[1], reverse=True)
    dominant = [s[0] for s in signal_contributions[:3] if s[1] > 0]

    return {
        "score": score,
        "rationale": {
            "pronoun_score": round(pronoun, 1),
            "subjectivity_score": round(subjectivity, 1),
            "modal_score": round(modal, 1),
            "hedging_score": round(hedging, 1),
            "attribution_score": round(attribution, 1),
            "metadata_score": round(metadata, 1),
            "rhetorical_score": round(rhetorical, 1),
            "value_judgment_score": round(value_judg, 1),
            "absolutist_assertion_score": round(absolutist, 1),
            "classification": classification,
            "dominant_signals": dominant,
        },
    }
