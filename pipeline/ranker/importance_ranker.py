"""
Importance/impact ranker for the void --news pipeline.

Scores story clusters by importance for feed ordering on the homepage.
Higher scores appear first in the news feed.

Uses rule-based heuristics (no LLM API calls):
    - Source coverage breadth (40%)
    - Editorial weight / cross-spectrum coverage (25%)
    - Recency with exponential decay (20%)
    - Geographic impact via NER (15%)
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
# Source baseline lean mapping (string to numeric for spectrum analysis)
# ---------------------------------------------------------------------------
LEAN_MAP: dict[str, str] = {
    "far-left": "left", "left": "left", "center-left": "left",
    "center": "center",
    "center-right": "right", "right": "right", "far-right": "right",
    "varies": "center",
}

# ---------------------------------------------------------------------------
# Tier weights
# ---------------------------------------------------------------------------
TIER_WEIGHTS: dict[str, float] = {
    "us_major": 1.0,
    "international": 1.0,
    "independent": 1.0,
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
    Score based on number of unique sources and tier diversity.
    Returns 0-100.
    """
    if not cluster_articles:
        return 0.0

    # Build source lookup
    source_map = {s.get("id", ""): s for s in sources}

    source_ids = list({a.get("source_id", "") for a in cluster_articles})
    source_count = len(source_ids)

    # Base score from source count: 1 source = 10, 5 = 50, 10+ = max
    count_score = min(100.0, source_count * 10.0)

    # Tier diversity bonus
    tiers_covered = set()
    for sid in source_ids:
        src = source_map.get(sid, {})
        tier = src.get("tier", "")
        if tier:
            tiers_covered.add(tier)

    # Having coverage from all 3 tiers = full bonus
    tier_count = len(tiers_covered)
    if tier_count >= 3:
        tier_bonus = 20.0
    elif tier_count == 2:
        tier_bonus = 10.0
    else:
        tier_bonus = 0.0

    return min(100.0, count_score + tier_bonus)


def _editorial_weight_score(
    cluster_articles: list[dict],
    sources: list[dict],
) -> float:
    """
    Score based on cross-spectrum coverage.
    Left + center + right all covering it = maximum boost.
    Returns 0-100.
    """
    source_map = {s.get("id", ""): s for s in sources}

    spectrum_covered: set[str] = set()
    for article in cluster_articles:
        sid = article.get("source_id", "")
        src = source_map.get(sid, {})
        baseline = str(src.get("political_lean_baseline", "center")).lower()
        spectrum = LEAN_MAP.get(baseline, "center")
        spectrum_covered.add(spectrum)

    # Full spectrum coverage (left + center + right) = 100
    if len(spectrum_covered) >= 3:
        return 100.0
    elif len(spectrum_covered) == 2:
        return 60.0
    elif len(spectrum_covered) == 1:
        return 30.0
    return 10.0


def _recency_score(cluster_articles: list[dict]) -> float:
    """
    Score based on recency with exponential decay.
    Articles from last 6 hours score highest.
    Returns 0-100.
    """
    now = datetime.now(timezone.utc)

    # Find the most recent article
    most_recent = None
    for article in cluster_articles:
        pub = article.get("published_at", "")
        if not pub:
            continue
        try:
            if isinstance(pub, str):
                # Handle ISO format with or without timezone
                pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            else:
                pub_dt = pub
            if most_recent is None or pub_dt > most_recent:
                most_recent = pub_dt
        except (ValueError, TypeError):
            continue

    if most_recent is None:
        return 30.0  # unknown recency, moderate score

    # Ensure timezone-aware
    if most_recent.tzinfo is None:
        most_recent = most_recent.replace(tzinfo=timezone.utc)

    hours_old = (now - most_recent).total_seconds() / 3600.0
    hours_old = max(0, hours_old)

    # Exponential decay: half-life of 12 hours
    # score = 100 * exp(-0.0578 * hours)  (ln(2)/12 ~= 0.0578)
    decay_rate = math.log(2) / 12.0
    score = 100.0 * math.exp(-decay_rate * hours_old)

    return max(0.0, min(100.0, score))


def _geographic_impact_score(cluster_articles: list[dict]) -> float:
    """
    Score based on geographic scope via NER.
    Mentions of multiple countries/regions = higher impact.
    Returns 0-100.
    """
    nlp = _get_nlp()

    countries_mentioned: set[str] = set()
    global_keyword_count = 0

    for article in cluster_articles[:10]:  # limit for performance
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

    # Score based on geographic diversity
    geo_count = len(countries_mentioned)
    geo_score = min(60.0, geo_count * 10.0)

    # Global keyword bonus
    keyword_bonus = min(40.0, global_keyword_count * 5.0)

    return min(100.0, geo_score + keyword_bonus)


def rank_importance(
    cluster_articles: list[dict],
    sources: list[dict],
) -> float:
    """
    Score the importance of a story cluster for feed ranking.

    Args:
        cluster_articles: List of article dicts belonging to this cluster,
            each with: source_id, published_at, full_text, title.
        sources: Full list of source dicts with: id, tier,
            political_lean_baseline.

    Returns:
        Float score 0-100 (higher = more important).
    """
    if not cluster_articles:
        return 0.0

    # Sub-scores
    coverage = _source_coverage_score(cluster_articles, sources)
    editorial = _editorial_weight_score(cluster_articles, sources)
    recency = _recency_score(cluster_articles)
    geographic = _geographic_impact_score(cluster_articles)

    # Weighted combination (matches spec)
    weighted = (
        coverage * 0.40
        + editorial * 0.25
        + recency * 0.20
        + geographic * 0.15
    )

    return round(max(0.0, min(100.0, weighted)), 2)
