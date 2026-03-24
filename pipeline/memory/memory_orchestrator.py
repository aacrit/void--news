"""
News Memory Engine — Memory Orchestrator

Called after each pipeline run to:
1. Deactivate the previous top story
2. Identify the new #1 ranked cluster
3. Extract its source slugs
4. Create/update a story_memory record
5. Denormalize is_top_story onto story_clusters for fast frontend queries

Graceful degradation: all operations are wrapped so failures don't crash
the main pipeline.
"""

import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.supabase_client import supabase


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

    # The top cluster is index 0 (clusters are sorted by headline_rank desc)
    top_cluster = clusters[0]
    top_cluster_id = cluster_ids[0]
    headline = (top_cluster.get("title") or "Developing Story")[:500]
    category = top_cluster.get("category", "politics")

    # Extract source slugs from the top cluster's articles
    source_slugs = _extract_source_slugs(top_cluster)

    # Step 1: Deactivate all previous top stories
    _deactivate_old_top_stories()

    # Step 2: Clear is_top_story on all clusters
    _clear_cluster_top_story_flags()

    # Step 3: Create new story_memory record
    memory_id = _create_story_memory(
        cluster_id=top_cluster_id,
        headline=headline,
        category=category,
        source_slugs=source_slugs,
        pipeline_run_id=pipeline_run_id,
    )

    # Step 4: Denormalize onto the cluster row
    if memory_id:
        _denormalize_top_story(top_cluster_id, memory_id)

    # Step 5: Clean up old memories
    cleanup_old_memories()

    return {
        "status": "ok",
        "top_story": headline[:80],
        "source_count": len(source_slugs),
        "memory_id": memory_id,
    }


def _extract_source_slugs(cluster: dict) -> list[str]:
    """Extract unique source slugs from a cluster's articles."""
    slugs = set()
    for art in cluster.get("articles", []):
        slug = art.get("source_slug") or art.get("source_id", "")
        if slug:
            slugs.add(slug)
    return sorted(slugs)


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
            "pipeline_run_id": pipeline_run_id,
            "activated_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
        if result.data:
            return result.data[0]["id"]
    except Exception as e:
        print(f"  [memory] Error creating story_memory: {e}")
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
