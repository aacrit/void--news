"""
Importance/impact ranker v3.3 for the void --news pipeline.

Scores story clusters by importance for feed ordering on the homepage.
Higher scores appear first in the news feed.

Uses rule-based heuristics (no LLM API calls) with 9 signals:
    - Source coverage breadth (27%) — diminishing returns curve; up from 25%
    - Recency with adaptive decay (14%) — breaking news decays slower; down from 15%
    - Perspective diversity (10%) — editorial viewpoint spread (bias-blind); down from 12%
    - Coverage velocity (9%) — sources added in recent window; down from 10%
    - Consequentiality (10%) — outcome/action verbs; gate: 0-score stories get 0.82x multiplier
    - Divergence score (7%) — framing-weighted source disagreement; down from 8%
    - Geographic impact via NER (6%) — down from 8%
    - Tier diversity (13%) — now composition-aware: us_major presence explicitly rewarded; up from 8%
    - Factual density (4%) — average factual rigor across cluster; unchanged

Design principle: ranking is BIAS-BLIND. Bias analysis belongs in the
display layer (BiasLens, Sigil, Deep Dive), not in story selection.
We never boost or penalize a story for its political lean distribution.

v3.3 calibration changes (2026-03-20):
    - Tier diversity weight: 8% → 13% (primary fix for editorial consensus alignment)
    - Tier scoring is now composition-aware: us_major presence gets explicit reward
      (us_major only: 20 → 50; us_major+other: 55 → 70-80)
    - Coverage breadth: 25% → 27%
    - Consequentiality gate: stories with zero consequentiality score (no outcome/action
      verbs — entertainment, celebrity, sports fluff) receive a 0.82x multiplier on
      final score. Fixes sports/entertainment floating into top 10 on recency+velocity.
    - Geographic impact: 8% → 6% (was overweighted vs editorial signal)
    - Redistributed 4pp from recency(1), perspective_div(2), velocity(1), divergence(1)
      to coverage(2) and tier_diversity(5). Weights still sum to 1.0.
    - Confidence multiplier softened: linear floor 0.4 → soft curve (0.65 + 0.35 * conf).
      Prevents high-source clusters from being crushed by poorly-scraped articles.
    - Topic diversity re-rank now per section (world/us) instead of per content_type.

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


def _source_coverage_score(cluster_articles: list[dict]) -> float:
    """
    Score based on number of unique sources with diminishing returns.
    Going from 1→5 sources matters more than 15→20.
    Returns 0-100.
    """
    if not cluster_articles:
        return 0.0

    count = len({a.get("source_id", "") for a in cluster_articles})

    # Diminishing returns: 100 * (1 - e^(-count/5))
    # 2 sources ≈ 33, 3 ≈ 45, 5 ≈ 63, 10 ≈ 86, 15 ≈ 95
    return 100.0 * (1.0 - math.exp(-count / 5.0))


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
    v3.1: runs NER on titles first (fast). Only processes full text
    if title-only NER finds fewer than 2 GPEs (avoids expensive NER
    on up to 20KB of text for already-geographic stories).
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

    geo_count = len(countries_mentioned)
    geo_score = min(60.0, geo_count * 10.0)
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
    Returns 0-100.
    """
    unique_verbs: set[str] = set()
    total_hits = 0

    for article in cluster_articles[:10]:
        title = (article.get("title", "") or "")
        summary = (article.get("summary", "") or "")
        # Weight title 3x — consequentiality in headlines is a strong signal
        text = f"{title} {title} {title} {summary}"

        matches = _CONSEQUENTIALITY_PATTERN.findall(text)
        for m in matches:
            unique_verbs.add(m.lower())
            total_hits += 1

    if not unique_verbs:
        return 0.0

    # Reward both breadth (unique verbs) and depth (total hits)
    breadth = min(100.0, len(unique_verbs) * 20.0)  # 5 unique verbs = 100
    depth = min(100.0, total_hits * 5.0)  # 20 hits = 100

    return breadth * 0.6 + depth * 0.4


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
) -> dict:
    """
    Score the importance of a story cluster for feed ranking.

    v3.1 formula: 9 signals with confidence multiplier.
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
    coverage = _source_coverage_score(cluster_articles)
    spectrum = _perspective_diversity_score(cluster_articles, source_map, bias_scores)
    divergence = _divergence_score(bias_scores)
    recency = _recency_score(timestamps, source_count)
    factual = _factual_density_score(bias_scores)
    geographic = _geographic_impact_score(cluster_articles)
    tier_div = _tier_diversity_score(cluster_articles, source_map)
    velocity, velocity_raw = _coverage_velocity_score(
        cluster_articles, timestamps
    )
    consequentiality = _consequentiality_score(cluster_articles)

    # v3.3 weighted combination (9 signals, weights sum to 1.0)
    # Key changes from v3.2:
    #   coverage: 0.25 → 0.27  (+2pp)
    #   tier_div: 0.08 → 0.13  (+5pp, PRIMARY FIX — us_major presence rewarded)
    #   recency:  0.15 → 0.14  (-1pp)
    #   spectrum: 0.12 → 0.10  (-2pp)
    #   velocity: 0.10 → 0.09  (-1pp)
    #   diverge:  0.08 → 0.07  (-1pp)
    #   geo:      0.08 → 0.06  (-2pp, was overweighted)
    headline_rank = (
        coverage * 0.27
        + recency * 0.14
        + spectrum * 0.10
        + velocity * 0.09
        + consequentiality * 0.10
        + divergence * 0.07
        + geographic * 0.06
        + tier_div * 0.13
        + factual * 0.04
    )

    # Confidence multiplier: discount low-confidence clusters.
    # v3.3: softened curve — 0.65 + 0.35 * confidence.
    # Maps: 0.0→0.65, 0.5→0.825, 0.7→0.895, 1.0→1.0
    # Previous linear multiplier (floor 0.4) was too aggressive: a 20-source
    # cluster with p25 confidence 0.5 got halved, losing to 4-source clusters
    # with higher confidence. The soft curve preserves the signal direction
    # while preventing high-source editorial consensus stories from being
    # crushed by a few poorly-scraped articles.
    conf_mult = 0.65 + 0.35 * max(0.0, min(1.0, cluster_confidence))
    headline_rank *= conf_mult

    # Consequentiality gate (v3.3): stories with zero consequentiality score
    # have no outcome/action verbs — they are entertainment, celebrity news,
    # or sports previews that should not surface above hard news via recency
    # or velocity alone. Apply a 0.82x multiplier to final score.
    # Threshold <5 instead of ==0 to handle minor false-negative matches.
    if consequentiality < 5.0:
        headline_rank *= 0.82

    headline_rank = round(max(0.0, min(100.0, headline_rank)), 2)

    return {
        "importance_score": headline_rank,
        "divergence_score": round(divergence, 2),
        "coverage_velocity": velocity_raw,
        "headline_rank": headline_rank,
        "component_scores": {
            "coverage": round(coverage, 2),
            "spectrum": round(spectrum, 2),
            "divergence": round(divergence, 2),
            "recency": round(recency, 2),
            "factual": round(factual, 2),
            "geographic": round(geographic, 2),
            "tier_diversity": round(tier_div, 2),
            "velocity": round(velocity, 2),
            "consequentiality": round(consequentiality, 2),
        },
    }
