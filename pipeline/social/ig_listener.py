"""
ig_listener.py — hashtag monitoring + mention archive.

Polls Graph API hashtag_search + top_media for the niche-hashtag stack we
defined in ig_caption.py. Writes engagement opportunities into
ig_hashtag_candidates for the admin to review (we never auto-comment on
others' content — that's a ban path).

Mentions are pushed via webhook; this module is purely for hashtag pulls.

Usage:
    python -m pipeline.social.ig_listener
    python -m pipeline.social.ig_listener --hashtag medialiteracy

Environment:
    INSTAGRAM_GRAPH_TOKEN, INSTAGRAM_USER_ID, SUPABASE_URL/KEY
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
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

HASHTAGS_TO_MONITOR = [
    "medialiteracy",
    "newsmediabias",
    "algorithmaccountability",
    "datajournalism",
    "computationaljournalism",
    "explanatoryjournalism",
]


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


def _resolve_hashtag_id(token: str, user_id: str, name: str) -> str | None:
    r = _get(f"{GRAPH_BASE}/ig_hashtag_search", {"user_id": user_id, "q": name, "access_token": token})
    if not r or r.get("_error"):
        return None
    data = r.get("data") or []
    if data:
        return data[0].get("id")
    return None


def _top_media(token: str, user_id: str, hashtag_id: str) -> list[dict[str, Any]]:
    fields = "id,caption,permalink,like_count,comments_count,timestamp,username"
    r = _get(
        f"{GRAPH_BASE}/{hashtag_id}/top_media",
        {"user_id": user_id, "fields": fields, "access_token": token, "limit": 25},
    )
    if not r or r.get("_error"):
        return []
    return r.get("data") or []


def _record(row: dict[str, Any]) -> bool:
    try:
        supabase.table("ig_hashtag_candidates").upsert(
            row, on_conflict="ig_media_id"
        ).execute()
        return True
    except Exception as e:
        print(f"  [warn] candidate insert: {e}")
        return False


def listen(hashtag: str | None = None) -> int:
    token = os.environ.get("INSTAGRAM_GRAPH_TOKEN", "").strip()
    user_id = os.environ.get("INSTAGRAM_USER_ID", "").strip()
    if not (token and user_id):
        print("  [error] INSTAGRAM_GRAPH_TOKEN / INSTAGRAM_USER_ID not set")
        return 0

    tags = [hashtag] if hashtag else HASHTAGS_TO_MONITOR
    captured = 0
    for tag in tags:
        hid = _resolve_hashtag_id(token, user_id, tag)
        if not hid:
            print(f"  [listener] could not resolve #{tag}")
            continue
        media = _top_media(token, user_id, hid)
        for m in media:
            engagement = (m.get("like_count") or 0) + 3 * (m.get("comments_count") or 0)
            row = {
                "hashtag": tag,
                "ig_media_id": m.get("id"),
                "ig_username": m.get("username"),
                "caption": (m.get("caption") or "")[:600],
                "permalink": m.get("permalink"),
                "engagement_score": engagement,
            }
            if row["ig_media_id"]:
                if _record(row):
                    captured += 1
        print(f"  [listener] #{tag}: {len(media)} media surfaced")
    return captured


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--hashtag", default=None)
    args = p.parse_args()
    n = listen(hashtag=args.hashtag)
    print(f"  [listener] captured {n} candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
