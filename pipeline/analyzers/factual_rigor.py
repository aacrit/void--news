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

from utils.nlp_shared import get_nlp


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


def _named_source_score(text: str, doc=None) -> float:
    """
    Count unique named persons used as sources via spaCy NER.

    Also counts SPECIFIC_ATTRIBUTION regex matches (titled persons like
    "Secretary Smith", "Director Johnson") as named sources. Wire-service
    articles heavily cite titled officials without always tagging them as
    PERSON entities — this corrects the resulting underscoring. (Priority 4 fix)

    Returns 0-100.
    """
    if doc is None:
        nlp = get_nlp()
        doc = nlp(text[:15000])

    # Find PERSON entities near attribution verbs
    named_sources = set()
    for ent in doc.ents:
        if ent.label_ == "PERSON":
            # Check if attribution verb appears within 120 chars of entity
            context_start = max(0, ent.start_char - 120)
            context_end = min(len(text), ent.end_char + 120)
            context = text[context_start:context_end]
            if ATTRIBUTION_VERBS.search(context):
                named_sources.add(ent.text.lower().strip())

    # Also count titled-person attributions (e.g. "Secretary Smith said")
    # that spaCy may miss as PERSON entities, particularly in wire copy.
    for match in SPECIFIC_ATTRIBUTION.finditer(text[:15000]):
        named_sources.add(match.group(0).lower().strip())

    count = len(named_sources)
    # 0 sources = 0, 1 = 20, 2 = 40, 3 = 60, 5+ = 100
    return min(100.0, count * 20.0)


def _org_citation_score(text: str, doc=None) -> float:
    """
    Count organization entities cited as sources.
    Returns 0-100.
    """
    if doc is None:
        nlp = get_nlp()
        doc = nlp(text[:15000])

    cited_orgs = set()
    for ent in doc.ents:
        if ent.label_ == "ORG":
            context_start = max(0, ent.start_char - 120)
            context_end = min(len(text), ent.end_char + 120)
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

    Neutral baseline (50) when no SPECIFIC_ATTRIBUTION matches and no vague
    sourcing: the article is neither confirmed specific nor confirmed vague.
    This avoids penalising wire-service articles where named sources are
    cited without formal title prefixes (e.g. "Powell said" vs
    "Chair Powell said"). Previously returning 0 here caused a 10% weight
    penalty on all such articles.
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

    # No evidence either way: neutral score (neither credited nor penalised)
    if specific_count == 0 and vague_count == 0:
        return 50.0

    total = specific_count + vague_count
    specific_ratio = specific_count / total
    # All specific = 100, all vague = 0, mixed = proportional
    return specific_ratio * 100.0


def analyze_factual_rigor(article: dict) -> dict:
    """
    Score the factual rigor of an article.

    Args:
        article: Dict with keys: full_text, title, summary.

    Returns:
        Dict with "score" (int 0-100) and "rationale" (dict with evidence counts).

    Text assembly: title + full_text + summary (in that order, summary appended
    last so longer full_text dominates signal). Including summary ensures that
    RSS-only articles (scrape failure fallback) still contribute their summary
    signal — otherwise short combined text causes all sub-scorers to return 0.

    Minimum floor: a length-proportional floor prevents scores of 0 for
    articles with very short text (title-only, RSS stubs). The floor scales
    from 5 (empty) to 0 at 200+ words, so genuinely short articles are not
    penalised to zero but also don't artificially inflate the score.
    Short-text floor values:
        0 words  -> 10 (early-return)
        1-50 words   -> floor ~7
        50-100 words -> floor ~4
        100-200 words -> floor ~1
        200+ words   -> floor 0 (no correction needed)
    """
    full_text = article.get("full_text", "") or ""
    title = article.get("title", "") or ""
    summary = article.get("summary", "") or ""

    # Include summary in analysis text so RSS-fallback articles have signal.
    # Append after full_text (not before) so full_text dominates NER context.
    combined = f"{title} {full_text} {summary}".strip()

    if not combined:
        return {
            "score": 10,
            "rationale": {
                "named_sources_count": 0, "org_citations_count": 0,
                "data_points_count": 0, "direct_quotes_count": 0,
                "vague_sources_count": 0, "specificity_ratio": 0,
            },
        }

    # Parse once with spaCy and share the doc for NER-based sub-scores
    nlp = get_nlp()
    doc = nlp(combined[:15000])

    # Sub-scores
    named_src = _named_source_score(combined, doc=doc)
    org_cite = _org_citation_score(combined, doc=doc)
    data_stats = _data_statistics_score(combined)
    quotes = _direct_quote_score(combined)
    refs = _reference_score(combined)
    specificity = _attribution_specificity_score(combined)

    # Weighted combination
    weighted = (
        named_src * 0.30
        + data_stats * 0.25
        + quotes * 0.20
        + org_cite * 0.15
        + specificity * 0.10
    )
    ref_bonus = min(refs * 0.05, 5.0)
    weighted += ref_bonus

    raw_score = max(0.0, min(100.0, weighted))

    # Length-proportional minimum floor: prevents score=0 for short text
    # articles where all NLP sub-scorers return 0 due to insufficient signal.
    # Floor decays linearly from 8 (<=50 words) to 0 (>=200 words).
    # This is a conservative floor — it does not inflate good articles, only
    # prevents catastrophic under-scoring of stubs and RSS-fallback articles.
    word_count = len(combined.split())
    if word_count < 200:
        floor = max(0.0, 8.0 * (1.0 - word_count / 200.0))
        raw_score = max(raw_score, floor)

    score = max(0, min(100, int(round(raw_score))))

    # Collect counts for rationale
    # Named sources: score / 20 gives approximate count (0=0, 20=1, 40=2, etc.)
    named_count = int(round(named_src / 20.0))
    org_count = int(round(org_cite / 25.0))
    data_count = int(round(data_stats / 33.0 * (len(combined.split()) / 100.0)))
    quote_count = int(round(quotes / 20.0 * (len(combined.split()) / 500.0)))

    # Vague sources count
    text_lower = combined.lower()
    vague_count = 0
    for phrase in VAGUE_SOURCES:
        vague_count += text_lower.count(phrase)

    # Specificity ratio
    specific_count = len(SPECIFIC_ATTRIBUTION.findall(combined))
    total_attr = specific_count + vague_count
    spec_ratio = round(specific_count / total_attr, 2) if total_attr > 0 else 0.0

    return {
        "score": score,
        "rationale": {
            "named_sources_count": named_count,
            "org_citations_count": org_count,
            "data_points_count": max(0, data_count),
            "direct_quotes_count": max(0, quote_count),
            "vague_sources_count": vague_count,
            "specificity_ratio": spec_ratio,
        },
    }
