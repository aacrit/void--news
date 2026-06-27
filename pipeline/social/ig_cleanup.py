"""
ig_cleanup.py — reject IG posts stuck in a transient lock state.

ig_capture sets a post to 'rendering' (and ig_caption sets 'captioning') as a
short-lived lock while it works. If a run is interrupted, posts can be stranded
in those states forever: the capture/caption fetchers only look at
'draft'/'render_failed', so a stuck post is never retried and never reaches the
admin queue. This one-shot rejects them so the review queue stays clean.

Usage:
    python -m pipeline.social.ig_cleanup

Environment:
    SUPABASE_URL / KEY  service-role credentials (existing pipeline vars)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.supabase_client import supabase  # noqa: E402

# Transient lock states a healthy run always moves OUT of. Anything left here is
# the residue of an interrupted run (e.g. the weeks of failed pre-fix runs).
STUCK_STATES = ["rendering", "captioning"]


def reject_stuck() -> int:
    rows = (
        supabase.table("ig_posts")
        .select("id, state")
        .in_("state", STUCK_STATES)
        .execute()
        .data
    ) or []
    if not rows:
        print("  [cleanup] nothing stuck")
        return 0

    rejected = 0
    for row in rows:
        pid = row["id"]
        try:
            supabase.table("ig_posts").update({
                "state": "rejected",
                "error": "auto-rejected: stuck in a transient state from an interrupted run",
            }).eq("id", pid).execute()
            rejected += 1
            print(f"  [cleanup] {pid} ({row.get('state')}) -> rejected")
        except Exception as e:
            print(f"  [error] reject {pid}: {e}")
    print(f"  [cleanup] done. {rejected} stuck post(s) rejected.")
    return rejected


def main() -> int:
    reject_stuck()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
