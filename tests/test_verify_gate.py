#!/usr/bin/env python3
"""Self-test for the production verification gate.

Proves the gate discriminates: it PASSES a known-good render and FAILS
deliberately corrupted ones. "A gate that has never caught anything is not a
gate" - this is the anything.

2026-09-06: the clean fixture used to FAIL (its summaries were written before
MIN_SUMMARY_CHARS rose to 300), so this test was red and nothing ran it in CI.
Both are fixed: the fixture carries real prose plus canonical /story/ anchors,
and the assertions now check WHICH check fired, not just the exit code. A
fixture that trips ten checks at once cannot prove the eleventh works.

Run: python tests/test_verify_gate.py   (exit 0 = every assertion holds)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIFY = ROOT / "scripts" / "verify_production.py"
FIX = ROOT / "tests" / "fixtures"
# The fixtures are 3-card pages; the real feed size lives in
# frontend/config/feed.json and is passed by scripts/verify-production.sh.
FIXTURE_CARDS = "3"


def run(fixture: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(VERIFY), str(FIX / fixture), "--url", fixture,
         "--expect-count", FIXTURE_CARDS],
        capture_output=True, text=True,
    )


def main() -> int:
    ok = True

    clean = run("clean_feed.html")
    if clean.returncode != 0:
        print(f"FAIL: clean fixture should pass (got exit {clean.returncode})")
        print(clean.stdout)
        ok = False
    else:
        print("PASS: clean fixture accepted")

    broken = run("broken_feed.html")
    if broken.returncode == 0:
        print("FAIL: broken fixture should be rejected (got exit 0)")
        ok = False
    else:
        print("PASS: broken fixture rejected")

    # Each of these plants ONE defect and must be rejected BY THE CHECK NAMED.
    # Asserting on the message is what proves the new assertion works: the
    # query-link fixture was already caught by the old shape check, and the
    # missing-anchor fixture was caught by nothing at all.
    cases = [
        ("tail_query_href_feed.html",
         "do not link to a canonical /story/<uuid>/ page",
         "archive-miss /?story= link on the last card"),
        ("tail_missing_anchor_feed.html",
         "cards rendered but 2 stretch-link anchors found",
         "card rendered with no stretch-link anchor"),
    ]
    for fixture, needle, what in cases:
        res = run(fixture)
        if res.returncode == 0:
            print(f"FAIL: {what} should be rejected (got exit 0)")
            ok = False
        elif needle not in res.stdout:
            print(f"FAIL: {what} rejected, but not by the anchor-coverage check.")
            print(f"      expected to see: {needle}")
            ok = False
        else:
            print(f"PASS: {what} rejected by the anchor-coverage check")

    # The count assertion must notice a short render even when the page is
    # self-consistent (header count == cards rendered).
    res = run("clean_feed.html")
    short = subprocess.run(
        [sys.executable, str(VERIFY), str(FIX / "clean_feed.html"),
         "--url", "clean", "--expect-count", "20"],
        capture_output=True, text=True,
    )
    if short.returncode == 0 or "configured feed size is 20" not in short.stdout:
        print("FAIL: a 3-card page should fail --expect-count 20")
        ok = False
    else:
        print("PASS: short render rejected against the configured feed size")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
