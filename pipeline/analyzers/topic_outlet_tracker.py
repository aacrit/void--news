"""
Per-Topic Per-Outlet Tracking for the void --news bias engine (Axis 6).

Tracks how each source's bias scores vary by topic category using
exponential moving averages. An outlet's political lean may differ
significantly between economics coverage and social issues coverage.

Uses EMA (alpha=0.3) to weight recent articles more heavily while
retaining historical signal.

No LLM API calls -- pure arithmetic on existing bias scores.
"""

from collections import defaultdict
from datetime import datetime, timezone


# EMA smoothing factor: 0.3 weights recent articles ~30%, history ~70%
EMA_ALPHA = 0.3


def _ema(old_avg: float, new_value: float, alpha: float = EMA_ALPHA) -> float:
    """Compute exponential moving average."""
    return alpha * new_value + (1.0 - alpha) * old_avg


def update_source_topic_lean(
    articles_with_scores: list[dict],
    supabase_client,
) -> dict:
    """
    Update per-source per-topic lean tracking.

    Each article dict should have:
        source_id, category, political_lean, sensationalism, opinion_fact

    Uses EMA to blend new scores with existing averages.
    Returns stats dict with counts.
    """
    if not articles_with_scores:
        return {"groups_processed": 0, "rows_upserted": 0}

    # Step 1: Group articles by (source_id, category)
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for art in articles_with_scores:
        source_id = art.get("source_id")
        category = art.get("category")
        if source_id and category:
            groups[(source_id, category)].append(art)

    if not groups:
        return {"groups_processed": 0, "rows_upserted": 0}

    # Step 2: Fetch existing rows for all (source_id, category) pairs
    # Build a lookup of existing data to avoid N+1 queries
    all_source_ids = list({k[0] for k in groups.keys()})
    existing_map: dict[tuple, dict] = {}

    try:
        # Fetch in chunks to avoid query size limits
        for i in range(0, len(all_source_ids), 50):
            chunk_ids = all_source_ids[i:i + 50]
            result = (
                supabase_client.table("source_topic_lean")
                .select("source_id,category,avg_lean,avg_sensationalism,avg_opinion,article_count")
                .in_("source_id", chunk_ids)
                .execute()
            )
            if result.data:
                for row in result.data:
                    key = (row["source_id"], row["category"])
                    existing_map[key] = row
    except Exception as e:
        # If table doesn't exist yet (migration not run), return gracefully
        if "does not exist" in str(e).lower() or "relation" in str(e).lower():
            print(f"    [info] source_topic_lean table not found; skipping tracking")
            return {"groups_processed": 0, "rows_upserted": 0, "error": "table_not_found"}
        raise

    # Step 3: Compute new averages using EMA and build upsert rows
    upsert_rows = []
    now = datetime.now(timezone.utc).isoformat()

    for (source_id, category), articles in groups.items():
        # Compute batch average for this group's new articles
        batch_lean = sum(a.get("political_lean", 50) for a in articles) / len(articles)
        batch_sens = sum(a.get("sensationalism", 10) for a in articles) / len(articles)
        batch_opin = sum(a.get("opinion_fact", 25) for a in articles) / len(articles)

        existing = existing_map.get((source_id, category))

        if existing and existing.get("article_count", 0) > 0:
            # EMA blend with existing averages
            new_lean = _ema(float(existing["avg_lean"]), batch_lean)
            new_sens = _ema(float(existing["avg_sensationalism"]), batch_sens)
            new_opin = _ema(float(existing["avg_opinion"]), batch_opin)
            new_count = existing["article_count"] + len(articles)
        else:
            # First time: use batch averages directly
            new_lean = batch_lean
            new_sens = batch_sens
            new_opin = batch_opin
            new_count = len(articles)

        upsert_rows.append({
            "source_id": source_id,
            "category": category,
            "avg_lean": round(new_lean, 2),
            "avg_sensationalism": round(new_sens, 2),
            "avg_opinion": round(new_opin, 2),
            "article_count": new_count,
            "last_updated": now,
        })

    # Step 4: Upsert results in chunks
    rows_upserted = 0
    try:
        for i in range(0, len(upsert_rows), 100):
            chunk = upsert_rows[i:i + 100]
            supabase_client.table("source_topic_lean").upsert(
                chunk, on_conflict="source_id,category"
            ).execute()
            rows_upserted += len(chunk)
    except Exception as e:
        print(f"    [warn] source_topic_lean upsert failed: {e}")
        return {
            "groups_processed": len(groups),
            "rows_upserted": rows_upserted,
            "error": str(e),
        }

    return {
        "groups_processed": len(groups),
        "rows_upserted": rows_upserted,
    }
