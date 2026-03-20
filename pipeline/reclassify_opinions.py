"""
Targeted re-classification of opinion articles.

Phase 1: Re-score articles with opinion/editorial/analysis URL markers
         using the fixed opinion detector (metadata override floor).
Phase 2: Re-classify clusters containing opinion articles.
Phase 3: Re-rank to populate the Opinion tab.

Usage:
    PYTHONUNBUFFERED=1 python3 pipeline/reclassify_opinions.py
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_client import supabase
from analyzers.opinion_detector import analyze_opinion

# URL markers that indicate opinion content, ordered by strength
OPINION_URL_MARKERS = [
    "opinion", "editorial", "op-ed", "oped", "commentary",
    "column", "perspective", "analysis", "viewpoint", "blog",
    "letters-to-the-editor", "first-person",
]


def main():
    start = time.time()
    print("=" * 60)
    print("Opinion reclassification pipeline")
    print("=" * 60)

    # Phase 1: Find and re-score opinion articles
    print("\n[1/3] Finding articles with opinion markers in URL...")

    # Fetch all articles (paginate if needed)
    all_articles = []
    offset = 0
    batch = 1000
    while True:
        res = supabase.table("articles").select(
            "id,url,title,summary,full_text,section,source_id,word_count"
        ).range(offset, offset + batch - 1).execute()
        if not res.data:
            break
        all_articles.extend(res.data)
        if len(res.data) < batch:
            break
        offset += batch

    print(f"  Fetched {len(all_articles)} total articles")

    # Filter to opinion-marked articles
    opinion_articles = []
    for art in all_articles:
        url = (art.get("url") or "").lower()
        title = (art.get("title") or "").lower()
        for marker in OPINION_URL_MARKERS:
            if marker in url or (marker in title and marker in ["editorial", "op-ed", "commentary"]):
                opinion_articles.append(art)
                break

    print(f"  Found {len(opinion_articles)} articles with opinion markers")

    if not opinion_articles:
        print("  No opinion articles found. Exiting.")
        return

    # Re-score each with the fixed opinion detector
    print("\n[2/3] Re-scoring opinion articles...")
    updated_scores = []
    for i, art in enumerate(opinion_articles):
        result = analyze_opinion(art)
        new_score = result["score"]
        classification = result["rationale"]["classification"]

        updated_scores.append({
            "article_id": art["id"],
            "opinion_fact": new_score,
            "classification": classification,
            "source_id": art.get("source_id"),
        })

        if (i + 1) % 25 == 0:
            print(f"  [{i+1}/{len(opinion_articles)}] "
                  f"last: {new_score} ({classification}) "
                  f"\"{(art.get('title') or '')[:50]}\"")

    over50 = sum(1 for s in updated_scores if s["opinion_fact"] > 50)
    print(f"\n  Results: {over50}/{len(updated_scores)} scored as Opinion (>50)")
    print(f"  Breakdown:")
    for label in ["Reporting", "Analysis", "Opinion", "Editorial"]:
        count = sum(1 for s in updated_scores if s["classification"] == label)
        print(f"    {label}: {count}")

    # Write updated opinion_fact scores to bias_scores table
    print("\n  Updating bias_scores...")
    write_count = 0
    for s in updated_scores:
        try:
            supabase.table("bias_scores").update(
                {"opinion_fact": s["opinion_fact"]}
            ).eq("article_id", s["article_id"]).execute()
            write_count += 1
        except Exception as e:
            print(f"  [err] {s['article_id'][:8]}: {e}")
    print(f"  Updated {write_count} bias_scores rows")

    # Phase 2: Re-classify clusters containing opinion articles
    print("\n[3/3] Re-classifying clusters...")
    opinion_article_ids = {s["article_id"] for s in updated_scores if s["opinion_fact"] > 50}

    if not opinion_article_ids:
        print("  No articles scored >50. No clusters to reclassify.")
        elapsed = time.time() - start
        print(f"\n  Done in {elapsed:.1f}s")
        return

    # Find clusters containing these articles
    cluster_ids_to_update = set()
    for aid in opinion_article_ids:
        ca_res = supabase.table("cluster_articles").select(
            "cluster_id"
        ).eq("article_id", aid).execute()
        for row in (ca_res.data or []):
            cluster_ids_to_update.add(row["cluster_id"])

    print(f"  Found {len(cluster_ids_to_update)} clusters with opinion articles")

    # For each cluster, recompute avg opinion_fact and set content_type
    reclassified = 0
    for cid in cluster_ids_to_update:
        # Get all article IDs in this cluster
        ca_res = supabase.table("cluster_articles").select(
            "article_id"
        ).eq("cluster_id", cid).execute()
        c_article_ids = [r["article_id"] for r in (ca_res.data or [])]

        if not c_article_ids:
            continue

        # Get bias scores for all articles in the cluster
        bs_res = supabase.table("bias_scores").select(
            "opinion_fact"
        ).in_("article_id", c_article_ids).execute()
        of_scores = [r["opinion_fact"] for r in (bs_res.data or []) if r.get("opinion_fact") is not None]

        if not of_scores:
            continue

        avg_of = sum(of_scores) / len(of_scores)
        new_type = "opinion" if avg_of > 50 else "reporting"

        try:
            supabase.table("story_clusters").update(
                {"content_type": new_type}
            ).eq("id", cid).execute()
            if new_type == "opinion":
                reclassified += 1
        except Exception as e:
            print(f"  [err] Cluster {cid[:8]}: {e}")

    print(f"  Reclassified {reclassified} clusters as 'opinion'")

    # Show summary
    print("\n  --- Final opinion cluster count ---")
    ct_res = supabase.table("story_clusters").select(
        "content_type"
    ).execute()
    ct_counts = {}
    for r in ct_res.data:
        ct = r.get("content_type") or "NULL"
        ct_counts[ct] = ct_counts.get(ct, 0) + 1
    for ct, count in sorted(ct_counts.items()):
        print(f"    {ct}: {count}")

    elapsed = time.time() - start
    print(f"\n  Done in {elapsed:.1f}s")
    print("  Refresh the frontend — Opinion tab should now have stories.")


if __name__ == "__main__":
    main()
