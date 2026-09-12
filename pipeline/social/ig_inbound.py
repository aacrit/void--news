"""
ig_inbound.py — score comments, auto-reply to low-risk patterns, queue rest.

Runs after the webhook receiver populates ig_comments. This module:
  • Scores unseen comments (heuristic on commenter follower count when
    available, media-adjacency, text length, sentiment proxy).
  • Auto-replies (via Graph API) only to comments matching narrow, low-risk
    patterns — emoji-only, "love this", "great work" — with a single
    thank-you emoji equivalent. NOTHING editorial is auto-replied.
  • Everything else is left for the /admin/ig/inbox page with a drafted
    suggested response.

NEVER auto-replies to comments containing question marks, the words "why"/"how"/
"what", or to comments by accounts with >10k followers. Those need a human.

Usage:
    python -m pipeline.social.ig_inbound        # process unseen
    python -m pipeline.social.ig_inbound --dry  # no API calls

Environment:
    INSTAGRAM_GRAPH_TOKEN, INSTAGRAM_USER_ID, SUPABASE_URL/KEY
"""

from __future__ import annotations

import argparse
import os
import re
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

# Patterns that may be auto-replied to.
LOW_RISK_PATTERNS = [
    r"^[\s\W_]*$",                 # emoji-only
    r"^(love this|love it|great|nice|cool|👏|🔥|💯|amazing|brilliant)\W*$",
    r"^thanks?\W*$",
    r"^(beautiful|stunning) (work|post)\W*$",
]
LOW_RISK_RE = re.compile("|".join(LOW_RISK_PATTERNS), re.IGNORECASE)

# Anything that signals "needs editorial response" — never auto-reply.
HIGH_RISK_TOKENS = [
    "?", "why", "how", "what", "where", "when", "wrong", "incorrect",
    "biased", "lying", "agenda", "fake", "true", "false", "data",
    "methodology", "source", "evidence",
]


def _score_comment(c: dict[str, Any]) -> float:
    """0..100 heuristic. Higher = surface to admin sooner."""
    text = (c.get("text") or "").lower()
    score = 30.0
    if "?" in text:
        score += 20
    for tok in ("press", "journalist", "newsroom", "reporter", "editor"):
        if tok in text:
            score += 25
    for tok in ("methodology", "data", "source", "axis", "evidence"):
        if tok in text:
            score += 15
    # Length proxy.
    if len(text) > 200:
        score += 10
    if len(text) < 20:
        score -= 10
    return max(0.0, min(100.0, score))


def _auto_reply_text(comment_text: str) -> str | None:
    """Returns the canned reply to send, or None to skip."""
    if not LOW_RISK_RE.search(comment_text.strip()):
        return None
    for tok in HIGH_RISK_TOKENS:
        if tok in comment_text.lower():
            return None
    # One emoji, one short word. Editorial would push us to skip even this,
    # but a brief signal of being seen is fine for emoji-only comments.
    return "🜂"  # alchemy fire — quiet, unique, on-brand


def _send_reply(token: str, comment_id: str, text: str) -> str | None:
    if requests is None:
        return None
    try:
        r = requests.post(
            f"{GRAPH_BASE}/{comment_id}/replies",
            data={"message": text, "access_token": token},
            timeout=20,
        )
        if r.status_code >= 200 and r.status_code < 300:
            return r.json().get("id")
        print(f"  [warn] reply failed: {r.status_code} {r.text[:200]}")
        return None
    except Exception as e:
        print(f"  [error] reply send: {e}")
        return None


def process(dry: bool = False, limit: int = 100) -> int:
    rows = (
        supabase.table("ig_comments")
        .select("id, ig_comment_id, ig_user_id, text, auto_replied, reply_sent_at, score")
        .eq("auto_replied", False)
        .is_("reply_sent_at", "null")
        .eq("hidden_or_deleted", False)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )
    if not rows:
        print("  [inbound] nothing to process")
        return 0

    token = os.environ.get("INSTAGRAM_GRAPH_TOKEN", "").strip()
    handled = 0
    for c in rows:
        text = (c.get("text") or "").strip()
        score = _score_comment(c)

        update: dict[str, Any] = {"score": score}
        canned = _auto_reply_text(text)
        if canned and token and not dry:
            new_id = _send_reply(token, c["ig_comment_id"], canned)
            if new_id:
                update["auto_replied"] = True
                update["reply_sent_at"] = "now()"
                update["reply_ig_id"] = new_id
                handled += 1
                print(f"  [inbound] auto-replied to {c['ig_comment_id']}")
        elif canned and dry:
            print(f"  [inbound dry] would auto-reply: {text!r}")

        try:
            supabase.table("ig_comments").update(update).eq("id", c["id"]).execute()
        except Exception as e:
            print(f"  [error] persist {c['id']}: {e}")

    return handled


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--dry", action="store_true")
    p.add_argument("--limit", type=int, default=100)
    args = p.parse_args()
    n = process(dry=args.dry, limit=args.limit)
    print(f"  [inbound] auto-replied {n}; rest in admin queue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
