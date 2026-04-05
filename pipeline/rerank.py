"""
Re-rank existing clusters using the v6.0 ranking engine.

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
from ranker.edition_ranker import apply_edition_ranking, EDITIONS
from categorizer.auto_categorize import categorize_article, map_to_desk

SOURCES_PATH = Path(__file__).parent.parent / "data" / "sources.json"
DRY_RUN = "--dry-run" in sys.argv


def _cluster_in_section(cluster_id: str, clusters: list[dict], section: str) -> bool:
    """Check if a cluster belongs to a section via sections[] array.
    This matches the frontend query logic (.contains("sections", [section]))
    so that ranking pools see the same stories the user sees."""
    for c in clusters:
        if c["id"] == cluster_id:
            sections = c.get("sections") or [c.get("section", "world")]
            return section in sections
    return section == "world"


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
    print(f"void --news re-ranker v5.7 {'(DRY RUN)' if DRY_RUN else ''}")
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

    updates.sort(key=lambda u: u["headline_rank"], reverse=True)

    # ── Per-edition rank computation (v6.0 — shared edition_ranker) ──
    # Normalize update dicts for the shared module: needs "articles", "title", "sections"
    _cluster_lookup = {c["id"]: c for c in clusters}
    for u in updates:
        if "articles" not in u:
            u["articles"] = u.get("_articles", [])
        if "title" not in u:
            cl = _cluster_lookup.get(u["id"])
            u["title"] = cl["title"] if cl else ""
        if "sections" not in u:
            cl = _cluster_lookup.get(u["id"])
            if cl:
                u["sections"] = cl.get("sections") or [cl.get("section", "world")]
            else:
                u["sections"] = ["world"]

    apply_edition_ranking(
        updates, sources, get_article_edition="source_lookup"
    )

    # REMOVED: old per-section lead gate, same-event cap, topic diversity,
    # edition ranking (v5.7), freshness decay, source depth bonus.
    # All now handled by edition_ranker.py (single source of truth).
    #
    # Dummy block to satisfy the remaining code flow:
    # Print top 15 per edition
    for ed in EDITIONS:
        pool = [u for u in updates if _cluster_in_section(u["id"], clusters, ed)]
        pool.sort(key=lambda u: u.get(f"rank_{ed}", 0), reverse=True)
        print(f"\n  --- Top 15 {ed.upper()} by rank_{ed} ---")
        for j, u in enumerate(pool[:15]):
            title = next(
                (c["title"] for c in clusters if c["id"] == u["id"]), "?"
            )[:60]
            print(f"  {j+1:2}. [{u.get(f'rank_{ed}', 0):5.1f}] {u['source_count']:2}src {u.get('category',''):12} {title}")

    if DRY_RUN:
        print(f"\n  DRY RUN — no writes. Re-run without --dry-run to apply.")
        return

    # 4. Write back to Supabase in batches (16 concurrent workers).
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
            "rank_europe": u.get("rank_europe", u["headline_rank"]),
            # Edition name "south-asia" (hyphen) → DB column "rank_south_asia" (underscore)
            "rank_south_asia": u.get("rank_south-asia", u["headline_rank"]),
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
