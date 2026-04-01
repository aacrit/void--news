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
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Add pipeline root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_client import supabase
from ranker.importance_ranker import rank_importance
from categorizer.auto_categorize import categorize_article, map_to_desk

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

    # 3. Bulk-fetch all cluster_articles, articles, and bias_scores upfront.
    # Previously: 3 queries per cluster = 25,941 HTTP calls for 8,647 clusters.
    # Now: 3 paginated bulk fetches + in-memory dicts = ~30 HTTP calls total.
    print("\n[3/4] Bulk-fetching cluster data...")

    def _paginated_fetch(table: str, select: str, page_size: int = 500) -> list[dict]:
        """Fetch all rows with pagination and retry on connection drops."""
        all_rows: list[dict] = []
        offset = 0
        retries = 0
        while True:
            try:
                res = supabase.table(table).select(select).range(
                    offset, offset + page_size - 1
                ).execute()
                retries = 0
            except Exception as e:
                retries += 1
                if retries <= 3:
                    print(f"  [retry {retries}/3] {table} offset {offset}: {type(e).__name__}")
                    time.sleep(2)
                    continue
                print(f"  [err] {table} failed after 3 retries at offset {offset}")
                break
            if not res.data:
                break
            all_rows.extend(res.data)
            if len(res.data) < page_size:
                break
            offset += page_size
        return all_rows

    # 3a. Fetch all cluster_articles rows
    ca_rows = _paginated_fetch("cluster_articles", "cluster_id,article_id")
    cluster_article_map: dict[str, list[str]] = {}
    for row in ca_rows:
        cluster_article_map.setdefault(row["cluster_id"], []).append(row["article_id"])
    print(f"  cluster_articles: {len(ca_rows)} rows covering {len(cluster_article_map)} clusters")

    # 3b. Fetch all articles
    art_rows = _paginated_fetch("articles",
        "id,source_id,title,summary,full_text,published_at,word_count")
    articles_by_id: dict[str, dict] = {r["id"]: r for r in art_rows}
    print(f"  articles: {len(articles_by_id)} rows fetched")

    # 3c. Fetch all bias_scores
    bs_rows = _paginated_fetch("bias_scores",
        "article_id,political_lean,sensationalism,opinion_fact,factual_rigor,framing,confidence")
    bias_by_article_id: dict[str, dict] = {r["article_id"]: r for r in bs_rows}
    print(f"  bias_scores: {len(bias_by_article_id)} rows fetched")

    # 3d. Re-rank each cluster using in-memory data (no per-cluster DB queries)
    print("\n  Re-ranking clusters in memory...")
    updates = []
    errors = 0

    for i, cluster in enumerate(clusters):
        cid = cluster["id"]

        article_ids = cluster_article_map.get(cid, [])
        if not article_ids:
            continue

        articles = [articles_by_id[aid] for aid in article_ids if aid in articles_by_id]
        if not articles:
            continue

        bias_scores = [bias_by_article_id[aid] for aid in article_ids if aid in bias_by_article_id]

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
                (bs.get("opinion_fact") or 25) for bs in bias_scores
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
            best_cat = max(cat_votes, key=cat_votes.get) if cat_votes else "politics"
            category = map_to_desk(best_cat)
        except Exception:
            category = cluster.get("category", "politics")

        # Read editorial intelligence from DB (Gemini-generated, may be NULL)
        editorial_importance = cluster.get("editorial_importance")
        story_type = cluster.get("story_type")

        # Run v5.1 ranker — pass sections for US-only divergence damper
        cluster_sections = cluster.get("sections") or [cluster.get("section", "world")]
        try:
            result = rank_importance(
                articles, sources, bias_scores,
                cluster_confidence=cluster_confidence,
                category=category,
                editorial_importance=editorial_importance,
                sections=cluster_sections,
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

        # --- Same-event cap (v5.1, strengthened v5.6) ---
        # Detects event clusters by keyword overlap in titles.
        # "Iran war" stories all share keywords like iran/tehran/hormuz.
        # v5.6: Reduced from 3 to 2 in top pool. Deferred stories get
        # 0.92x rank decay so they don't cluster at positions 11-20
        # (benchmark found 11/20 world stories were Iran variants).
        MAX_SAME_EVENT = 2
        EVENT_DECAY = 0.92  # rank multiplier for deferred same-event stories
        _EVENT_KEYWORDS = {
            "iran": {"iran", "iranian", "tehran", "hormuz", "persian gulf", "irgc", "hegseth", "isfahan"},
            "ukraine": {"ukraine", "ukrainian", "kyiv", "zelenskyy", "zelensky", "donbas", "crimea"},
            "israel_palestine": {"gaza", "hamas", "west bank", "netanyahu", "idf", "hezbollah"},
            "china_taiwan": {"taiwan", "taipei", "strait", "xi jinping", "pla"},
            "us_scotus": {"supreme court", "scotus", "constitutional"},
        }

        def _detect_event(title: str) -> str | None:
            """Return event key if title matches a known event, else None."""
            t = title.lower()
            for event_key, keywords in _EVENT_KEYWORDS.items():
                if any(kw in t for kw in keywords):
                    return event_key
            return None

        if len(pool) > TOP_N:
            event_counts: dict[str, int] = {}
            event_promoted: list[dict] = []
            event_deferred: list[dict] = []

            for u in pool:
                title = next((c["title"] for c in clusters if c["id"] == u["id"]), "")
                event = _detect_event(title)
                if event and event_counts.get(event, 0) >= MAX_SAME_EVENT:
                    event_deferred.append(u)
                else:
                    event_promoted.append(u)
                    if event:
                        event_counts[event] = event_counts.get(event, 0) + 1

            # v5.6: Apply rank decay to deferred same-event stories.
            # Without decay, deferred stories keep their original rank and
            # cluster at positions 11-20 (e.g., 8 Iran stories in a row).
            # Each deferred story gets 0.92x, making them spread out and
            # allowing non-event stories to interleave naturally.
            for u in event_deferred:
                u["headline_rank"] = round(u["headline_rank"] * EVENT_DECAY, 2)

            # Merge: promoted first, deferred after
            pool[:] = event_promoted + event_deferred

            event_demoted = len(event_deferred)
            if event_demoted:
                print(f"  Event diversity ({section_val}): demoted {event_demoted} stories exceeding same-event cap (max {MAX_SAME_EVENT})")

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
                # Use 0.1pt spacing: enough to avoid false ties (0.01 made
                # 22src Paris bomb = 6src strike) without distorting ranks
                # (0.5 pushed a 57pt airstrike down to 48.5).
                for j in range(1, len(promoted)):
                    if promoted[j]["headline_rank"] >= promoted[j-1]["headline_rank"]:
                        promoted[j]["headline_rank"] = round(promoted[j-1]["headline_rank"] - 0.1, 2)

            demoted_count = sum(1 for d in deferred if d not in pool[TOP_N:])
            if demoted_count:
                print(f"  Topic diversity ({section_val}): demoted {demoted_count} stories exceeding category cap")

    updates.sort(key=lambda u: u["headline_rank"], reverse=True)

    # --- Per-edition rank computation (v5.4) ---
    # The per-section gates above modified headline_rank in-place, which
    # causes cross-contamination between editions. Now compute independent
    # per-edition ranks using the base importance score, and apply
    # cross-edition demotion (0.92x for stories already top-5 elsewhere).
    CROSS_EDITION_TOP = 5
    CROSS_DEMOTION = 0.92
    EDITIONS = ["world", "us", "india"]

    # Store base importance (pre-gate) for each update
    for u in updates:
        if "base_rank" not in u:
            u["base_rank"] = u["importance_score"]

    claimed_ids: set[str] = set()
    for edition in EDITIONS:
        pool = [u for u in updates if _cluster_in_section(u["id"], clusters, edition)]
        # Start from base_rank for each edition (independent of other editions)
        for u in pool:
            u[f"rank_{edition}"] = u["base_rank"]

        # Apply cross-edition demotion: stories already top-5 elsewhere
        for u in pool:
            if u["id"] in claimed_ids:
                u[f"rank_{edition}"] = round(u[f"rank_{edition}"] * CROSS_DEMOTION, 2)

        # Re-sort by this edition's rank
        pool.sort(key=lambda u: u[f"rank_{edition}"], reverse=True)

        # Apply per-edition topic diversity (same logic but on edition rank)
        if len(pool) > TOP_N:
            promoted_e: list[dict] = []
            deferred_e: list[dict] = []
            cat_counts_e: dict[str, int] = {}
            for u in pool:
                if len(promoted_e) >= TOP_N:
                    deferred_e.append(u)
                    continue
                cat = u.get("category", "general")
                cat_limit = MAX_SAME_CAT_SOFT if cat in _SOFT_CATS else MAX_SAME_CAT_DEFAULT
                if cat_counts_e.get(cat, 0) < cat_limit:
                    promoted_e.append(u)
                    cat_counts_e[cat] = cat_counts_e.get(cat, 0) + 1
                else:
                    deferred_e.append(u)
            while len(promoted_e) < TOP_N and deferred_e:
                promoted_e.append(deferred_e.pop(0))
            for j in range(1, len(promoted_e)):
                if promoted_e[j][f"rank_{edition}"] >= promoted_e[j - 1][f"rank_{edition}"]:
                    promoted_e[j][f"rank_{edition}"] = round(
                        promoted_e[j - 1][f"rank_{edition}"] - 0.1, 2
                    )
            pool_final = promoted_e + deferred_e
        else:
            pool_final = pool

        # Claim this edition's top 5
        for u in pool_final[:CROSS_EDITION_TOP]:
            claimed_ids.add(u["id"])

    # Report overlap
    section_top5: dict[str, list[str]] = {}
    for edition in EDITIONS:
        pool = [u for u in updates if _cluster_in_section(u["id"], clusters, edition)]
        pool.sort(key=lambda u: u.get(f"rank_{edition}", 0), reverse=True)
        section_top5[edition] = [u["id"] for u in pool[:CROSS_EDITION_TOP]]

    world_us = len(set(section_top5.get("world", [])) & set(section_top5.get("us", [])))
    world_india = len(set(section_top5.get("world", [])) & set(section_top5.get("india", [])))
    print(f"  Cross-edition overlap: world/us={world_us}/5, world/india={world_india}/5")

    updates.sort(key=lambda u: u["headline_rank"], reverse=True)

    # Print top 15 per section using per-edition ranks
    for section_val in ("world", "us", "india"):
        rank_col = f"rank_{section_val}"
        section_updates = [u for u in updates if _cluster_in_section(u["id"], clusters, section_val)]
        section_updates.sort(key=lambda u: u.get(rank_col, 0), reverse=True)
        print(f"\n  --- Top 15 {section_val.upper()} by rank_{section_val} ---")
        for j, u in enumerate(section_updates[:15]):
            title = next(
                (c["title"] for c in clusters if c["id"] == u["id"]), "?"
            )[:60]
            print(f"  {j+1:2}. [{u.get(rank_col, 0):5.1f}] {u['source_count']:2}src {u['category']:12} {title}")

    if DRY_RUN:
        print(f"\n  DRY RUN — no writes. Re-run without --dry-run to apply.")
        return

    # 4. Write back to Supabase
    # 4. Write back to Supabase in batches.
    # Previously: one UPDATE per cluster = 8,647 sequential HTTP calls.
    # Now: parallel batches of 100 rows, 16 concurrent workers.
    print(f"\n[4/4] Writing {len(updates)} updates to Supabase (batched, 16 workers)...")
    write_rows = [
        {
            "id": u["id"],
            "headline_rank": u["headline_rank"],
            "importance_score": u["importance_score"],
            "divergence_score": u["divergence_score"],
            "coverage_velocity": u["coverage_velocity"],
            "content_type": u["content_type"],
            "category": u["category"],
            "source_count": u["source_count"],
            "rank_world": u.get("rank_world", u["headline_rank"]),
            "rank_us": u.get("rank_us", u["headline_rank"]),
            "rank_india": u.get("rank_india", u["headline_rank"]),
        }
        for u in updates
    ]

    WRITE_CHUNK = 100
    write_chunks = [
        write_rows[i:i + WRITE_CHUNK]
        for i in range(0, len(write_rows), WRITE_CHUNK)
    ]

    written = 0
    write_errors = 0

    def _write_chunk(chunk: list[dict]) -> int:
        ok = 0
        for row in chunk:
            rid = row.pop("id")
            try:
                supabase.table("story_clusters").update(row).eq("id", rid).execute()
                ok += 1
            except Exception as e:
                if ok == 0:  # only log first error per chunk to avoid spam
                    print(f"  [err] Write failed for {rid[:8]}: {e}")
            finally:
                row["id"] = rid  # restore for any retry logic
        return ok

    with ThreadPoolExecutor(max_workers=16) as write_exec:
        write_futures = [write_exec.submit(_write_chunk, chunk) for chunk in write_chunks]
        for future in as_completed(write_futures):
            try:
                written += future.result()
            except Exception:
                write_errors += WRITE_CHUNK

    elapsed = time.time() - start
    print(f"\n  Done. {written} clusters re-ranked in {elapsed:.1f}s"
          + (f" ({write_errors} write errors)" if write_errors else ""))
    print("  Refresh the frontend to see new rankings.")


if __name__ == "__main__":
    main()
