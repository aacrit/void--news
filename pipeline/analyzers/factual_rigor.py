"""
Factual rigor scorer for the void --news bias engine.

Scores each article on a 0-100 factual rigor spectrum:
    0   = no sourcing, unsubstantiated claims
    100 = heavily sourced, data-backed, well-cited

Uses rule-based NLP heuristics (no LLM API calls):
    - Named source counting via spaCy NER
    - Organization citations
    - Data/statistics presence
    - Direct quote counting
    - Link/reference density
    - Attribution pattern specificity
    - Vague sourcing penalties
"""

import re

import spacy

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
# Attribution verb patterns (for named source detection)
# ---------------------------------------------------------------------------
ATTRIBUTION_VERBS = re.compile(
    r"\b(said|says|told|stated|reported|confirmed|announced|testified|"
    r"explained|noted|argued|claimed|contended|acknowledged|insisted|"
    r"emphasized|stressed|warned|cautioned|added|remarked|commented|"
    r"responded|replied|wrote|published|revealed|disclosed)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Organization citation patterns
# ---------------------------------------------------------------------------
ORG_CITATION_PATTERNS = re.compile(
    r"(according to (the )?|as reported by |data from (the )?|"
    r"a report by (the )?|a study by (the )?|"
    r"the .{3,40} (reported|found|said|stated|showed|determined|concluded|estimated)|"
    r"published (in|by) (the )?)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Data/statistics patterns
# ---------------------------------------------------------------------------
DATA_PATTERNS: list[re.Pattern] = [
    re.compile(r"\d+(\.\d+)?%"),                    # percentages
    re.compile(r"\$\d[\d,]*(\.\d+)?"),              # dollar amounts
    re.compile(r"\d[\d,]*\s*(million|billion|trillion)", re.I),  # large numbers
    re.compile(r"(rose|fell|increased|decreased|grew|dropped|declined|surged|plummeted)\s+by\s+\d", re.I),
    re.compile(r"\d{4}\s*(study|survey|poll|report|analysis)", re.I),  # dated studies
    re.compile(r"(data|statistics|figures|numbers)\s+(show|indicate|suggest|reveal)", re.I),
    re.compile(r"(per|every)\s+\d[\d,]*\s+\w+"),   # rates (per 100,000)
    re.compile(r"(average|median|mean)\s+of\s+\d"),  # statistical measures
    re.compile(r"\d+\s*-\s*\d+\s*(percent|%|year|month|day)", re.I),  # ranges
]

# ---------------------------------------------------------------------------
# Direct quote patterns
# ---------------------------------------------------------------------------
QUOTE_PATTERNS: list[re.Pattern] = [
    re.compile(r'"[^"]{10,}"'),      # double quotes with substantial content
    re.compile(r"\u201c[^\u201d]{10,}\u201d"),  # smart double quotes
    re.compile(r"'[^']{20,}'"),      # single quotes (longer to avoid possessives)
    re.compile(r"\u2018[^\u2019]{20,}\u2019"),  # smart single quotes
]

# ---------------------------------------------------------------------------
# Reference/link patterns
# ---------------------------------------------------------------------------
REFERENCE_PATTERNS: list[re.Pattern] = [
    re.compile(r"https?://\S+"),                     # URLs
    re.compile(r"(study|report|paper)\s+published\s+in", re.I),
    re.compile(r"(journal|publication)\s+of\s+\w+", re.I),
    re.compile(r"according\s+to\s+(a|the|an)\s+(report|study|survey|analysis|paper|document)", re.I),
    re.compile(r"(white paper|working paper|policy brief|press release)", re.I),
    re.compile(r"(footnote|endnote|reference|citation)", re.I),
]

# ---------------------------------------------------------------------------
# Vague sourcing penalties
# ---------------------------------------------------------------------------
VAGUE_SOURCES: list[str] = [
    "some say", "many believe", "critics argue", "observers note",
    "people familiar with", "sources say", "sources said",
    "sources familiar with", "people close to",
    "anonymous sources", "unnamed sources",
    "insiders say", "some experts", "some analysts",
    "it is believed", "it is thought", "it is said",
    "according to sources", "according to reports",
    "reports suggest", "rumors suggest", "speculation",
]

# ---------------------------------------------------------------------------
# Specific attribution (bonus patterns)
# ---------------------------------------------------------------------------
SPECIFIC_ATTRIBUTION = re.compile(
    r"(Dr\.|Prof\.|Professor|Director|Secretary|Minister|Senator|"
    r"Representative|President|CEO|Chief|Commissioner|Spokesperson|"
    r"Chairman|Chairwoman|Mayor|Governor|Attorney General|Judge)\s+"
    r"[A-Z][a-z]+(\s+[A-Z][a-z]+)?",
)


def _named_source_score(text: str) -> float:
    """
    Count unique named persons used as sources via spaCy NER.
    Returns 0-100.
    """
    nlp = _get_nlp()
    doc = nlp(text[:100000])

    # Find PERSON entities near attribution verbs
    named_sources = set()
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            # Check if attribution verb appears within 50 chars of entity
            context_start = max(0, ent.start_char - 50)
            context_end = min(len(text), ent.end_char + 50)
            context = text[context_start:context_end]
            if ATTRIBUTION_VERBS.search(context):
                named_sources.add(ent.text.lower().strip())

    count = len(named_sources)
    # 0 sources = 0, 1 = 20, 2 = 40, 3 = 60, 5+ = 100
    return min(100.0, count * 20.0)


def _org_citation_score(text: str) -> float:
    """
    Count organization entities cited as sources.
    Returns 0-100.
    """
    nlp = _get_nlp()
    doc = nlp(text[:100000])

    cited_orgs = set()
    for ent in doc.ents:
        if ent.label_ == "ORG":
            context_start = max(0, ent.start_char - 80)
            context_end = min(len(text), ent.end_char + 80)
            context = text[context_start:context_end]
            if ORG_CITATION_PATTERNS.search(context) or ATTRIBUTION_VERBS.search(context):
                cited_orgs.add(ent.text.lower().strip())

    count = len(cited_orgs)
    # 0 orgs = 0, 1 = 25, 2 = 50, 4+ = 100
    return min(100.0, count * 25.0)


def _data_statistics_score(text: str) -> float:
    """
    Count data points and statistics in the text.
    Returns 0-100.
    """
    word_count = len(text.split())
    if word_count == 0:
        return 0.0

    total_matches = 0
    for pattern in DATA_PATTERNS:
        total_matches += len(pattern.findall(text))

    # Normalize by article length: data points per 100 words
    data_per_100 = total_matches / max(word_count / 100, 1)
    # 0 = 0, 1 per 100 words = 30, 3+ per 100 words = 100
    return min(100.0, data_per_100 * 33.0)


def _direct_quote_score(text: str) -> float:
    """
    Count direct quotes in the text.
    Returns 0-100.
    """
    word_count = len(text.split())
    if word_count == 0:
        return 0.0

    total_quotes = 0
    for pattern in QUOTE_PATTERNS:
        total_quotes += len(pattern.findall(text))

    # Normalize: quotes per 500 words
    quotes_per_500 = total_quotes / max(word_count / 500, 1)
    # 0 = 0, 1 per 500 = 20, 3 per 500 = 60, 5+ = 100
    return min(100.0, quotes_per_500 * 20.0)


def _reference_score(text: str) -> float:
    """
    Count references, links, and study citations.
    Returns 0-100.
    """
    total_refs = 0
    for pattern in REFERENCE_PATTERNS:
        total_refs += len(pattern.findall(text))

    # 0 = 0, 1 = 20, 3 = 60, 5+ = 100
    return min(100.0, total_refs * 20.0)


def _attribution_specificity_score(text: str) -> float:
    """
    Score based on specificity of attribution.
    Specific titles + names score high; vague sourcing scores low.
    Returns 0-100.
    """
    text_lower = text.lower()
    word_count = len(text_lower.split())
    if word_count == 0:
        return 0.0

    # Count specific attributions (titled persons)
    specific_count = len(SPECIFIC_ATTRIBUTION.findall(text))

    # Count vague sourcing
    vague_count = 0
    for phrase in VAGUE_SOURCES:
        vague_count += text_lower.count(phrase)

    # Net specificity: specific attributions boost, vague ones penalize
    if specific_count == 0 and vague_count == 0:
        return 30.0  # neutral baseline

    total = specific_count + vague_count
    if total == 0:
        return 30.0

    specific_ratio = specific_count / total
    # All specific = 100, all vague = 0, mixed = proportional
    return specific_ratio * 100.0


def analyze_factual_rigor(article: dict) -> int:
    """
    Score the factual rigor of an article.

    Args:
        article: Dict with keys: full_text, title, summary.

    Returns:
        Integer score 0-100 (0=no sourcing, 100=heavily sourced).
    """
    full_text = article.get("full_text", "") or ""
    title = article.get("title", "") or ""
    combined = f"{title} {full_text}"

    if not combined.strip():
        return 10  # no text = very low rigor

    # Sub-scores
    named_src = _named_source_score(combined)            # 0-100
    org_cite = _org_citation_score(combined)             # 0-100
    data_stats = _data_statistics_score(combined)        # 0-100
    quotes = _direct_quote_score(combined)               # 0-100
    refs = _reference_score(combined)                    # 0-100
    specificity = _attribution_specificity_score(combined)  # 0-100

    # Weighted combination (matches spec)
    weighted = (
        named_src * 0.30
        + data_stats * 0.25
        + quotes * 0.20
        + org_cite * 0.15
        + specificity * 0.10
    )

    # Small bonus for references (additional signal not in main weights)
    ref_bonus = min(refs * 0.05, 5.0)
    weighted += ref_bonus

    return max(0, min(100, int(round(weighted))))
