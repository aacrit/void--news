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
from datetime import datetime, timezone
from pathlib import Path

# Add pipeline root to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.supabase_client import supabase
from ranker.importance_ranker import rank_importance
from ranker.feed_ranker import apply_feed_ordering
from categorizer.auto_categorize import categorize_article, map_to_desk

SOURCES_PATH = Path(__file__).parent.parent / "data" / "sources.json"
DRY_RUN = "--dry-run" in sys.argv
# `--all` re-ranks every cluster the old way (orphans included). Kept for audits
# that want to compare the two paths on a real state DB; production never uses it.
RANK_ALL = "--all" in sys.argv

# ---------------------------------------------------------------------------
# WHICH CLUSTERS ARE WORTH RANKING (P2-1, rev 85)
# ---------------------------------------------------------------------------
# Step 8c re-ranked every cluster in the table: 15,566 on run #385, in 637 s,
# of which about 11,800 were one- or two-source orphans. Nothing downstream can
# show an orphan. The candidate bench (`display_window.select_candidates`) and
# the display predicate (`is_displayable`) both refuse any row under
# MIN_SOURCES, so an orphan's rank only ever decided ONE thing: whether it sat
# among the top POOL rows by rank_world and pushed a candidate out of the pool.
#
# So the pool-eligible clusters are ranked exactly as before, and every orphan is
# parked at ORPHAN_RANK_FLOOR, or one point under the lowest rank this run wrote
# if that is lower (`parking_floor`), so it sits below every ranked row. Orphans
# keep their headline_rank and every other column as they are.
#
# Measured on the 2026-10-01 state snapshot (15,430 clusters, 623 eligible): the
# old path took 523 s, this one 60 s; the 35-candidate bench was identical in
# order, and so was the eligible ordering down to position 178.
#
# What this can change, stated rather than hoped: apply_feed_ordering's
# same-event cap and its two top-80 scans used to see orphans too, so an orphan
# that out-ranked a displayable cluster could take one of an event's two kept
# slots or a place in the scan window. That interaction let a row that can never
# be shown decay one that can. Without orphans the eligible clusters are ordered
# on their own merits, and the pool can no longer be crowded by rows the bench
# then throws away. tests/test_rerank_pool.py asserts the candidate bench is
# identical on a synthetic day where orphans rank below the displayable set
# (the normal case: the single-source gate is 0.65x) and that the floor holds.
try:
    from utils.display_window import MIN_SOURCES as POOL_MIN_SOURCES
except ImportError:  # imported as pipeline.rerank
    from pipeline.utils.display_window import MIN_SOURCES as POOL_MIN_SOURCES

ORPHAN_RANK_FLOOR = -100.0


def parking_floor(ranked_rows: list[dict]) -> float:
    """The rank_world an orphan is parked at: below every ranked row."""
    lowest = min((float(r.get("rank_world") or 0) for r in ranked_rows), default=0.0)
    return round(min(ORPHAN_RANK_FLOOR, lowest - 1.0), 2)


def is_pool_eligible(row: dict) -> bool:
    """True when a cluster can reach the candidate bench (source_count >= 3)."""
    try:
        return int(float(row.get("source_count") or 0)) >= POOL_MIN_SOURCES
    except (TypeError, ValueError):
        return False


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


def rerank_all_clusters(sources: list[dict], dry_run: bool = False,
                        run_id: str | None = None, pool_only: bool = True) -> int:
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
        pool_only: rank only clusters that can reach the candidate bench and
            park the rest at ORPHAN_RANK_FLOOR (see the note above
            is_pool_eligible). False is the pre-rev-85 path, for audits.

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
            # story_type / editorial_importance intentionally NOT selected
            # (2026-08-10 deterministic-ranking): nothing in the ranking path
            # reads them anymore.
            "id,title,category,section,sections,content_type,headline_rank,source_count,"
            "mega_cluster_capped,first_published,rank_world"
        )
    except Exception:
        try:
            clusters = _fetch_all_clusters(
                "id,title,category,section,sections,content_type,headline_rank,source_count,"
                "mega_cluster_capped,first_published"
            )
        except Exception:
            clusters = _fetch_all_clusters(
                "id,title,category,section,sections,content_type,headline_rank,source_count"
            )
    print(f"  {len(clusters)} clusters found")

    if not clusters:
        print("  No clusters to re-rank.")
        return 0

    # Orphans are parked, not ranked (see is_pool_eligible). Every cluster still
    # contributes its articles to the corpus-size count below, so the adaptive
    # is_headline band sees exactly the corpus it saw before.
    all_clusters = clusters
    if pool_only:
        orphans = [c for c in clusters if not is_pool_eligible(c)]
        clusters = [c for c in clusters if is_pool_eligible(c)]
        print(f"  {len(clusters)} pool-eligible (source_count >= {POOL_MIN_SOURCES}) "
              f"ranked; {len(orphans)} orphans parked at {ORPHAN_RANK_FLOOR}")
    else:
        orphans = []

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
    # COUPLING: this 48h window must stay >= main.py's cluster retention
    # window (2 days on first_published). Clusters whose articles all fall
    # outside this window are skipped and keep a stale rank_world; today
    # retention deletes them first, but widening retention without widening
    # this window re-opens the 2026-05-22 stale-pin regression.
    _window_cutoff_iso = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()

    # 3a. Fetch cluster_articles for the clusters we care about. cluster_ids
    # come from the caller via `clusters` and is a small list (<5K), so we
    # use an IN-list filter on cluster_id to skip unrelated cluster_articles
    # rows (which could be 50K+ if the table accumulated history).
    _cluster_ids = [c["id"] for c in all_clusters if c.get("id")]
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
    _ranked_ids = {c["id"] for c in clusters if c.get("id")}
    _needed_article_ids = list({row["article_id"] for row in ca_rows
                                if row["cluster_id"] in _ranked_ids})
    art_rows = _paginated_fetch(
        "articles",
        "id,source_id,title,summary,full_text,published_at,word_count,"
        "is_wire_copy,wire_origin_publisher_id",
        gte_column="published_at", gte_value=_window_cutoff_iso,
        in_column="id", in_values=_needed_article_ids,
    )
    articles_by_id: dict[str, dict] = {r["id"]: r for r in art_rows}
    # Articles that belong ONLY to parked orphans: id and published_at, which is
    # all the corpus-size count below reads. No bodies, no bias rows.
    _needed_set = set(_needed_article_ids)
    _orphan_only_ids = list({row["article_id"] for row in ca_rows} - _needed_set)
    corpus_published: dict[str, str] = {
        r["id"]: (r.get("published_at") or "") for r in art_rows}
    if _orphan_only_ids:
        for r in _paginated_fetch(
            "articles", "id,published_at",
            gte_column="published_at", gte_value=_window_cutoff_iso,
            in_column="id", in_values=_orphan_only_ids,
        ):
            corpus_published[r["id"]] = r.get("published_at") or ""
    print(
        f"  articles: {len(articles_by_id)} rows fetched "
        f"(from {len(_needed_article_ids)} cluster-linked ids, 48h window)"
        + (f"; {len(corpus_published) - len(articles_by_id)} orphan-only ids "
           f"read for the corpus count" if _orphan_only_ids else "")
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
        1 for pub in corpus_published.values() if pub >= _cutoff
    )
    print(f"  Corpus window (last 48h): {corpus_articles_window} articles "
          f"(of {len(corpus_published)} total in DB)")

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

        # Re-categorize. Headline-primary (O10): the cluster headline is the
        # cleanest topical signal and is immune to the off-topic members an
        # over-merged cluster accumulates; fall back to a wide member-sample
        # vote only when the headline is too vague. This MUST mirror main.py's
        # step-7 categorization — the holistic re-ranker runs last and writes
        # the final category, so without this it overwrote O10 with the old
        # 3-article vote (e.g. a SCOTUS ruling mislabeled "health"). (2026-06-28)
        try:
            cluster_title = (cluster.get("title") or "").strip()
            headline_cats = (
                categorize_article(
                    {"title": cluster_title, "summary": "", "full_text": ""}
                )
                if cluster_title
                else []
            )
            if headline_cats:
                # Trust the headline category, including "general" (e.g. an
                # accident headline); member-vote only when there is no
                # headline, so the polluted member sample can't re-mislabel a
                # cluster the headline already classified. (2026-06-29)
                best_cat = headline_cats[0]
            else:
                cat_votes: dict[str, int] = {}
                for art in articles[:8]:
                    for cat in categorize_article(art):
                        cat_votes[cat] = cat_votes.get(cat, 0) + 1
                best_cat = (
                    max(cat_votes, key=cat_votes.get) if cat_votes else "politics"
                )
            category = map_to_desk(best_cat)
        except Exception:
            category = cluster.get("category", "politics")

        # 2026-08-10 (deterministic-ranking): the Gemini editorial_importance
        # and story_type fields are NO LONGER read into the ranking path.
        # rank_importance is ei-neutral (v6.4) and apply_feed_ordering dropped
        # its story_type gates + ei nudge, so nothing downstream would consume
        # them. They are left in the DB for other (non-ordering) consumers.

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
                editorial_importance=None,  # severed 2026-08-10 (ei-neutral)
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

        # 2026-08-10 (deterministic-ranking): the story_type gates were removed
        # from apply_feed_ordering, so story_type is no longer threaded into the
        # update dict below. rank_world is now a pure function of the
        # deterministic headline_rank + the deterministic feed-ordering guards.

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
            # story_type / editorial_importance intentionally NOT threaded here
            # (2026-08-10 deterministic-ranking): apply_feed_ordering no longer
            # reads them, so passing them would be dead weight.
            # first_published feeds the deterministic longevity signal only;
            # diagnostic/ordering, NOT written back.
            "first_published": cluster.get("first_published"),
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

    # 4. Write back to Supabase with CHUNKED BULK UPSERTS.
    #
    # 2026-08-11 (pipeline-perf-writes) — replaces the previous per-row
    # UPDATE loop (one HTTP UPDATE per cluster across 16 concurrent workers).
    # On the profiled 107-min run that loop issued ~9,493 individual UPDATEs
    # and triggered HTTP/2 "Server disconnected" / ConnectionTerminated retry
    # storms (~62 row failures). We now send ~500 rows per upsert call
    # (~19 calls total) via PostgREST's bulk `upsert(..., on_conflict="id")`.
    #
    # VALUE-IDENTICAL GUARANTEE: `write_rows` is built EXACTLY as before —
    # same keys, same values, computed by the same code path. The ONLY change
    # is the transport (one bulk upsert per 500 rows instead of one UPDATE per
    # row). Because every `id` here was just fetched from story_clusters this
    # run, `on_conflict="id"` always resolves to the UPDATE branch and touches
    # only the columns present in each row (all others retain their stored
    # values), so the effect is byte-identical to the old per-row .update(row).
    print(f"\n[4/4] Writing {len(updates)} updates to Supabase (bulk upsert, 500/chunk)...")
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

    WRITE_CHUNK = 500
    write_chunks = [
        write_rows[i:i + WRITE_CHUNK]
        for i in range(0, len(write_rows), WRITE_CHUNK)
    ]

    intended_ids = {r["id"] for r in write_rows}
    written_ids: set[str] = set()
    chunk_failures = 0

    def _upsert_chunk(chunk: list[dict]) -> list[str]:
        # Bounded exponential backoff on transient transport drops only
        # (Server disconnected / reset / read timeout); 3 attempts max, so a
        # bad chunk fails fast and visibly instead of stalling the run.
        _MARKERS = (
            "server disconnected", "remoteprotocolerror", "remote protocol",
            "connection reset", "connection aborted", "connection closed",
            "connectionerror", "connecterror", "readtimeout", "read timeout",
            "writetimeout", "connecttimeout", "pooltimeout", "httpcore",
            "protocolerror", "broken pipe", "eof occurred", "timed out",
            "temporarily unavailable", "connection refused",
        )
        last_err: Exception | None = None
        for attempt in range(3):
            try:
                res = (
                    supabase.table("story_clusters")
                    .upsert(chunk, on_conflict="id")
                    .execute()
                )
                # PostgREST returns the affected rows; use them to prove the
                # write landed rather than assuming success.
                return [r["id"] for r in (res.data or []) if r.get("id")]
            except Exception as e:
                last_err = e
                s = (str(e) + " " + type(e).__name__).lower()
                transient = any(m in s for m in _MARKERS)
                if transient and attempt < 2:
                    backoff = 0.75 * (2 ** attempt)  # 0.75s, 1.5s — bounded
                    print(f"  [warn] upsert chunk transport drop "
                          f"(retry {attempt+1}/2, backoff {backoff:.2f}s): {e}")
                    time.sleep(backoff)
                    continue
                break
        print(f"  [err] Bulk upsert chunk failed after retries: {last_err}")
        return []

    for chunk in write_chunks:
        written_ids.update(_upsert_chunk(chunk))

    # Park the orphans. Only rank_world moves (headline_rank and the rest stay
    # as clustering and step 7 left them), and only on rows not already parked,
    # so a day's write is this run's new orphans rather than all of them.
    #
    # The floor is ORPHAN_RANK_FLOOR or one point under the lowest rank written
    # above, whichever is lower, so no eligible row can ever sit beneath an orphan
    # (the strictly decreasing encoding can walk a long clamped tail downwards).
    floor = parking_floor(write_rows)
    _park = [c["id"] for c in orphans if c.get("id") and (
        c.get("rank_world") is None
        or float(c.get("rank_world") or 0) > floor)]
    parked = 0
    for i in range(0, len(_park), 500):
        batch = _park[i:i + 500]
        try:
            supabase.table("story_clusters").update(
                {"rank_world": floor}).in_("id", batch).execute()
            parked += len(batch)
        except Exception as e:
            print(f"  [err] parking {len(batch)} orphans failed: {e}")
    if orphans:
        print(f"  Parked {parked} of {len(_park)} orphans at {floor} "
              f"({len(orphans) - len(_park)} already there)")

    written = len(written_ids)
    missing_ids = intended_ids - written_ids
    chunk_failures = len(missing_ids)

    elapsed = time.time() - start
    # Post-write assertion: every intended row must come back in an upsert
    # response. A shortfall means a silent drop (the exact failure class the
    # old per-row loop hid); surface it loudly instead of pinning stale ranks.
    print(f"\n  Done. {written}/{len(write_rows)} clusters re-ranked in {elapsed:.1f}s"
          + (f" ({chunk_failures} rows NOT confirmed written)" if chunk_failures else ""))
    if missing_ids:
        print(f"  [warn] {len(missing_ids)} cluster ids were NOT confirmed by the "
              f"upsert response (possible silent drop):")
        for fid in list(missing_ids)[:20]:
            print(f"    - {fid}")
        if len(missing_ids) > 20:
            print(f"    ... and {len(missing_ids) - 20} more")
        # A silent re-rank drop is a pipeline error, not a warning: from
        # 2026-08-11 to 2026-09-06 every run printed this block while the end
        # of run summary said "Errors: 0" (that counter only counted RSS fetch
        # errors), so the dead re-rank went unnoticed for weeks.
        if run_id:
            try:
                from utils.supabase_client import append_pipeline_run_errors
                append_pipeline_run_errors(run_id, [{
                    "stage": "8c-rerank",
                    "error": (f"{len(missing_ids)} of {len(write_rows)} re-ranked rows "
                              f"not confirmed written (bulk upsert failed)"),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }])
            except Exception as _e:
                print(f"  [warn] could not record re-rank error on the run: {_e}")
    else:
        print(f"  [ok] Write count matches intended ({written} == {len(write_rows)}).")
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

    rerank_all_clusters(sources, dry_run=DRY_RUN, pool_only=not RANK_ALL)


if __name__ == "__main__":
    main()
