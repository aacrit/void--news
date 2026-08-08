"""Newspaper of Record — permanent print archive (pipeline step 8f).

Snapshots the day's DISPLAYED top-50 clusters into the permanent, public-read
``printed_days`` / ``printed_stories`` tables (migration 075). Metadata only:
titles, summaries, bias aggregates, and a compact per-source member list (source
name/tier/lean/rigor/url) — NEVER article bodies, so the archive is copyright
clean and tiny.

Distinct from ``cluster_archive`` (016), the rolling 10-day weekly-digest buffer.
This record is permanent and additive.

Design guarantees:
  * NON-FATAL. Every internal step is defensively wrapped; the caller (main.py
    step 8f) also wraps the whole call in try/except. The archive can never fail
    a daily pipeline run.
  * IDEMPOTENT. Re-running for the same ``edition_date`` UPDATES rows in place
    (upsert on ``(printed_on, source_cluster_id)``) and reconciles strays, so
    exactly one coherent edition exists per date. Permalinks (row ids) are
    preserved across same-day reruns.
  * Mirrors the homepage display window EXACTLY: the ``sections @> ['world']``
    set ordered by ``rank_world`` desc, keep ``source_count >= 3``, take the
    first ``limit`` — identical to ``cluster_summarizer.ensure_top50_summary_floor``.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any


# Tier fill order when a huge cluster is capped to `member_cap` members.
_TIER_ORDER = {"us_major": 0, "international": 1, "independent": 2}

# Snapshot columns pulled from story_clusters (no article bodies).
_CLUSTER_COLS = (
    "id,title,summary,category,content_type,story_type,editorial_importance,"
    "summary_tier,rank_world,headline_rank,source_count,divergence_score,"
    "first_published,consensus_points,divergence_points,claim_consensus,"
    "bias_diversity"
)


# ─────────────────────────── generic helpers ────────────────────────────

def _fetch_all(supabase, table: str, select: str, col: str,
               values: list, page: int = 1000, chunk: int = 150) -> list[dict]:
    """Fetch every row matching ``col IN values``, chunking the filter (URL
    length) and paginating each chunk past PostgREST's 1,000-row response cap.
    Uses the repo's ``.range(offset, offset+page-1)`` pagination pattern.
    """
    out: list[dict] = []
    if not values:
        return out
    for i in range(0, len(values), chunk):
        chunk_vals = values[i:i + chunk]
        offset = 0
        while True:
            try:
                res = (
                    supabase.table(table)
                    .select(select)
                    .in_(col, chunk_vals)
                    .range(offset, offset + page - 1)
                    .execute()
                )
            except Exception as e:
                print(f"    [warn] print-archive fetch {table} failed: {e}")
                break
            data = res.data or []
            out.extend(data)
            if len(data) < page:
                break
            offset += page
    return out


def _brief_kw(title: str) -> set[str]:
    """Stemmed content keywords of a title, REUSING the daily-brief matcher so
    threading here is consistent with the brief's continuing-story logic.
    Degrades to an empty set if the brief module is unavailable.
    """
    try:
        from briefing.daily_brief_generator import _brief_title_keywords
        return _brief_title_keywords(title or "")
    except Exception:
        return set()


# ─────────────────────────── member building ────────────────────────────

def _build_members_by_cluster(supabase, cluster_ids: list[str],
                              sources_by_id: dict) -> dict[str, list[dict]]:
    """Return {cluster_id: [member, ...]} with compact per-article members.

    Three batched, paginated queries (no article bodies):
      cluster_articles(cluster_id, article_id)
      articles(id, url, published_at, source_id, is_wire_copy)
      bias_scores(article_id, political_lean, factual_rigor, confidence)
    Source name/tier come from the in-memory ``sources_by_id`` map (no query);
    ``sources_by_id`` is keyed by the DB source id (== articles.source_id).
    """
    by_cluster: dict[str, list[dict]] = {cid: [] for cid in cluster_ids}

    links = _fetch_all(
        supabase, "cluster_articles", "cluster_id,article_id",
        "cluster_id", cluster_ids)
    if not links:
        return by_cluster

    article_ids = sorted({l.get("article_id") for l in links if l.get("article_id")})
    art_to_cluster: dict[str, str] = {}
    for l in links:
        aid, cid = l.get("article_id"), l.get("cluster_id")
        if aid and cid and aid not in art_to_cluster:
            art_to_cluster[aid] = cid

    arts = _fetch_all(
        supabase, "articles", "id,url,published_at,source_id,is_wire_copy",
        "id", article_ids)
    art_by_id = {a.get("id"): a for a in arts}

    bias = _fetch_all(
        supabase, "bias_scores",
        "article_id,political_lean,factual_rigor,confidence",
        "article_id", article_ids)
    bias_by_art = {b.get("article_id"): b for b in bias}

    for aid in article_ids:
        cid = art_to_cluster.get(aid)
        if cid is None or cid not in by_cluster:
            continue
        a = art_by_id.get(aid) or {}
        b = bias_by_art.get(aid) or {}
        src = sources_by_id.get(a.get("source_id")) or {}
        by_cluster[cid].append({
            "source_id": a.get("source_id"),
            "source_name": src.get("name", ""),
            "tier": src.get("tier", "independent"),
            "lean": b.get("political_lean"),
            "rigor": b.get("factual_rigor"),
            "confidence": b.get("confidence"),
            "url": a.get("url"),
            "published_at": a.get("published_at"),
            "is_wire_copy": bool(a.get("is_wire_copy")),
        })
    return by_cluster


def _cap_members(members: list[dict], member_cap: int) -> list[dict]:
    """Cap a cluster's member list. Keep one member per distinct source first,
    then fill by tier (us_major -> international -> independent) up to the cap.
    Order-preserving no-op when already within the cap.
    """
    if len(members) <= member_cap:
        return members

    by_source: dict[Any, list[dict]] = {}
    for m in members:
        by_source.setdefault(m.get("source_id"), []).append(m)

    def _tier_key(m: dict) -> int:
        return _TIER_ORDER.get(m.get("tier"), 3)

    reps = sorted((lst[0] for lst in by_source.values()), key=_tier_key)
    if len(reps) >= member_cap:
        return reps[:member_cap]

    kept = list(reps)
    remaining = sorted(
        (m for lst in by_source.values() for m in lst[1:]), key=_tier_key)
    kept.extend(remaining[: member_cap - len(kept)])
    return kept


# ─────────────────────────────── main API ───────────────────────────────

def archive_printed_edition(supabase, sources_by_id: dict, edition_date,
                            pipeline_run_id=None, limit: int = 50,
                            member_cap: int = 60,
                            thread_lookback_days: int = 7) -> dict:
    """Snapshot today's displayed top-``limit`` into the permanent print archive.

    Returns {stories, threads_new, threads_continued, stats}. Non-fatal: on any
    internal failure it returns partial metrics rather than raising.
    """
    metrics: dict = {"stories": 0, "threads_new": 0, "threads_continued": 0,
                     "stats": {}}
    if isinstance(edition_date, str):
        edition_date = date.fromisoformat(edition_date[:10])

    # ── 1. Select the printed set (homepage display window) ───────────────
    try:
        res = (
            supabase.table("story_clusters")
            .select(_CLUSTER_COLS)
            .contains("sections", ["world"])
            .order("rank_world", desc=True)
            .limit(100)
            .execute()
        )
        rows = res.data or []
    except Exception as e:
        print(f"    [warn] print-archive cluster select failed: {e}")
        return metrics

    printed: list[dict] = []
    for row in rows:
        if len(printed) >= limit:
            break
        if (row.get("source_count") or 0) < 3:
            continue
        printed.append(row)
    if not printed:
        print("    [8f] no clusters in display window; nothing to print")
        return metrics
    for pos, row in enumerate(printed, start=1):
        row["_position"] = pos

    cluster_ids = [r["id"] for r in printed]

    # ── 2. Compact members + denormalized bias scalars ────────────────────
    try:
        members_by_cluster = _build_members_by_cluster(
            supabase, cluster_ids, sources_by_id or {})
    except Exception as e:
        print(f"    [warn] print-archive member build failed: {e}")
        members_by_cluster = {cid: [] for cid in cluster_ids}

    # ── 3. Existing same-day ids (preserve permalinks on rerun) ───────────
    existing_id_by_cluster: dict[str, str] = {}
    try:
        ex = (
            supabase.table("printed_stories")
            .select("id,source_cluster_id")
            .eq("printed_on", edition_date.isoformat())
            .execute()
        )
        for r in ex.data or []:
            if r.get("source_cluster_id") and r.get("id"):
                existing_id_by_cluster[r["source_cluster_id"]] = r["id"]
    except Exception as e:
        print(f"    [warn] print-archive existing-row fetch failed: {e}")

    # Reconcile an id for each of today's rows (reuse existing, else new).
    id_by_cluster: dict[str, str] = {}
    kw_by_cluster: dict[str, set[str]] = {}
    for row in printed:
        cid = row["id"]
        id_by_cluster[cid] = existing_id_by_cluster.get(cid) or str(uuid.uuid4())
        kw_by_cluster[cid] = _brief_kw(row.get("title", ""))

    # ── 4. Threading (best-effort, reuses the brief matcher) ──────────────
    prior_rows: list[dict] = []
    try:
        cutoff = (edition_date - timedelta(days=thread_lookback_days)).isoformat()
        offset = 0
        while True:
            pr = (
                supabase.table("printed_stories")
                .select("id,story_thread_id,title_keywords,source_cluster_id,"
                        "printed_on,edition_position")
                .gte("printed_on", cutoff)
                .lt("printed_on", edition_date.isoformat())
                .order("printed_on", desc=True)
                .range(offset, offset + 999)
                .execute()
            )
            page = pr.data or []
            prior_rows.extend(page)
            if len(page) < 1000:
                break
            offset += 1000
    except Exception as e:
        print(f"    [warn] print-archive prior-printing fetch failed: {e}")
        prior_rows = []

    # Fast-path index: latest prior printing per source_cluster_id.
    prior_by_cluster: dict[str, dict] = {}
    for p in prior_rows:
        scid = p.get("source_cluster_id")
        if not scid:
            continue
        cur = prior_by_cluster.get(scid)
        if cur is None or _prior_rank(p) > _prior_rank(cur):
            prior_by_cluster[scid] = p

    # Pre-parse prior keyword sets for the brief-rule match.
    prior_parsed = [
        (p, set(p.get("title_keywords") or []))
        for p in prior_rows
    ]

    threads_new = 0
    threads_continued = 0
    thread_info: dict[str, tuple[str, str | None]] = {}  # cid -> (thread_id, continues_id)
    for row in printed:
        cid = row["id"]
        own_id = id_by_cluster[cid]
        match = None  # a prior row dict

        # FAST PATH: same source_cluster_id printed in the lookback window.
        fp = prior_by_cluster.get(cid)
        if fp is not None:
            match = fp
        else:
            kw = kw_by_cluster[cid]
            if len(kw) >= 2:
                best = None
                best_key = None
                for p, prev_kw in prior_parsed:
                    if len(prev_kw) < 2:
                        continue
                    shared = len(kw & prev_kw)
                    ok = shared >= 3 or (
                        shared >= 2
                        and shared / max(1, min(len(kw), len(prev_kw))) >= 0.5
                    )
                    if not ok:
                        continue
                    # best = highest shared, tie-break most recent, lowest position
                    key = (shared, _prior_rank(p))
                    if best_key is None or key > best_key:
                        best_key = key
                        best = p
                match = best

        if match is not None:
            thread_id = match.get("story_thread_id") or own_id
            thread_info[cid] = (thread_id, match.get("id"))
            threads_continued += 1
        else:
            thread_info[cid] = (own_id, None)
            threads_new += 1

    # ── 5. Build rows + write idempotently ────────────────────────────────
    story_rows: list[dict] = []
    for row in printed:
        cid = row["id"]
        members = members_by_cluster.get(cid, [])
        member_count = len(members)
        capped = _cap_members(members, member_cap)
        bd = row.get("bias_diversity") or {}
        kw_list = sorted(kw_by_cluster[cid])
        thread_id, continues_id = thread_info[cid]
        search_terms = (" ".join(kw_list) + " " + (row.get("category") or "")).strip()

        story_rows.append({
            "id": id_by_cluster[cid],
            "printed_on": edition_date.isoformat(),
            "edition_position": row["_position"],
            "source_cluster_id": cid,
            "title": row.get("title") or "",
            "summary": row.get("summary"),
            "category": row.get("category"),
            "content_type": row.get("content_type"),
            "story_type": row.get("story_type"),
            "editorial_importance": row.get("editorial_importance"),
            "summary_tier": row.get("summary_tier"),
            "rank_world": row.get("rank_world") or 0,
            "headline_rank": row.get("headline_rank"),
            "source_count": row.get("source_count") or 0,
            "divergence_score": row.get("divergence_score"),
            "first_published": row.get("first_published") or None,
            "consensus_points": row.get("consensus_points"),
            "divergence_points": row.get("divergence_points"),
            "claim_consensus": row.get("claim_consensus"),
            "bias_diversity": bd or None,
            "mean_lean": bd.get("avg_political_lean"),
            "polarization": bd.get("polarization"),
            "lean_spread": bd.get("lean_spread"),
            "aggregate_confidence": bd.get("aggregate_confidence"),
            "members": capped,
            "member_count": member_count,
            "title_keywords": kw_list,
            "story_thread_id": thread_id,
            "continues_printed_id": continues_id,
            "search_terms": search_terms,
        })

    # Resolve the day's world daily_briefs.id (best-effort).
    daily_brief_id = _resolve_daily_brief_id(supabase, pipeline_run_id)

    # 5a. Upsert the day header FIRST (printed_stories FKs printed_on).
    try:
        supabase.table("printed_days").upsert({
            "printed_on": edition_date.isoformat(),
            "pipeline_run_id": pipeline_run_id,
            "story_count": len(story_rows),
            "daily_brief_id": daily_brief_id,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }, on_conflict="printed_on").execute()
    except Exception as e:
        # Retry without the now() literal / brief id in case of type issues.
        print(f"    [warn] print-archive printed_days upsert failed: {e}")
        try:
            supabase.table("printed_days").upsert({
                "printed_on": edition_date.isoformat(),
                "story_count": len(story_rows),
            }, on_conflict="printed_on").execute()
        except Exception as e2:
            print(f"    [warn] print-archive printed_days retry failed: {e2}")
            return metrics

    # 5b. Upsert the stories in place (preserve id on conflict).
    try:
        supabase.table("printed_stories").upsert(
            story_rows, on_conflict="printed_on,source_cluster_id"
        ).execute()
    except Exception as e:
        print(f"    [warn] print-archive printed_stories upsert failed: {e}")
        return metrics

    # 5c. Delete same-day strays (exactly one coherent edition per date).
    try:
        (
            supabase.table("printed_stories")
            .delete()
            .eq("printed_on", edition_date.isoformat())
            .not_.in_("source_cluster_id", cluster_ids)
            .execute()
        )
    except Exception as e:
        print(f"    [warn] print-archive stray cleanup failed: {e}")

    # ── 6. Stats + return ─────────────────────────────────────────────────
    metrics["stories"] = len(story_rows)
    metrics["threads_new"] = threads_new
    metrics["threads_continued"] = threads_continued
    try:
        st = supabase.rpc("printed_archive_stats", {}).execute()
        metrics["stats"] = st.data if isinstance(st.data, dict) else (st.data or {})
    except Exception as e:
        print(f"    [warn] print-archive stats RPC failed: {e}")
    return metrics


# ─────────────────────────── small helpers ──────────────────────────────

def _prior_rank(p: dict) -> tuple:
    """Recency/priority key for a prior printing: most recent date, then the
    strongest (lowest) position. Higher tuple wins."""
    printed_on = str(p.get("printed_on") or "")
    # lower position is stronger -> negate so higher tuple = better
    pos = p.get("edition_position")
    pos = -pos if isinstance(pos, (int, float)) else 0
    return (printed_on, pos)


def _resolve_daily_brief_id(supabase, pipeline_run_id):
    """Best-effort id of the day's world daily brief. Prefer the row from this
    pipeline run; fall back to the most recent world brief. Returns None on any
    failure (the column is nullable)."""
    try:
        if pipeline_run_id:
            r = (
                supabase.table("daily_briefs")
                .select("id")
                .eq("edition", "world")
                .eq("pipeline_run_id", pipeline_run_id)
                .limit(1)
                .execute()
            )
            if r.data:
                return r.data[0].get("id")
        r = (
            supabase.table("daily_briefs")
            .select("id")
            .eq("edition", "world")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if r.data:
            return r.data[0].get("id")
    except Exception:
        pass
    return None
