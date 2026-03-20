"""
Re-rank existing clusters using the v3.3 ranking engine.

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


def _get_section(cluster_id: str, clusters: list[dict]) -> str:
    """Look up the section (world/us) for a cluster by ID."""
    for c in clusters:
        if c["id"] == cluster_id:
            return c.get("section", "world")
    return "world"


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
    print(f"void --news re-ranker v3.3 {'(DRY RUN)' if DRY_RUN else ''}")
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

    # Lead eligibility gate (v3.3): top 10 positions require 3+ sources.
    # 2-source stories were slipping into positions 6-10 despite the gate
    # only covering top 5. Extended to full top 10 for editorial quality.
    LEAD_MIN_SOURCES = 3
    LEAD_SLOTS = 10
    updates.sort(key=lambda u: u["headline_rank"], reverse=True)

    lead_ineligible_in_top = []

    # Check if any top-LEAD_SLOTS items are ineligible
    for i in range(min(LEAD_SLOTS, len(updates))):
        if updates[i]["source_count"] < LEAD_MIN_SOURCES:
            lead_ineligible_in_top.append(i)

    if lead_ineligible_in_top:
        # Swap ineligible leads with the best eligible stories not in top LEAD_SLOTS
        eligible_idx = 0
        for slot in lead_ineligible_in_top:
            while eligible_idx < len(updates):
                if updates[eligible_idx]["source_count"] >= LEAD_MIN_SOURCES and eligible_idx >= LEAD_SLOTS:
                    updates[eligible_idx]["headline_rank"] = updates[slot]["headline_rank"] + 0.01
                    eligible_idx += 1
                    break
                eligible_idx += 1
        updates.sort(key=lambda u: u["headline_rank"], reverse=True)
        print(f"  Lead gate: promoted {len(lead_ineligible_in_top)} stories with 3+ sources into top-5 slots")

    # Topic diversity re-rank (v3.3): max 2 stories per category in the
    # top 10 of each section. Prevents sports×3, BTS×2, etc.
    # Runs per section (world/us) since that's how the frontend displays.
    MAX_SAME_CAT = 2
    TOP_N = 10
    for section_val in ("world", "us", "india"):
        pool = [u for u in updates if _get_section(u["id"], clusters) == section_val]
        if len(pool) <= TOP_N:
            continue
        promoted: list[dict] = []
        deferred: list[dict] = []
        cat_counts: dict[str, int] = {}

        for u in pool:
            if len(promoted) >= TOP_N:
                deferred.append(u)
                continue
            cat = u.get("category", "general")
            if cat_counts.get(cat, 0) < MAX_SAME_CAT:
                promoted.append(u)
                cat_counts[cat] = cat_counts.get(cat, 0) + 1
            else:
                deferred.append(u)

        # Backfill if we couldn't fill TOP_N
        while len(promoted) < TOP_N and deferred:
            promoted.append(deferred.pop(0))

        # Adjust headline_rank for demoted items so DB sort order matches
        final_order = promoted + deferred
        if final_order:
            top_rank = final_order[0]["headline_rank"]
            for i, u in enumerate(final_order):
                if i < TOP_N:
                    u["headline_rank"] = round(top_rank - (i * 0.01), 2)

        demoted_count = sum(1 for d in deferred if d not in pool[TOP_N:])
        if demoted_count:
            print(f"  Topic diversity ({section_val}): demoted {demoted_count} stories exceeding category cap")

    # Re-sort after topic diversity adjustments
    updates.sort(key=lambda u: u["headline_rank"], reverse=True)

    # Print top 15 per section
    for section_val in ("world", "us", "india"):
        section_updates = [u for u in updates if _get_section(u["id"], clusters) == section_val]
        print(f"\n  --- Top 15 {section_val.upper()} by v3.3 headline_rank ---")
        for j, u in enumerate(section_updates[:15]):
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
