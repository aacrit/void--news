#!/usr/bin/env python3
"""Clustering Validation Runner.

Mirrors pipeline/validation/runner.py (bias suite) but exercises
pipeline.clustering.story_cluster.cluster_stories() instead of analyzers.

Usage:
    python pipeline/validation/clustering/runner.py            # full pass
    python pipeline/validation/clustering/runner.py --json     # CI output
    python pipeline/validation/clustering/runner.py --case 001 # single fixture
    python pipeline/validation/clustering/runner.py --update-snapshot

Exit codes:
    0 — all pass / no regression vs snapshot
    1 — any CATASTROPHIC failure OR a WRONG/CATASTROPHIC count increase
        vs the prior snapshot (regression gate)
    2 — environment error (missing spaCy etc.)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime, timezone

# ---------------------------------------------------------------------------
# Path setup — must precede local imports
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_PIPELINE_DIR = os.path.join(_REPO_ROOT, "pipeline")
if _PIPELINE_DIR not in sys.path:
    sys.path.insert(0, _PIPELINE_DIR)

# ---------------------------------------------------------------------------
# spaCy model check — fail fast with helpful message if missing
# ---------------------------------------------------------------------------
try:
    import spacy
    spacy.load("en_core_web_sm")
except OSError:
    print(
        "ERROR: spaCy model 'en_core_web_sm' not found.\n"
        "Install it with: python -m spacy download en_core_web_sm",
        file=sys.stderr,
    )
    sys.exit(2)

# ---------------------------------------------------------------------------
# Local imports (after path setup)
# ---------------------------------------------------------------------------
from clustering.story_cluster import cluster_stories

# Local package imports — package-style first, file-relative fallback
try:
    from validation.clustering.article_loader import load_fixtures, load_fixture
    from validation.clustering import assertions as A
except ImportError:
    sys.path.insert(0, os.path.dirname(__file__))
    from article_loader import load_fixtures, load_fixture  # type: ignore
    import assertions as A  # type: ignore


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GRADE_ORDER = ["CORRECT", "ACCEPTABLE", "WRONG", "CATASTROPHIC"]

_HERE = os.path.dirname(__file__)
_SNAPSHOT_PATH = os.path.join(_HERE, "snapshot.json")
_FIXTURES_DIR = os.path.join(_HERE, "fixtures")


# ---------------------------------------------------------------------------
# Snapshot helpers
# ---------------------------------------------------------------------------

def load_snapshot() -> dict:
    """Load the regression snapshot (or empty dict if missing/invalid)."""
    if not os.path.exists(_SNAPSHOT_PATH):
        return {"runs": [], "current_summary": {}}
    try:
        with open(_SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Backward-compat: ensure expected shape
        if "runs" not in data:
            data["runs"] = []
        if "current_summary" not in data:
            data["current_summary"] = {}
        return data
    except (json.JSONDecodeError, OSError):
        return {"runs": [], "current_summary": {}}


def save_snapshot(data: dict) -> None:
    with open(_SNAPSHOT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Snapshot saved to {_SNAPSHOT_PATH}")


def grade_summary(results: list[dict]) -> dict[str, int]:
    """Reduce per-fixture results to a {grade: count} summary."""
    out = {g: 0 for g in GRADE_ORDER}
    for r in results:
        out[r["grade"]] = out.get(r["grade"], 0) + 1
    return out


def is_regression(prev_summary: dict, curr_summary: dict) -> tuple[bool, list[str]]:
    """Return (regressed?, reasons) by comparing two grade-count dicts.

    Regression rule: if WRONG or CATASTROPHIC counts INCREASED vs the
    prior snapshot, fail. Improvements (counts going down) never fail.
    First-time runs (empty prev) never regress.
    """
    if not prev_summary:
        return False, []
    reasons: list[str] = []
    for grade in ("WRONG", "CATASTROPHIC"):
        prev = prev_summary.get(grade, 0)
        curr = curr_summary.get(grade, 0)
        if curr > prev:
            reasons.append(f"{grade} count rose {prev}->{curr}")
    return bool(reasons), reasons


# ---------------------------------------------------------------------------
# Fixture execution
# ---------------------------------------------------------------------------

def run_fixture(fixture: dict) -> dict:
    """Run a single fixture through cluster_stories() and grade it.

    Returns a dict suitable for the report and JSON output:
        id, name, failure_kind, grade, message, n_clusters,
        n_articles, expectation_type
    """
    articles = fixture["articles"]
    expectation = fixture["expectation"]

    try:
        clusters = cluster_stories(articles)
    except Exception as e:
        return {
            "id": fixture["id"],
            "name": fixture["name"],
            "failure_kind": fixture["failure_kind"],
            "grade": "CATASTROPHIC",
            "message": f"cluster_stories() raised {type(e).__name__}: {e}",
            "n_clusters": 0,
            "n_articles": len(articles),
            "expectation_type": expectation.get("type", "?"),
        }

    grade, msg = A.evaluate(clusters, expectation)

    return {
        "id": fixture["id"],
        "name": fixture["name"],
        "failure_kind": fixture["failure_kind"],
        "grade": grade,
        "message": msg,
        "n_clusters": len(clusters),
        "n_articles": len(articles),
        "expectation_type": expectation.get("type", "?"),
    }


def filter_fixtures(fixtures: list[dict], case: str | None) -> list[dict]:
    """Filter loaded fixtures by --case (substring match on id OR filename).

    Accepts:
      --case 001                # filename prefix
      --case streeting          # id substring
      --case warsh-fed-chair    # id full
    """
    if not case:
        return fixtures
    case_lower = case.lower()
    out = []
    for f in fixtures:
        fid = f["id"].lower()
        fname = os.path.basename(f.get("_path", "")).lower()
        if case_lower in fid or case_lower in fname:
            out.append(f)
    return out


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

_STATUS_TAG = {
    "CORRECT":      "PASS",
    "ACCEPTABLE":   "~OK~",
    "WRONG":        "FAIL",
    "CATASTROPHIC": "CRIT",
}


def print_text_report(
    results: list[dict],
    summary: dict[str, int],
    snapshot: dict,
    regressions: list[str],
) -> None:
    total = len(results)
    print("=" * 72)
    print("CLUSTERING VALIDATION REPORT")
    print(
        f"Date: {date.today()}  |  "
        f"Fixtures: {total}  |  "
        f"Predicates: {len(set(r['expectation_type'] for r in results))}"
    )
    print("=" * 72)
    print()

    for r in results:
        status = _STATUS_TAG[r["grade"]]
        kind = r["failure_kind"] or "-"
        print(f"--- [{kind}] {r['id']} ---")
        print(
            f"  [{status}] {r['name']}\n"
            f"         predicate={r['expectation_type']}  "
            f"clusters={r['n_clusters']}/{r['n_articles']}  grade={r['grade']}"
        )
        print(f"         {r['message']}")
        print()

    print("=" * 72)
    print("RESULTS:")
    print(f"  CORRECT:      {summary['CORRECT']:3d}/{total}")
    print(f"  ACCEPTABLE:   {summary['ACCEPTABLE']:3d}/{total}")
    print(f"  WRONG:        {summary['WRONG']:3d}/{total}")
    print(f"  CATASTROPHIC: {summary['CATASTROPHIC']:3d}/{total}")
    pass_pct = (summary["CORRECT"] + summary["ACCEPTABLE"]) / max(total, 1) * 100
    print(f"  PASS-RATE:    {pass_pct:.1f}%  (CORRECT + ACCEPTABLE)")
    print()

    # By failure_kind
    by_kind: dict[str, list[str]] = {}
    for r in results:
        by_kind.setdefault(r["failure_kind"] or "unknown", []).append(r["grade"])
    print("BY FAILURE KIND:")
    for kind in sorted(by_kind):
        grades = by_kind[kind]
        n = len(grades)
        n_ok = sum(1 for g in grades if g in ("CORRECT", "ACCEPTABLE"))
        print(f"  {kind:32s}  {n_ok}/{n} pass")
    print()

    # Regression vs snapshot
    prev_summary = snapshot.get("current_summary") or {}
    if prev_summary:
        print("REGRESSION VS SNAPSHOT:")
        for g in GRADE_ORDER:
            prev = prev_summary.get(g, 0)
            curr = summary[g]
            arrow = "==" if curr == prev else ("UP" if curr > prev else "DN")
            print(f"  {g:14s}  {prev} -> {curr}  [{arrow}]")
        if regressions:
            print()
            print("  REGRESSION FLAGS:")
            for r in regressions:
                print(f"    [WARN] {r}")
        else:
            print("  No regressions vs snapshot.")
    else:
        print("REGRESSION VS SNAPSHOT: no prior snapshot data — first run.")
    print()
    print("=" * 72)


def build_json_report(
    results: list[dict],
    summary: dict[str, int],
    snapshot: dict,
    regressions: list[str],
) -> dict:
    total = len(results)
    return {
        "date": str(date.today()),
        "fixtures": total,
        "summary": summary,
        "pass_rate_pct": round(
            (summary["CORRECT"] + summary["ACCEPTABLE"]) / max(total, 1) * 100, 1
        ),
        "results": results,
        "regressions": regressions,
        "prev_summary": snapshot.get("current_summary") or {},
    }


# ---------------------------------------------------------------------------
# Main entry
# ---------------------------------------------------------------------------

def run_validation(
    case: str | None = None,
    json_output: bool = False,
    update_snapshot: bool = False,
) -> int:
    fixtures = load_fixtures(_FIXTURES_DIR)
    fixtures = filter_fixtures(fixtures, case)

    if not fixtures:
        msg = "No fixtures loaded."
        if case:
            msg = f"No fixtures matched --case '{case}'."
        if json_output:
            print(json.dumps({"error": msg}))
        else:
            print(msg)
        return 1

    snapshot = load_snapshot()
    results = [run_fixture(f) for f in fixtures]
    summary = grade_summary(results)
    regressed, reasons = is_regression(snapshot.get("current_summary") or {}, summary)

    if json_output:
        report = build_json_report(results, summary, snapshot, reasons)
        # IMPORTANT: emit a recognizable summary line for CI grep, in addition
        # to the JSON body. Mirrors the bias-suite CI gate pattern in
        # .github/workflows/validate-bias.yml which greps for
        # "CATASTROPHIC: [1-9]+".
        print(
            f"GRADES: CORRECT: {summary['CORRECT']} | "
            f"ACCEPTABLE: {summary['ACCEPTABLE']} | "
            f"WRONG: {summary['WRONG']} | "
            f"CATASTROPHIC: {summary['CATASTROPHIC']}",
            file=sys.stderr,
        )
        print(json.dumps(report, indent=2))
    else:
        print_text_report(results, summary, snapshot, reasons)
        # Same summary line for CI greps in non-JSON mode too
        print(
            f"GRADES: CORRECT: {summary['CORRECT']} | "
            f"ACCEPTABLE: {summary['ACCEPTABLE']} | "
            f"WRONG: {summary['WRONG']} | "
            f"CATASTROPHIC: {summary['CATASTROPHIC']}"
        )

    if update_snapshot:
        # Append to runs[] history and replace current_summary.
        run_record = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "fixtures": len(fixtures),
            "summary": summary,
            "per_fixture": [
                {"id": r["id"], "grade": r["grade"], "kind": r["failure_kind"]}
                for r in results
            ],
        }
        runs = list(snapshot.get("runs") or [])
        runs.append(run_record)
        # Keep at most last 20 runs to bound file size
        runs = runs[-20:]
        save_snapshot({"runs": runs, "current_summary": summary})

    # Exit code: catastrophic failure OR regression gate
    if summary["CATASTROPHIC"] > 0:
        return 1
    if regressed:
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Clustering Validation Runner")
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Emit JSON report (for CI integration)",
    )
    parser.add_argument(
        "--case", type=str, default=None,
        help="Substring match against fixture id (e.g., --case 001 or --case streeting)",
    )
    parser.add_argument(
        "--update-snapshot", action="store_true",
        help="Refresh regression baseline (snapshot.json) with current results",
    )
    args = parser.parse_args()

    sys.exit(run_validation(
        case=args.case,
        json_output=args.json_output,
        update_snapshot=args.update_snapshot,
    ))


if __name__ == "__main__":
    main()
