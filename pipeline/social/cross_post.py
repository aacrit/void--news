"""
cross_post.py — mirror a posted IG row to Bluesky (atproto).

Threads auto-forks from IG natively. LinkedIn requires manual paste because
the public LinkedIn API is gated and the long-form caption deserves a human
voice. Bluesky is the third public surface and supports up to 4 images per
post and 300 chars of text.

Runs as the last step of the publisher cron. Reads ig_posts rows where
state='posted' AND bluesky_uri IS NULL.

Usage:
    python -m pipeline.social.cross_post                       # all eligible
    python -m pipeline.social.cross_post --post-id <uuid>      # one row

Environment:
    BLUESKY_HANDLE          handle (e.g. void.news.bsky.social or custom)
    BLUESKY_APP_PASSWORD    app password from bsky settings → app passwords
"""

from __future__ import annotations

import argparse
import io
import os
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.supabase_client import supabase  # noqa: E402

try:
    import requests
except ImportError:
    requests = None  # type: ignore

try:
    from atproto import Client as AtClient  # type: ignore
    ATPROTO_AVAILABLE = True
except ImportError:
    ATPROTO_AVAILABLE = False

BLUESKY_TEXT_LIMIT = 300
BLUESKY_IMAGE_MAX = 4
BLUESKY_IMAGE_BYTES = 976_560  # ~1MB Bluesky cap; 950KB safe margin


def _eligible_rows(post_id: str | None) -> list[dict]:
    if post_id:
        res = supabase.table("ig_posts").select("*").eq("id", post_id).execute()
        return res.data or []
    res = (
        supabase.table("ig_posts")
        .select("*")
        .eq("state", "posted")
        .is_("bluesky_uri", "null")
        .order("posted_at", desc=False)
        .limit(20)
        .execute()
    )
    return res.data or []


def _download_image(url: str) -> bytes | None:
    if requests is None:
        print("  [error] requests not installed")
        return None
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            return None
        return r.content
    except Exception as e:
        print(f"  [error] download {url}: {e}")
        return None


def _compress_if_needed(data: bytes) -> bytes:
    if len(data) <= BLUESKY_IMAGE_BYTES:
        return data
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        quality = 90
        while quality > 40:
            out = io.BytesIO()
            img.save(out, format="JPEG", quality=quality, optimize=True)
            buf = out.getvalue()
            if len(buf) <= BLUESKY_IMAGE_BYTES:
                return buf
            quality -= 10
        return buf  # best effort
    except Exception as e:
        print(f"  [warn] compress failed: {e}")
        return data[:BLUESKY_IMAGE_BYTES]


def _build_text(row: dict[str, Any]) -> str:
    caption = (row.get("caption") or "").strip()
    if not caption:
        return ""

    # Drop hashtag chunk if present at the end of the caption.
    lines = caption.splitlines()
    cleaned_lines: list[str] = []
    for line in lines:
        if line.startswith("#") and all(tok.startswith("#") for tok in line.split() if tok):
            continue
        cleaned_lines.append(line)
    body = "\n".join(cleaned_lines).strip()

    # Keep 2 niche hashtags max — Bluesky doesn't reward hashtag walls.
    pool = ["#medialiteracy", "#journalism"]
    if len(body) + 1 + sum(len(t) + 1 for t in pool) > BLUESKY_TEXT_LIMIT:
        # Trim the body to fit
        slack = BLUESKY_TEXT_LIMIT - sum(len(t) + 1 for t in pool) - 1
        body = body[: max(0, slack - 1)].rstrip()
        if not body.endswith(("…", ".", "!", "?")):
            body += "…"
    return (body + "\n" + " ".join(pool)).strip()


def _mark(row_id: str, uri: str | None, error: str | None = None) -> None:
    payload: dict[str, Any] = {}
    if uri:
        payload["bluesky_uri"] = uri
    if error:
        # Don't clobber a real ig publish error — only set if absent.
        payload["error"] = error[:500]
    if not payload:
        return
    try:
        supabase.table("ig_posts").update(payload).eq("id", row_id).execute()
    except Exception as e:
        print(f"  [error] mark {row_id}: {e}")


def cross_post(post_id: str | None = None, dry_run: bool = False) -> int:
    if not ATPROTO_AVAILABLE:
        print("  [error] atproto not installed. pip install atproto")
        return 0

    handle = os.environ.get("BLUESKY_HANDLE", "").strip()
    password = os.environ.get("BLUESKY_APP_PASSWORD", "").strip()
    if not (handle and password):
        print("  [warn] BLUESKY_HANDLE / BLUESKY_APP_PASSWORD not set; skipping")
        return 0

    rows = _eligible_rows(post_id)
    if not rows:
        print("  [cross-post] nothing to mirror")
        return 0

    client = AtClient()
    try:
        client.login(handle, password)
    except Exception as e:
        print(f"  [error] bluesky login: {e}")
        return 0

    done = 0
    for row in rows:
        urls = (row.get("image_urls") or [])[:BLUESKY_IMAGE_MAX]
        if not urls:
            continue
        text = _build_text(row)
        if not text:
            continue

        if dry_run:
            print(f"  [dry-run] would post to bluesky: {text[:80]}…")
            done += 1
            continue

        image_blobs: list[tuple[bytes, str]] = []
        for u in urls:
            data = _download_image(u)
            if not data:
                continue
            data = _compress_if_needed(data)
            image_blobs.append((data, f"void --news post {row['id'][:8]}"))

        if not image_blobs:
            _mark(row["id"], None, "bluesky cross-post: no images downloaded")
            continue

        try:
            resp = client.send_images(text=text, images=[b for b, _ in image_blobs], image_alts=[a for _, a in image_blobs])
            uri = getattr(resp, "uri", None) or getattr(resp, "ref", None)
            if isinstance(uri, str) and uri:
                _mark(row["id"], uri)
                print(f"  [cross-post] {row['id']} → {uri}")
                done += 1
            else:
                _mark(row["id"], None, "bluesky returned no uri")
        except Exception as e:
            print(f"  [error] bluesky send {row['id']}: {e}")
            _mark(row["id"], None, f"bluesky: {e}")

    return done


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-id", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    n = cross_post(post_id=args.post_id, dry_run=args.dry_run)
    print(f"  [cross-post] done. {n} mirror(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
