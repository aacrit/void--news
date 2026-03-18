"""
Importance/impact ranker for the void --news pipeline.

Scores story clusters by importance for feed ordering on the homepage.
Higher scores appear first in the news feed.

Uses rule-based heuristics (no LLM API calls):
    - Source count: more sources covering a story = more important
    - Source tier diversity: coverage across tiers (US major + international
      + independent) indicates broader significance
    - Recency: newer stories score higher (time decay function)
    - Word count average: longer articles suggest deeper coverage
    - Named entity significance: mentions of heads of state, major
      organizations, or conflict zones boost importance
    - Category weight: Conflict and Politics get slight boost over Sports
    - Update velocity: stories gaining new articles quickly = developing

Phase 2 implementation.
"""


def rank_importance(cluster: dict, articles: list[dict]) -> float:
    """
    Score the importance of a story cluster for feed ranking.

    Args:
        cluster: Dict with keys: title, summary, source_count,
            first_published, article_ids.
        articles: List of article dicts belonging to this cluster,
            each with: source_id, published_at, word_count, full_text.

    Returns:
        Float score 0.0-1.0 (higher = more important).
        Used to order stories in the homepage feed.
    """
    raise NotImplementedError("Phase 2: Importance ranking not yet implemented.")
