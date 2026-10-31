"""Void News evaluation system (v1).

A deterministic, $0, no-LLM rule layer that interrogates the most recent daily
run's DISPLAYED top-50 feed and emits ranked red-flag findings + a scored
report.

This module produces high-signal CANDIDATE findings deterministically and emits
exactly the payload a Claude-agent "judge" needs to confirm them. The judge /
resolution layer is intentionally OUT of scope here (it runs separately over the
JSON candidates this module writes).

Public surface:
    checks.run_all_checks(clusters)  -> list[Finding]
    checks.score_findings(findings)  -> ScoreReport
    run_eval.main()                  -> writes eval_report.json + eval_report.md
"""

from .checks import (  # noqa: F401
    Finding,
    ScoreReport,
    GRADES,
    RED_FLAGS,
    run_all_checks,
    score_findings,
)

__all__ = [
    "Finding",
    "ScoreReport",
    "GRADES",
    "RED_FLAGS",
    "run_all_checks",
    "score_findings",
]
