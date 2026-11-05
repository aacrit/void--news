"""Seed the weekly back-issue archive from git history.

The weekly job restores the Actions cache and never saves it back, on purpose:
the daily pipeline is usually still running at 12:00 UTC and a save would push a
pre-run copy under a newer key and lose a day. So each weekly row is written to
a database discarded at job end, and the only durable record of a past issue is
the `frontend/public/data/weekly.json` that run committed.

This walks those commits and merges every distinct issue into
`frontend/build-data/weekly-issues.json`, which `export_static.py` appends to
from here on. It is a one-shot: after this, the archive accrues forward.

Be honest about the yield. `git log --follow` on weekly.json has very few
commits, because the section was 301-hidden from the 2026-08-05 launch trim
until rev 69 and the job was writing to a decommissioned Supabase the whole
time. Two issues is enough to make the archive real and the route worth
prerendering; it is not a rich back catalogue.

Recovered issues are put through the same repair the live snapshot gets — the
headline guard, the payload normalization — because they were written by the
same generator with the same defects. Issue #23's cover "headline" is a
paragraph too. Audio URLs pointing at the decommissioned Supabase bucket are
cleared rather than carried: a dead enclosure in the playlist is worse than no
enclosure.

    python -m pipeline.briefing.backfill_weekly_archive            # apply
    python -m pipeline.briefing.backfill_weekly_archive --dry-run  # show only
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "pipeline") not in sys.path:
    sys.path.insert(0, str(REPO / "pipeline"))

from briefing.repair_weekly_snapshot import normalize, repair  # noqa: E402

SNAPSHOT = "frontend/public/data/weekly.json"
ISSUES = REPO / "frontend" / "build-data" / "weekly-issues.json"
ARCHIVE = REPO / "frontend" / "public" / "data" / "weekly-archive.json"

INDEX_COLS = ("id", "issue_number", "edition", "week_start", "week_end",
              "cover_headline", "cover_image_url", "audio_url",
              "audio_duration_seconds", "created_at")

# Storage that no longer exists. Supabase was decommissioned 2026-08-29..09-01
# after an egress lockout; every object in that bucket is gone.
DEAD_AUDIO_HOSTS = ("supabase.co", "supabase.in")


def git(*args) -> str:
    return subprocess.run(["git", "-C", str(REPO), *args],
                          capture_output=True, text=True, check=True).stdout


def snapshots():
    """Every committed version of weekly.json, oldest first."""
    shas = git("log", "--follow", "--format=%H", "--", SNAPSHOT).split()
    for sha in reversed(shas):
        try:
            raw = git("show", f"{sha}:{SNAPSHOT}")
        except subprocess.CalledProcessError:
            continue
        try:
            yield sha, json.loads(raw)
        except ValueError:
            continue


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report without writing")
    args = ap.parse_args()

    by_key = {}
    if ISSUES.exists():
        for issue in json.loads(ISSUES.read_text(encoding="utf-8")) or []:
            by_key[(issue.get("edition"), issue.get("week_start"))] = issue

    found = 0
    for sha, data in snapshots():
        key = (data.get("edition"), data.get("week_start"))
        if not key[1]:
            continue
        found += 1
        notes = normalize(data) + repair(data)

        url = str(data.get("audio_url") or "")
        if any(h in url for h in DEAD_AUDIO_HOSTS):
            data["audio_url"] = None
            data["audio_duration_seconds"] = None
            notes.append("audio_url cleared (decommissioned Supabase bucket)")

        fresh = key not in by_key
        by_key[key] = data
        print(f"{sha[:8]}  issue #{data.get('issue_number')} "
              f"({key[1]})  {'new' if fresh else 'replaces existing'}")
        for n in notes:
            print(f"            {n}")

    merged = sorted(by_key.values(), key=lambda i: str(i.get("week_start") or ""),
                    reverse=True)
    print(f"\n{found} snapshot(s) in history -> {len(merged)} distinct issue(s)")

    if args.dry_run:
        return 0

    ISSUES.parent.mkdir(parents=True, exist_ok=True)
    ISSUES.write_text(json.dumps(merged, ensure_ascii=False), encoding="utf-8")
    ARCHIVE.write_text(
        json.dumps([{k: i.get(k) for k in INDEX_COLS} for i in merged],
                   ensure_ascii=False), encoding="utf-8")
    print(f"wrote {ISSUES.relative_to(REPO)} and {ARCHIVE.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
