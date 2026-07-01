"""
Diagnostic: pipeline health snapshot.

Reports current Supabase state for:
  - Most recent daily_briefs entry per edition (was today's pipeline run successful?)
  - Story cluster size distribution (any mega-cluster pollution remaining?)
  - Article ingestion freshness (when was the last batch ingested?)

Reads SUPABASE_URL and SUPABASE_KEY from environment. No writes.

Usage:
    SUPABASE_URL=https://xxx.supabase.co \\
    SUPABASE_KEY=sb_secret_... \\
    python pipeline/scripts/pipeline_health.py
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.supabase_client import supabase


def _hours_ago(ts: str | None) -> str:
    if not ts:
        return "never"
    try:
        dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return f"unparseable: {ts}"
    delta = datetime.now(timezone.utc) - dt
    hours = delta.total_seconds() / 3600.0
    if hours < 1:
        return f"{int(delta.total_seconds() / 60)} min ago"
    if hours < 48:
        return f"{hours:.1f}h ago"
    return f"{int(hours / 24)}d ago"


def section(title: str) -> None:
    print(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def brief_health() -> None:
    section("DAILY BRIEFS — most recent per edition")
    rows = (
        supabase.table("daily_briefs")
        .select("edition, created_at, tldr_headline, opinion_headline")
        .order("created_at", desc=True)
        .limit(20)
        .execute()
        .data
        or []
    )
    if not rows:
        print("  No daily_briefs rows found.")
        return
    seen: set[str] = set()
    for r in rows:
        ed = r.get("edition", "?")
        if ed in seen:
            continue
        seen.add(ed)
        ts = r.get("created_at", "")
        age = _hours_ago(ts)
        head = (r.get("tldr_headline") or "")[:60]
        opin = (r.get("opinion_headline") or "")[:60]
        print(f"  [{ed:8}] {age:>14}   tldr: {head!r}")
        print(f"  {'':8}  {'':>14}   opin: {opin!r}")


def cluster_health() -> None:
    section("STORY CLUSTERS — size distribution + mega-cluster audit")
    rows = (
        supabase.table("story_clusters")
        .select("id, title, source_count, mega_cluster_capped, mega_cluster_original_count, last_updated")
        .order("source_count", desc=True)
        .limit(20)
        .execute()
        .data
        or []
    )
    if not rows:
        print("  No story_clusters rows found.")
        return
    over = [r for r in rows if (r.get("source_count") or 0) > 75]
    capped = [r for r in rows if r.get("mega_cluster_capped")]
    print(f"  Rows above source_count=75: {len(over)}")
    print(f"  Rows with mega_cluster_capped=TRUE: {len(capped)}")
    if over:
        print("\n  Over-cap rows (POST-MIGRATION-056 these should be empty):")
        for r in over[:10]:
            print(
                f"    {r['source_count']:>4}src  capped={r.get('mega_cluster_capped')}  "
                f"orig={r.get('mega_cluster_original_count') or '-'}  "
                f"{(r.get('title') or '')[:60]!r}"
            )
    if capped:
        print("\n  Top capped rows (ranker should demote these via 0.65x mega_capped):")
        for r in capped[:10]:
            orig = r.get("mega_cluster_original_count") or "?"
            age = _hours_ago(r.get("last_updated"))
            print(
                f"    {r['source_count']:>4}src  orig={orig}  {age:>14}  "
                f"{(r.get('title') or '')[:60]!r}"
            )


def article_health() -> None:
    section("ARTICLES — recent ingestion")
    rows = (
        supabase.table("articles")
        .select("id, published_at, source_id")
        .order("published_at", desc=True)
        .limit(5)
        .execute()
        .data
        or []
    )
    if not rows:
        print("  No articles found.")
        return
    print(f"  Most recent article published: {_hours_ago(rows[0].get('published_at'))}")
    for r in rows[:3]:
        print(f"    {r.get('published_at')}  src={r.get('source_id', '?')[:20]}")


def main() -> int:
    if not os.environ.get("SUPABASE_URL") or not os.environ.get("SUPABASE_KEY"):
        print("ERROR: set SUPABASE_URL and SUPABASE_KEY in env.", file=sys.stderr)
        return 2
    try:
        brief_health()
        cluster_health()
        article_health()
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 1
    print("\nDone.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
