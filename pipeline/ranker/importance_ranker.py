"""
Importance/impact ranker v4.0 for the void --news pipeline.

Scores story clusters by importance for feed ordering on the homepage.
Higher scores appear first in the news feed.

Uses rule-based heuristics (no LLM API calls) with 10 signals:
    - Source coverage breadth (20%) — tier-weighted diminishing returns curve
    - Story maturity (16%) — recency × log(source_depth); replaces separate
      recency (14%) + velocity (9%) — rewards "recent AND thoroughly reported"
    - Tier diversity (13%) — composition-aware: us_major presence rewarded
    - Consequentiality (10%) — outcome/action verbs + high-authority floor
    - Institutional authority (8%) — heads of state, supreme courts, central
      banks, UN Security Council → intrinsic front-page weight
    - Factual density (8%) — average factual rigor; gate: <30 gets 0.88x
    - Divergence score (7%) — framing-weighted source disagreement
    - Perspective diversity (6%) — editorial viewpoint spread (bias-blind)
    - Geographic impact via NER (6%) — geopolitically weighted GPEs
    - Soft-news category gate — sports/entertainment/culture get 0.78x multiplier

Design principle: ranking is BIAS-BLIND. Bias analysis belongs in the
display layer (BiasLens, Sigil, Deep Dive), not in story selection.
We never boost or penalize a story for its political lean distribution.

v4.0 calibration changes (2026-03-20):
    - NEW: Institutional authority signal (8%) — regex tiers for heads of
      state, central banks, supreme courts, UN bodies. The single biggest
      upgrade: stories about powerful institutions get intrinsic front-page
      weight regardless of source count.
    - NEW: Story maturity signal (16%) — replaces independent recency +
      velocity. Formula: recency_score * log2(1 + source_count). Rewards
      stories that are both recent AND thoroughly reported. Fixes "trivial
      story published 1h ago beats assassination covered for 18h" problem.
    - NEW: Soft-news category gate — sports/entertainment/culture categories
      get 0.78x multiplier on final score. Belt-and-suspenders with the
      consequentiality gate. Category param added to rank_importance().
    - NEW: Tier-weighted source counting — independent sources count 1.5x,
      international 1.2x, us_major 1.0x in coverage score. Reduces wire
      service roundup inflation (10 AP republications ≠ 10 independent reports).
    - NEW: Geopolitical weighting — G20/P5 nations score 3x vs. small nations
      in geographic impact. Prevents "5 small countries" beating "US + China".
    - NEW: High-authority consequentiality floor — phrases like "declared war",
      "martial law", "supreme court ruled" set a floor of 70 regardless of
      other matches. Major events can't be missed.
    - NEW: Low-rigor gate — clusters with avg factual_rigor < 30 get 0.88x
      multiplier. Penalizes speculative/unattributed coverage.
    - Factual density weight: 4% → 8% (doubled — rewards real journalism)
    - Coverage breadth: 27% → 20% (reduced — authority + maturity absorb role)
    - Perspective diversity: 10% → 6% (partially redundant with tier diversity)
    - Recency + velocity merged into maturity (14% + 9% → 16%)
    - Confidence multiplier: unchanged (0.65 + 0.35 * conf)

v3.1 optimizations (retained):
    - Source map built once, shared across all sub-functions
    - Timestamps parsed once, shared between recency and velocity
    - Consequentiality uses word-boundary regex (no false substring matches)
    - Confidence uses p25 instead of min (one bad article doesn't tank cluster)
    - Geographic NER runs on titles only first; full text only when needed
    - Perspective diversity replaces cross-spectrum (removed partisan bucket bonus)
"""

import math
import re
from datetime import datetime, timezone

from utils.nlp_shared import get_nlp


# ---------------------------------------------------------------------------
# Source baseline lean mapping (string to numeric)
# ---------------------------------------------------------------------------
LEAN_NUMERIC: dict[str, int] = {
    "far-left": 10, "left": 20, "center-left": 35,
    "center": 50,
    "center-right": 65, "right": 80, "far-right": 90,
    "varies": 50,
}

LEAN_BUCKET: dict[str, str] = {
    "far-left": "left", "left": "left", "center-left": "left",
    "center": "center",
    "center-right": "right", "right": "right", "far-right": "right",
    "varies": "center",
}

# ---------------------------------------------------------------------------
# Global / geographic impact keywords
# ---------------------------------------------------------------------------
GLOBAL_KEYWORDS: list[str] = [
    "global", "worldwide", "international", "world leaders",
    "united nations", "un security council", "g7", "g20",
    "european union", "nato",
    # NOTE: bare "who" intentionally excluded — it matches "who said", "who told",
    # etc. in every sentence, producing false positives on all articles.
    "world health organization",
    "multiple countries", "several nations", "across borders",
    "global economy", "world economy", "pandemic", "epidemic",
]

# ---------------------------------------------------------------------------
# Geopolitical weight map (v4.0) — G20 + P5 + major geopolitical actors
# score 3x; mid-tier nations score 2x; all others score 1x.
# Keyed by lowercase GPE text as returned by spaCy NER.
# ---------------------------------------------------------------------------
_GEOPOLITICAL_WEIGHT: dict[str, float] = {
    # P5 / G7 / major powers
    "united states": 3.0, "us": 3.0, "u.s.": 3.0, "america": 3.0, "usa": 3.0,
    "china": 3.0, "russia": 3.0, "united kingdom": 3.0, "uk": 3.0, "u.k.": 3.0,
    "britain": 3.0, "france": 3.0, "germany": 3.0, "japan": 3.0, "india": 3.0,
    # Rest of G20
    "brazil": 3.0, "canada": 3.0, "australia": 3.0, "south korea": 3.0,
    "mexico": 3.0, "indonesia": 3.0, "turkey": 3.0, "saudi arabia": 3.0,
    "argentina": 3.0, "south africa": 3.0, "italy": 3.0,
    # Major geopolitical actors (not G20 but global significance)
    "iran": 3.0, "israel": 3.0, "ukraine": 3.0, "taiwan": 3.0,
    "north korea": 3.0, "pakistan": 3.0, "egypt": 3.0, "nigeria": 3.0,
    # Mid-tier nations with frequent news impact
    "spain": 2.0, "poland": 2.0, "netherlands": 2.0, "sweden": 2.0,
    "switzerland": 2.0, "norway": 2.0, "colombia": 2.0, "chile": 2.0,
    "thailand": 2.0, "vietnam": 2.0, "philippines": 2.0, "bangladesh": 2.0,
    "ethiopia": 2.0, "kenya": 2.0, "iraq": 2.0, "syria": 2.0,
    "afghanistan": 2.0, "myanmar": 2.0, "venezuela": 2.0, "cuba": 2.0,
    # Major cities that imply major-nation impact
    "washington": 3.0, "beijing": 3.0, "moscow": 3.0, "london": 3.0,
    "paris": 3.0, "berlin": 3.0, "tokyo": 3.0, "new delhi": 3.0,
    "brussels": 2.0, "jerusalem": 3.0, "kyiv": 3.0, "tehran": 3.0,
    "taipei": 3.0,
}

# ---------------------------------------------------------------------------
# Consequentiality lexicon — outcome/action verbs that signal real-world
# impact. "Senate passes bill" > "Senate discusses bill".
# Compiled into a single regex for O(n) matching instead of O(n*m).
# ---------------------------------------------------------------------------
_CONSEQUENTIALITY_TERMS: list[str] = [
    # Legislative/executive actions
    "passed", "signed into law", "enacted", "vetoed", "ratified", "repealed",
    "approved", "rejected", "overturned", "upheld", "ruled",
    # Conflict/security
    "invaded", "attacked", "bombed", "killed", "assassinated",
    "arrested", "detained", "charged", "convicted", "sentenced",
    "sanctioned", "deployed", "evacuated",
    # Political transitions
    "elected", "resigned", "impeached", "ousted", "appointed",
    "inaugurated", "abdicated", "overthrown",
    # Economic outcomes
    "collapsed", "defaulted", "bankrupt", "crashed", "surged",
    "plunged", "acquired", "merged",
    # Disasters/events
    "struck", "devastated", "erupted", "declared emergency",
    "state of emergency",
    # Agreements/diplomacy
    "ceasefire", "peace deal", "trade deal", "agreement reached",
    "treaty signed", "broke off", "severed ties",
]

# Pre-compile regex with word boundaries to prevent false matches
# ("approved" won't match inside "disapproved", "killed" won't match "skilled")
# Multi-word phrases use the phrase as-is; single words get \b boundaries.
_CONSEQUENTIALITY_PATTERN: re.Pattern = re.compile(
    r"|".join(
        rf"\b{re.escape(t)}\b" if " " not in t else re.escape(t)
        for t in _CONSEQUENTIALITY_TERMS
    ),
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# High-authority event phrases (v4.0) — these set a consequentiality floor
# of 70. When matched, the story is intrinsically front-page-worthy
# regardless of how many other consequentiality terms appear.
# ---------------------------------------------------------------------------
_HIGH_AUTHORITY_PHRASES: list[str] = [
    "declared war", "nuclear test", "nuclear strike", "nuclear weapon",
    "mass casualty", "mass shooting", "death toll",
    "martial law", "state of emergency", "constitutional crisis",
    "snap election", "general election",
    "central bank rate", "interest rate decision", "rate decision",
    "federal reserve", "the fed raised", "the fed cut",
    "supreme court ruled", "supreme court overturned", "supreme court struck",
    # "executive order signed" — passive/post-noun order (e.g. "executive order
    #     signed by the president"). Bare "executive order" was removed because
    #     it triggered the floor=70 for routine EO references (discussed, criticized,
    #     trivially mentioned). Use _HIGH_AUTHORITY_EO_PATTERN for natural word order.
    "executive order signed",
    "genocide", "ethnic cleansing", "war crimes",
    "peace agreement", "ceasefire agreement",
    "coup attempt", "military coup",
    "pandemic declared", "public health emergency",
    "territorial invasion", "airspace violation",
]

_HIGH_AUTHORITY_PATTERN: re.Pattern = re.compile(
    r"|".join(re.escape(t) for t in _HIGH_AUTHORITY_PHRASES),
    re.IGNORECASE,
)

# Supplemental pattern for "signed the/an executive order" (natural English order).
# Cannot be expressed via re.escape() in the list above, so compiled separately.
# Combined with _HIGH_AUTHORITY_PATTERN via logical OR in _consequentiality_score.
# Matches: "signed the executive order", "signed an executive order",
#          "signed a sweeping executive order", etc. (up to 4 intervening words).
# Does NOT match: "critics of the executive order", "discussed the executive order".
# (Priority H1 fix — executive order false positive in high-authority floor)
_HIGH_AUTHORITY_EO_PATTERN: re.Pattern = re.compile(
    r"\bsigned\s+(?:\w+\s+){0,4}executive\s+order\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Institutional authority lexicon (v4.0) — detects WHO is involved.
# Tier 1 (score 80-100): heads of state, supreme courts, central banks,
#     UN Security Council, constitutional bodies.
# Tier 2 (score 40-70): cabinet ministers, federal courts, major treaty orgs.
# ---------------------------------------------------------------------------
_AUTHORITY_TIER1: list[str] = [
    # Heads of state / government
    "president of", "prime minister", "chancellor of",
    "head of state",
    # Specific leaders (by title, not name — names change)
    "the president", "the prime minister",
    # Supreme/constitutional courts
    "supreme court", "constitutional court", "high court ruling",
    # Central banks
    "federal reserve", "the fed ", "european central bank", "ecb ",
    "bank of england", "bank of japan", "people's bank of china",
    "reserve bank of india",
    # UN top-level bodies
    "un security council", "united nations security council",
    "un general assembly", "international court of justice",
    # Constitutional / sovereignty events
    "constitution", "constitutional amendment", "impeachment",
    "declaration of independence", "sovereignty",
]

_AUTHORITY_TIER2: list[str] = [
    # Cabinet-level officials
    "secretary of state", "secretary of defense", "secretary of treasury",
    "foreign minister", "defense minister", "finance minister",
    "home minister", "interior minister",
    "attorney general", "chief justice",
    # Federal courts / regulatory bodies
    "federal court", "appeals court", "circuit court",
    "securities and exchange", "sec ", "fda ",
    "federal trade commission", "ftc ",
    # International organizations
    "world trade organization", "wto ", "imf ",
    "international monetary fund",
    "world bank", "european commission", "european parliament",
    "african union", "asean",
    # Military leadership
    "joint chiefs", "pentagon", "ministry of defense",
    "nato secretary", "commander in chief",
    # Legislative bodies
    "senate voted", "house voted", "congress passed",
    "parliament voted", "parliament passed",
    "bundestag", "lok sabha", "rajya sabha", "diet voted",
]

_AUTHORITY_TIER1_PATTERN: re.Pattern = re.compile(
    r"|".join(re.escape(t) for t in _AUTHORITY_TIER1),
    re.IGNORECASE,
)

_AUTHORITY_TIER2_PATTERN: re.Pattern = re.compile(
    r"|".join(re.escape(t) for t in _AUTHORITY_TIER2),
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Soft-news categories that get demoted (v4.0)
# ---------------------------------------------------------------------------
_SOFT_NEWS_CATEGORIES: frozenset[str] = frozenset({
    "sports", "entertainment", "culture", "lifestyle",
    "celebrity", "music", "film", "television", "gaming",
    "food", "travel", "fashion", "arts",
})


def _build_source_map(sources: list[dict]) -> dict[str, dict]:
    """
    Build a source lookup keyed by BOTH db_id (UUID) and slug.
    Fixes the UUID mismatch: articles have source_id as UUID, but
    sources.json uses slugs as the 'id' field.
    """
    source_map: dict[str, dict] = {}
    for s in sources:
        slug = s.get("id", "")
        if slug:
            source_map[slug] = s
        db_id = s.get("db_id", "")
        if db_id:
            source_map[db_id] = s
    return source_map


def _parse_timestamps(cluster_articles: list[dict]) -> list[datetime]:
    """Parse and cache timestamps from cluster articles (shared by recency + velocity)."""
    timestamps: list[datetime] = []
    for article in cluster_articles:
        pub = article.get("published_at", "")
        if not pub:
            continue
        try:
            if isinstance(pub, str):
                pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            else:
                pub_dt = pub
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            timestamps.append(pub_dt)
        except (ValueError, TypeError):
            continue
    return timestamps


def _source_coverage_score(
    cluster_articles: list[dict],
    source_map: dict[str, dict],
) -> float:
    """
    Score based on number of unique sources with diminishing returns.
    v4.0: tier-weighted counting — independent sources count 1.5x,
    international 1.2x, us_major 1.0x. This reduces inflation from
    wire service roundups (10 AP republications ≠ 10 independent reports).
    Going from 1→5 sources matters more than 15→20.
    Returns 0-100.
    """
    if not cluster_articles:
        return 0.0

    # Tier weights: independent editorial judgment is more valuable signal
    tier_weights = {"independent": 1.5, "international": 1.2, "us_major": 1.0}

    seen_sources: set[str] = set()
    weighted_count = 0.0
    for a in cluster_articles:
        sid = a.get("source_id", "")
        if sid and sid not in seen_sources:
            seen_sources.add(sid)
            src = source_map.get(sid, {})
            tier = src.get("tier", "us_major")
            weighted_count += tier_weights.get(tier, 1.0)

    # Diminishing returns: 100 * (1 - e^(-weighted_count/5))
    return 100.0 * (1.0 - math.exp(-weighted_count / 5.0))


def _perspective_diversity_score(
    cluster_articles: list[dict],
    source_map: dict[str, dict],
    bias_scores: list[dict] | None = None,
) -> float:
    """
    Score based on diversity of editorial perspectives covering a story.
    NOT a balance signal — this measures whether coverage comes from
    outlets with different editorial viewpoints, which is a weak proxy
    for "this story is important enough to cross editorial boundaries."

    Deliberately bias-blind in ranking: we do NOT reward left+right
    balance specifically. A story covered by 10 centrist outlets is
    just as valid as one covered by 5 left + 5 right. Political
    diversity of coverage belongs in the display layer (BiasLens),
    not in what stories we surface first.

    The consensus floor prevents a math artifact: many agreeing sources
    producing low stddev should not score lower than 2 disagreeing sources.
    Returns 0-100.
    """
    lean_values: list[float] = []

    # Prefer actual per-article bias scores if available
    if bias_scores:
        for bs in bias_scores:
            pl = bs.get("political_lean")
            if pl is not None:
                lean_values.append(float(pl))

    # Fall back to source baselines
    if not lean_values:
        for article in cluster_articles:
            sid = article.get("source_id", "")
            src = source_map.get(sid, {})
            baseline = str(src.get("political_lean_baseline", "center")).lower()
            lean_values.append(float(LEAN_NUMERIC.get(baseline, 50)))

    if not lean_values:
        return 10.0

    if len(lean_values) == 1:
        return 15.0

    stddev = _stddev(lean_values)
    lean_range = max(lean_values) - min(lean_values)

    # Combined: stddev (60% weight) + range (40% weight)
    stddev_score = min(100.0, (stddev / 20.0) * 100.0)
    range_score = min(100.0, (lean_range / 60.0) * 100.0)

    raw_score = stddev_score * 0.6 + range_score * 0.4

    # Consensus floor: many sources agreeing is authoritative, not boring.
    # Without this, AP+Reuters+BBC (all ~50) score near-zero because their
    # stddev is tiny. The floor is proportional to source count — more
    # sources agreeing = stronger consensus signal.
    if len(lean_values) >= 5 and stddev < 8.0:
        consensus_floor = min(45.0, len(lean_values) * 5.0)
        raw_score = max(raw_score, consensus_floor)
    elif len(lean_values) >= 3 and stddev < 5.0:
        consensus_floor = min(30.0, len(lean_values) * 5.0)
        raw_score = max(raw_score, consensus_floor)

    return raw_score


def _stddev(values: list[float]) -> float:
    """Population standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((v - mean) ** 2 for v in values) / len(values))


def _divergence_score(
    bias_scores: list[dict] | None = None,
) -> float:
    """
    Stories where sources disagree on framing are more newsworthy.
    v3: rebalanced to weight framing divergence higher than lean divergence.
    Returns 0-100.
    """
    if not bias_scores or len(bias_scores) < 2:
        return 0.0

    lean_values = [float(bs["political_lean"]) for bs in bias_scores if bs.get("political_lean") is not None]
    framing_values = [float(bs["framing"]) for bs in bias_scores if bs.get("framing") is not None]
    sens_values = [float(bs["sensationalism"]) for bs in bias_scores if bs.get("sensationalism") is not None]

    if len(lean_values) < 2:
        return 0.0

    # Lean range (reduced weight — spectrum signal already captures this)
    lean_range = max(lean_values) - min(lean_values)
    range_score = min(100.0, (lean_range / 60.0) * 100.0)

    framing_score = min(100.0, (_stddev(framing_values) / 25.0) * 100.0) if len(framing_values) >= 2 else 0.0
    sens_score = min(100.0, (_stddev(sens_values) / 20.0) * 100.0) if len(sens_values) >= 2 else 0.0

    # Framing-heavy weighting to reduce overlap with spectrum signal
    return range_score * 0.20 + framing_score * 0.50 + sens_score * 0.30


def _recency_score(
    timestamps: list[datetime],
    source_count: int = 1,
) -> float:
    """
    Score based on recency with adaptive decay.
    Breaking stories (gaining sources quickly) decay slower.
    Returns 0-100.
    """
    if not timestamps:
        return 15.0  # no timestamps = probably stale

    now = datetime.now(timezone.utc)
    most_recent = max(timestamps)
    earliest = min(timestamps)
    hours_old = max(0, (now - most_recent).total_seconds() / 3600.0)

    # Adaptive half-life: stories still gaining sources decay slower
    time_spread_hours = (most_recent - earliest).total_seconds() / 3600.0
    if source_count >= 4 and time_spread_hours < 6.0 and hours_old < 12.0:
        half_life = 18.0  # breaking news — slower decay
    elif source_count >= 3 and hours_old < 6.0:
        half_life = 15.0  # active story
    else:
        half_life = 12.0  # standard decay

    decay_rate = math.log(2) / half_life
    score = 100.0 * math.exp(-decay_rate * hours_old)

    return max(0.0, min(100.0, score))


def _story_maturity_score(
    timestamps: list[datetime],
    source_count: int,
) -> float:
    """
    v4.0: Combined recency + source depth signal that rewards stories
    that are both recent AND thoroughly reported.

    Formula: recency_raw * log2(1 + source_count) / log2(1 + 15)
    - A 1-hour-old story with 2 sources: high recency, low depth → moderate
    - An 18-hour-old story with 15 sources: lower recency, high depth → moderate
    - A 3-hour-old story with 10 sources: high recency, high depth → TOP

    The log2(1+15) ≈ 4.0 normalization keeps the score in 0-100 range.
    source_count is capped at 20 to prevent runaway from wire roundups.

    Returns 0-100.
    """
    recency = _recency_score(timestamps, source_count)

    # Cap source count to prevent wire roundup inflation
    effective_sources = min(source_count, 20)

    # Depth multiplier: log curve with diminishing returns
    # log2(1+1)=1.0, log2(1+3)=2.0, log2(1+7)=3.0, log2(1+15)=4.0
    max_depth = math.log2(1 + 15)  # ≈ 4.0
    depth_mult = math.log2(1 + effective_sources) / max_depth

    # Combined: recency weighted by depth
    # Pure recency contributes 40% floor (a fresh story with 1 source still ranks)
    # Depth boost contributes up to 60% additional
    score = recency * (0.40 + 0.60 * depth_mult)

    return max(0.0, min(100.0, score))


def _factual_density_score(
    bias_scores: list[dict] | None = None,
) -> float:
    """Average factual rigor across the cluster. Returns 0-100."""
    if not bias_scores:
        return 40.0
    rigor_values = [bs["factual_rigor"] for bs in bias_scores if bs.get("factual_rigor") is not None]
    if not rigor_values:
        return 40.0
    return sum(rigor_values) / len(rigor_values)


def _geographic_impact_score(cluster_articles: list[dict]) -> float:
    """
    Score based on geographic scope via NER.
    v4.0: geopolitically weighted — G20/P5 nations score 3x, mid-tier 2x,
    others 1x. Prevents "5 small countries" beating "US + China".
    v3.1: runs NER on titles first (fast). Only processes full text
    if title-only NER finds fewer than 2 GPEs.
    Returns 0-100.
    """
    nlp = get_nlp()

    countries_mentioned: set[str] = set()
    global_keyword_count = 0

    # Phase 1: titles only (fast — typically <100 chars each)
    title_text = " ".join(
        (a.get("title", "") or "") for a in cluster_articles[:10]
    )
    title_lower = title_text.lower()

    doc = nlp(title_text)
    for ent in doc.ents:
        if ent.label_ == "GPE":
            countries_mentioned.add(ent.text.lower())

    for keyword in GLOBAL_KEYWORDS:
        if keyword in title_lower:
            global_keyword_count += 1

    # Phase 2: full text only if titles didn't find enough signal
    if len(countries_mentioned) < 2 and global_keyword_count < 2:
        for article in cluster_articles[:5]:
            full_text = (article.get("full_text", "") or "")[:1500]
            if not full_text:
                continue
            ft_lower = full_text.lower()
            ft_doc = nlp(full_text)
            for ent in ft_doc.ents:
                if ent.label_ == "GPE":
                    countries_mentioned.add(ent.text.lower())
            for keyword in GLOBAL_KEYWORDS:
                if keyword in ft_lower:
                    global_keyword_count += 1

    # v4.0: geopolitically weighted scoring
    geo_weighted = 0.0
    for country in countries_mentioned:
        geo_weighted += _GEOPOLITICAL_WEIGHT.get(country, 1.0)

    # Weighted score: 10 points per weight unit (G20 country = 30pts)
    geo_score = min(60.0, geo_weighted * 10.0)
    keyword_bonus = min(40.0, global_keyword_count * 5.0)

    return min(100.0, geo_score + keyword_bonus)


def _tier_diversity_score(
    cluster_articles: list[dict],
    source_map: dict[str, dict],
) -> float:
    """
    Coverage across source tiers, weighted by tier composition.

    v3.3: composition-aware scoring. The presence of us_major sources
    (AP, Reuters, NYT, CNN, WSJ, etc.) is a strong editorial consensus
    signal — major wire services only cover a story when it clears a
    high significance threshold. Simply counting tiers treated
    "3 niche independent outlets" the same as "us_major + international",
    which inflated scores for obscure-source clusters.

    New scores (0-100):
      us_major alone:              50  (up from 20)
      international alone:         30  (up from 20)
      independent alone:           15  (down from 20)
      us_major + international:    80  (up from 55)
      us_major + independent:      70  (up from 55)
      intl + independent:          50  (down from 55)
      all 3 tiers:                100  (unchanged)

    Returns 0-100.
    """
    tiers_covered: set[str] = set()
    for article in cluster_articles:
        sid = article.get("source_id", "")
        src = source_map.get(sid, {})
        tier = src.get("tier", "")
        if tier:
            tiers_covered.add(tier)

    has_major = "us_major" in tiers_covered
    has_intl = "international" in tiers_covered
    has_independent = "independent" in tiers_covered

    if has_major and has_intl and has_independent:
        return 100.0
    if has_major and has_intl:
        return 80.0
    if has_major and has_independent:
        return 70.0
    if has_major:
        return 50.0
    if has_intl and has_independent:
        return 50.0
    if has_intl:
        return 30.0
    if has_independent:
        return 15.0
    return 0.0


def _coverage_velocity_score(
    cluster_articles: list[dict],
    timestamps: list[datetime],
    window_hours: float = 6.0,
) -> tuple[float, int]:
    """
    Normalized velocity score + raw count.
    v3.1: reuses pre-parsed timestamps instead of re-parsing.
    Returns (score 0-100, raw_velocity int).
    """
    now = datetime.now(timezone.utc)
    recent_sources: set[str] = set()

    for article, ts in zip(cluster_articles, timestamps):
        hours_ago = (now - ts).total_seconds() / 3600.0
        if hours_ago <= window_hours:
            recent_sources.add(article.get("source_id", ""))

    # Also check articles without parsed timestamps (best-effort)
    if len(timestamps) < len(cluster_articles):
        for article in cluster_articles[len(timestamps):]:
            pub = article.get("published_at", "")
            if not pub:
                continue
            try:
                if isinstance(pub, str):
                    pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                else:
                    pub_dt = pub
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
                if (now - pub_dt).total_seconds() / 3600.0 <= window_hours:
                    recent_sources.add(article.get("source_id", ""))
            except (ValueError, TypeError):
                continue

    velocity = len(recent_sources)
    # Diminishing returns: 100 * (1 - e^(-velocity/4))
    score = 100.0 * (1.0 - math.exp(-velocity / 4.0))
    return score, velocity


def _consequentiality_score(cluster_articles: list[dict]) -> float:
    """
    Score based on presence of outcome/action verbs that signal real-world
    impact. Uses pre-compiled regex with word boundaries for accuracy.

    v4.0: High-authority phrase floor — phrases like "declared war",
    "martial law", "supreme court ruled" set a floor of 70 regardless
    of regular lexicon matches. Major events can't score low.

    Returns 0-100.
    """
    unique_verbs: set[str] = set()
    total_hits = 0
    has_high_authority = False

    for article in cluster_articles[:10]:
        title = (article.get("title", "") or "")
        summary = (article.get("summary", "") or "")
        # Weight title 3x — consequentiality in headlines is a strong signal
        text = f"{title} {title} {title} {summary}"

        # Check high-authority phrases first (v4.0).
        # Also checks the supplemental EO pattern for natural word order
        # ("signed the executive order") which cannot be expressed via
        # re.escape() in the main list. (Priority H1 fix)
        if not has_high_authority and (
            _HIGH_AUTHORITY_PATTERN.search(text)
            or _HIGH_AUTHORITY_EO_PATTERN.search(text)
        ):
            has_high_authority = True

        matches = _CONSEQUENTIALITY_PATTERN.findall(text)
        for m in matches:
            unique_verbs.add(m.lower())
            total_hits += 1

    if not unique_verbs and not has_high_authority:
        return 0.0

    # Reward both breadth (unique verbs) and depth (total hits)
    breadth = min(100.0, len(unique_verbs) * 20.0)  # 5 unique verbs = 100
    depth = min(100.0, total_hits * 5.0)  # 20 hits = 100

    score = breadth * 0.6 + depth * 0.4

    # v4.0: high-authority floor — these events are intrinsically consequential
    if has_high_authority:
        score = max(score, 70.0)

    return score


def _institutional_authority_score(cluster_articles: list[dict]) -> float:
    """
    v4.0: Score based on the institutional authority of the actors/subjects
    in the story. A Federal Reserve rate decision or Supreme Court ruling
    carries intrinsic front-page weight regardless of source count.

    Tier 1 (80-100): heads of state, supreme courts, central banks,
        UN Security Council, constitutional bodies.
    Tier 2 (40-70): cabinet ministers, federal courts, major treaty orgs,
        legislative body votes.

    Matches against titles and summaries of cluster articles.
    Multiple tier matches boost the score (a story about the President
    AND the Supreme Court scores higher than either alone).

    Returns 0-100.
    """
    tier1_hits = 0
    tier2_hits = 0

    for article in cluster_articles[:10]:
        title = (article.get("title", "") or "")
        summary = (article.get("summary", "") or "")
        text = f"{title} {title} {summary}"  # weight title 2x

        tier1_matches = _AUTHORITY_TIER1_PATTERN.findall(text)
        tier2_matches = _AUTHORITY_TIER2_PATTERN.findall(text)
        tier1_hits += len(set(m.lower() for m in tier1_matches))
        tier2_hits += len(set(m.lower() for m in tier2_matches))

    if tier1_hits == 0 and tier2_hits == 0:
        return 0.0

    # Tier 1 base: 80 + up to 20 for multiple tier1 matches
    if tier1_hits > 0:
        tier1_score = min(100.0, 80.0 + (tier1_hits - 1) * 10.0)
    else:
        tier1_score = 0.0

    # Tier 2 base: 40 + up to 30 for multiple tier2 matches
    if tier2_hits > 0:
        tier2_score = min(70.0, 40.0 + (tier2_hits - 1) * 10.0)
    else:
        tier2_score = 0.0

    # Combined: tier1 dominates, tier2 adds a bonus
    if tier1_hits > 0 and tier2_hits > 0:
        return min(100.0, tier1_score + tier2_score * 0.2)
    return max(tier1_score, tier2_score)


def compute_coverage_velocity(
    cluster_articles: list[dict],
    window_hours: float = 6.0,
) -> int:
    """
    Count how many sources were added within the last N hours.
    Public API — used by main.py directly for DB storage.
    """
    now = datetime.now(timezone.utc)
    recent_sources: set[str] = set()

    for article in cluster_articles:
        pub = article.get("published_at", "")
        if not pub:
            continue
        try:
            if isinstance(pub, str):
                pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            else:
                pub_dt = pub
            if pub_dt.tzinfo is None:
                pub_dt = pub_dt.replace(tzinfo=timezone.utc)
            hours_ago = (now - pub_dt).total_seconds() / 3600.0
            if hours_ago <= window_hours:
                recent_sources.add(article.get("source_id", ""))
        except (ValueError, TypeError):
            continue

    return len(recent_sources)


def rank_importance(
    cluster_articles: list[dict],
    sources: list[dict],
    bias_scores: list[dict] | None = None,
    cluster_confidence: float = 1.0,
    category: str | None = None,
) -> dict:
    """
    Score the importance of a story cluster for feed ranking.

    v4.0 formula: 10 signals with confidence multiplier + 3 gates.
    Optimized: source map built once, timestamps parsed once, NER two-phase.

    Args:
        cluster_articles: List of article dicts belonging to this cluster,
            each with: source_id, published_at, full_text, title.
        sources: Full list of source dicts with: id, db_id, tier,
            political_lean_baseline.
        bias_scores: Optional list of per-article bias score dicts with:
            political_lean, sensationalism, opinion_fact, factual_rigor,
            framing, confidence.
        cluster_confidence: Confidence across cluster articles (0-1).
            Low-confidence clusters get discounted.
        category: Optional category label (e.g., "sports", "politics").
            Used for soft-news gate.

    Returns:
        Dict with:
            importance_score: float 0-100
            divergence_score: float 0-100
            coverage_velocity: int
            headline_rank: float 0-100
            component_scores: dict of individual signal scores
    """
    if not cluster_articles:
        return {
            "importance_score": 0.0,
            "divergence_score": 0.0,
            "coverage_velocity": 0,
            "headline_rank": 0.0,
            "component_scores": {},
        }

    # Build shared lookups once
    source_map = _build_source_map(sources)
    timestamps = _parse_timestamps(cluster_articles)
    source_count = len({a.get("source_id", "") for a in cluster_articles})

    # Compute all sub-scores (shared source_map + timestamps)
    coverage = _source_coverage_score(cluster_articles, source_map)
    spectrum = _perspective_diversity_score(cluster_articles, source_map, bias_scores)
    divergence = _divergence_score(bias_scores)
    factual = _factual_density_score(bias_scores)
    geographic = _geographic_impact_score(cluster_articles)
    tier_div = _tier_diversity_score(cluster_articles, source_map)
    velocity, velocity_raw = _coverage_velocity_score(
        cluster_articles, timestamps
    )
    consequentiality = _consequentiality_score(cluster_articles)
    authority = _institutional_authority_score(cluster_articles)
    maturity = _story_maturity_score(timestamps, source_count)

    # v4.0 weighted combination (10 signals, weights sum to 1.0)
    #
    # Key design: authority + maturity + tier_diversity = 37% of score.
    # These three signals together answer: "Is this about powerful
    # institutions (authority), thoroughly reported (maturity), and
    # validated by editorial consensus across tiers (tier_diversity)?"
    # That's the front-page test.
    #
    # Weight table (sum = 1.00):
    #   coverage:          0.20  (down from 0.27 — tier-weighted now)
    #   maturity:          0.16  (NEW — replaces recency 0.14 + velocity 0.09)
    #   tier_diversity:    0.13  (unchanged)
    #   consequentiality:  0.10  (unchanged)
    #   authority:         0.08  (NEW — institutional power signal)
    #   factual:           0.08  (up from 0.04 — rewards real journalism)
    #   divergence:        0.07  (unchanged)
    #   spectrum:          0.06  (down from 0.10 — partially redundant w/ tier)
    #   geographic:        0.06  (unchanged)
    #   velocity:          0.06  (retained as independent breaking-news signal)
    headline_rank = (
        coverage * 0.20
        + maturity * 0.16
        + tier_div * 0.13
        + consequentiality * 0.10
        + authority * 0.08
        + factual * 0.08
        + divergence * 0.07
        + spectrum * 0.06
        + geographic * 0.06
        + velocity * 0.06
    )

    # Confidence multiplier: discount low-confidence clusters.
    # v3.3: softened curve — 0.65 + 0.35 * confidence.
    # Maps: 0.0→0.65, 0.5→0.825, 0.7→0.895, 1.0→1.0
    conf_mult = 0.65 + 0.35 * max(0.0, min(1.0, cluster_confidence))
    headline_rank *= conf_mult

    # Gate 1: Consequentiality gate — stories with zero consequentiality
    # score have no outcome/action verbs. Apply 0.82x multiplier.
    if consequentiality < 5.0:
        headline_rank *= 0.82

    # Gate 2: Soft-news category gate (v4.0) — sports/entertainment/culture
    # stories get demoted. This is belt-and-suspenders with the
    # consequentiality gate — sports stories DO contain consequential verbs
    # ("won", "defeated") but are still soft news.
    if category and category.lower() in _SOFT_NEWS_CATEGORIES:
        headline_rank *= 0.78

    # Gate 3: Low factual rigor gate (v4.0) — clusters with poor sourcing
    # and attribution get penalized. Rewards AP/Reuters/ProPublica-style
    # reporting over speculative/unattributed coverage.
    if factual < 30.0:
        headline_rank *= 0.88

    headline_rank = round(max(0.0, min(100.0, headline_rank)), 2)

    return {
        "importance_score": headline_rank,
        "divergence_score": round(divergence, 2),
        "coverage_velocity": velocity_raw,
        "headline_rank": headline_rank,
        "component_scores": {
            "coverage": round(coverage, 2),
            "maturity": round(maturity, 2),
            "spectrum": round(spectrum, 2),
            "divergence": round(divergence, 2),
            "factual": round(factual, 2),
            "geographic": round(geographic, 2),
            "tier_diversity": round(tier_div, 2),
            "velocity": round(velocity, 2),
            "consequentiality": round(consequentiality, 2),
            "authority": round(authority, 2),
        },
    }
