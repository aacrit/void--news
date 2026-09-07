"""The display window: ONE definition of "which clusters the homepage shows".

Before 2026-09-06 four Python predicates approximated the frontend's rule and
each differed from it: export_static (source_count and tier), print_archive
(tier and a non-empty summary), the summary floor (tier, summary and the
raw-excerpt test), the 8d window (source_count only). The frontend
(feedMapping.clusterHasRealSummary + HomeContent's source_count >= 3) is the
rule that decides what a reader sees, so every Python consumer that must
agree with the page (print archive, export, evals, Stage 2 candidate
selection) calls this module.

Mirror of the TypeScript, in order:
  1. source_count >= 3                          (HomeContent filteredStories)
  2. CSAM topic -> keep (headline + sources)     (clusterHasRealSummary)
  3. clean_feed_summary(summary) empty -> drop   (raw excerpt, or nothing left)
  4. summary_tier null/blank -> drop             (never summarized)

The pre-summary passes (8d, 8d.6) deliberately do NOT use this predicate for
their window: they are the passes that create the summary, so they count
source_count >= 3 rows only. They take the window SIZE from feed_config.
"""
from __future__ import annotations

from typing import Iterable, Optional

try:
    from utils.summary_hygiene import clean_feed_summary, is_csam_topic
except ImportError:  # imported as pipeline.utils.display_window
    from pipeline.utils.summary_hygiene import clean_feed_summary, is_csam_topic

MIN_SOURCES = 3


def is_displayable(row: dict) -> bool:
    """True when the frontend would render this cluster as a card."""
    if (row.get("source_count") or 0) < MIN_SOURCES:
        return False
    title = row.get("title") or ""
    summary = row.get("summary") or ""
    if is_csam_topic(f"{title} {summary}"):
        return True
    if not clean_feed_summary(summary, title).strip():
        return False
    tier = (row.get("summary_tier") or "").strip()
    if not tier:
        return False
    return True


def filter_displayable(rows: Iterable[dict], limit: int,
                       with_articles: Optional[set] = None) -> list[dict]:
    """The first `limit` displayable rows of `rows` (already in rank order).

    `with_articles`: when given and non-empty, a cluster whose id is absent is a
    ghost (source_count survived a cascade-delete of its links) and is skipped,
    mirroring the frontend's empty-Deep-Dive drop. An empty set means the
    membership read failed, so it is ignored (fail open), never treated as
    "everything is a ghost".
    """
    out: list[dict] = []
    for row in rows:
        if len(out) >= limit:
            break
        if with_articles and row.get("id") not in with_articles:
            continue
        if not is_displayable(row):
            continue
        out.append(row)
    return out


def fetch_display_pool(supabase, edition: str = "world", pool: int = 100,
                       columns: str = "id,title,summary,summary_tier,source_count,"
                                      "rank_world,headline_rank,category,content_type") -> list[dict]:
    """Top `pool` clusters by rank_world for `edition`, via the supabase shim."""
    res = (
        supabase.table("story_clusters")
        .select(columns)
        .contains("sections", [edition])
        .order("rank_world", desc=True)
        .limit(pool)
        .execute()
    )
    return list(res.data or [])


def fetch_display_pool_sqlite(conn, pool: int = 100) -> list[dict]:
    """Same pool read straight from sqlite3 (export_static's path)."""
    conn.row_factory = __import__("sqlite3").Row
    rows = conn.execute(
        "SELECT * FROM story_clusters WHERE sections LIKE '%world%' "
        "ORDER BY CAST(rank_world AS REAL) DESC LIMIT ?", (pool,)
    ).fetchall()
    return [dict(r) for r in rows]
