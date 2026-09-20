"""Re-apply the headline guard to the ALREADY PUBLISHED weekly snapshot.

`parse_essay` used to take the first non-empty line as the headline with no
sanity check. When Gemini opened a feature straight into prose, its whole lede
became the headline and the essay LOST that paragraph. Issue #26 shipped that
way: `cover_text[1].headline` is 698 characters of reporting, set on the live
page as a display-size red <h2> and as coverline #1 on the cover.

The parser is fixed, but the fix only takes effect on the next Monday run, and
a paragraph should not sit on the live site as a headline until then. This
repairs the published snapshot in place: no LLM call, no database, not one word
of the issue regenerated.

Where a headline is really a paragraph, it is moved back to the FRONT of the
essay body — that is where it was written to go — and the feature is named from
its own data timeline, whose entries carry the real cluster titles. That is the
same fallback the generator now applies at write time, so a repaired snapshot
and a freshly generated one agree.

    python -m pipeline.briefing.repair_weekly_snapshot            # apply
    python -m pipeline.briefing.repair_weekly_snapshot --dry-run  # show only
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO / "pipeline") not in sys.path:
    sys.path.insert(0, str(REPO / "pipeline"))

from briefing.weekly_parse import (  # noqa: E402
    _opinion_items, banned_terms, looks_like_headline, strip_dashes,
)

WEEKLY = REPO / "frontend" / "public" / "data" / "weekly.json"

# THE DEPLOY TREE IS THE ARCHIVE OF RECORD, and since /weekly became a server
# component it is also what the PAGE reads. Repairing weekly.json alone fixed a
# file no component imports any more: the prose on the live page comes from
# build-data. All three carry the same issues, so all three are repaired.
ISSUES = REPO / "frontend" / "build-data" / "weekly-issues.json"
ARCHIVE = REPO / "frontend" / "public" / "data" / "weekly-archive.json"


def title_from_timeline(entries) -> str:
    """The best cluster title available offline: the most-sourced day."""
    best = ""
    best_n = -1
    for e in entries or []:
        n = e.get("source_count") or 0
        if e.get("title") and n > best_n:
            best, best_n = e["title"], n
    return best


# Every field of the row that is EDITORIAL PROSE, and therefore dash-free by
# the cardinal rule. Audio scripts are deliberately absent: there a dash is a
# breath mark for the synthesiser, and the exporter drops them anyway.
_PROSE_SCALARS = ("cover_headline", "opinion_text", "opinion_headline",
                  "bias_report_text")
_PROSE_IN_LISTS = {
    "cover_text": ("headline", "text"),
    "departments": ("headline", "text"),
    "opinions": ("headline", "text", "topic"),
    "opinion_left": ("headline", "text", "topic"),
    "opinion_center": ("headline", "text", "topic"),
    "opinion_right": ("headline", "text", "topic"),
    "recap_stories": ("headline", "summary"),
}


def dedash(data) -> list[str]:
    """Strip em and en dashes from every published prose field.

    CLAUDE.md bans both as an AI tell, and the prompts said so, but only one of
    six generators enforced anything — so the live page carries three in the
    opinion columns alone. The generator checks now; this is the half that
    takes effect today rather than on Monday.

    Banned TERMS are deliberately not touched. "Crucially" cannot be removed
    without rewriting the sentence around it, and a script guessing at that
    would do more damage than the word does. Those nine hits stand until the
    next run writes prose that was measured.
    """
    changes = []
    n = 0

    for k in _PROSE_SCALARS:
        v = data.get(k)
        if isinstance(v, str) and ("\u2014" in v or "\u2013" in v):
            data[k] = strip_dashes(v)
            n += 1
            changes.append(f"{k}: dashes removed")

    for key, fields in _PROSE_IN_LISTS.items():
        for i, item in enumerate(data.get(key) or []):
            if not isinstance(item, dict):
                continue
            for f in fields:
                v = item.get(f)
                if isinstance(v, str) and ("\u2014" in v or "\u2013" in v):
                    item[f] = strip_dashes(v)
                    n += 1
                    changes.append(f"{key}[{i}].{f}: dashes removed")

    if n:
        left = sorted({t for key, fields in _PROSE_IN_LISTS.items()
                       for item in (data.get(key) or []) if isinstance(item, dict)
                       for f in fields for t in banned_terms(item.get(f))})
        if left:
            changes.append("banned terms still present and NOT rewritten: "
                           + ", ".join(left) + " (the next run writes measured prose)")
    return changes


def repair(data) -> list[str]:
    """Repair in place. Returns a line per change, empty when nothing to do."""
    changes = []

    for i, story in enumerate(data.get("cover_text") or []):
        if not isinstance(story, dict):
            continue
        head = (story.get("headline") or "").strip()
        if not head or looks_like_headline(head):
            continue
        body = (story.get("text") or "").strip()
        story["text"] = (head + "\n\n" + body).strip() if body else head
        new = title_from_timeline(story.get("timeline"))
        story["headline"] = new
        changes.append(
            f"cover_text[{i}]: {len(head)}-char paragraph moved back into the essay; "
            f"headline -> {new or '(none available)'!r}"
        )

    for i, story in enumerate(data.get("recap_stories") or []):
        if not isinstance(story, dict):
            continue
        head = (story.get("headline") or "").strip()
        if not head or looks_like_headline(head):
            continue
        summary = (story.get("summary") or "").strip()
        story["summary"] = (head + " " + summary).strip()
        story["headline"] = ""
        changes.append(f"recap_stories[{i}]: {len(head)}-char paragraph moved into the summary")

    # cover_headline is copied from covers[0] at write time, so it inherits the
    # same defect and must follow the same repair.
    covers = [c for c in (data.get("cover_text") or []) if isinstance(c, dict)]
    top = (data.get("cover_headline") or "").strip()
    if top and not looks_like_headline(top):
        new = (covers[0].get("headline") if covers else "") or ""
        data["cover_headline"] = new
        changes.append(f"cover_headline -> {new or '(none available)'!r}")

    return changes


# Fields the exporter parses out of the DB's TEXT columns. A snapshot written
# before these were added carries them as raw JSON strings.
_JSON_FIELDS = ("cover_text", "cover_timelines", "cover_numbers", "recap_stories",
                "departments", "opinions", "opinion_left", "opinion_center",
                "opinion_right", "bias_report_data")

# TTS source and a derivable map, rendered nowhere, ~15 KB per page load.
_DROPPED = ("audio_script", "opinion_audio_script", "opinion_headlines")


def normalize(data) -> list[str]:
    """Bring a published snapshot in line with what the exporter now emits."""
    changes = []

    for k in _JSON_FIELDS:
        if isinstance(data.get(k), str):
            try:
                data[k] = json.loads(data[k])
            except ValueError:
                continue
            changes.append(f"{k}: parsed (was shipping to browsers as a raw JSON string)")

    for k in _DROPPED:
        if k in data:
            n = len(data[k] or "") if isinstance(data.get(k), str) else 0
            data.pop(k)
            changes.append(f"{k}: dropped from the browser payload"
                           + (f" ({n:,} chars)" if n else ""))

    # The flat opinion array, recovered from the three lean buckets. The
    # generator writes it from 2026-09-20 on; rebuilding it here means the
    # PUBLISHED issue gets its left-vs-right dialectic back now rather than on
    # Monday. Bucket order is left, center, right, so `position` is restored
    # from the stored `paired` flag rather than from the original index.
    if not data.get("opinions"):
        merged = []
        for k in ("opinion_left", "opinion_center", "opinion_right"):
            merged.extend(data.get(k) or [])
        if merged:
            merged.sort(key=lambda o: (not o.get("paired"), o.get("lean", "")))
            data["opinions"] = _opinion_items(merged, data.get("issue_number") or 0)
            paired = sum(1 for o in data["opinions"] if o["paired"])
            changes.append(f"opinions: rebuilt {len(merged)} essays from the lean "
                           f"buckets ({paired} paired)")

    # Shipping the flat array AND the three buckets duplicates every essay.
    if data.get("opinions"):
        for k in ("opinion_left", "opinion_center", "opinion_right"):
            if k in data:
                data.pop(k)
                changes.append(f"{k}: dropped (superseded by `opinions`)")

    # `total_scored` was capped at exactly 3000 by a single .limit(3000), so a
    # snapshot sitting on that number is a truncated query reported as a count
    # — in the one section whose job is to be honest about measurement. The
    # generator pages the query now; an already-published issue can only be
    # flagged, so the page says "more than" rather than stating the cap.
    stats = (data.get("bias_report_data") or {}).get("stats")
    if isinstance(stats, dict) and stats.get("total_scored") == 3000 \
            and "truncated" not in stats:
        stats["truncated"] = True
        changes.append("bias stats: total_scored 3000 marked truncated (it was a query cap)")

    # Departments are text that was never written; an empty list is the honest
    # answer until the next run generates and stores them.
    if data.get("departments") is None:
        data["departments"] = []
        changes.append("departments: [] (this issue predates them being persisted)")

    return changes


def _fix(row) -> list[str]:
    """normalize first: it parses the JSON columns that repair walks."""
    return normalize(row) + repair(row) + dedash(row)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report without writing")
    args = ap.parse_args()

    if not WEEKLY.exists():
        print(f"no snapshot at {WEEKLY}")
        return 1

    touched = 0

    # 1. The latest-issue snapshot.
    data = json.loads(WEEKLY.read_text(encoding="utf-8"))
    print(f"{WEEKLY.name}: issue #{data.get('issue_number')} ({data.get('week_start')})")
    changes = _fix(data)
    for line in changes:
        print(f"  {line}")
    if not changes:
        print("  already matches what the exporter emits")
    elif not args.dry_run:
        # Match export_static.wj() exactly, so a repair is a small diff.
        WEEKLY.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        touched += 1

    # 2. The archive of record, and the copy served to the browser. EVERY issue
    #    in them, because a back issue is a live page too.
    for path in (ISSUES, ARCHIVE):
        if not path.exists():
            continue
        rows = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(rows, list):
            continue
        print(f"{path.name}: {len(rows)} issue(s)")
        n = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            # The archive is a WeeklyIssueSummary list: eleven keys, no
            # essays. Running the full repair on it invents columns it does
            # not have, so a summary row only gets its prose cleaned.
            fix = _fix if "cover_text" in row else dedash
            for line in fix(row):
                n += 1
                print(f"  #{row.get('issue_number')}: {line}")
        if not n:
            print("  already clean")
        elif not args.dry_run:
            path.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
            touched += 1

    if not args.dry_run and touched:
        print(f"written ({touched} file(s))")
    return 0


if __name__ == "__main__":
    sys.exit(main())
