#!/usr/bin/env python3
"""Self-test for the production verification gate.

Proves the gate discriminates: it PASSES a known-good render and FAILS a
deliberately corrupted one. "A gate that has never caught anything is not a
gate" — this is the anything.

Run: python tests/test_verify_gate.py   (exit 0 = both assertions hold)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERIFY = ROOT / "scripts" / "verify_production.py"
FIX = ROOT / "tests" / "fixtures"


def run(fixture: str) -> int:
    return subprocess.run(
        [sys.executable, str(VERIFY), str(FIX / fixture), "--url", fixture],
        capture_output=True, text=True,
    ).returncode


def main() -> int:
    clean = run("clean_feed.html")
    broken = run("broken_feed.html")
    ok = True
    if clean != 0:
        print(f"FAIL: clean fixture should pass (got exit {clean})")
        ok = False
    else:
        print("PASS: clean fixture accepted")
    if broken == 0:
        print("FAIL: broken fixture should be rejected (got exit 0)")
        ok = False
    else:
        print("PASS: broken fixture rejected")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
