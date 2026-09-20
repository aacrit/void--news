"""Illustrate an ALREADY PUBLISHED weekly issue, without regenerating a word.

Images are attached at generation time, so fixing the image lookup does
nothing for an issue that has already shipped. Vol. I, No. 1 went out with no
photographs and would have stayed that way until the next Sunday run. This is
the same move `repair_weekly_snapshot` makes for prose: repair the published
snapshot in place, no LLM call, no database, not one word regenerated.

It attaches only what `find_cover_image_for_cluster` returns, which means every
image has passed the overlap guard, the licence allowlist and the resolution
floor. Where nothing passes, the slot stays empty. That is the correct outcome:
a headline naming no indexable subject gets no photograph, and a wrong
photograph is worse than none because it looks authoritative.

Every attached image carries a CAPTION naming what it is. This is file
photography, not event coverage, and the caption is what keeps that honest.

    python -m pipeline.briefing.backfill_weekly_images --dry-run
    python -m pipeline.briefing.backfill_weekly_images
    python -m pipeline.briefing.backfill_weekly_images --all-issues
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "pipeline") not in sys.path:
    sys.path.insert(0, str(REPO / "pipeline"))

from media.image_search import find_cover_image_for_cluster  # noqa: E402

WEEKLY = REPO / "frontend" / "public" / "data" / "weekly.json"
ISSUES = REPO / "frontend" / "build-data" / "weekly-issues.json"
ARCHIVE = REPO / "frontend" / "public" / "data" / "weekly-archive.json"

#: Which collections carry art. NOTHING IS CAPPED. The generator caps brief
#: thumbnails at three because every lookup is a network round trip inside a
#: run that is already the slowest job in the repo. A backfill is not on that
#: clock, and `BriefList` renders a thumbnail for any item that has one, so a
#: cap here only means fewer pictures for no saving. The first run capped at
#: three and illustrated three slots on an issue where the coverage probe,
#: uncapped, resolved nine.
SLOTS = (("cover_text", None), ("departments", None), ("recap_stories", None))


def _load(row, key):
    """The JSON columns ship as strings on some rows and as lists on others."""
    v = row.get(key)
    if isinstance(v, str):
        try:
            return json.loads(v), True
        except ValueError:
            return [], False
    return (v or []), False


def illustrate(row, *, dry_run=False) -> list[str]:
    """Attach art to one issue row. Returns one line per change."""
    out = []
    for key, cap in SLOTS:
        items, was_str = _load(row, key)
        if not isinstance(items, list) or not items:
            continue
        changed = False
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            if cap is not None and i >= cap:
                break
            head = (item.get("headline") or item.get("label") or "").strip()
            if not head:
                continue

            # AN IMAGE WITH NO CAPTION IS REPAIRED OR REMOVED, never left.
            # Slots illustrated before captions existed carry a picture and no
            # label, which is the exact failure this design exists to prevent:
            # Vol. I, No. 1 shipped a photograph of a US-Japan air formation
            # over the Pacific on a North Korean missile-test brief, correctly
            # licensed, matched on the word "missile", with nothing on the page
            # saying what it was. A reader cannot tell a file photograph from
            # event coverage unless we say so.
            stale = bool(item.get("image_url")) and not (item.get("image_caption") or "").strip()
            if item.get("image_url") and not stale:
                continue                      # already illustrated and labelled
            try:
                found = find_cover_image_for_cluster(
                    item.get("cluster_id") or "", head,
                    alt_title=item.get("cluster_title", ""),
                )
            except Exception as e:
                out.append(f"{key}[{i}] lookup failed: {e}")
                continue
            if not found:
                if stale:
                    # Nothing better resolved, so the unlabelled picture goes.
                    # No photograph is the honest outcome; an unexplained one
                    # asserts something we cannot stand behind.
                    if not dry_run:
                        for k in ("image_url", "image_attribution", "image_caption"):
                            item.pop(k, None)
                        changed = True
                    out.append(f"{key}[{i}] DROPPED an uncaptioned image "
                               f"({head[:38]!r} resolved to nothing better)")
                else:
                    out.append(f"{key}[{i}] no licensed subject for {head[:42]!r}")
                continue
            if not dry_run:
                item["image_url"] = found["url"]
                if found.get("attribution"):
                    item["image_attribution"] = found["attribution"]
                if found.get("caption"):
                    item["image_caption"] = found["caption"]
            changed = True
            verb = "re-resolved" if stale else "->"
            out.append(f"{key}[{i}] {verb} {found.get('caption')}")
        if changed and not dry_run:
            # Written back in the shape it arrived in, or the exporter's own
            # parse of this column changes meaning underneath the frontend.
            row[key] = json.dumps(items, ensure_ascii=False) if was_str else items
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report without writing")
    ap.add_argument("--all-issues", action="store_true",
                    help="also illustrate back issues, not just the latest")
    args = ap.parse_args()

    if not WEEKLY.exists():
        print(f"no snapshot at {WEEKLY}")
        return 1

    touched = 0
    data = json.loads(WEEKLY.read_text(encoding="utf-8"))
    print(f"{WEEKLY.name}: issue #{data.get('issue_number')} ({data.get('week_start')})")
    lines = illustrate(data, dry_run=args.dry_run)
    for line in lines:
        print(f"  {line}")
    if not lines:
        print("  nothing to illustrate")
    elif not args.dry_run:
        WEEKLY.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        touched += 1

    # The deploy tree is the archive of record AND what the page reads, so an
    # image written to weekly.json alone would not appear on a back issue.
    for path in (ISSUES, ARCHIVE):
        if not path.exists():
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            continue
        latest = data.get("week_start")
        n = 0
        for row in rows:
            if not isinstance(row, dict) or "cover_text" not in row:
                continue          # a summary row carries no essays and no art
            if not args.all_issues and row.get("week_start") != latest:
                continue
            for line in illustrate(row, dry_run=args.dry_run):
                n += 1
                print(f"  {path.name} #{row.get('issue_number')}: {line}")
        if n and not args.dry_run:
            path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            touched += 1

    if not args.dry_run and touched:
        print(f"written ({touched} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
