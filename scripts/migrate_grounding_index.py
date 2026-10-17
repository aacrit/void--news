#!/usr/bin/env python3
"""Convert a format-1 grounding record (prose) into a format-2 index.

Format 1 stored up to 24,000 characters of each source article. The repo
commits `frontend/build-data/grounding/`, so on 2026-09-22 the committed tree
held 519,041 characters of publisher article text, against the top-priority
control in `docs/IP-COMPLIANCE.md`.

Deleting those files would have been the quick fix and would have cost the
audit: E-13 and E-14 could no longer be run against the feed that shipped on
2026-09-21, which is the only feed whose sources still exist anywhere. So each
record is converted instead. The index is built FROM the prose, then the prose
is dropped, so the working tree keeps its verification power and loses the
text.

This does not touch git history. The prose committed before today is still in
it; removing that is a history rewrite and a separate decision.

Usage: python3 scripts/migrate_grounding_index.py [--apply] [dir]
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pipeline.editorial import grounding  # noqa: E402


def convert(record: dict) -> dict:
    """A format-2 index built from a format-1 record's own stored text."""
    articles = [{"id": a.get("id"), "url": a.get("url"),
                 "full_text": a.get("text") or ""}
                for a in record.get("articles") or []]
    out = grounding.build_record(record.get("cluster"), articles)
    # The original lengths and truncation flags are the format-1 record's, and
    # they are the honest ones: this pass sees only what was kept, so it would
    # otherwise report every already-cut article as whole.
    for new, old in zip(out["articles"], record.get("articles") or []):
        if old.get("chars") is not None:
            new["chars"] = old["chars"]
        if old.get("truncated") is not None:
            new["truncated"] = bool(old["truncated"])
    out["truncated"] = any(a["truncated"] for a in out["articles"])
    out["convertedFrom"] = 1
    return out


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--apply"]
    apply = "--apply" in sys.argv
    base = pathlib.Path(args[0]) if args else (
        ROOT / "frontend" / "build-data" / grounding.DIRNAME)
    files = sorted(base.glob("*.json"))
    if not files:
        print(f"no records under {base}")
        return 0
    before = after = 0
    converted = 0
    for path in files:
        rec = json.loads(path.read_text(encoding="utf-8"))
        if int(rec.get("format") or 1) >= grounding.FORMAT:
            continue
        prose = sum(len(a.get("text") or "") for a in rec.get("articles") or [])
        new = convert(rec)
        before += prose
        blob = json.dumps(new, ensure_ascii=False)
        after += len(blob)
        converted += 1
        if apply:
            path.write_text(blob, encoding="utf-8")
    verb = "converted" if apply else "would convert"
    print(f"{verb} {converted}/{len(files)} record(s): "
          f"{before:,} characters of article text out, "
          f"{after:,} characters of index in")
    if not apply:
        print("dry run. pass --apply to write.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
