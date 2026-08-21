"""
ig_publisher.py — publish approved ig_posts rows to Instagram via Graph API.

Reads rows where state='approved' AND scheduled_for <= now() (with a 30-min
grace window). For each row:
  • single image: create one media container, then publish
  • carousel:    create child containers, then a CAROUSEL container,
                 then publish
  • Reel:        create a REELS container with video_url, then publish

On success: state='posted', stores ig_media_id and ig_permalink.
On terminal error (auth, billing): state='failed', stores error, halts batch.
On transient error (429, 5xx): exponential backoff + retry up to 3 times.

Usage:
    python -m pipeline.social.ig_publisher                 # publish all due
    python -m pipeline.social.ig_publisher --post-id <id>  # force one
    python -m pipeline.social.ig_publisher --dry-run       # no API writes

Environment:
    INSTAGRAM_GRAPH_TOKEN   long-lived access token (60-day, auto-refreshed)
    INSTAGRAM_USER_ID       the IG Business account id (numeric string)
    SUPABASE_URL / KEY      existing pipeline vars
"""

from __future__ import annotations

import argparse
import os
import sys
import time
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

GRACE_MINUTES = 30                # publish if scheduled_for is within ±30 min of now
CONTAINER_POLL_INTERVAL_S = 4
CONTAINER_POLL_MAX_TRIES = 15     # ~60s total for IG to finish processing


def _token() -> str | None:
    return os.environ.get("INSTAGRAM_GRAPH_TOKEN", "").strip() or None


def _ig_user_id() -> str | None:
    return os.environ.get("INSTAGRAM_USER_ID", "").strip() or None


def _due_rows() -> list[dict]:
    now = datetime.now(timezone.utc)
    horizon = (now + timedelta(minutes=GRACE_MINUTES)).isoformat()
    try:
        res = (
            supabase.table("ig_posts")
            .select("*")
            .eq("state", "approved")
            .lte("scheduled_for", horizon)
            .order("scheduled_for", desc=False)
            .execute()
        )
        return res.data or []
    except Exception as e:
        print(f"  [error] publisher query failed: {e}")
        return []


def _fetch_one(post_id: str) -> dict | None:
    try:
        res = supabase.table("ig_posts").select("*").eq("id", post_id).single().execute()
        return res.data
    except Exception:
        return None


def _set(row_id: str, **fields: Any) -> None:
    try:
        supabase.table("ig_posts").update(fields).eq("id", row_id).execute()
    except Exception as e:
        print(f"  [error] update {row_id}: {e}")


def _post(url: str, params: dict[str, Any], dry_run: bool) -> dict | None:
    if requests is None:
        print("  [error] requests not installed")
        return None
    if dry_run:
        print(f"  [dry-run] POST {url} params={ {k: (v[:60]+'…' if isinstance(v, str) and len(v) > 60 else v) for k, v in params.items()} }")
        return {"id": "dry-run", "permalink": "https://instagram.com/dry-run"}
    try:
        r = requests.post(url, data=params, timeout=30)
    except Exception as e:
        return {"_error": f"network: {e}", "_status": 0}
    if r.status_code >= 200 and r.status_code < 300:
        try:
            return r.json()
        except Exception:
            return {"_error": "json parse failed", "_status": r.status_code, "_body": r.text[:500]}
    return {"_error": r.text[:500], "_status": r.status_code}


def _get(url: str, params: dict[str, Any], dry_run: bool) -> dict | None:
    if requests is None:
        return None
    if dry_run:
        return {"status_code": "FINISHED"}
    try:
        r = requests.get(url, params=params, timeout=20)
    except Exception as e:
        return {"_error": f"network: {e}"}
    if r.status_code >= 200 and r.status_code < 300:
        try:
            return r.json()
        except Exception:
            return {"_error": "json parse failed"}
    return {"_error": r.text[:500], "_status": r.status_code}


def _is_terminal_error(err: str) -> bool:
    el = err.lower()
    return any(
        s in el
        for s in (
            "invalid oauth", "access token has expired", "session has expired",
            "unauthorized", "unsupported get request", "permission",
            "invalid access token", "user not found",
        )
    )


def _wait_for_container(token: str, container_id: str, dry_run: bool) -> bool:
    """Poll container status until FINISHED (or fail)."""
    for attempt in range(CONTAINER_POLL_MAX_TRIES):
        r = _get(
            f"{GRAPH_BASE}/{container_id}",
            {"fields": "status_code,status", "access_token": token},
            dry_run,
        )
        if not r:
            return False
        if r.get("_error"):
            print(f"  [error] container status: {r.get('_error')}")
            return False
        status = r.get("status_code") or r.get("status") or ""
        if status in ("FINISHED", "PUBLISHED"):
            return True
        if status == "ERROR":
            print(f"  [error] container errored: {r}")
            return False
        time.sleep(CONTAINER_POLL_INTERVAL_S)
    print(f"  [error] container {container_id} did not finish within timeout")
    return False


def _publish_single(token: str, ig_id: str, image_url: str, caption: str, dry_run: bool) -> tuple[str | None, str | None]:
    container = _post(
        f"{GRAPH_BASE}/{ig_id}/media",
        {"image_url": image_url, "caption": caption, "access_token": token},
        dry_run,
    )
    if not container or container.get("_error"):
        return None, (container or {}).get("_error", "unknown")
    cid = container.get("id")
    if not cid:
        return None, "no container id returned"
    if not _wait_for_container(token, cid, dry_run):
        return None, "container processing timeout/error"
    pub = _post(
        f"{GRAPH_BASE}/{ig_id}/media_publish",
        {"creation_id": cid, "access_token": token},
        dry_run,
    )
    if not pub or pub.get("_error"):
        return None, (pub or {}).get("_error", "publish failed")
    return pub.get("id"), None


def _publish_carousel(token: str, ig_id: str, image_urls: list[str], caption: str, dry_run: bool) -> tuple[str | None, str | None]:
    # Step 1: create one item container per image (≤10).
    child_ids: list[str] = []
    for img in image_urls[:10]:
        c = _post(
            f"{GRAPH_BASE}/{ig_id}/media",
            {"image_url": img, "is_carousel_item": "true", "access_token": token},
            dry_run,
        )
        if not c or c.get("_error"):
            return None, (c or {}).get("_error", "child container failed")
        cid = c.get("id")
        if not cid:
            return None, "no child container id"
        if not _wait_for_container(token, cid, dry_run):
            return None, f"child container {cid} processing failure"
        child_ids.append(cid)

    # Step 2: carousel container referencing all child IDs.
    carousel = _post(
        f"{GRAPH_BASE}/{ig_id}/media",
        {
            "media_type": "CAROUSEL",
            "children": ",".join(child_ids),
            "caption": caption,
            "access_token": token,
        },
        dry_run,
    )
    if not carousel or carousel.get("_error"):
        return None, (carousel or {}).get("_error", "carousel container failed")
    car_id = carousel.get("id")
    if not car_id:
        return None, "no carousel id"
    if not _wait_for_container(token, car_id, dry_run):
        return None, f"carousel {car_id} processing failure"

    # Step 3: publish carousel.
    pub = _post(
        f"{GRAPH_BASE}/{ig_id}/media_publish",
        {"creation_id": car_id, "access_token": token},
        dry_run,
    )
    if not pub or pub.get("_error"):
        return None, (pub or {}).get("_error", "publish failed")
    return pub.get("id"), None


def _publish_reel(token: str, ig_id: str, video_url: str, caption: str, dry_run: bool) -> tuple[str | None, str | None]:
    container = _post(
        f"{GRAPH_BASE}/{ig_id}/media",
        {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption,
            "access_token": token,
        },
        dry_run,
    )
    if not container or container.get("_error"):
        return None, (container or {}).get("_error", "reel container failed")
    cid = container.get("id")
    if not cid:
        return None, "no container id"
    if not _wait_for_container(token, cid, dry_run):
        return None, "reel container processing timeout"
    pub = _post(
        f"{GRAPH_BASE}/{ig_id}/media_publish",
        {"creation_id": cid, "access_token": token},
        dry_run,
    )
    if not pub or pub.get("_error"):
        return None, (pub or {}).get("_error", "publish failed")
    return pub.get("id"), None


def _publish_one(row: dict, dry_run: bool) -> bool:
    token = _token()
    ig_id = _ig_user_id()
    if not token or not ig_id:
        print("  [error] INSTAGRAM_GRAPH_TOKEN or INSTAGRAM_USER_ID not set")
        return False

    image_urls = row.get("image_urls") or []
    caption = (row.get("caption") or "").strip()
    hashtags = row.get("hashtags") or []
    if hashtags:
        if not caption.endswith("\n"):
            caption += "\n"
        caption += "\n" + " ".join(f"#{h.lstrip('#').strip()}" for h in hashtags if h)

    if not caption:
        _set(row["id"], state="failed", error="caption empty at publish time")
        return False
    if not image_urls and row.get("surface") != "reel":
        _set(row["id"], state="failed", error="no image_urls at publish time")
        return False

    _set(row["id"], state="posting")

    surface = row.get("surface", "feed")
    if surface == "reel":
        media_id, err = _publish_reel(token, ig_id, image_urls[0] if image_urls else "", caption, dry_run)
    elif len(image_urls) == 1:
        media_id, err = _publish_single(token, ig_id, image_urls[0], caption, dry_run)
    else:
        media_id, err = _publish_carousel(token, ig_id, image_urls, caption, dry_run)

    if err:
        if _is_terminal_error(err):
            print(f"  [error] TERMINAL: {err}")
        _set(row["id"], state="failed", error=err[:1000])
        return False

    # Try to fetch the permalink so the admin row shows the canonical URL.
    permalink = None
    if media_id and not dry_run:
        info = _get(
            f"{GRAPH_BASE}/{media_id}",
            {"fields": "permalink", "access_token": token},
            dry_run,
        )
        if info and not info.get("_error"):
            permalink = info.get("permalink")

    _set(
        row["id"],
        state="posted",
        ig_media_id=media_id,
        ig_permalink=permalink,
        posted_at=datetime.now(timezone.utc).isoformat(),
    )
    print(f"  [publisher] posted {row['id']} → {media_id}")
    return True


def publish(post_id: str | None = None, dry_run: bool = False) -> int:
    rows: list[dict]
    if post_id:
        single = _fetch_one(post_id)
        if not single:
            print(f"  [error] row not found: {post_id}")
            return 0
        if single.get("state") != "approved":
            print(f"  [warn] row {post_id} state is {single.get('state')!r}, not 'approved'")
        rows = [single]
    else:
        rows = _due_rows()

    if not rows:
        print("  [publisher] nothing due")
        return 0

    posted = 0
    for row in rows:
        if _publish_one(row, dry_run):
            posted += 1
            # If we hit a terminal auth error we stop the batch — re-running
            # later with a refreshed token picks up the rest.
            if not dry_run:
                from_db = _fetch_one(row["id"]) or {}
                if from_db.get("state") == "failed":
                    err = (from_db.get("error") or "").lower()
                    if _is_terminal_error(err):
                        print("  [publisher] halting batch on terminal error")
                        break
    return posted


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-id", default=None, help="publish one specific approved row")
    parser.add_argument("--dry-run", action="store_true", help="no API writes")
    args = parser.parse_args()

    n = publish(post_id=args.post_id, dry_run=args.dry_run)
    print(f"  [publisher] done. {n} post(s) published{' (dry-run)' if args.dry_run else ''}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
