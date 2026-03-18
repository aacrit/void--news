"""
Importance/impact ranker v2 for the void --news pipeline.

Scores story clusters by importance for feed ordering on the homepage.
Higher scores appear first in the news feed.

Uses rule-based heuristics (no LLM API calls) with 7 signals:
    - Source coverage breadth (25%) — diminishing returns curve
    - Cross-spectrum coverage (20%) — continuous lean spread
    - Divergence score (15%) — how much sources disagree
    - Recency with adaptive decay (15%) — breaking news decays slower
    - Factual density (10%) — average factual rigor across cluster
    - Geographic impact via NER (10%)
    - Tier diversity (5%) — coverage across us_major/intl/independent
"""

import math
import re
from datetime import datetime, timezone

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
    "european union", "nato", "who",
    "multiple countries", "several nations", "across borders",
    "global economy", "world economy", "pandemic", "epidemic",
]


def _source_coverage_score(
    cluster_articles: list[dict],
    sources: list[dict],
) -> float:
    """
    Score based on number of unique sources with diminishing returns.
    Going from 1→5 sources matters more than 15→20.
    Returns 0-100.
    """
    if not cluster_articles:
        return 0.0

    source_ids = list({a.get("source_id", "") for a in cluster_articles})
    count = len(source_ids)

    # Diminishing returns: 100 * (1 - e^(-count/5))
    # 1 source ≈ 18, 3 ≈ 45, 5 ≈ 63, 10 ≈ 86, 15 ≈ 95
    return 100.0 * (1.0 - math.exp(-count / 5.0))


def _cross_spectrum_score(
    cluster_articles: list[dict],
    sources: list[dict],
    bias_scores: list[dict] | None = None,
) -> float:
    """
    Score based on actual political lean spread across sources.
    Uses per-article bias scores when available, falls back to source baselines.
    Returns 0-100.
    """
    source_map = {s.get("id", ""): s for s in sources}

    # Collect lean values
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

    # Standard deviation of lean values — higher = more diverse coverage
    mean_lean = sum(lean_values) / len(lean_values)
    variance = sum((v - mean_lean) ** 2 for v in lean_values) / len(lean_values)
    stddev = math.sqrt(variance)

    # stddev of 0 = single perspective, 20+ = very diverse
    # Also consider range
    lean_range = max(lean_values) - min(lean_values)

    # Combined: stddev (60% weight) + range (40% weight)
    stddev_score = min(100.0, (stddev / 20.0) * 100.0)
    range_score = min(100.0, (lean_range / 60.0) * 100.0)

    return stddev_score * 0.6 + range_score * 0.4


def _divergence_score(
    bias_scores: list[dict] | None = None,
) -> float:
    """
    Stories where sources disagree on framing/lean are more newsworthy.
    High framing spread + high lean spread = high divergence.
    Returns 0-100.
    """
    if not bias_scores or len(bias_scores) < 2:
        return 0.0

    lean_values = [float(bs["political_lean"]) for bs in bias_scores if bs.get("political_lean") is not None]
    framing_values = [float(bs["framing"]) for bs in bias_scores if bs.get("framing") is not None]

    if len(lean_values) < 2:
        return 0.0

    # Lean range
    lean_range = max(lean_values) - min(lean_values)
    range_score = min(100.0, (lean_range / 60.0) * 100.0)

    # Lean stddev
    lean_mean = sum(lean_values) / len(lean_values)
    lean_var = sum((v - lean_mean) ** 2 for v in lean_values) / len(lean_values)
    lean_stddev = math.sqrt(lean_var)
    spread_score = min(100.0, (lean_stddev / 20.0) * 100.0)

    # Framing stddev
    framing_score = 0.0
    if len(framing_values) >= 2:
        framing_mean = sum(framing_values) / len(framing_values)
        framing_var = sum((v - framing_mean) ** 2 for v in framing_values) / len(framing_values)
        framing_stddev = math.sqrt(framing_var)
        framing_score = min(100.0, (framing_stddev / 25.0) * 100.0)

    return range_score * 0.4 + spread_score * 0.3 + framing_score * 0.3


def _recency_score(
    cluster_articles: list[dict],
    source_count: int = 1,
) -> float:
    """
    Score based on recency with adaptive decay.
    Breaking stories (gaining sources quickly) decay slower.
    Returns 0-100.
    """
    now = datetime.now(timezone.utc)

    # Find most recent and earliest articles
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

    if not timestamps:
        return 30.0

    most_recent = max(timestamps)
    earliest = min(timestamps)
    hours_old = max(0, (now - most_recent).total_seconds() / 3600.0)

    # Adaptive half-life: stories still gaining sources decay slower
    # Base half-life: 12 hours
    # If sources added recently (time spread < 6hrs and count > 3), use 18hr half-life
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
    """
    Average factual rigor across the cluster.
    Well-sourced stories should rank higher.
    Returns 0-100.
    """
    if not bias_scores:
        return 40.0  # neutral default

    rigor_values = [bs["factual_rigor"] for bs in bias_scores if bs.get("factual_rigor") is not None]
    if not rigor_values:
        return 40.0

    return sum(rigor_values) / len(rigor_values)


def _geographic_impact_score(cluster_articles: list[dict]) -> float:
    """
    Score based on geographic scope via NER.
    Mentions of multiple countries/regions = higher impact.
    Returns 0-100.
    """
    nlp = _get_nlp()

    countries_mentioned: set[str] = set()
    global_keyword_count = 0

    for article in cluster_articles[:10]:
        title = article.get("title", "") or ""
        full_text = article.get("full_text", "") or ""
        text = f"{title} {full_text[:2000]}"

        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ == "GPE":
                countries_mentioned.add(ent.text.lower())

        text_lower = text.lower()
        for keyword in GLOBAL_KEYWORDS:
            if keyword in text_lower:
                global_keyword_count += 1

    geo_count = len(countries_mentioned)
    geo_score = min(60.0, geo_count * 10.0)
    keyword_bonus = min(40.0, global_keyword_count * 5.0)

    return min(100.0, geo_score + keyword_bonus)


def _tier_diversity_score(
    cluster_articles: list[dict],
    sources: list[dict],
) -> float:
    """
    Separate signal for coverage across all 3 source tiers.
    Returns 0-100.
    """
    source_map = {s.get("id", ""): s for s in sources}

    tiers_covered = set()
    for article in cluster_articles:
        sid = article.get("source_id", "")
        src = source_map.get(sid, {})
        tier = src.get("tier", "")
        if tier:
            tiers_covered.add(tier)

    tier_count = len(tiers_covered)
    if tier_count >= 3:
        return 100.0
    elif tier_count == 2:
        return 55.0
    elif tier_count == 1:
        return 20.0
    return 0.0


def compute_coverage_velocity(
    cluster_articles: list[dict],
    window_hours: float = 6.0,
) -> int:
    """
    Count how many sources were added within the last N hours.
    High velocity = breaking/trending story.
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
) -> dict:
    """
    Score the importance of a story cluster for feed ranking.

    Args:
        cluster_articles: List of article dicts belonging to this cluster,
            each with: source_id, published_at, full_text, title.
        sources: Full list of source dicts with: id, tier,
            political_lean_baseline.
        bias_scores: Optional list of per-article bias score dicts with:
            political_lean, sensationalism, opinion_fact, factual_rigor, framing.

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

    source_count = len({a.get("source_id", "") for a in cluster_articles})

    # Compute all sub-scores
    coverage = _source_coverage_score(cluster_articles, sources)
    spectrum = _cross_spectrum_score(cluster_articles, sources, bias_scores)
    divergence = _divergence_score(bias_scores)
    recency = _recency_score(cluster_articles, source_count)
    factual = _factual_density_score(bias_scores)
    geographic = _geographic_impact_score(cluster_articles)
    tier_div = _tier_diversity_score(cluster_articles, sources)
    velocity = compute_coverage_velocity(cluster_articles)

    # Weighted combination (7 signals)
    headline_rank = (
        coverage * 0.25
        + spectrum * 0.20
        + divergence * 0.15
        + recency * 0.15
        + factual * 0.10
        + geographic * 0.10
        + tier_div * 0.05
    )

    headline_rank = round(max(0.0, min(100.0, headline_rank)), 2)

    # Legacy importance_score (backward compatible with existing queries)
    importance_score = headline_rank

    return {
        "importance_score": importance_score,
        "divergence_score": round(divergence, 2),
        "coverage_velocity": velocity,
        "headline_rank": headline_rank,
        "component_scores": {
            "coverage": round(coverage, 2),
            "spectrum": round(spectrum, 2),
            "divergence": round(divergence, 2),
            "recency": round(recency, 2),
            "factual": round(factual, 2),
            "geographic": round(geographic, 2),
            "tier_diversity": round(tier_div, 2),
        },
    }
