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
from datetime import datetime, timezone
from pathlib import Path

# Add pipeline root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_client import supabase
from ranker.importance_ranker import rank_importance
from ranker.feed_ranker import apply_feed_ordering
from categorizer.auto_categorize import categorize_article, categorize_cluster, map_to_desk

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


def rerank_all_clusters(sources: list[dict], dry_run: bool = False) -> int:
    """
    Re-rank ALL clusters in Supabase with the current ranking engine.

    Fetches all clusters, articles, and bias scores from DB, runs
    rank_importance() + apply_feed_ordering() on each, and writes
    back updated scores. This ensures all clusters compete on equal
    footing with the same engine version.

    Called by:
      - main.py after storing new clusters (holistic ranking)
      - rerank.py CLI for manual re-ranking

    Args:
        sources: Full sources list with id, db_id, tier, etc.
        dry_run: If True, compute scores but don't write to DB.

    Returns:
        Number of clusters re-ranked.
    """
    start = time.time()
    print(f"\n  Re-ranking all clusters {'(DRY RUN)' if dry_run else ''}...")

    # Fetch all clusters — paginated. PostgREST caps any single response at
    # 1,000 rows; with orphan-wrapping the retention window routinely holds
    # more, and every cluster past the cap silently kept its stale
    # headline_rank/rank_world (the same stale-pin class as the 2026-05-22
    # 13-source #1 regression).
    def _fetch_all_clusters(select: str) -> list[dict]:
        rows: list[dict] = []
        page = 1000
        offset = 0
        while True:
            res = supabase.table("story_clusters").select(select).range(
                offset, offset + page - 1
            ).execute()
            batch = res.data or []
            rows.extend(batch)
            if len(batch) < page:
                return rows
            offset += page

    try:
        clusters = _fetch_all_clusters(
            "id,title,summary,category,section,sections,content_type,headline_rank,source_count,"
            "editorial_importance,story_type,mega_cluster_capped"
        )
    except Exception:
        try:
            clusters = _fetch_all_clusters(
                "id,title,category,section,sections,content_type,headline_rank,source_count,"
                "mega_cluster_capped"
            )
        except Exception:
            clusters = _fetch_all_clusters(
                "id,title,category,section,sections,content_type,headline_rank,source_count"
            )
    print(f"  {len(clusters)} clusters found")

    if not clusters:
        print("  No clusters to re-rank.")
        return 0

    # 3. Bulk-fetch all cluster_articles, articles, and bias_scores upfront.
    # Previously: 3 queries per cluster = 25,941 HTTP calls for 8,647 clusters.
    # Now: 3 paginated bulk fetches + in-memory dicts = ~30 HTTP calls total.
    print("\n[3/4] Bulk-fetching cluster data...")

    def _paginated_fetch(
        table: str,
        select: str,
        page_size: int = 500,
        gte_column: str | None = None,
        gte_value: str | None = None,
        in_column: str | None = None,
        in_values: list[str] | None = None,
    ) -> list[dict]:
        """Fetch all rows with pagination and retry on connection drops.

        Optional column filters:
          gte_column / gte_value — server-side WHERE column >= value
          in_column / in_values  — server-side WHERE column IN (...)
                                   (auto-chunked into IN-batches of 200)

        Both filters reduce egress: the server filters before sending bytes
        across the wire, instead of us paginating the whole table.
        """
        all_rows: list[dict] = []

        if in_column and in_values is not None:
            # IN-list filter: chunk in batches of 200 to stay under PostgREST URL
            # length limits. Pagination within each chunk is identical to the
            # no-filter case.
            chunk_size = 200
            for i in range(0, len(in_values), chunk_size):
                chunk = in_values[i:i + chunk_size]
                offset = 0
                retries = 0
                while True:
                    try:
                        q = supabase.table(table).select(select).in_(in_column, chunk)
                        if gte_column and gte_value:
                            q = q.gte(gte_column, gte_value)
                        res = q.range(offset, offset + page_size - 1).execute()
                        retries = 0
                    except Exception as e:
                        retries += 1
                        if retries <= 3:
                            print(f"  [retry {retries}/3] {table} chunk {i} offset {offset}: {type(e).__name__}")
                            time.sleep(2)
                            continue
                        print(f"  [err] {table} failed after 3 retries at chunk {i} offset {offset}")
                        break
                    if not res.data:
                        break
                    all_rows.extend(res.data)
                    if len(res.data) < page_size:
                        break
                    offset += page_size
            return all_rows

        # No IN-list filter: simple paginated fetch (with optional GTE).
        offset = 0
        retries = 0
        while True:
            try:
                q = supabase.table(table).select(select)
                if gte_column and gte_value:
                    q = q.gte(gte_column, gte_value)
                res = q.range(offset, offset + page_size - 1).execute()
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

    # 2026-06-01 egress fix — rerank previously paginated through ALL articles
    # in the table (8 days × 4K/day = 32K rows × ~5 KB = ~150 MB per run).
    # The rerank only needs articles that BELONG to currently-loaded clusters,
    # which themselves are filtered by clusters.last_updated being recent.
    # We compute the article-id whitelist from cluster_articles and pass it as
    # an IN-list filter, plus a 48h published_at floor as defence in depth.
    from datetime import datetime, timezone, timedelta
    _window_cutoff_iso = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

    # 3a. Fetch cluster_articles for the clusters we care about. cluster_ids
    # come from the caller via `clusters` and is a small list (<5K), so we
    # use an IN-list filter on cluster_id to skip unrelated cluster_articles
    # rows (which could be 50K+ if the table accumulated history).
    _cluster_ids = [c["id"] for c in clusters if c.get("id")]
    ca_rows = _paginated_fetch(
        "cluster_articles", "cluster_id,article_id",
        in_column="cluster_id", in_values=_cluster_ids,
    )
    cluster_article_map: dict[str, list[str]] = {}
    for row in ca_rows:
        cluster_article_map.setdefault(row["cluster_id"], []).append(row["article_id"])
    print(f"  cluster_articles: {len(ca_rows)} rows covering {len(cluster_article_map)} clusters")

    # 3b. Build the article-id whitelist from cluster_articles, then fetch
    # only those articles (server-side IN filter). Adds a published_at >=
    # 48h floor as defence in depth so we never pull anything older.
    # Wire fields (is_wire_copy, wire_origin_publisher_id) are required for
    # the ranker's wire-syndication voice collapse.
    _needed_article_ids = list({row["article_id"] for row in ca_rows})
    art_rows = _paginated_fetch(
        "articles",
        "id,source_id,title,summary,full_text,published_at,word_count,"
        "is_wire_copy,wire_origin_publisher_id",
        gte_column="published_at", gte_value=_window_cutoff_iso,
        in_column="id", in_values=_needed_article_ids,
    )
    articles_by_id: dict[str, dict] = {r["id"]: r for r in art_rows}
    print(
        f"  articles: {len(articles_by_id)} rows fetched "
        f"(from {len(_needed_article_ids)} cluster-linked ids, 48h window)"
    )

    # 3c. Fetch bias_scores ONLY for the articles we loaded. Same IN-list
    # pattern. Saves the no-longer-needed bias rows for articles outside
    # the 48h window. Bias scores cascade-delete with articles (migration
    # 046), so 8-day retention means at most 4× this set in the table —
    # filtering down to the current 48h subset cuts ~75% of the rows.
    bs_rows = _paginated_fetch(
        "bias_scores",
        "article_id,political_lean,sensationalism,opinion_fact,factual_rigor,framing,confidence",
        in_column="article_id", in_values=list(articles_by_id.keys()),
    )
    bias_by_article_id: dict[str, dict] = {r["article_id"]: r for r in bs_rows}
    print(f"  bias_scores: {len(bias_by_article_id)} rows fetched")

    # 3d. Re-rank each cluster using in-memory data (no per-cluster DB queries)
    print("\n  Re-ranking clusters in memory...")
    updates = []
    errors = 0

    # 2026-05-28 — corpus-size proxy for the adaptive is_headline band must
    # reflect THIS RUN's recent corpus, not the all-time articles_by_id snapshot
    # (8-day retention × 5K/day = 40K+ → always lands in busy-mode, killing
    # slow-day headlines). Use the count of articles published in the last 48h
    # as a stable, window-relative proxy. Matches main.py's len(stored_articles).
    from datetime import datetime, timezone, timedelta
    _cutoff = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
    corpus_articles_window = sum(
        1 for r in articles_by_id.values()
        if (r.get("published_at") or "") >= _cutoff
    )
    print(f"  Corpus window (last 48h): {corpus_articles_window} articles "
          f"(of {len(articles_by_id)} total in DB)")

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

        # Re-categorize from the polished cluster title + summary (+ members),
        # not just articles[:3] which on an over-merged cluster mislabels the
        # story (2026-07-01 review CAT-1/CAT-2). Members here carry full_text,
        # so the member-fallback path is strong when the title is thin.
        try:
            best_cat = categorize_cluster(
                cluster.get("title", "") or "",
                cluster.get("summary", "") or "",
                articles,
            )
            category = map_to_desk(best_cat)
        except Exception:
            category = cluster.get("category", "politics")

        # Read editorial intelligence from DB (Gemini-generated, may be NULL)
        editorial_importance = cluster.get("editorial_importance")
        story_type = cluster.get("story_type")

        # Run v5.1 ranker — pass sections for US-only divergence damper
        cluster_sections = cluster.get("sections") or [cluster.get("section", "world")]
        mega_capped = bool(cluster.get("mega_cluster_capped", False))
        try:
            # 2026-05-24 v2 — pass cluster dict so ranker can read _cohesion
            # stashed by Phase 5 (only present on >=20-article clusters).
            # For rerank, _cohesion is absent (we didn't re-run clustering),
            # so ranker falls back to the default 60 for cohesion_score.
            # is_headline + headline_confidence still get a correct value
            # because the coverage + authority/spectrum gates are computed
            # fresh from the rerank-time data.
            result = rank_importance(
                articles, sources, bias_scores,
                cluster_confidence=cluster_confidence,
                category=category,
                editorial_importance=editorial_importance,
                sections=cluster_sections,
                mega_capped=mega_capped,
                cluster=cluster,
                # 2026-05-28 fix — `articles_by_id` is the all-time DB
                # article snapshot (often 40K+), which forced the
                # is_headline adaptive band to ALWAYS pick busy-mode
                # thresholds (rank>=45, conf>=60) regardless of how
                # quiet the actual news day was. That silently
                # OVERWROTE is_headline=true with is_headline=false on
                # every cluster main.py just marked, producing the
                # "0 headlines" homepage. Use the same window-relative
                # count main.py uses: the unique published_at-recent
                # articles touching THIS run's clusters.
                corpus_size=corpus_articles_window,
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

        # `source_count` is OWNED BY CLUSTERING (Phase 5 cap +
        # wire-aware voice collapse). Recomputing it here from raw
        # cluster_articles rows bypasses both — wire fields aren't even
        # persisted on the articles table. Keep DB-stored value; expose
        # the raw count locally only for the diagnostic print below.
        raw_source_count = len({a["source_id"] for a in articles if a.get("source_id")})
        db_source_count = cluster.get("source_count", raw_source_count)
        updates.append({
            "id": cid,
            "headline_rank": new_rank,
            "importance_score": result["importance_score"],
            "divergence_score": result["divergence_score"],
            "coverage_velocity": result["coverage_velocity"],
            "content_type": content_type,
            "category": category,
            "source_count": db_source_count,  # for diagnostic print only; NOT written back
            "_articles": articles,
            "_bias_scores": bias_scores,
            "is_headline": result.get("is_headline", False),
            "headline_confidence": result.get("headline_confidence", 0),
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

    apply_feed_ordering(updates, sources)

    # Diagnostic: top 15 of the single feed.
    sorted_updates = sorted(
        updates, key=lambda u: u.get("rank_world", 0), reverse=True
    )
    print("\n  --- Top 15 by rank_world ---")
    for j, u in enumerate(sorted_updates[:15]):
        title = next(
            (c["title"] for c in clusters if c["id"] == u["id"]), "?"
        )[:60]
        print(
            f"  {j+1:2}. [{u.get('rank_world', 0):5.1f}] "
            f"{u['source_count']:2}src {u.get('category',''):12} {title}"
        )

    if dry_run:
        print(f"\n  DRY RUN — no writes. Re-run without --dry-run to apply.")
        return len(updates)

    # 4. Write back to Supabase in batches (16 concurrent workers).
    print(f"\n[4/4] Writing {len(updates)} updates to Supabase (batched, 16 workers)...")
    # source_count is intentionally omitted — owned by clustering
    # (Phase 5 cap + wire-aware voice collapse). Writing it from rerank
    # overwrites both, producing the 217-source mega-cluster regression.
    #
    # 2026-05-22 — last_updated MUST be explicitly set. Previously omitted;
    # if a write failed silently (see below), the frontend freshness filter
    # still favored the stale story because last_updated hadn't advanced.
    # Caused the 13-source #1-pin regression: yesterday's headline_rank
    # stayed in place AND the cluster appeared fresh.
    _now_iso = datetime.now(timezone.utc).isoformat()
    write_rows = [
        {
            "id": u["id"],
            "headline_rank": u["headline_rank"],
            "importance_score": u["importance_score"],
            "divergence_score": u["divergence_score"],
            "coverage_velocity": u["coverage_velocity"],
            "content_type": u["content_type"],
            "category": u["category"],
            "rank_world": u.get("rank_world", u["headline_rank"]),
            "last_updated": _now_iso,
            # 2026-05-24 v2 — headline signal (migration 059)
            "is_headline": bool(u.get("is_headline", False)),
            "headline_confidence": int(u.get("headline_confidence", 0)),
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
    failed_ids: list[str] = []

    def _write_chunk(chunk: list[dict]) -> int:
        # 2026-05-22 — single retry with exponential backoff on transient
        # errors. Was: bare `except: continue` silently swallowed every
        # failure → 13-source cluster never got today's rerank value
        # written back → stayed at yesterday's headline_rank.
        ok = 0
        for row in chunk:
            rid = row.pop("id")
            last_err: Exception | None = None
            for attempt in range(2):
                try:
                    supabase.table("story_clusters").update(row).eq("id", rid).execute()
                    ok += 1
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    if attempt == 0:
                        time.sleep(0.5 + (attempt * 0.5))  # 0.5s then give up
            if last_err is not None:
                # Per-row logging so we can grep failures in CI; capture id
                # in failed_ids so we can surface a summary at the end.
                print(f"  [err] Write failed for {rid[:8]} after retry: {last_err}")
                failed_ids.append(rid)
            row["id"] = rid  # restore for caller debugging
        return ok

    with ThreadPoolExecutor(max_workers=16) as write_exec:
        write_futures = [write_exec.submit(_write_chunk, chunk) for chunk in write_chunks]
        for future in as_completed(write_futures):
            try:
                written += future.result()
            except Exception:
                write_errors += WRITE_CHUNK

    elapsed = time.time() - start
    # Per-row failures aggregated separately from chunk-level failures
    # (chunk-level fires only if the whole worker raised, which is rare
    # under the retry-aware _write_chunk above).
    per_row_failures = len(failed_ids)
    print(f"\n  Done. {written} clusters re-ranked in {elapsed:.1f}s"
          + (f" ({write_errors} chunk failures, {per_row_failures} row failures)"
             if (write_errors or per_row_failures) else ""))
    if per_row_failures:
        print(f"  [warn] {per_row_failures} cluster ids failed to update after retry:")
        # Cap printed list at 20 to avoid log flood; full list is in failed_ids
        # if the orchestrator wants to retry them in a follow-up pass.
        for fid in failed_ids[:20]:
            print(f"    - {fid}")
        if per_row_failures > 20:
            print(f"    ... and {per_row_failures - 20} more")
    return written


def main():
    """CLI entry point — loads sources and runs full re-rank."""
    print("=" * 60)
    print(f"void --news re-ranker v6.0 {'(DRY RUN)' if DRY_RUN else ''}")
    print("=" * 60)

    print("\n[1/4] Loading sources...")
    sources = load_sources()
    sources = sync_source_ids(sources)
    matched = sum(1 for s in sources if s.get("db_id"))
    print(f"  {len(sources)} sources loaded, {matched} matched to DB")

    rerank_all_clusters(sources, dry_run=DRY_RUN)


if __name__ == "__main__":
    main()
