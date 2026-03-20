"""
Re-rank existing clusters using the v3.1 ranking engine.

Reads clusters + articles + bias scores from Supabase, runs rank_importance()
on each, and writes back updated headline_rank + divergence_score +
coverage_velocity. Skips fetch/scrape/analyze — just re-scores.

Usage:
    python pipeline/rerank.py           # re-rank all clusters
    python pipeline/rerank.py --dry-run # show scores without writing
"""

import json
import sys
import time
from pathlib import Path

# Add pipeline root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_client import supabase
from ranker.importance_ranker import rank_importance
from categorizer.auto_categorize import categorize_article

SOURCES_PATH = Path(__file__).parent.parent / "data" / "sources.json"
DRY_RUN = "--dry-run" in sys.argv


def load_sources() -> list[dict]:
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def sync_source_ids(sources: list[dict]) -> list[dict]:
    """Fetch DB UUIDs for all sources so the ranker can resolve source_id lookups."""
    result = supabase.table("sources").select("id,slug,tier,political_lean_baseline").execute()
    db_map = {r["slug"]: r for r in (result.data or [])}
    for s in sources:
        slug = s.get("id", "")
        db_row = db_map.get(slug)
        if db_row:
            s["db_id"] = db_row["id"]
    return sources


def main():
    start = time.time()
    print("=" * 60)
    print(f"void --news re-ranker v3.1 {'(DRY RUN)' if DRY_RUN else ''}")
    print("=" * 60)

    # 1. Load sources with DB IDs
    print("\n[1/4] Loading sources...")
    sources = load_sources()
    sources = sync_source_ids(sources)
    matched = sum(1 for s in sources if s.get("db_id"))
    print(f"  {len(sources)} sources loaded, {matched} matched to DB")

    # 2. Fetch all clusters
    print("\n[2/4] Fetching clusters from Supabase...")
    clusters_res = supabase.table("story_clusters").select(
        "id,title,category,section,content_type,headline_rank,source_count"
    ).execute()
    clusters = clusters_res.data or []
    print(f"  {len(clusters)} clusters found")

    if not clusters:
        print("No clusters to re-rank.")
        return

    # 3. Re-rank each cluster
    print("\n[3/4] Re-ranking clusters...")
    updates = []
    errors = 0

    for i, cluster in enumerate(clusters):
        cid = cluster["id"]

        # Fetch articles for this cluster
        ca_res = supabase.table("cluster_articles").select(
            "article_id"
        ).eq("cluster_id", cid).execute()
        article_ids = [r["article_id"] for r in (ca_res.data or [])]

        if not article_ids:
            continue

        # Fetch article data
        art_res = supabase.table("articles").select(
            "id,source_id,title,summary,full_text,published_at,word_count"
        ).in_("id", article_ids).execute()
        articles = art_res.data or []

        if not articles:
            continue

        # Fetch bias scores
        bs_res = supabase.table("bias_scores").select(
            "article_id,political_lean,sensationalism,opinion_fact,factual_rigor,framing,confidence"
        ).in_("article_id", article_ids).execute()
        bias_scores = bs_res.data or []

        # Map articles for ranker (add published_at key it expects)
        for art in articles:
            art["published_at"] = art.get("published_at", "")

        # Compute cluster confidence (p25)
        conf_values = sorted(
            bs.get("confidence", 0.5) for bs in bias_scores
        )
        if conf_values:
            p25_idx = max(0, len(conf_values) // 4)
            cluster_confidence = conf_values[p25_idx]
        else:
            cluster_confidence = 0.5

        # Classify content type
        if bias_scores:
            avg_opinion = sum(
                bs.get("opinion_fact", 25) for bs in bias_scores
            ) / len(bias_scores)
        else:
            avg_opinion = 25.0
        content_type = "opinion" if avg_opinion > 50 else "reporting"

        # Re-categorize using up to 3 articles
        try:
            cat_votes: dict[str, int] = {}
            for art in articles[:3]:
                for cat in categorize_article(art):
                    cat_votes[cat] = cat_votes.get(cat, 0) + 1
            category = max(cat_votes, key=cat_votes.get) if cat_votes else "politics"
        except Exception:
            category = cluster.get("category", "politics")

        # Run v3.1 ranker
        try:
            result = rank_importance(
                articles, sources, bias_scores,
                cluster_confidence=cluster_confidence,
            )
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  [err] Cluster {cid[:8]}: {e}")
            continue

        old_rank = cluster.get("headline_rank") or 0
        new_rank = result["headline_rank"]

        source_count = len({a["source_id"] for a in articles if a.get("source_id")})
        updates.append({
            "id": cid,
            "headline_rank": new_rank,
            "importance_score": result["importance_score"],
            "divergence_score": result["divergence_score"],
            "coverage_velocity": result["coverage_velocity"],
            "content_type": content_type,
            "category": category,
            "source_count": source_count,
        })

        # Progress
        if (i + 1) % 25 == 0 or i == len(clusters) - 1:
            print(f"  [{i+1}/{len(clusters)}] "
                  f"last: \"{cluster['title'][:50]}\" "
                  f"{old_rank:.1f} -> {new_rank:.1f}")

    print(f"\n  Scored {len(updates)} clusters, {errors} errors")

    # Lead eligibility gate: top 2 positions (lead stories) require 5+
    # sources. Stories with <5 sources get demoted below lead slots.
    # This ensures the hero treatment only goes to well-covered stories.
    LEAD_MIN_SOURCES = 5
    LEAD_SLOTS = 2
    updates.sort(key=lambda u: u["headline_rank"], reverse=True)

    lead_eligible = [u for u in updates if u["source_count"] >= LEAD_MIN_SOURCES]
    lead_ineligible_in_top = []

    # Check if any top-LEAD_SLOTS items are ineligible
    for i in range(min(LEAD_SLOTS, len(updates))):
        if updates[i]["source_count"] < LEAD_MIN_SOURCES:
            lead_ineligible_in_top.append(i)

    if lead_ineligible_in_top and lead_eligible:
        # Swap ineligible leads with the best eligible stories not in top 2
        eligible_idx = 0
        for slot in lead_ineligible_in_top:
            # Find next eligible story not already in top LEAD_SLOTS
            while eligible_idx < len(updates):
                if updates[eligible_idx]["source_count"] >= LEAD_MIN_SOURCES and eligible_idx >= LEAD_SLOTS:
                    # Swap: bump eligible story's rank above the ineligible one
                    updates[eligible_idx]["headline_rank"] = updates[slot]["headline_rank"] + 0.01
                    eligible_idx += 1
                    break
                eligible_idx += 1
        updates.sort(key=lambda u: u["headline_rank"], reverse=True)
        print(f"  Lead gate: promoted {len(lead_ineligible_in_top)} stories with 5+ sources to lead slots")

    print("\n  --- Top 15 by v3.2 headline_rank ---")
    for j, u in enumerate(updates[:15]):
        # Find original title
        title = next(
            (c["title"] for c in clusters if c["id"] == u["id"]), "?"
        )[:60]
        print(f"  {j+1:2}. [{u['headline_rank']:5.1f}] {u['source_count']:2}src {u['category']:12} {title}")

    if DRY_RUN:
        print(f"\n  DRY RUN — no writes. Re-run without --dry-run to apply.")
        return

    # 4. Write back to Supabase
    print(f"\n[4/4] Writing {len(updates)} updates to Supabase...")
    written = 0
    for u in updates:
        try:
            supabase.table("story_clusters").update({
                "headline_rank": u["headline_rank"],
                "importance_score": u["importance_score"],
                "divergence_score": u["divergence_score"],
                "coverage_velocity": u["coverage_velocity"],
                "content_type": u["content_type"],
                "category": u["category"],
            }).eq("id", u["id"]).execute()
            written += 1
        except Exception as e:
            print(f"  [err] Write failed for {u['id'][:8]}: {e}")

    elapsed = time.time() - start
    print(f"\n  Done. {written} clusters re-ranked in {elapsed:.1f}s")
    print("  Refresh the frontend to see new rankings.")


if __name__ == "__main__":
    main()
