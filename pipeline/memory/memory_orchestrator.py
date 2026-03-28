"""
News Memory Engine — Memory Orchestrator

Called after each pipeline run to:
1. Deactivate previous top stories
2. Identify the top 2 ranked clusters
3. Extract top 10 sources per cluster (tier-prioritized)
4. Create story_memory records (rank 1 and 2)
5. Denormalize is_top_story onto story_clusters for fast frontend queries

Graceful degradation: all operations are wrapped so failures don't crash
the main pipeline.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.supabase_client import supabase

# Number of top stories to track
TOP_STORY_COUNT = 2

# Max sources to poll per story (tier-prioritized)
MAX_SOURCES_PER_STORY = 10

# Tier priority for source selection
_TIER_PRIORITY = {"us_major": 0, "international": 1, "independent": 2}


def update_memory_after_pipeline_run(
    pipeline_run_id: str,
    clusters: list[dict],
    cluster_ids: list[str],
) -> dict:
    """
    Main entry point — called from main.py after clusters are stored.

    Args:
        pipeline_run_id: UUID of the current pipeline run.
        clusters: List of cluster dicts from the pipeline (with article data).
        cluster_ids: List of cluster UUIDs as stored in Supabase (parallel to clusters).

    Returns:
        Summary dict with status and details.
    """
    if not cluster_ids:
        return {"status": "skip", "reason": "no clusters"}

    # Step 1: Deactivate all previous top stories
    _deactivate_old_top_stories()

    # Step 2: Clear is_top_story on all clusters
    _clear_cluster_top_story_flags()

    # Step 3: Track top N stories (up to TOP_STORY_COUNT)
    tracked = []
    count = min(TOP_STORY_COUNT, len(clusters))

    for rank_idx in range(count):
        cluster = clusters[rank_idx]
        cluster_id = cluster_ids[rank_idx]
        headline = (cluster.get("title") or "Developing Story")[:500]
        category = cluster.get("category", "politics")

        # Select top 10 sources by tier priority
        source_slugs = _select_top_sources(cluster)

        # Create story_memory record
        memory_id = _create_story_memory(
            cluster_id=cluster_id,
            headline=headline,
            category=category,
            source_slugs=source_slugs,
            pipeline_run_id=pipeline_run_id,
            rank=rank_idx + 1,
        )

        # Denormalize onto the cluster row
        if memory_id:
            _denormalize_top_story(cluster_id, memory_id)

        tracked.append({
            "rank": rank_idx + 1,
            "headline": headline[:80],
            "source_count": len(source_slugs),
            "memory_id": memory_id,
        })

    # Step 4: Clean up old memories
    cleanup_old_memories()

    return {
        "status": "ok",
        "tracked_stories": tracked,
        "count": len(tracked),
    }


def _select_top_sources(cluster: dict) -> list[str]:
    """
    Extract top MAX_SOURCES_PER_STORY source slugs from a cluster's articles.
    Prioritizes by tier: us_major > international > independent.
    """
    # Collect slugs with their tier info from articles
    slug_tiers: dict[str, str] = {}
    for art in cluster.get("articles", []):
        slug = art.get("source_slug") or art.get("source_id", "")
        tier = art.get("source_tier", "independent")
        if slug and slug not in slug_tiers:
            slug_tiers[slug] = tier

    if not slug_tiers:
        return _extract_all_source_slugs(cluster)

    # Sort by tier priority (us_major first), then alphabetically
    sorted_slugs = sorted(
        slug_tiers.keys(),
        key=lambda s: (_TIER_PRIORITY.get(slug_tiers[s], 2), s),
    )

    return sorted_slugs[:MAX_SOURCES_PER_STORY]


def _extract_all_source_slugs(cluster: dict) -> list[str]:
    """Fallback: extract all unique source slugs from a cluster's articles."""
    slugs = set()
    for art in cluster.get("articles", []):
        slug = art.get("source_slug") or art.get("source_id", "")
        if slug:
            slugs.add(slug)
    return sorted(slugs)[:MAX_SOURCES_PER_STORY]


def _deactivate_old_top_stories() -> None:
    """Mark all active top stories as inactive."""
    try:
        supabase.table("story_memory").update({
            "is_top_story": False,
            "is_active": False,
            "deactivated_at": datetime.now(timezone.utc).isoformat(),
        }).eq("is_active", True).execute()
    except Exception as e:
        print(f"  [memory] Warning: failed to deactivate old top stories: {e}")


def _clear_cluster_top_story_flags() -> None:
    """Clear is_top_story on all story_clusters."""
    try:
        supabase.table("story_clusters").update({
            "is_top_story": False,
            "story_memory_id": None,
            "live_update_count": 0,
            "last_live_update_at": None,
        }).eq("is_top_story", True).execute()
    except Exception as e:
        print(f"  [memory] Warning: failed to clear cluster top story flags: {e}")


def _create_story_memory(
    cluster_id: str,
    headline: str,
    category: str,
    source_slugs: list[str],
    pipeline_run_id: str,
    rank: int = 1,
) -> str | None:
    """Create a new story_memory record. Returns the memory ID or None."""
    try:
        result = supabase.table("story_memory").insert({
            "cluster_id": cluster_id,
            "headline": headline,
            "category": category,
            "source_slugs": source_slugs,
            "source_count": len(source_slugs),
            "is_top_story": True,
            "is_active": True,
            "rank": rank,
            "pipeline_run_id": pipeline_run_id,
            "activated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        if result.data:
            return result.data[0]["id"]
    except Exception as e:
        print(f"  [memory] Error creating story_memory (rank {rank}): {e}")
    return None


def _denormalize_top_story(cluster_id: str, memory_id: str) -> None:
    """Set is_top_story and story_memory_id on the cluster row."""
    try:
        supabase.table("story_clusters").update({
            "is_top_story": True,
            "story_memory_id": memory_id,
        }).eq("id", cluster_id).execute()
    except Exception as e:
        print(f"  [memory] Warning: failed to denormalize top story: {e}")


def cleanup_old_memories(ttl_hours: int = 48) -> dict:
    """Delete story_memory records older than ttl_hours."""
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=ttl_hours)).isoformat()
    deleted = 0
    try:
        # First clean up live_updates for old memories
        old = supabase.table("story_memory").select("id").lt(
            "created_at", cutoff
        ).execute()
        if old.data:
            old_ids = [r["id"] for r in old.data]
            for mid in old_ids:
                supabase.table("live_updates").delete().eq(
                    "story_memory_id", mid
                ).execute()
            supabase.table("story_memory").delete().in_("id", old_ids).execute()
            deleted = len(old_ids)
    except Exception as e:
        print(f"  [memory] Warning: cleanup failed: {e}")
    return {"deleted": deleted}
