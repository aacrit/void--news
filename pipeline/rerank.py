"""
Re-rank existing clusters using the v4.0 ranking engine.

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
    """Look up the primary section (world/us) for a cluster by ID."""
    for c in clusters:
        if c["id"] == cluster_id:
            return c.get("section", "world")
    return "world"


def _cluster_in_section(cluster_id: str, clusters: list[dict], section: str) -> bool:
    """Check if a cluster belongs to a section via sections[] array.
    This matches the frontend query logic (.contains("sections", [section]))
    so that ranking pools see the same stories the user sees."""
    for c in clusters:
        if c["id"] == cluster_id:
            sections = c.get("sections") or [c.get("section", "world")]
            return section in sections
    return section == "world"


def _get_cluster_tier_info(articles: list[dict], sources: list[dict]) -> dict:
    """Get tier breakdown and independent factual rigor for lead gate exemptions."""
    source_map = {}
    for s in sources:
        if s.get("db_id"):
            source_map[s["db_id"]] = s
        if s.get("id"):
            source_map[s["id"]] = s

    tiers = set()
    for a in articles:
        sid = a.get("source_id", "")
        src = source_map.get(sid, {})
        tier = src.get("tier", "")
        if tier:
            tiers.add(tier)

    return {"tiers": tiers}


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
    print(f"void --news re-ranker v5.0 {'(DRY RUN)' if DRY_RUN else ''}")
    print("=" * 60)

    # 1. Load sources with DB IDs
    print("\n[1/4] Loading sources...")
    sources = load_sources()
    sources = sync_source_ids(sources)
    matched = sum(1 for s in sources if s.get("db_id"))
    print(f"  {len(sources)} sources loaded, {matched} matched to DB")

    # 2. Fetch all clusters
    print("\n[2/4] Fetching clusters from Supabase...")
    # Try fetching with v5.0 editorial columns; fall back without them
    try:
        clusters_res = supabase.table("story_clusters").select(
            "id,title,category,section,sections,content_type,headline_rank,source_count,"
            "editorial_importance,story_type"
        ).execute()
    except Exception:
        # editorial columns may not exist yet (migration 013 not applied)
        clusters_res = supabase.table("story_clusters").select(
            "id,title,category,section,sections,content_type,headline_rank,source_count"
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

        # Read editorial intelligence from DB (Gemini-generated, may be NULL)
        editorial_importance = cluster.get("editorial_importance")
        story_type = cluster.get("story_type")

        # Run v5.0 ranker
        try:
            result = rank_importance(
                articles, sources, bias_scores,
                cluster_confidence=cluster_confidence,
                category=category,
                editorial_importance=editorial_importance,
            )
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"  [err] Cluster {cid[:8]}: {e}")
            continue

        # Story-type gates (v5.0): demote incremental updates and ceremonial
        if story_type == "incremental_update":
            result["headline_rank"] *= 0.75
            result["importance_score"] = result["headline_rank"]
        elif story_type == "ceremonial":
            result["headline_rank"] *= 0.82
            result["importance_score"] = result["headline_rank"]

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
            "_articles": articles,
            "_bias_scores": bias_scores,
        })

        # Progress
        if (i + 1) % 25 == 0 or i == len(clusters) - 1:
            print(f"  [{i+1}/{len(clusters)}] "
                  f"last: \"{cluster['title'][:50]}\" "
                  f"{old_rank:.1f} -> {new_rank:.1f}")

    print(f"\n  Scored {len(updates)} clusters, {errors} errors")

    # Per-section lead gate + topic diversity (v4.0)
    # Both gates run PER SECTION so each section's top 10 is independently curated.
    LEAD_MIN_SOURCES = 3
    LEAD_SLOTS = 10
    _SOFT_CATS = {"sports", "entertainment", "culture", "lifestyle",
                  "celebrity", "music", "film", "television", "gaming"}
    MAX_SAME_CAT_DEFAULT = 2
    MAX_SAME_CAT_SOFT = 1
    TOP_N = 10

    updates.sort(key=lambda u: u["headline_rank"], reverse=True)

    for section_val in ("world", "us", "india"):
        pool = [u for u in updates if _cluster_in_section(u["id"], clusters, section_val)]
        if not pool:
            continue

        # --- Lead gate: top LEAD_SLOTS positions require 3+ sources ---
        # Exception: independent-tier stories with factual_rigor > 70
        # Strategy: separate eligible vs ineligible, rebuild the pool
        # with eligible stories first (up to LEAD_SLOTS), then backfill.
        def _is_lead_exempt(u: dict) -> bool:
            """Check if a low-source story qualifies for lead gate exemption."""
            tier_info = _get_cluster_tier_info(u.get("_articles", []), sources)
            avg_rigor = 0.0
            bs_list = u.get("_bias_scores", [])
            if bs_list:
                rigor_vals = [bs.get("factual_rigor", 0) for bs in bs_list if bs.get("factual_rigor") is not None]
                avg_rigor = sum(rigor_vals) / len(rigor_vals) if rigor_vals else 0.0
            return "independent" in tier_info["tiers"] and avg_rigor > 70

        lead_eligible = []
        lead_deferred = []
        for u in pool:
            if u["source_count"] >= LEAD_MIN_SOURCES or _is_lead_exempt(u):
                lead_eligible.append(u)
            else:
                lead_deferred.append(u)

        # Rebuild: eligible stories fill the top, ineligible go after
        if lead_eligible and lead_deferred:
            new_pool = lead_eligible[:LEAD_SLOTS]
            # Backfill remaining slots with deferred if not enough eligible
            remaining_eligible = lead_eligible[LEAD_SLOTS:]
            # Merge remaining eligible + deferred by score
            overflow = remaining_eligible + lead_deferred
            overflow.sort(key=lambda u: u["headline_rank"], reverse=True)
            new_pool.extend(overflow)
            demoted = len(pool) - len(new_pool)  # should be 0
            if len(new_pool) == len(pool):
                pool[:] = new_pool
                print(f"  Lead gate ({section_val}): enforced 3+ sources in top-{LEAD_SLOTS} ({len(lead_deferred)} stories deferred)")

        # --- Topic diversity: soft-news max 1 slot, others max 2 ---
        if len(pool) > TOP_N:
            promoted: list[dict] = []
            deferred: list[dict] = []
            cat_counts: dict[str, int] = {}

            for u in pool:
                if len(promoted) >= TOP_N:
                    deferred.append(u)
                    continue
                cat = u.get("category", "general")
                cat_limit = MAX_SAME_CAT_SOFT if cat in _SOFT_CATS else MAX_SAME_CAT_DEFAULT
                if cat_counts.get(cat, 0) < cat_limit:
                    promoted.append(u)
                    cat_counts[cat] = cat_counts.get(cat, 0) + 1
                else:
                    deferred.append(u)

            while len(promoted) < TOP_N and deferred:
                promoted.append(deferred.pop(0))

            final_order = promoted + deferred
            if final_order and len(promoted) >= 2:
                # Preserve raw scores for promoted items but ensure monotonic
                # ordering so DB sort matches diversity-adjusted order.
                # Only nudge items that are out of order after the shuffle.
                for j in range(1, len(promoted)):
                    if promoted[j]["headline_rank"] >= promoted[j-1]["headline_rank"]:
                        promoted[j]["headline_rank"] = round(promoted[j-1]["headline_rank"] - 0.01, 2)

            demoted_count = sum(1 for d in deferred if d not in pool[TOP_N:])
            if demoted_count:
                print(f"  Topic diversity ({section_val}): demoted {demoted_count} stories exceeding category cap")

    updates.sort(key=lambda u: u["headline_rank"], reverse=True)

    # Cross-edition demotion (v4.0): if a story is top-5 in one edition,
    # demote it below position 5 in other editions it appears in.
    # This prevents the same story being #1 in both World and US.
    # Each cluster's primary edition = its `section` field (majority vote).
    # Secondary editions = other entries in `sections[]` array.
    CROSS_EDITION_TOP = 5
    cluster_sections_map = {c["id"]: (c.get("section", "world"), c.get("sections") or [c.get("section", "world")]) for c in clusters}

    # Build per-section ranked lists
    section_pools: dict[str, list[dict]] = {}
    for section_val in ("world", "us", "india"):
        section_pools[section_val] = [u for u in updates if _cluster_in_section(u["id"], clusters, section_val)]

    # Identify cross-listed clusters in top-5 of any section
    top5_ids_by_section: dict[str, set[str]] = {}
    for section_val, pool in section_pools.items():
        top5_ids_by_section[section_val] = {u["id"] for u in pool[:CROSS_EDITION_TOP]}

    # For each cluster in top-5 of one section, check if it also appears
    # in another section's top-5. If so, keep it in its primary section
    # and demote in secondary sections.
    cross_demoted = 0
    for section_val, pool in section_pools.items():
        for i, u in enumerate(pool[:CROSS_EDITION_TOP]):
            cid = u["id"]
            primary, all_sections = cluster_sections_map.get(cid, ("world", ["world"]))
            # If this cluster's primary section is NOT this section,
            # and it's already top-5 in its primary section, demote it here
            if primary != section_val and cid in top5_ids_by_section.get(primary, set()):
                # Push it to position 6+ by setting rank just below position 5
                if len(pool) > CROSS_EDITION_TOP:
                    target_rank = pool[CROSS_EDITION_TOP]["headline_rank"] - 0.01
                    u["headline_rank"] = round(target_rank, 2)
                    cross_demoted += 1

    if cross_demoted:
        print(f"  Cross-edition: demoted {cross_demoted} stories already leading in their primary section")

    # Final re-sort
    updates.sort(key=lambda u: u["headline_rank"], reverse=True)

    # Print top 15 per section
    for section_val in ("world", "us", "india"):
        section_updates = [u for u in updates if _cluster_in_section(u["id"], clusters, section_val)]
        print(f"\n  --- Top 15 {section_val.upper()} by v4.0 headline_rank ---")
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
