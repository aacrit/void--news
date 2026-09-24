"""No kill-list term in the committed Weekly issues, checked before deploy.

W-10 (scripts/verify_sections.py) reads the SERVED /weekly page, so it can only
fail after a deploy. Issue #26 (2026-09-14) was published before the generator
enforced the kill list and turned main red for a day with 21 hits. This runs
the same matcher over the committed issue data, so a hit fails the branch
instead of production.

Run: python tests/test_weekly_killlist.py
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from verify_sections import kill_list_hits  # noqa: E402

FILES = [
    ROOT / "frontend" / "build-data" / "weekly-issues.json",
    ROOT / "frontend" / "public" / "data" / "weekly.json",
]


def strings(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield from strings(v, f"{path}.{k}")
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from strings(v, f"{path}[{i}]")
    elif isinstance(o, str):
        yield path, o


def main() -> int:
    planted = kill_list_hits("<p>This marks a key moment and a significant shift.</p>")
    if len(planted) < 2:
        print("FAIL  self-test: the matcher missed a planted kill-list term")
        return 1
    failures = []
    for f in FILES:
        if not f.exists():
            continue
        for path, s in strings(json.loads(f.read_text(encoding="utf-8"))):
            for hit in kill_list_hits("<p>" + html.escape(s) + "</p>"):
                failures.append(f"{f.name}{path}: {hit}")
    if failures:
        for line in failures:
            print("FAIL ", line)
        return 1
    print("PASS  no kill-list term in the committed Weekly issues")
    return 0


if __name__ == "__main__":
    sys.exit(main())
