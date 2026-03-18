"""
Framing analyzer for the void --news bias engine.

Scores each article on a 0-100 framing spectrum:
    0   = neutral, balanced framing
    100 = heavily framed (emphasis/omission patterns detected)

Uses rule-based NLP heuristics (no LLM API calls):
    - Connotation analysis (TextBlob sentiment around key entities)
    - Keyword emphasis (charged synonyms vs neutral alternatives)
    - Omission detection (one-sided sourcing)
    - Headline vs body divergence
    - Active vs passive voice for agency (spaCy dependency parsing)
"""

import re

import spacy
from textblob import TextBlob

# ---------------------------------------------------------------------------
# Lazy-load spaCy model
# ---------------------------------------------------------------------------
_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp


# ---------------------------------------------------------------------------
# Charged vs neutral synonym pairs
# Format: (charged_form, neutral_form, charge_intensity 1-3)
# ---------------------------------------------------------------------------
SYNONYM_PAIRS: list[tuple[str, str, int]] = [
    # Conflict & violence
    ("killed", "died", 2),
    ("slaughtered", "killed", 3),
    ("massacre", "mass killing", 3),
    ("regime", "government", 3),
    ("dictator", "leader", 3),
    ("puppet", "ally", 3),
    ("thug", "suspect", 3),
    ("mob", "crowd", 2),
    ("riot", "protest", 2),
    ("looting", "property damage", 2),
    ("invasion", "military operation", 3),
    ("occupation", "presence", 2),
    ("terrorist", "militant", 3),
    ("freedom fighter", "rebel", 3),
    # Immigration
    ("flood", "influx", 2),
    ("swarm", "large number", 3),
    ("invasion", "migration", 3),
    ("illegal alien", "undocumented immigrant", 3),
    ("anchor baby", "child of immigrants", 3),
    # Political
    ("slammed", "criticized", 2),
    ("blasted", "responded to", 2),
    ("destroyed", "countered", 3),
    ("eviscerated", "challenged", 3),
    ("ripped", "criticized", 2),
    ("torched", "denounced", 2),
    ("grilled", "questioned", 2),
    ("hammered", "pressed", 2),
    ("schooled", "corrected", 2),
    ("doubled down", "reiterated", 1),
    # Economic
    ("tax burden", "tax rate", 2),
    ("job killing", "affecting employment", 3),
    ("government handout", "government assistance", 3),
    ("entitlement", "benefit program", 2),
    ("big tech", "technology companies", 2),
    ("bailout", "financial assistance", 2),
    ("wealth grab", "tax policy", 3),
    # Social
    ("radical", "progressive", 2),
    ("extremist", "activist", 3),
    ("woke", "socially conscious", 3),
    ("cancel culture", "public accountability", 3),
    ("indoctrination", "education", 3),
    ("propaganda", "messaging", 3),
]

# ---------------------------------------------------------------------------
# One-sided sourcing indicators
# ---------------------------------------------------------------------------
PRO_INDICATORS = re.compile(
    r"\b(supporters?|proponents?|advocates?|backers?|allies|defenders?)\s+(say|said|argue|argued|claim|believe)",
    re.IGNORECASE,
)

ANTI_INDICATORS = re.compile(
    r"\b(critics?|opponents?|detractors?|skeptics?|foes)\s+(say|said|argue|argued|claim|believe)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Passive voice pattern (simplified via spaCy dep parsing)
# ---------------------------------------------------------------------------
PASSIVE_MARKERS = re.compile(
    r"\b(was|were|been|being|is|are)\s+\w+ed\b",
    re.IGNORECASE,
)

# Evasive passive patterns
EVASIVE_PASSIVE: list[str] = [
    "mistakes were made", "errors were committed",
    "it was decided", "it was determined",
    "shots were fired", "damage was done",
    "lives were lost", "jobs were lost",
    "concerns were raised", "questions were raised",
    "steps were taken", "actions were taken",
    "measures were implemented",
]


def _connotation_score(text: str) -> float:
    """
    Measure sentiment polarity around key entities.
    High absolute polarity around entities = more framing.
    Returns 0-100.
    """
    nlp = _get_nlp()
    doc = nlp(text[:80000])

    # Extract key entities (PERSON, ORG, GPE, NORP)
    key_labels = {"PERSON", "ORG", "GPE", "NORP", "EVENT"}
    entities = [ent for ent in doc.ents if ent.label_ in key_labels]

    if not entities:
        return 10.0  # no entities to frame

    # Collect sentiment of sentences containing entities
    total_abs_polarity = 0.0
    entity_sentences = 0

    for sent in doc.sents:
        sent_ents = [e for e in entities if e.start >= sent.start and e.end <= sent.end]
        if sent_ents:
            blob = TextBlob(sent.text)
            total_abs_polarity += abs(blob.sentiment.polarity)
            entity_sentences += 1

    if entity_sentences == 0:
        return 10.0

    avg_abs_polarity = total_abs_polarity / entity_sentences
    # avg_abs_polarity ranges 0-1; 0 = neutral, 0.5+ = heavily framed
    return min(100.0, avg_abs_polarity * 200.0)


def _keyword_emphasis_score(text: str) -> float:
    """
    Check for emotionally charged synonyms vs neutral alternatives.
    Returns 0-100.
    """
    text_lower = text.lower()
    word_count = len(text_lower.split())
    if word_count == 0:
        return 0.0

    charged_score = 0
    total_pairs_found = 0

    for charged, neutral, intensity in SYNONYM_PAIRS:
        charged_count = text_lower.count(charged)
        if charged_count > 0:
            charged_score += charged_count * intensity
            total_pairs_found += charged_count

    if total_pairs_found == 0:
        return 5.0  # baseline low framing

    # Normalize by article length
    density = charged_score / max(word_count / 100, 1)
    return min(100.0, density * 15.0)


def _omission_score(text: str, cluster_articles: list[dict] | None = None) -> float:
    """
    Detect one-sided sourcing within the article.
    If cluster_articles provided, compare entity coverage.
    Returns 0-100.
    """
    text_lower = text.lower()

    pro_count = len(PRO_INDICATORS.findall(text_lower))
    anti_count = len(ANTI_INDICATORS.findall(text_lower))

    total_sided = pro_count + anti_count
    if total_sided == 0:
        # No explicit pro/anti sourcing detected
        base = 10.0
    elif pro_count == 0 or anti_count == 0:
        # Only one side represented
        base = min(100.0, total_sided * 15.0)
    else:
        # Both sides present; check balance
        ratio = min(pro_count, anti_count) / max(pro_count, anti_count)
        # ratio = 1.0 means balanced, 0 means completely one-sided
        base = (1.0 - ratio) * 60.0

    # Cross-article omission detection (if cluster provided)
    if cluster_articles and len(cluster_articles) >= 2:
        nlp = _get_nlp()
        # Get entities from this article
        doc = nlp(text[:50000])
        this_entities = {ent.text.lower() for ent in doc.ents
                        if ent.label_ in ("PERSON", "ORG", "GPE")}

        # Get entities from all cluster articles
        cluster_entities: set[str] = set()
        for other in cluster_articles[:10]:  # limit for performance
            other_text = other.get("full_text", "") or ""
            if other_text and other_text != text:
                other_doc = nlp(other_text[:30000])
                for ent in other_doc.ents:
                    if ent.label_ in ("PERSON", "ORG", "GPE"):
                        cluster_entities.add(ent.text.lower())

        if cluster_entities:
            # What fraction of cluster entities does this article mention?
            if this_entities:
                overlap = len(this_entities & cluster_entities) / len(cluster_entities)
                # Low overlap = potential omission
                omission_penalty = (1.0 - overlap) * 30.0
                base += omission_penalty

    return min(100.0, base)


def _headline_body_divergence(title: str, body: str) -> float:
    """
    Compare headline sentiment to body sentiment.
    Large divergence = framing.
    Returns 0-100.
    """
    if not title.strip() or not body.strip():
        return 0.0

    title_blob = TextBlob(title)
    body_blob = TextBlob(body[:10000])

    # Polarity divergence
    polarity_diff = abs(title_blob.sentiment.polarity - body_blob.sentiment.polarity)

    # Subjectivity divergence
    subj_diff = abs(title_blob.sentiment.subjectivity - body_blob.sentiment.subjectivity)

    # Combined divergence: both range 0-2, so combined max ~4
    divergence = polarity_diff + subj_diff
    return min(100.0, divergence * 50.0)


def _passive_voice_score(text: str) -> float:
    """
    Check for evasive passive voice constructions.
    Returns 0-100.
    """
    text_lower = text.lower()
    word_count = len(text_lower.split())
    if word_count == 0:
        return 0.0

    # Check for evasive passive patterns
    evasive_count = 0
    for phrase in EVASIVE_PASSIVE:
        evasive_count += text_lower.count(phrase)

    # General passive voice density using spaCy
    nlp = _get_nlp()
    doc = nlp(text[:80000])

    passive_count = 0
    active_count = 0
    for token in doc:
        if token.dep_ == "nsubjpass":
            passive_count += 1
        elif token.dep_ == "nsubj":
            active_count += 1

    total_subj = passive_count + active_count
    if total_subj == 0:
        passive_ratio = 0.0
    else:
        passive_ratio = passive_count / total_subj

    # Evasive patterns are more heavily weighted
    evasive_score = min(evasive_count * 15.0, 40.0)

    # General passive ratio: > 0.3 is notable, > 0.5 is heavy
    passive_score = max(0.0, (passive_ratio - 0.2)) * 100.0

    return min(100.0, evasive_score + passive_score)


def analyze_framing(article: dict, cluster_articles: list[dict] | None = None) -> int:
    """
    Score the framing bias of an article.

    Args:
        article: Dict with keys: full_text, title, summary.
        cluster_articles: Optional list of other articles in the same
            story cluster, used for omission detection.

    Returns:
        Integer score 0-100 (0=neutral framing, 100=heavily framed).
    """
    full_text = article.get("full_text", "") or ""
    title = article.get("title", "") or ""

    if not full_text.strip() and not title.strip():
        return 15  # default low

    # Sub-scores
    connotation = _connotation_score(full_text)          # 0-100
    keyword_emp = _keyword_emphasis_score(full_text)     # 0-100
    omission = _omission_score(full_text, cluster_articles)  # 0-100
    headline_div = _headline_body_divergence(title, full_text)  # 0-100
    passive = _passive_voice_score(full_text)            # 0-100

    # Weighted combination
    weighted = (
        connotation * 0.25
        + keyword_emp * 0.25
        + omission * 0.20
        + headline_div * 0.15
        + passive * 0.15
    )

    return max(0, min(100, int(round(weighted))))
