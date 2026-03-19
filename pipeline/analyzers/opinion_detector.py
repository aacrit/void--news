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
# Value judgment words (opinion signals when used without attribution)
# ---------------------------------------------------------------------------
VALUE_JUDGMENTS: list[str] = [
    "good", "bad", "wrong", "right", "dangerous", "important",
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
    """Score first-person pronoun usage. Returns 0-100."""
    words = text.lower().split()
    if not words:
        return 0.0

    pronoun_count = sum(1 for w in words if w.strip(".,!?;:'\"()") in FIRST_PERSON_PRONOUNS)
    pronoun_ratio = pronoun_count / len(words)

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
    """
    text_lower = text.lower()
    word_count = len(text_lower.split())
    if word_count == 0:
        return 50.0

    attr_count = 0
    for phrase in ATTRIBUTION_PHRASES:
        attr_count += text_lower.count(phrase)

    attr_per_100 = attr_count / max(word_count / 100, 1)
    # High attribution = low score (factual)
    # 0 attributions = 80, 3+ per 100 words = 0
    raw = 80.0 - attr_per_100 * 25.0
    return max(0.0, min(100.0, raw))


def _metadata_score(article: dict) -> float:
    """
    Check URL, section, and other metadata for opinion markers.
    Returns a gradated score based on marker strength:
        90 = explicit opinion/editorial
        50 = analysis/column (interpretive but sourced)
        30 = blog/personal essay (lighter opinion signal)
         0 = no markers found
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

    # Weighted combination
    weighted = (
        pronoun * 0.12
        + subjectivity * 0.23
        + modal * 0.12
        + hedging * 0.08
        + attribution * 0.15
        + metadata * 0.12
        + rhetorical * 0.08
        + value_judg * 0.10
    )

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
        ("subjectivity", subjectivity * 0.23),
        ("attribution_gaps", attribution * 0.15),
        ("pronouns", pronoun * 0.12),
        ("modal_language", modal * 0.12),
        ("metadata", metadata * 0.12),
        ("value_judgments", value_judg * 0.10),
        ("hedging", hedging * 0.08),
        ("rhetorical_questions", rhetorical * 0.08),
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
            "classification": classification,
            "dominant_signals": dominant,
        },
    }
