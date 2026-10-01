"""The daily brief's writer is never handed a story it cannot source.

2026-09-30: the Christa Pike cluster reached the brief with an empty summary.
Given only a headline, the writer added "This follows a February 25, 2026,
order from U.S. District Judge Brian Murphy", taken from the deportation story
listed above it, and On Air broadcast it. A summary-less story now never enters
the prompt, and the radio rundown marks one as headline-only.

    python tests/test_brief_inputs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from briefing import daily_brief_generator as dbg  # noqa: E402
from briefing.radio_script_generator import build_stories_block  # noqa: E402

dbg._get_previous_cluster_info = lambda edition: (set(), [])  # no DB

failures: list[str] = []


def check(cond: bool, msg: str) -> None:
    print(f"  {'ok  ' if cond else 'FAIL'} {msg}")
    if not cond:
        failures.append(msg)


clusters = [
    {"id": "a", "title": "Court lets third-country deportations resume", "sections": ["world"],
     "summary": "The order lifts a February 25 ruling by U.S. District Judge Brian Murphy.",
     "rank_world": 90, "source_count": 30},
    {"id": "b", "title": "Court temporarily halts Christa Pike's execution", "sections": ["world"],
     "summary": "", "rank_world": 80, "source_count": 12},
    {"id": "c", "title": "Listed summary", "sections": ["world"],
     "summary": ["One sentence.", "Two."], "rank_world": 70, "source_count": 5},
]
top, block = dbg._build_stories_block(clusters, "world")
ids = [c["id"] for c in top]
check("b" not in ids, f"a story with no summary is not handed to the brief writer ({ids})")
check("Christa Pike" not in block, "its headline is not in the prompt")
check("a" in ids and "c" in ids, "stories with a summary, string or list, stay")

radio = build_stories_block(clusters)
check("No summary: say only what the headline says" in radio,
      "the radio rundown marks a summary-less story as headline-only")

if failures:
    print(f"\nFAIL  {len(failures)} brief-input check(s)")
    sys.exit(1)
print("\nPASS  the brief writer is handed only stories it can source")
