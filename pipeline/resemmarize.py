"""
One-off backfill: re-summarize existing clusters with the new Gemini Voice prompts.

Fetches clusters with 3+ sources from Supabase, re-runs summarize_cluster()
with the updated _SYSTEM_INSTRUCTION + _USER_PROMPT_TEMPLATE, and writes
new headline, summary, consensus_points, divergence_points back to the DB.

Respects the 25-call cap. Run with:
    cd /home/aacrit/projects/void-news
    python -m pipeline.resemmarize [--dry-run] [--limit N]

Requires SUPABASE_URL, SUPABASE_KEY, GEMINI_API_KEY in .env or environment.
"""

import argparse
import json
import sys

from pipeline.utils.supabase_client import supabase
from pipeline.summarizer.cluster_summarizer import (
    summarize_cluster,
    _SYSTEM_INSTRUCTION,
    _USER_PROMPT_TEMPLATE,
    _build_context_line,
    _build_articles_block,
    _build_source_names_line,
    _check_quality,
)
import pipeline.summarizer.gemini_client as gemini_mod
from pipeline.summarizer.gemini_client import is_available, calls_remaining, generate_json


def _summarize_any_cluster(articles: list[dict]) -> dict | None:
    """Call Gemini directly for any cluster size (bypasses 3-source gate)."""
    if not articles:
        return None

    context_line = _build_context_line(articles)
    source_names_line = _build_source_names_line(articles)
    articles_block = _build_articles_block(articles)
    prompt = _USER_PROMPT_TEMPLATE.format(
        context_line=context_line,
        source_names_line=source_names_line,
        articles_block=articles_block,
    )
    result = generate_json(prompt, system_instruction=_SYSTEM_INSTRUCTION)

    if not result:
        return None

    headline = result.get("headline", "")
    summary = result.get("summary", "")
    consensus = result.get("consensus", [])
    divergence = result.get("divergence", [])

    if not isinstance(headline, str) or not headline.strip():
        return None
    if not isinstance(summary, str) or not summary.strip():
        return None
    if not isinstance(consensus, list):
        consensus = []
    if not isinstance(divergence, list):
        divergence = []

    # Extract editorial intelligence fields
    editorial_importance = result.get("editorial_importance")
    if isinstance(editorial_importance, (int, float)):
        editorial_importance = max(1, min(10, int(editorial_importance)))
    else:
        editorial_importance = None

    _VALID_STORY_TYPES = {
        "breaking_crisis", "policy_action", "investigation",
        "ongoing_crisis", "incremental_update", "human_interest",
        "ceremonial", "entertainment",
    }
    story_type_raw = result.get("story_type", "")
    story_type = story_type_raw if story_type_raw in _VALID_STORY_TYPES else None

    has_binding = result.get("has_binding_consequences")
    has_binding_consequences = bool(has_binding) if isinstance(has_binding, bool) else None

    validated = {
        "headline": headline.strip()[:500],
        "summary": summary.strip(),
        "consensus": [str(c) for c in consensus if c],
        "divergence": [str(d) for d in divergence if d],
        "editorial_importance": editorial_importance,
        "story_type": story_type,
        "has_binding_consequences": has_binding_consequences,
    }
    _check_quality(validated)
    return validated


def fetch_clusters(limit: int = 25, offset: int = 0) -> list[dict]:
    """Fetch non-opinion clusters with 2+ sources, sorted by source_count desc."""
    resp = (
        supabase.table("story_clusters")
        .select("id, title, summary, source_count, section, content_type, consensus_points, divergence_points")
        .gte("source_count", 2)
        .neq("content_type", "opinion")
        .order("source_count", desc=True)
        .range(offset, offset + limit - 1)
        .execute()
    )
    clusters = resp.data or []
    print(f"Fetched {len(clusters)} non-opinion clusters with 2+ sources (offset={offset})")
    return clusters


def fetch_cluster_articles(cluster_id: str) -> list[dict]:
    """Fetch articles for a cluster with their source tier info."""
    resp = (
        supabase.table("cluster_articles")
        .select("article_id, articles(id, title, summary, url, source_id, sources(tier, name))")
        .eq("cluster_id", cluster_id)
        .execute()
    )
    rows = resp.data or []

    articles = []
    for row in rows:
        art = row.get("articles")
        if not art:
            continue
        source = art.get("sources") or {}
        articles.append({
            "title": art.get("title", ""),
            "summary": art.get("summary", ""),
            "url": art.get("url", ""),
            "tier": source.get("tier", ""),
            "source_name": source.get("name", ""),
        })
    return articles


def update_cluster_summary(cluster_id: str, result: dict) -> bool:
    """Write new summary data back to the cluster."""
    update_data = {
        "title": result["headline"],
        "summary": result["summary"],
        "consensus_points": result["consensus"],
        "divergence_points": result["divergence"],
    }
    # Editorial intelligence columns may not exist in all environments.
    # Try with them first; fall back to core fields only on schema error.
    ei_fields = {}
    if result.get("editorial_importance") is not None:
        ei_fields["editorial_importance"] = result["editorial_importance"]
    if result.get("story_type") is not None:
        ei_fields["story_type"] = result["story_type"]
    if result.get("has_binding_consequences") is not None:
        ei_fields["has_binding_consequences"] = result["has_binding_consequences"]
    try:
        supabase.table("story_clusters").update({**update_data, **ei_fields}).eq("id", cluster_id).execute()
        return True
    except Exception as e:
        if "PGRST204" in str(e) or "column" in str(e).lower():
            # Column doesn't exist — retry without editorial intelligence fields
            try:
                supabase.table("story_clusters").update(update_data).eq("id", cluster_id).execute()
                return True
            except Exception as e2:
                print(f"  [error] Failed to update cluster {cluster_id}: {e2}")
                return False
        print(f"  [error] Failed to update cluster {cluster_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Re-summarize existing clusters with new Gemini Voice")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to DB")
    parser.add_argument("--limit", type=int, default=555, help="Max clusters to process (default: all)")
    parser.add_argument("--offset", type=int, default=0, help="Skip first N clusters (for pagination)")
    parser.add_argument("--cap", type=int, default=500, help="Gemini call cap for this run (default: 500)")
    args = parser.parse_args()

    if not is_available():
        print("Gemini is not available (missing GEMINI_API_KEY). Exiting.")
        sys.exit(1)

    # Override the per-run call cap for backfill (pipeline default is 25,
    # but free tier allows 1500 RPD — safe to use up to 500 for backfill)
    gemini_mod._MAX_CALLS_PER_RUN = args.cap
    gemini_mod._call_count = 0

    print(f"Gemini Voice Backfill — {'DRY RUN' if args.dry_run else 'LIVE'}")
    print(f"Call cap: {calls_remaining()} calls remaining (raised for backfill)\n")

    clusters = fetch_clusters(limit=args.limit, offset=args.offset)
    if not clusters:
        print("No clusters found with 3+ sources.")
        return

    updated = 0
    skipped = 0
    failed = 0

    for cluster in clusters:
        cid = cluster["id"]
        old_title = cluster.get("title", "")[:60]

        if calls_remaining() <= 0:
            print(f"\nCall cap reached after {updated} clusters. Remaining will keep old summaries.")
            break

        articles = fetch_cluster_articles(cid)
        if not articles:
            skipped += 1
            continue

        print(f"[{updated + 1}] Cluster {cid} ({len(articles)} articles): {old_title}...")

        # Use summarize_cluster for 3+ sources; call Gemini directly for 1-2 sources
        # (summarize_cluster has a 3-source gate in the batch path, but the single
        # function works for any count — we call it directly here)
        result = _summarize_any_cluster(articles)

        if not result:
            print(f"  Gemini returned None — skipping")
            failed += 1
            continue

        print(f"  New headline: {result['headline']}")
        print(f"  Summary: {result['summary'][:80]}...")

        if args.dry_run:
            print(f"  [dry-run] Would update cluster {cid}")
            updated += 1
        else:
            if update_cluster_summary(cid, result):
                print(f"  Updated cluster {cid}")
                updated += 1
            else:
                failed += 1

    print(f"\nDone. Updated: {updated}, Skipped: {skipped}, Failed: {failed}")
    print(f"Gemini calls remaining: {calls_remaining()}")


if __name__ == "__main__":
    main()
