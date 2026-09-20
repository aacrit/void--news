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

from briefing.weekly_parse import _opinion_items, looks_like_headline  # noqa: E402

WEEKLY = REPO / "frontend" / "public" / "data" / "weekly.json"


def title_from_timeline(entries) -> str:
    """The best cluster title available offline: the most-sourced day."""
    best = ""
    best_n = -1
    for e in entries or []:
        n = e.get("source_count") or 0
        if e.get("title") and n > best_n:
            best, best_n = e["title"], n
    return best


def repair(data) -> list[str]:
    """Repair in place. Returns a line per change, empty when nothing to do."""
    changes = []

    for i, story in enumerate(data.get("cover_text") or []):
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
        head = (story.get("headline") or "").strip()
        if not head or looks_like_headline(head):
            continue
        summary = (story.get("summary") or "").strip()
        story["summary"] = (head + " " + summary).strip()
        story["headline"] = ""
        changes.append(f"recap_stories[{i}]: {len(head)}-char paragraph moved into the summary")

    # cover_headline is copied from covers[0] at write time, so it inherits the
    # same defect and must follow the same repair.
    covers = data.get("cover_text") or []
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

    # Departments are text that was never written; an empty list is the honest
    # answer until the next run generates and stores them.
    if data.get("departments") is None:
        data["departments"] = []
        changes.append("departments: [] (this issue predates them being persisted)")

    return changes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="report without writing")
    args = ap.parse_args()

    if not WEEKLY.exists():
        print(f"no snapshot at {WEEKLY}")
        return 1

    data = json.loads(WEEKLY.read_text(encoding="utf-8"))
    print(f"issue #{data.get('issue_number')} ({data.get('week_start')})")

    changes = repair(data) + normalize(data)
    if not changes:
        print("  snapshot already matches what the exporter emits")
        return 0
    for line in changes:
        print(f"  {line}")

    if args.dry_run:
        return 0

    # Match export_static.wj() exactly, so a repair is a small diff.
    WEEKLY.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    print("  written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
