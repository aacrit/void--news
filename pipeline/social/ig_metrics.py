"""
ig_metrics.py — pull Instagram insights for recently-posted rows.

For each ig_posts row with state='posted' and posted_at within the last 30
days, calls Graph API `GET /{media-id}/insights` and merges the response
into ig_posts.metrics. Daily cron at 14:00 UTC.

Usage:
    python -m pipeline.social.ig_metrics              # last 30 days
    python -m pipeline.social.ig_metrics --post-id X  # one post

Environment:
    INSTAGRAM_GRAPH_TOKEN
    INSTAGRAM_USER_ID
    SUPABASE_URL / KEY
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.supabase_client import supabase  # noqa: E402

try:
    import requests
except ImportError:
    requests = None  # type: ignore

GRAPH_API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v21.0")
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

# Metric names per Instagram Graph API. saved + reach + shares + comments work
# for Feed posts; profile_visits + website_clicks are media-level.
FEED_METRICS = ["reach", "saved", "shares", "likes", "comments", "total_interactions"]
# Account-level metrics (separate endpoint).
ACCOUNT_METRICS = ["follower_count", "profile_views", "website_clicks"]


def _token() -> str | None:
    return os.environ.get("INSTAGRAM_GRAPH_TOKEN", "").strip() or None


def _get(url: str, params: dict[str, Any]) -> dict | None:
    if requests is None:
        return None
    try:
        r = requests.get(url, params=params, timeout=20)
    except Exception as e:
        return {"_error": str(e)}
    if r.status_code >= 200 and r.status_code < 300:
        try:
            return r.json()
        except Exception:
            return {"_error": "json parse"}
    return {"_error": r.text[:500], "_status": r.status_code}


def _eligible_rows(post_id: str | None) -> list[dict]:
    if post_id:
        res = supabase.table("ig_posts").select("id, ig_media_id, posted_at, metrics").eq("id", post_id).execute()
        return res.data or []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    res = (
        supabase.table("ig_posts")
        .select("id, ig_media_id, posted_at, metrics")
        .eq("state", "posted")
        .not_.is_("ig_media_id", "null")
        .gte("posted_at", cutoff)
        .order("posted_at", desc=True)
        .limit(200)
        .execute()
    )
    return res.data or []


def _fetch_media_insights(token: str, media_id: str) -> dict[str, int]:
    out: dict[str, int] = {}
    r = _get(
        f"{GRAPH_BASE}/{media_id}/insights",
        {"metric": ",".join(FEED_METRICS), "access_token": token},
    )
    if not r or r.get("_error"):
        # Some metrics may not be available for very-fresh posts; ignore.
        return out
    for item in r.get("data", []) or []:
        name = item.get("name")
        values = item.get("values", []) or []
        if name and values:
            val = values[0].get("value")
            if isinstance(val, (int, float)):
                out[name] = int(val)
    return out


def metrics(post_id: str | None = None) -> int:
    token = _token()
    if not token:
        print("  [error] INSTAGRAM_GRAPH_TOKEN not set")
        return 0

    rows = _eligible_rows(post_id)
    if not rows:
        print("  [metrics] nothing to refresh")
        return 0

    updated = 0
    for row in rows:
        media_id = row.get("ig_media_id")
        if not media_id:
            continue
        data = _fetch_media_insights(token, media_id)
        if not data:
            continue
        merged = {**(row.get("metrics") or {}), **data}
        merged["updated_at"] = datetime.now(timezone.utc).isoformat()
        try:
            supabase.table("ig_posts").update({
                "metrics": merged,
                "metrics_updated_at": merged["updated_at"],
            }).eq("id", row["id"]).execute()
            updated += 1
        except Exception as e:
            print(f"  [error] persist metrics {row['id']}: {e}")
    print(f"  [metrics] refreshed {updated} row(s)")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-id", default=None)
    args = parser.parse_args()
    metrics(post_id=args.post_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
