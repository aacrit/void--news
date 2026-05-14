"""
ig_dms.py — DM keyword router + first-touch template.

For each unread inbound DM:
  • Classify priority via keyword router (press / inbox / noise).
  • If priority='press' and first_touch_sent=False: send the press first-touch
    template via Graph API Messaging.
  • Mark conversations so /admin/ig/inbox can show them in priority order.

Press first-touch is the only automated DM send we do. Everything beyond is
manual — the warm reply must stay editorial.

Usage:
    python -m pipeline.social.ig_dms        # process unseen
    python -m pipeline.social.ig_dms --dry

Environment:
    INSTAGRAM_GRAPH_TOKEN, INSTAGRAM_USER_ID, SUPABASE_URL/KEY
"""

from __future__ import annotations

import argparse
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

GRAPH_API_VERSION = os.environ.get("META_GRAPH_API_VERSION", "v21.0")
GRAPH_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

PRESS_KEYWORDS = [
    "press", "journalist", "reporter", "newsroom", "editor",
    "newsletter", "writer", "freelance",
    "interview", "quote", "comment", "speak with you",
    "story about", "writing about", "covering",
    "media inquir",
]

NOISE_KEYWORDS = [
    "promote", "buy", "follow back", "f4f", "growth service",
    "boost", "shoutout", "click my bio",
]

PRESS_TEMPLATE = (
    "Thanks for reaching out. I will get you a longer reply within 24 hours. "
    "If it helps in the meantime: press kit and methodology at "
    "void-news.pages.dev/press. Talk soon."
)


def _classify(text: str) -> tuple[str, list[str]]:
    low = (text or "").lower()
    matched = [k for k in PRESS_KEYWORDS if k in low]
    if matched:
        return "press", matched
    if any(k in low for k in NOISE_KEYWORDS):
        return "noise", []
    return "inbox", []


def _send_dm(token: str, recipient_id: str, text: str) -> bool:
    if requests is None:
        return False
    # IG Messaging via the /me/messages endpoint of the linked Page.
    try:
        r = requests.post(
            f"{GRAPH_BASE}/me/messages",
            params={"access_token": token},
            json={
                "recipient": {"id": recipient_id},
                "message": {"text": text},
                "messaging_type": "RESPONSE",
            },
            timeout=20,
        )
        if r.status_code >= 200 and r.status_code < 300:
            return True
        print(f"  [warn] dm send failed: {r.status_code} {r.text[:200]}")
        return False
    except Exception as e:
        print(f"  [error] dm send: {e}")
        return False


def process(dry: bool = False, limit: int = 100) -> int:
    rows = (
        supabase.table("ig_dms")
        .select("id, ig_thread_id, ig_user_id, text, priority, first_touch_sent, inbound, read_by_admin, matched_keywords")
        .eq("inbound", True)
        .eq("read_by_admin", False)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )
    if not rows:
        print("  [dms] nothing new")
        return 0

    token = os.environ.get("INSTAGRAM_GRAPH_TOKEN", "").strip()
    handled = 0
    for d in rows:
        priority, matched = _classify(d.get("text") or "")
        update: dict[str, Any] = {"priority": priority, "matched_keywords": matched or None}

        if priority == "press" and not d.get("first_touch_sent") and token and not dry:
            if _send_dm(token, d["ig_user_id"], PRESS_TEMPLATE):
                update["first_touch_sent"] = True
                handled += 1
                print(f"  [dms] press first-touch sent to {d['ig_user_id']}")

        try:
            supabase.table("ig_dms").update(update).eq("id", d["id"]).execute()
        except Exception as e:
            print(f"  [error] persist {d['id']}: {e}")

    return handled


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry", action="store_true")
    p.add_argument("--limit", type=int, default=100)
    args = p.parse_args()
    n = process(dry=args.dry, limit=args.limit)
    print(f"  [dms] first-touches sent: {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
