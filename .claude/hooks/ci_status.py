#!/usr/bin/env python3
"""Decide whether main is green, from one Actions API response per workflow.

Read by `.claude/hooks/session-start.sh`. Input arrives on STDIN as one JSON
object mapping a workflow file name to the body of
`GET /repos/{slug}/actions/workflows/{file}/runs?...` (or null when the call
failed). It used to be one `actions/runs?per_page=8` call passed as argv, which
had three defects (audit 3 item 6, 2026-10-02):

1. Eight runs across the whole repository were mostly Pair Test and Anchor
   Pairs commits, so the pipeline, freshness, deploy and verify workflows were
   usually not in the window at all, and "main is green" meant "the collectors
   are green".
2. It took each workflow's NEWEST run. A newer `skipped` or `cancelled` run
   therefore masked an older `failure`: the failure was still the last real
   verdict, and the hook printed green over it.
3. 121 KB of JSON as one argv entry sits near the kernel's 128 KB limit for a
   single argument, and `|| true` swallowed the failure silently.

Now the verdict for a workflow is its newest COMPLETED run that is neither
skipped nor cancelled. A run in progress is reported but decides nothing.

Prints the report and exits 0 always; the caller must never fail a session.
`tests/test_session_start_hook.py` holds the fixtures.
"""
from __future__ import annotations

import json
import sys

# Conclusions that are not a verdict on the code: a conditional job declining
# to run, or a run superseded by a newer one.
NOT_A_VERDICT = {"skipped", "cancelled"}
GREEN = {"success", "neutral"}


def verdict(runs: list[dict]) -> tuple[str | None, dict | None, bool]:
    """(conclusion, run, newer_run_in_flight) for one workflow's runs, newest first."""
    in_flight = False
    for r in runs:
        if r.get("status") != "completed":
            in_flight = True
            continue
        c = r.get("conclusion")
        if c in NOT_A_VERDICT or c is None:
            continue
        return c, r, in_flight
    return None, None, in_flight


def report(payload: dict) -> list[str]:
    lines: list[str] = []
    bad: list[str] = []
    checked = 0
    unknown: list[str] = []
    for wf, body in payload.items():
        if wf.startswith("_"):
            continue
        runs = (body or {}).get("workflow_runs") if isinstance(body, dict) else None
        if runs is None:
            unknown.append(wf)
            continue
        c, r, in_flight = verdict(runs)
        if c is None:
            unknown.append(wf)
            continue
        checked += 1
        if c not in GREEN:
            when = (r or {}).get("created_at", "?")
            branch = (r or {}).get("head_branch", "?")
            note = " (a newer run is in progress)" if in_flight else ""
            bad.append(f"{wf}: {c} on {branch} at {when}{note}")
    if bad:
        lines.append("[void] *** main IS NOT GREEN ***")
        lines += [f"[void]     {b}" for b in bad]
        lines.append("[void] main is production. Per CLAUDE.md, a red main is fixed")
        lines.append("[void] BEFORE any new work: a commit not on main is not live, and")
        lines.append("[void] every branch inherits main's data, so this blocks everyone.")
        lines.append("[void] (verdict = newest completed run that was not skipped or cancelled)")
    elif checked:
        lines.append(f"[void] main is green ({checked} workflow(s) checked: newest completed, "
                     "non-skipped run of each)")
    if unknown:
        lines.append(f"[void] no verdict for: {', '.join(unknown)} (API unreachable or no completed run)")
    return lines


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        print("[void] could not parse the GitHub API responses; main's CI state unknown")
        return 0
    if not isinstance(payload, dict):
        print("[void] unexpected GitHub API payload; main's CI state unknown")
        return 0
    for line in report(payload):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
