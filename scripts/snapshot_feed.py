#!/usr/bin/env python3
"""Daily feed snapshot — persist the displayed top-50 past DB retention.

Supabase keeps ~1-2 days of clusters, so a lean-label example read off the feed
on Monday is gone by Wednesday. That has made the lean-label P1 unwriteable three
times: the specific cards keep aging out. This captures, once per day, the
displayed feed's lean drivers into a small dated JSON committed to the repo, so
the examples survive and the lean-label analysis can accumulate a real sample
(also feeds the variance derivation for the Branch D floor).

Records per card: rank, title, category, source_count, and the lean drivers
(raw avg_political_lean, lean_spread, polarization, L/C/R segment counts,
aggregate_confidence). No article bodies, so the file stays tiny (~50 rows).

Usage:  python scripts/snapshot_feed.py [--date YYYY-MM-DD] [--out DIR]
Env:    SUPABASE_URL, SUPABASE_KEY
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default=None, help="UTC date stamp (default: today)")
    ap.add_argument("--out", default="data/feed-snapshots")
    ap.add_argument("--limit", type=int, default=50)
    args = ap.parse_args()

    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("[snapshot] SUPABASE_URL / SUPABASE_KEY not set", file=sys.stderr)
        return 2
    from supabase import create_client
    sb = create_client(url, key)

    date = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    res = (
        sb.table("story_clusters")
        .select("id,title,category,source_count,bias_diversity,rank_world")
        .gte("source_count", 3)
        .order("rank_world", desc=True)
        .limit(args.limit)
        .execute()
    )
    rows = []
    for i, c in enumerate(res.data or []):
        bd = c.get("bias_diversity") or {}
        rows.append({
            "rank": i + 1,
            "title": c.get("title"),
            "category": c.get("category"),
            "source_count": c.get("source_count"),
            "raw_lean": bd.get("avg_political_lean"),
            "lean_spread": bd.get("lean_spread"),
            "polarization": bd.get("polarization"),
            "lean_left_count": bd.get("lean_left_count"),
            "lean_center_count": bd.get("lean_center_count"),
            "lean_right_count": bd.get("lean_right_count"),
            "aggregate_confidence": bd.get("aggregate_confidence"),
        })

    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{date}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"date": date, "captured_at": None, "count": len(rows), "feed": rows},
                  fh, ensure_ascii=False, indent=1)
    print(f"[snapshot] wrote {len(rows)} rows -> {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
