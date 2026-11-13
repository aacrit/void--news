#!/usr/bin/env python3
"""The SessionStart hook cannot report green over an older failure.

Audit 3 item 6 (2026-10-02): `.claude/hooks/session-start.sh` read one
repo-wide `per_page=8` page of runs (mostly Pair Test and Anchor Pairs, so it
usually never saw the pipeline), judged each workflow by its NEWEST run (so a
newer `skipped` run masked an older `failure`), and passed ~121 KB of JSON as
one argv entry. The verdict now lives in `.claude/hooks/ci_status.py`, reads
STDIN, and judges each workflow by its newest completed, non-skipped run.

Planted defects, in `tests/fixtures/session_start/`:

  masked_failure.json  pipeline's newest runs are in progress, skipped and
                       cancelled; the newest real verdict under them is a
                       failure. Must print NOT GREEN and name the pipeline.
  all_green.json       the same shape over a success, with an OLDER failure
                       below it. Must print green: a fixed failure is fixed.

Also asserts the hook's shape: one call per workflow for the five that matter,
the payload on stdin, and no argv hand-off.

    python3 tests/test_session_start_hook.py
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOOK = ROOT / ".claude/hooks/session-start.sh"
STATUS = ROOT / ".claude/hooks/ci_status.py"
FIX = ROOT / "tests/fixtures/session_start"

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    print(f"[{'ok' if cond else 'FAIL'}] {name}" + (f": {detail}" if detail and not cond else ""))
    if not cond:
        failures.append(name)


def run(fixture: str) -> str:
    data = (FIX / fixture).read_text()
    p = subprocess.run([sys.executable, str(STATUS)], input=data,
                       capture_output=True, text=True, timeout=30)
    check(f"{fixture}: exits 0 (the hook never fails a session)", p.returncode == 0, p.stderr)
    return p.stdout


out = run("masked_failure.json")
check("masked failure prints NOT GREEN", "NOT GREEN" in out, out)
check("masked failure names the pipeline and the failure",
      bool(re.search(r"pipeline\.yml: failure on main", out)), out)
check("masked failure does not also claim green", "main is green" not in out, out)
check("a null or Not Found response is reported as no verdict, not as green",
      "freshness-check.yml" in out and "deploy-cloudflare.yml" in out, out)

out = run("all_green.json")
check("a success above an older failure is green", "main is green" in out and "NOT GREEN" not in out, out)

# Garbage on stdin must not crash or claim green.
p = subprocess.run([sys.executable, str(STATUS)], input="not json",
                   capture_output=True, text=True, timeout=30)
check("unparseable input exits 0 and claims nothing",
      p.returncode == 0 and "green" not in p.stdout.lower(), p.stdout)

# ---- the hook's shape ------------------------------------------------------
src = HOOK.read_text()
code = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith("#"))
for wf in ("pipeline.yml", "verify-production.yml", "freshness-check.yml",
           "deploy-cloudflare.yml", "auto-merge-claude.yml"):
    check(f"hook queries {wf}", wf in code)
check("hook calls the per-workflow runs endpoint",
      "/actions/workflows/$wf/runs" in code)
check("hook no longer reads the repo-wide per_page=8 page", "per_page=8" not in code)
check("hook pipes the payload to ci_status.py on stdin",
      bool(re.search(r"\|\s*python3\s+\"\$ROOT/\.claude/hooks/ci_status\.py\"", code)))
check("hook passes no JSON as argv (the old `python3 - \"$runs\"`)",
      '"$runs"' not in code and not re.search(r'python3 - "\$', code))
check("hook installs the pinned PyYAML without uninstalling the system one",
      "--ignore-installed" in code)

if failures:
    print(f"\nFAIL: {len(failures)} check(s)")
    sys.exit(1)
print("\nPASS  session-start hook: per-workflow calls, stdin JSON, a skipped run never masks a failure")
