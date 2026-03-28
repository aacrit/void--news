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
# Tier-based factual rigor baselines for source reputation blending.
#
# When an article has very short text (RSS stubs, 15-80 words), NER-based
# sub-scorers return near-zero because there is insufficient signal.  A
# tier baseline lets us weight in the source's editorial reputation so that
# an AP wire stub is not treated identically to an unsourced blog post.
#
# Blending weight is INVERSELY proportional to text length:
#   <100 words  → 0.60 text + 0.40 baseline  (lean on reputation)
#   100-300 words → 0.80 text + 0.20 baseline
#   300+ words  → 0.90 text + 0.10 baseline
#
# Tier values are intentionally conservative — reputation gives a floor,
# not a free pass.  A 15-word AP stub with baseline 65 blends to ~30,
# not 65, because text weight still dominates.
# ---------------------------------------------------------------------------
TIER_BASELINES: dict[str, float] = {
    "us_major":      65.0,   # AP, Reuters, NYT, WSJ, Bloomberg, etc.
    "international": 55.0,   # BBC, Al Jazeera, DW, France24, etc.
    # NOTE: raised from 40.0 to 50.0. ProPublica, Bellingcat, ICIJ, and similar
    # investigative independents consistently demonstrate rigorous sourcing;
    # 40.0 unfairly equated them with unvetted blogs. Still below us_major (65.0)
    # and international (55.0). (bias-auditor fix)
    "independent":   50.0,   # ProPublica, The Intercept, Bellingcat, ICIJ, etc.
}
_DEFAULT_BASELINE = 45.0     # Fallback for unknown/missing tier

# ---------------------------------------------------------------------------
# Low-credibility us_major outlets (Fix 15)
#
# These slugs receive a reduced tier baseline (35.0) instead of the standard
# us_major baseline (65.0).  They are us_major by audience size but
# consistently demonstrate weaker sourcing standards.  Adding here avoids
# touching sources.json and keeps the credibility split local to this scorer.
# ---------------------------------------------------------------------------
LOW_CREDIBILITY_US_MAJOR: frozenset[str] = frozenset({
    # Verified against data/sources.json (2026-03-28)
    'breitbart', 'newsmax', 'daily-wire', 'the-daily-caller', 'new-york-post',
})

# ---------------------------------------------------------------------------
# Attribution verb patterns (for named source detection)
# ---------------------------------------------------------------------------
ATTRIBUTION_VERBS = re.compile(
    r"\b(said|says|told|stated|reported|confirmed|announced|testified|"
    r"explained|noted|argued|claimed|contended|acknowledged|insisted|"
    r"emphasized|stressed|warned|cautioned|added|remarked|commented|"
    r"responded|replied|wrote|published|revealed|disclosed|"
    r"revised|projects|projected|estimated|estimates|found|concluded|"
    r"determined|calculated|forecasts|forecast|released|issued)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Organization citation patterns
# ---------------------------------------------------------------------------
# International sources expansion (2026-03-21): added think-tank and policy-outlet
# citation forms that are common in CFR, Chatham House, CSIS, RAND, OCCRP, and
# Carbon Brief articles but were absent from the original pattern set.
# "Research by [ORG]", "An analysis by [ORG]", "Findings by [ORG]",
# "Assessment by [ORG]", "A briefing by [ORG]", "A policy paper/brief by [ORG]"
# are standard citation formats in think-tank and policy journalism.
# These additions increase org_citation scores for investigative and policy outlets
# by 25-50 pts on typical articles, narrowing the gap with wire-service scoring.
# ---------------------------------------------------------------------------
ORG_CITATION_PATTERNS = re.compile(
    r"(according to (the )?|as reported by |data from (the )?|"
    r"a report by (the )?|a study by (the )?|"
    r"research by (the )?|an? analysis by (the )?|"
    r"findings by (the )?|an? assessment by (the )?|"
    r"an? briefing by (the )?|a policy (paper|brief) by (the )?|"
    r"the .{3,40} (reported|found|said|stated|showed|determined|concluded|estimated|argues?|contends?)|"
    r"published (in|by) (the )?)",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Data/statistics patterns
# ---------------------------------------------------------------------------
DATA_PATTERNS: list[re.Pattern] = [
    re.compile(r"\d+(\.\d+)?%"),                    # percentages (% symbol)
    re.compile(r"\d+(\.\d+)?\s*percent\b", re.I),  # percentages spelled out (AP style)
    re.compile(r"\$\d[\d,]*(\.\d+)?"),              # dollar amounts
    re.compile(r"\d[\d,]*\s*(million|billion|trillion)", re.I),  # large numbers
    re.compile(r"(rose|fell|increased|decreased|grew|dropped|declined|surged|plummeted)\s+by\s+\d", re.I),
    re.compile(r"(rose|fell|increased|decreased|grew|dropped|declined|surged)\s+to\s+\d", re.I),  # directional
    re.compile(r"\d{4}\s*(study|survey|poll|report|analysis)", re.I),  # dated studies
    re.compile(r"(data|statistics|figures|numbers)\s+(show|indicate|suggest|reveal)", re.I),
    re.compile(r"(per|every)\s+\d[\d,]*\s+\w+"),   # rates (per 100,000)
    re.compile(r"(average|median|mean)\s+of\s+\d"),  # statistical measures
    re.compile(r"\d+\s*-\s*\d+\s*(percent|%|year|month|day)", re.I),  # ranges
    re.compile(r"\d[\d,]+\s+(people|workers|citizens|soldiers|patients|refugees|cases|deaths|killed|wounded|displaced|arrested)\b", re.I),  # count nouns
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
    # Modern journalism variants (Fix 10)
    "a source with knowledge of",
    "people briefed on",
    "officials who requested anonymity",
    "a person familiar with the matter",
    "officials familiar with",
    "sources with direct knowledge",
    "a government official said",
    "people with knowledge of the matter",
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


def _named_source_score(text: str, doc=None) -> tuple[float, int]:
    """
    Count unique named persons used as sources via spaCy NER.

    Also counts SPECIFIC_ATTRIBUTION regex matches (titled persons like
    "Secretary Smith", "Director Johnson") as named sources, but only when
    an attribution verb appears within ±150 chars of the match. This prevents
    biographical mentions ("Director Johnson was appointed in 2019") from
    inflating the count. (Fix 4)

    Returns (score 0-100, raw_count).  (Fix 5)
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
    # Fix 4: require an attribution verb within ±150 chars of the match.
    for match in SPECIFIC_ATTRIBUTION.finditer(text[:15000]):
        start = max(0, match.start() - 150)
        end = min(len(text), match.end() + 150)
        context = text[start:end]
        if ATTRIBUTION_VERBS.search(context):
            named_sources.add(match.group(0).lower().strip())

    count = len(named_sources)
    # 0 sources = 0, 1 = 20, 2 = 40, 3 = 60, 5+ = 100
    return min(100.0, count * 20.0), count


def _org_citation_score(text: str, doc=None) -> tuple[float, int]:
    """
    Count organization entities cited as sources.

    Fix 13: Tightened proximity logic — ORG_CITATION_PATTERNS must match in
    the full ±120-char context, OR an attribution verb must appear within the
    first 80 chars of that context (i.e. close to the entity start).  The old
    broad ATTRIBUTION_VERBS fallback fired on almost any sentence and inflated
    counts.

    Fix 13: ORG names are normalised by stripping a leading "the " so that
    "the Fed" and "Federal Reserve" are not double-counted.

    Fix 5: Returns (score 0-100, raw_count).
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
            if ORG_CITATION_PATTERNS.search(context):
                org_text = ent.text.lower().strip()
                if org_text.startswith("the "):
                    org_text = org_text[4:]
                cited_orgs.add(org_text)
            elif ATTRIBUTION_VERBS.search(context[:80]):
                # Only count when verb is close to the entity (within first 80 chars)
                org_text = ent.text.lower().strip()
                if org_text.startswith("the "):
                    org_text = org_text[4:]
                cited_orgs.add(org_text)

    count = len(cited_orgs)
    # 0 orgs = 0, 1 = 25, 2 = 50, 4+ = 100
    return min(100.0, count * 25.0), count


def _data_statistics_score(text: str) -> tuple[float, int]:
    """
    Count data points and statistics in the text.
    Returns (score 0-100, total_matches).  (Fix 5)
    """
    word_count = len(text.split())
    if word_count == 0:
        return 0.0, 0

    total_matches = 0
    for pattern in DATA_PATTERNS:
        total_matches += len(pattern.findall(text))

    # Normalize by article length: data points per 100 words
    data_per_100 = total_matches / max(word_count / 100, 1)
    # 0 = 0, 1 per 100 words = 30, 3+ per 100 words = 100
    return min(100.0, data_per_100 * 33.0), total_matches


def _direct_quote_score(text: str) -> tuple[float, int]:
    """
    Count direct quotes in the text.
    Returns (score 0-100, total_quotes).  (Fix 5)
    """
    word_count = len(text.split())
    if word_count == 0:
        return 0.0, 0

    total_quotes = 0
    for pattern in QUOTE_PATTERNS:
        total_quotes += len(pattern.findall(text))

    # Normalize: quotes per 500 words
    quotes_per_500 = total_quotes / max(word_count / 500, 1)
    # 0 = 0, 1 per 500 = 20, 3 per 500 = 60, 5+ = 100
    return min(100.0, quotes_per_500 * 20.0), total_quotes


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


def analyze_factual_rigor(article: dict, source: dict | None = None, doc=None) -> dict:
    """
    Score the factual rigor of an article.

    Args:
        article: Dict with keys: full_text, title, summary.
        source:  Optional source dict.  If provided, must include "tier"
                 (one of "us_major", "international", "independent").
                 Used for tier-baseline blending on short-text articles.

    Returns:
        Dict with "score" (int 0-100) and "rationale" (dict with evidence counts).

    Text assembly: title + full_text + summary (in that order, summary appended
    last so longer full_text dominates signal). Including summary ensures that
    RSS-only articles (scrape failure fallback) still contribute their summary
    signal — otherwise short combined text causes all sub-scorers to return 0.

    Tier-baseline blending: on short articles (< 300 words) the raw NLP score
    is blended with a tier-based reputation baseline so that a 15-word AP stub
    does not receive the same score as a 15-word unsourced stub.  Blending
    weights are inversely proportional to word count:
        < 100 words  : 0.60 text + 0.40 baseline
        100-299 words: 0.80 text + 0.20 baseline
        300+ words   : 0.90 text + 0.10 baseline  (baseline almost invisible)

    Short-text floor (applied before blending):
        <= 30 words  : floor = 15  (nearly no signal — benefit of the doubt)
        31-100 words : floor = 10
        101-199 words: floor = 8
        200+ words   : no floor (enough text to score properly)
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
    if doc is None:
        nlp = get_nlp()
        doc = nlp(combined[:15000])

    # Sub-scores — each returns (score, raw_count) tuple (Fix 5)
    named_src, named_raw = _named_source_score(combined, doc=doc)
    org_cite, org_raw = _org_citation_score(combined, doc=doc)
    data_stats, data_raw = _data_statistics_score(combined)
    quotes, quotes_raw = _direct_quote_score(combined)
    refs = _reference_score(combined)
    specificity = _attribution_specificity_score(combined)

    # Weighted combination
    #
    # Weight rationale (recalibrated for institutional wire reporting):
    #   named_src  0.22 — PERSON NER under-fires on short text; reduced from 0.30
    #   org_cite   0.24 — institutional orgs (ECB, Fed, Eurostat) are the primary
    #                     sourcing vehicle for wire copy; raised from 0.15
    #   data_stats 0.27 — wire stories lead with numbers; slightly raised from 0.25
    #   quotes     0.17 — wire copy often paraphrases rather than direct-quotes;
    #                     reduced from 0.20
    #   specificity 0.10 — unchanged; neutral baseline holds for titled persons
    #
    # ref_bonus cap raised from 5.0 to 8.0 — "according to [report/agency]"
    # patterns are common in wire copy and deserve additional credit.
    weighted = (
        named_src * 0.22
        + org_cite * 0.24
        + data_stats * 0.27
        + quotes * 0.17
        + specificity * 0.10
    )
    ref_bonus = min(refs * 0.05, 8.0)
    weighted += ref_bonus

    # Vague-source penalty (Fix 15): penalise articles that lean on vague sourcing
    # language. Each vague phrase costs 3 points, capped at 15.
    combined_lower = combined.lower()
    vague_count_raw = sum(1 for p in VAGUE_SOURCES if p in combined_lower)
    vague_penalty = min(15.0, vague_count_raw * 3.0)
    weighted = max(0, weighted - vague_penalty)

    raw_score = max(0.0, min(100.0, weighted))

    # ---------------------------------------------------------------------------
    # Short-text floor: prevents catastrophic under-scoring of RSS stubs where
    # all NLP sub-scorers return 0 due to insufficient signal.
    # Floors are step-based (not linear) and calibrated to give benefit of the
    # doubt to very short articles while not inflating scores for medium-length
    # text where the NLP scorers already have enough signal.
    # ---------------------------------------------------------------------------
    word_count = len(combined.split())
    if word_count <= 30:
        floor = 15.0
    elif word_count <= 100:
        floor = 10.0
    elif word_count < 200:
        floor = 8.0
    else:
        floor = 0.0
    raw_score = max(raw_score, floor)

    # ---------------------------------------------------------------------------
    # Tier-baseline blending: on short articles the raw NLP score is blended
    # with a tier reputation baseline so that a reputable wire-service stub
    # is distinguished from an unsourced short stub.
    #
    # Blending weight on the baseline is inversely proportional to word count:
    #   < 100 words   → baseline_weight = 0.40
    #   100-299 words → baseline_weight = 0.20
    #   300+ words    → baseline_weight = 0.10  (baseline nearly invisible)
    # ---------------------------------------------------------------------------
    if source:
        tier = (source.get("tier") or "").lower()
        # Fix 15: low-credibility us_major outlets get a reduced baseline (35.0)
        source_slug = source.get('slug', '') if source else ''
        if tier == 'us_major' and source_slug in LOW_CREDIBILITY_US_MAJOR:
            tier_baseline = 35.0
        else:
            tier_baseline = TIER_BASELINES.get(tier, _DEFAULT_BASELINE)

        if word_count < 100:
            baseline_weight = 0.40
        elif word_count < 300:
            baseline_weight = 0.20
        else:
            baseline_weight = 0.10

        text_weight = 1.0 - baseline_weight
        raw_score = raw_score * text_weight + tier_baseline * baseline_weight
        raw_score = max(0.0, min(100.0, raw_score))

    score = max(0, min(100, int(round(raw_score))))

    # Rationale: use raw counts directly (Fix 5 — no back-calculation from capped scores)
    # vague_count_raw already computed above for the penalty; reuse it here.
    # specificity_ratio: based on SPECIFIC_ATTRIBUTION matches vs vague phrases.
    specific_count = len(SPECIFIC_ATTRIBUTION.findall(combined))
    total_attr = specific_count + vague_count_raw
    spec_ratio = round(specific_count / total_attr, 2) if total_attr > 0 else 0.0

    return {
        "score": score,
        "rationale": {
            "named_sources_count": named_raw,
            "org_citations_count": org_raw,
            "data_points_count": data_raw,
            "direct_quotes_count": quotes_raw,
            "vague_sources_count": vague_count_raw,
            "specificity_ratio": spec_ratio,
        },
    }
