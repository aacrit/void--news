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


def _alt_titles(item) -> list[str]:
    """Searchable names for a feature, best first.

    A cover headline is written to be read: "Greenland\u2019s Arctic Calculus"
    names no subject any encyclopedia indexes, and the overlap guard correctly
    refuses everything it resolves to. `cluster_title` carries the reported
    headline, but only on issues generated after that field existed, and the
    published Vol. I, No. 1 has None.

    Its TIMELINE does not. Each entry is a real cluster title, which is the
    same observation `repair_weekly_snapshot.title_from_timeline` is built on.
    "Denmark Affirms Sovereignty After US-Greenland Security Deal" resolves
    where the coinage above never will.
    """
    out = []
    ct = (item.get("cluster_title") or "").strip()
    if ct:
        out.append(ct)
    for e in (item.get("timeline") or []):
        t = (e.get("title") or "").strip() if isinstance(e, dict) else ""
        if t and t not in out:
            out.append(t)
    return out[:4]      # four network round trips is already generous


def _load(row, key):
    """The JSON columns ship as strings on some rows and as lists on others."""
    v = row.get(key)
    if isinstance(v, str):
        try:
            return json.loads(v), True
        except ValueError:
            return [], False
    return (v or []), False


def cover_image(row, *, dry_run=False) -> list[str]:
    """The MAGAZINE COVER, which is a top-level field and was being skipped.

    `cover_image_url` sits on the row, not inside `cover_text`, so the first
    version of this tool walked right past the largest picture in the issue
    while illustrating its thumbnails. Vol. I, No. 1 came out of generation
    with no cover photograph (correctly: the only candidate was an AFP wire
    image, which rev 60 retired the cacher to stop republishing) and kept none
    through three backfills.

    Resolved from the lead feature, because that is what the cover is ABOUT:
    its headline first, then the reported titles its timeline carries.
    """
    cur = row.get("cover_image_url") or ""
    # The cover is repaired on the same terms as any other slot. Returning
    # early whenever one existed would have left the diagram already attached
    # in place, on the largest surface in the issue, which is the one place
    # "already has an image" is least like "is fine".
    stale = bool(cur) and (
        _is_diagram(cur) or not (row.get("cover_image_caption") or "").strip()
    )
    if cur and not stale:
        return []
    covers, _ = _load(row, "cover_text")
    lead = covers[0] if covers and isinstance(covers[0], dict) else {}
    head = (row.get("cover_headline") or lead.get("headline") or "").strip()
    if not head:
        return []
    try:
        found = find_cover_image_for_cluster(
            lead.get("cluster_id") or "", head, alt_titles=_alt_titles(lead),
        )
    except Exception as e:
        return [f"cover image lookup failed: {e}"]
    if not found:
        if stale and not dry_run:
            # Nothing better resolved, so the diagram goes. A cover with no
            # photograph is a typographic cover, which this design already
            # has; a cover with the wrong photograph is a claim.
            for k in ("cover_image_url", "cover_image_attribution",
                      "cover_image_caption", "cover_image_source"):
                row.pop(k, None)
            return ["cover: DROPPED a diagram; nothing better resolved"]
        return [f"cover: no licensed subject for {head[:44]!r}"]
    if not dry_run:
        row["cover_image_url"] = found["url"]
        row["cover_image_attribution"] = found.get("attribution") or ""
        # Names the provenance honestly. The field previously read "og_image"
        # on an issue carrying a hotlinked wire photograph, which is the
        # labelling W-03 exists to catch.
        row["cover_image_source"] = "wikimedia-subject"
        row["cover_image_caption"] = found.get("caption") or ""
    return [f"cover -> {found.get('caption')}"]


def _is_diagram(url: str) -> bool:
    """A Commons SVG render. Maps, flags, logos and charts, not photographs."""
    return ".svg" in (url or "").lower()


def _used(row) -> set:
    """Every image URL the issue already carries, so nothing repeats.

    The cover is resolved FROM the lead feature, so without this they collide
    by construction: Vol. I, No. 1 came out of the backfill with the same
    Greenland map as its full-screen cover AND its lead feature one screen
    below. No magazine prints the same picture twice in one issue.
    """
    urls = {(row.get("cover_image_url") or "").split("?")[0]} - {""}
    for key, _ in SLOTS:
        items, _ = _load(row, key)
        for x in items:
            if isinstance(x, dict) and x.get("image_url"):
                urls.add(x["image_url"].split("?")[0])
    return urls


def illustrate(row, *, dry_run=False) -> list[str]:
    """Attach art to one issue row. Returns one line per change."""
    out = cover_image(row, dry_run=dry_run)
    seen = _used(row)
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
            cur = item.get("image_url") or ""
            # Repair, not skip: an image already attached can still be wrong.
            # Missing caption (predates captions) or a diagram (the Gaza war
            # control map under a celebrity-apology feature) both need
            # re-resolving, and dropping if nothing better passes.
            stale = bool(cur) and (
                not (item.get("image_caption") or "").strip() or _is_diagram(cur)
            )
            if item.get("image_url") and not stale:
                continue                      # already illustrated and labelled
            try:
                found = find_cover_image_for_cluster(
                    item.get("cluster_id") or "", head,
                    alt_titles=_alt_titles(item),
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
            # NOTHING APPEARS TWICE, decided BEFORE the write. This block sat
            # after the assignment, so a duplicate was attached, then detected,
            # then reported as "skipped" while staying on the page. The cover
            # and its lead feature shipped the same photograph under a log line
            # saying they had not.
            u = (found.get("url") or "").split("?")[0]
            if u in seen:
                if stale and not dry_run:
                    # It had an image, the replacement duplicates something
                    # else, so it keeps nothing.
                    for k in ("image_url", "image_attribution", "image_caption"):
                        item.pop(k, None)
                    changed = True
                out.append(f"{key}[{i}] skipped: would repeat {found.get('caption')}")
                continue

            if not dry_run:
                item["image_url"] = found["url"]
                if found.get("attribution"):
                    item["image_attribution"] = found["attribution"]
                if found.get("caption"):
                    item["image_caption"] = found["caption"]
            seen.add(u)
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
