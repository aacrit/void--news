"""
ig_cleanup.py — reject IG posts stuck in a transient lock state.

ig_capture sets a post to 'rendering' (and ig_caption sets 'captioning') as a
short-lived lock while it works. If a run is interrupted, posts can be stranded
in those states forever: the capture/caption fetchers only look at
'draft'/'render_failed', so a stuck post is never retried and never reaches the
admin queue. This one-shot rejects them so the review queue stays clean.

It also offers an opt-in purge of OLD draft rows. The generate-only pipeline
leaves finished drafts in the DB; since 2026-08-05 ig_export scopes each bundle
to the current run via `--since`, but stale drafts still accumulate. Purging
them is a one-command reset (`--purge-drafts`), off by default and time-bounded
so an in-flight run's fresh drafts are never touched.

Usage:
    python -m pipeline.social.ig_cleanup                          # reject stuck only
    python -m pipeline.social.ig_cleanup --purge-drafts           # + delete drafts >24h old
    python -m pipeline.social.ig_cleanup --purge-drafts --older-than-hours 0   # ALL drafts

Environment:
    SUPABASE_URL / KEY  service-role credentials (existing pipeline vars)
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
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


def purge_drafts(older_than_hours: int = 24) -> int:
    """Delete draft rows older than the cutoff. Only state='draft' rows are
    ever touched (never captioning/rendering/approved/posted). `older_than_hours`
    is a floor so an in-flight run's fresh drafts survive; pass 0 to purge every
    draft. Deletes in id-batches so a large backlog can't hit a statement
    timeout."""
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=max(0, older_than_hours))
    ).isoformat()
    try:
        rows = (
            supabase.table("ig_posts")
            .select("id")
            .eq("state", "draft")
            .lt("created_at", cutoff)
            .execute()
            .data
        ) or []
    except Exception as e:
        print(f"  [error] purge query failed: {e}")
        return 0

    if not rows:
        print(f"  [cleanup] no draft rows older than {older_than_hours}h to purge")
        return 0

    ids = [r["id"] for r in rows]
    deleted = 0
    for i in range(0, len(ids), 100):
        batch = ids[i : i + 100]
        try:
            supabase.table("ig_posts").delete().in_("id", batch).execute()
            deleted += len(batch)
        except Exception as e:
            print(f"  [error] purge batch {i // 100}: {e}")
    print(
        f"  [cleanup] purged {deleted} draft row(s) older than {older_than_hours}h "
        f"(cutoff {cutoff})"
    )
    return deleted


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reject stuck IG posts; optionally purge old drafts."
    )
    parser.add_argument(
        "--purge-drafts",
        action="store_true",
        help="also DELETE state='draft' rows older than --older-than-hours",
    )
    parser.add_argument(
        "--older-than-hours",
        type=int,
        default=24,
        help="purge floor in hours (default 24; 0 = every draft). "
        "Only used with --purge-drafts.",
    )
    args = parser.parse_args()

    reject_stuck()
    if args.purge_drafts:
        purge_drafts(args.older_than_hours)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
