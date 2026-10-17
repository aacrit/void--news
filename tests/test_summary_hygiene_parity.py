#!/usr/bin/env python3
"""The Python and TypeScript summary hygiene must agree.

utils/summary_hygiene.py and app/lib/summaryHygiene.ts are hand-kept in
lock-step and there was nothing checking that they still are. They decide the
same question on two sides of the same pipeline: the Python decides whether a
stored summary is a raw excerpt (the display window, the print archive, the
summary floor), the TypeScript decides whether to render it. A divergence
means a card the pipeline believes is fine renders blank, which is the exact
defect the floor pass was written to stop.

The fixture strings here are asserted IDENTICALLY by frontend/test/labels.test.mjs.
Adding a case to one file means adding it to the other.

Run: python tests/test_summary_hygiene_parity.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))

from utils.summary_hygiene import is_raw_excerpt  # noqa: E402

RAW_EXCERPT = [
    "Sign up for our newsletter to get the day's top stories.",
    "Why it matters: the vote splits the caucus three ways.",
    "The minister resigned on Tuesday. Photo: Getty Images",
    "Troops entered the city at dawn - reuters.com",
    "The council met on Tuesday (Ahmed Gomaa/Anadolu)",
    "The governmentSaid the investigationContinues into the collapse.",
]

CLEAN = [
    "The Senate voted 61 to 38 on Tuesday to confirm the nominee. "
    "Two Republicans crossed over.",
    "Pfizer said the mRNA candidate cut hospitalisations by 42 percent "
    "in the mRNA arm of the trial.",
    "Apple shipped 4.2 million iPhone units in the quarter, up from "
    "3.8 million a year earlier.",
]


def main() -> int:
    failed = 0
    for s in RAW_EXCERPT:
        if not is_raw_excerpt(s):
            failed += 1
            print(f"FAIL  python kept what the TypeScript blanks: {s[:60]!r}")
    for s in CLEAN:
        if is_raw_excerpt(s):
            failed += 1
            print(f"FAIL  python blanks what the TypeScript keeps: {s[:60]!r}")
    total = len(RAW_EXCERPT) + len(CLEAN)
    print(f"{total - failed}/{total} hygiene fixtures agree with the TypeScript")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
