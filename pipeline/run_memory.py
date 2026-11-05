"""
Standalone memory orchestrator runner.

Identifies the top 2 story clusters from the latest pipeline run and creates
story_memory records + denormalizes to story_clusters. Does NOT run the full
pipeline — just the memory step.

Usage:
    python pipeline/run_memory.py [--verbose] [--dry-run]
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_client import supabase
from memory.memory_orchestrator import update_memory_after_pipeline_run


def get_latest_pipeline_run() -> dict | None:
    """Get the most recent completed pipeline run."""
    result = supabase.table("pipeline_runs").select(
        "id,status,completed_at"
    ).eq("status", "completed").order(
        "completed_at", desc=True
    ).limit(1).execute()
    return result.data[0] if result.data else None


def get_top_clusters(limit: int = 10) -> list[dict]:
    """
    Get the top N clusters by headline_rank from the DB.
    Includes article data needed by the memory orchestrator.
    """
    # Get top clusters
    clusters_res = supabase.table("story_clusters").select(
        "id,title,category,headline_rank,source_count,sections"
    ).order("headline_rank", desc=True).limit(limit).execute()

    if not clusters_res.data:
        return []

    clusters = []
    for c in clusters_res.data:
        # Fetch articles for this cluster to extract source slugs
        arts_res = supabase.table("cluster_articles").select(
            "article:articles(id,source:sources(slug,tier))"
        ).eq("cluster_id", c["id"]).execute()

        articles = []
        for row in (arts_res.data or []):
            art = row.get("article")
            if not art:
                continue
            src = art.get("source") or {}
            articles.append({
                "source_slug": src.get("slug", ""),
                "source_tier": src.get("tier", "independent"),
            })

        clusters.append({
            "id": c["id"],
            "title": c["title"],
            "category": c["category"],
            "headline_rank": c["headline_rank"],
            "source_count": c["source_count"],
            "articles": articles,
        })

    return clusters


def main():
    parser = argparse.ArgumentParser(description="Run memory orchestrator standalone")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without writing")
    args = parser.parse_args()

    # 1. Get latest pipeline run
    run = get_latest_pipeline_run()
    if not run:
        print("No completed pipeline run found.")
        sys.exit(1)

    pipeline_run_id = run["id"]
    print(f"Latest pipeline run: {pipeline_run_id} ({run['completed_at']})")

    # 2. Get top clusters
    clusters = get_top_clusters(limit=10)
    if not clusters:
        print("No clusters found.")
        sys.exit(1)

    print(f"Found {len(clusters)} clusters. Top 2:")
    for i, c in enumerate(clusters[:2]):
        print(f"  #{i+1}: [{c['headline_rank']:.1f}] {c['title'][:80]} ({len(c['articles'])} articles)")

    if args.dry_run:
        print("\n[dry-run] Would create story_memory for top 2 clusters. Exiting.")
        return

    # 3. Run memory orchestrator
    cluster_ids = [c["id"] for c in clusters]
    result = update_memory_after_pipeline_run(pipeline_run_id, clusters, cluster_ids)

    print(f"\nResult: {json.dumps(result, indent=2, default=str)}")


if __name__ == "__main__":
    main()
