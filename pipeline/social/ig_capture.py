"""
ig_capture.py — Playwright headless renderer for Instagram post images.

For each ig_posts row in state='draft' or 'render_failed', launches Chromium
headless, navigates to http://localhost:{port}/ig/render/{post_id}?slide=N
for each slide in the spec, screenshots a 1080×1350 PNG, uploads to the
ig-renders Supabase storage bucket, and writes the public URL list back to
ig_posts.image_urls.

The Next.js dev server is expected to be running on RENDER_BASE_URL
(default http://localhost:3000). The orchestrating workflow starts the
server before invoking this script.

Usage:
    python -m pipeline.social.ig_capture                       # all draft rows
    python -m pipeline.social.ig_capture --post-id <uuid>      # one row
    python -m pipeline.social.ig_capture --post-id <uuid> --slide 0  # one slide

Environment:
    RENDER_BASE_URL          dev server URL (default http://localhost:3000)
    SUPABASE_URL / KEY       service-role credentials (existing pipeline vars)
"""

from __future__ import annotations

import argparse
import io
import os
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.supabase_client import supabase  # noqa: E402

RENDER_BASE_URL = os.environ.get("RENDER_BASE_URL", "http://localhost:3000")
BUCKET = "ig-renders"
VIEWPORT = (1080, 1350)


def _ensure_bucket() -> None:
    """Idempotent bucket creation. The 052 migration also creates it, but
    we double-check from Python in case the migration hasn't run yet."""
    try:
        from storage3.types import CreateOrUpdateBucketOptions  # type: ignore
        opts = CreateOrUpdateBucketOptions(public=True)
        try:
            supabase.storage.create_bucket(BUCKET, options=opts)
            print(f"  [capture] created bucket {BUCKET}")
        except Exception:
            pass  # already exists
    except Exception as e:
        print(f"  [warn] storage3 typed create skipped: {e}")


def _public_url(path: str) -> str:
    base = supabase.storage.from_(BUCKET).get_public_url(path)
    if isinstance(base, str):
        return base
    return f"{os.environ.get('SUPABASE_URL', '').rstrip('/')}/storage/v1/object/public/{BUCKET}/{path}"


def _upload_png(post_id: str, slide_index: int, png_bytes: bytes) -> str | None:
    path = f"{post_id}/slide-{slide_index}.png"
    try:
        supabase.storage.from_(BUCKET).remove([path])
    except Exception:
        pass
    try:
        supabase.storage.from_(BUCKET).upload(
            path,
            png_bytes,
            {"content-type": "image/png", "x-upsert": "true"},
        )
    except Exception as e:
        msg = str(e).lower()
        if "duplicate" in msg or "already exists" in msg or "resource already exists" in msg:
            try:
                supabase.storage.from_(BUCKET).update(
                    path, png_bytes, {"content-type": "image/png"}
                )
            except Exception as e2:
                print(f"  [error] upload {path} failed (update fallback): {e2}")
                return None
        else:
            print(f"  [error] upload {path} failed: {e}")
            return None
    return _public_url(path)


def _set_state(post_id: str, state: str, error: str | None = None) -> None:
    payload: dict[str, Any] = {"state": state}
    if error is not None:
        payload["error"] = error[:1000]
    try:
        supabase.table("ig_posts").update(payload).eq("id", post_id).execute()
    except Exception as e:
        print(f"  [error] state update {post_id} → {state}: {e}")


def _write_image_urls(post_id: str, urls: list[str]) -> None:
    try:
        supabase.table("ig_posts").update({"image_urls": urls}).eq("id", post_id).execute()
    except Exception as e:
        print(f"  [error] image_urls write {post_id}: {e}")


def _fetch_targets(post_id: str | None) -> list[dict]:
    q = supabase.table("ig_posts").select("id, slide_specs, state, pillar, launch_slot")
    if post_id:
        q = q.eq("id", post_id)
    else:
        q = q.in_("state", ["draft", "render_failed"])
    q = q.order("scheduled_for", desc=False).limit(50)
    res = q.execute()
    return res.data or []


def capture(post_id: str | None = None, only_slide: int | None = None) -> int:
    """Returns count of posts captured successfully."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("  [error] playwright not installed. pip install playwright; playwright install chromium")
        return 0

    rows = _fetch_targets(post_id)
    if not rows:
        print("  [capture] nothing to do")
        return 0

    _ensure_bucket()

    captured = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            for row in rows:
                pid = row["id"]
                specs = row.get("slide_specs") or []
                if not isinstance(specs, list) or len(specs) == 0:
                    _set_state(pid, "render_failed", "empty slide_specs")
                    continue

                slide_range = (
                    [only_slide] if only_slide is not None and 0 <= only_slide < len(specs)
                    else list(range(len(specs)))
                )

                _set_state(pid, "rendering")
                urls: list[str | None] = list(row.get("image_urls") or [])
                # pad to length
                while len(urls) < len(specs):
                    urls.append(None)

                ok = True
                for idx in slide_range:
                    url = f"{RENDER_BASE_URL}/ig/render/{pid}?slide={idx}"
                    context = browser.new_context(
                        viewport={"width": VIEWPORT[0], "height": VIEWPORT[1]},
                        device_scale_factor=1.0,
                    )
                    page = context.new_page()
                    try:
                        page.goto(url, wait_until="networkidle", timeout=30_000)
                        page.evaluate("() => document.fonts.ready")
                        # Wait a beat for any final reflow
                        page.wait_for_timeout(250)
                        png = page.screenshot(
                            type="png",
                            full_page=False,
                            clip={"x": 0, "y": 0, "width": VIEWPORT[0], "height": VIEWPORT[1]},
                        )
                    except Exception as e:
                        print(f"  [error] render {pid} slide {idx} failed: {e}")
                        _set_state(pid, "render_failed", f"slide {idx}: {e}")
                        ok = False
                        context.close()
                        break

                    context.close()

                    public_url = _upload_png(pid, idx, png)
                    if not public_url:
                        _set_state(pid, "render_failed", f"slide {idx}: upload failed")
                        ok = False
                        break
                    urls[idx] = public_url
                    print(f"  [capture] {pid} slide {idx} → {public_url}")

                if ok:
                    _write_image_urls(pid, [u for u in urls if u])
                    # Don't flip state here — caption step is next in the pipeline
                    if row.get("state") == "render_failed":
                        _set_state(pid, "draft")  # captioner picks it up
                    captured += 1
        finally:
            browser.close()
    return captured


def _wait_for_server(url: str, timeout_s: int = 120) -> bool:
    import urllib.request
    import urllib.error

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                if r.status < 500:
                    return True
        except (urllib.error.URLError, ConnectionResetError):
            time.sleep(1)
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--post-id", default=None, help="capture a single post")
    parser.add_argument("--slide", type=int, default=None, help="capture only this slide")
    parser.add_argument(
        "--wait-server",
        action="store_true",
        help="wait up to 120s for the dev server to be reachable before capturing",
    )
    args = parser.parse_args()

    if args.wait_server:
        ok = _wait_for_server(RENDER_BASE_URL)
        if not ok:
            print(f"  [error] dev server not reachable at {RENDER_BASE_URL}")
            return 1

    n = capture(post_id=args.post_id, only_slide=args.slide)
    print(f"  [capture] done. {n} post(s) captured.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
