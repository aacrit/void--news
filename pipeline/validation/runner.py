#!/usr/bin/env python3
"""
Bias Engine Cross-Reference Validation Runner (Tier 3)

Usage:
    python pipeline/validation/runner.py              # Full validation
    python pipeline/validation/runner.py --quick      # Skip distribution checks
    python pipeline/validation/runner.py --verbose    # Show per-signal decomposition
    python pipeline/validation/runner.py --update-snapshot  # Update regression baseline
    python pipeline/validation/runner.py --category wire    # Run specific category
    python pipeline/validation/runner.py --json       # JSON output for CI
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

# ---------------------------------------------------------------------------
# Path setup — must precede local imports
# ---------------------------------------------------------------------------
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
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
from analyzers.political_lean import analyze_political_lean
from analyzers.sensationalism import analyze_sensationalism
from analyzers.opinion_detector import analyze_opinion
from analyzers.factual_rigor import analyze_factual_rigor
from analyzers.framing import analyze_framing

from validation.fixtures import FIXTURES
from validation.source_profiles import ALLSIDES_TO_LEAN_RANGE, get_expected_range
from validation.signal_tracker import (
    decompose_lean,
    decompose_sensationalism,
    decompose_opinion,
    decompose_rigor,
    decompose_framing,
    detect_dead_signals,
    summarize_decomposition,
)

# ---------------------------------------------------------------------------
# Snapshot path
# ---------------------------------------------------------------------------
_SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "snapshot.json")

# ---------------------------------------------------------------------------
# Grade constants (match existing test_bias_engine.py grading logic)
# ---------------------------------------------------------------------------
GRADE_ORDER = ["CORRECT", "ACCEPTABLE", "WRONG", "CATASTROPHIC"]


def grade_axis(score: int, lo: int, hi: int) -> tuple[str, int]:
    """
    Grade a single axis score against its expected range.

    CORRECT     — score in [lo, hi]
    ACCEPTABLE  — score within 10 pts of boundary
    WRONG       — score 10-25 pts outside
    CATASTROPHIC — score > 25 pts outside

    Returns (grade_key, gap).
    """
    if lo <= score <= hi:
        return "CORRECT", 0
    gap = (lo - score) if score < lo else (score - hi)
    if gap <= 10:
        return "ACCEPTABLE", gap
    elif gap <= 25:
        return "WRONG", gap
    else:
        return "CATASTROPHIC", gap


# ---------------------------------------------------------------------------
# Cross-reference validation
# ---------------------------------------------------------------------------

def check_allsides_alignment(
    lean_score: int, allsides_rating: str, fixture_id: str,
    category: str = "",
) -> tuple[bool, str]:
    """
    Check if the lean score is consistent with the AllSides rating.

    Opinion-category articles get ±15 extra tolerance because per-article
    lean legitimately diverges from per-outlet AllSides ratings when text
    is densely partisan (e.g., a far-left column in a center-left paper).

    Returns (passed, detail_string).
    """
    expected_range = get_expected_range(allsides_rating)
    if expected_range is None:
        return True, f"no AllSides range for '{allsides_rating}' (skipped)"

    lo, hi = expected_range
    # Opinion articles: widen tolerance by 15 pts each direction
    if category == "opinion":
        lo = max(0, lo - 15)
        hi = min(100, hi + 15)
    if lo <= lean_score <= hi:
        suffix = " (opinion tolerance)" if category == "opinion" else ""
        return True, f"lean={lean_score} in AllSides '{allsides_rating}' [{lo},{hi}]{suffix}"
    gap = (lo - lean_score) if lean_score < lo else (lean_score - hi)
    return False, f"lean={lean_score} OUTSIDE AllSides '{allsides_rating}' [{lo},{hi}] gap={gap}"


# ---------------------------------------------------------------------------
# Distribution health checks
# ---------------------------------------------------------------------------

def check_distribution_health(
    axis_name: str,
    scores: list[int],
    source_tiers: list[str],
    lean_baselines: list[str],
) -> list[tuple[bool, str]]:
    """
    Run distribution health checks for a single axis across all fixture scores.

    Returns list of (passed, message) tuples.
    """
    results = []
    if not scores:
        return results

    n = len(scores)
    import statistics as _stats

    # 1. No extreme clustering: no 10-point band contains > 30% of scores
    band_counts: dict[int, int] = {}
    for s in scores:
        band = (s // 10) * 10  # e.g. 40-49 → 40
        band_counts[band] = band_counts.get(band, 0) + 1
    max_band = max(band_counts.values())
    max_band_key = max(band_counts, key=band_counts.get)
    max_pct = max_band / n * 100
    if max_pct > 30:
        results.append((False, f"Extreme clustering: {max_pct:.1f}% in [{max_band},{max_band+9}]"))
    else:
        results.append((True, f"No extreme clustering (max {max_pct:.1f}% in [{max_band},{max_band+9}])"))

    # 2. Score spread: std dev > 8
    if n >= 3:
        std = _stats.stdev(scores)
        if std < 8:
            results.append((False, f"Low spread: std_dev={std:.1f} (< 8 required)"))
        else:
            results.append((True, f"Adequate spread: std_dev={std:.1f}"))

    # 3. Floor/ceiling check: < 15% at exactly 0 or 100
    at_floor = sum(1 for s in scores if s == 0)
    at_ceiling = sum(1 for s in scores if s == 100)
    floor_pct = at_floor / n * 100
    ceil_pct = at_ceiling / n * 100
    if floor_pct > 15:
        results.append((False, f"Floor concentration: {floor_pct:.1f}% at score=0"))
    else:
        results.append((True, f"No floor concentration ({floor_pct:.1f}% at 0)"))
    if ceil_pct > 15:
        results.append((False, f"Ceiling concentration: {ceil_pct:.1f}% at score=100"))
    else:
        results.append((True, f"No ceiling concentration ({ceil_pct:.1f}% at 100)"))

    return results


def check_cross_axis_correlation(
    axis_scores: dict[str, list[int]],
    threshold: float = 0.70,
) -> list[tuple[bool, str]]:
    """
    Check pairwise Pearson correlation between axes.

    Flags pairs with |r| > threshold as potential redundancy.
    Returns list of (passed, message) tuples.
    """
    results = []
    axes = list(axis_scores.keys())
    n = len(axes)
    if not axes or len(axis_scores[axes[0]]) < 3:
        return results

    import statistics as _stats

    for i in range(n):
        for j in range(i + 1, n):
            xs = axis_scores[axes[i]]
            ys = axis_scores[axes[j]]
            if len(xs) != len(ys) or len(xs) < 3:
                continue
            mean_x = _stats.mean(xs)
            mean_y = _stats.mean(ys)
            std_x = _stats.stdev(xs)
            std_y = _stats.stdev(ys)
            if std_x == 0 or std_y == 0:
                continue
            cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / (len(xs) - 1)
            r = cov / (std_x * std_y)
            label = f"{axes[i]} x {axes[j]}: r={r:.3f}"
            if abs(r) > threshold:
                results.append((False, f"{label} (EXCEEDS {threshold} redundancy threshold)"))
            else:
                results.append((True, label))

    return results


def check_directional_invariants(
    lean_scores: list[int],
    baselines: list[str],
) -> list[tuple[bool, str]]:
    """
    Check known-outlet directional invariants for lean scores.

    - center outlets: mean lean should be in [40, 60]
    - left outlets (far-left, left): mean lean should be < 45
    - right outlets (far-right, right): mean lean should be > 55
    """
    results = []

    center_scores = [
        s for s, b in zip(lean_scores, baselines)
        if b == "center"
    ]
    left_scores = [
        s for s, b in zip(lean_scores, baselines)
        if b in ("far-left", "left")
    ]
    right_scores = [
        s for s, b in zip(lean_scores, baselines)
        if b in ("far-right", "right")
    ]

    if center_scores:
        mean_center = sum(center_scores) / len(center_scores)
        if 40 <= mean_center <= 60:
            results.append((True, f"Center outlets mean lean: {mean_center:.1f} (in [40,60])"))
        else:
            results.append((False, f"Center outlets mean lean: {mean_center:.1f} (expected [40,60])"))

    if left_scores:
        mean_left = sum(left_scores) / len(left_scores)
        if mean_left < 45:
            results.append((True, f"Left outlets mean lean: {mean_left:.1f} (< 45)"))
        else:
            results.append((False, f"Left outlets mean lean: {mean_left:.1f} (expected < 45)"))

    if right_scores:
        mean_right = sum(right_scores) / len(right_scores)
        if mean_right > 55:
            results.append((True, f"Right outlets mean lean: {mean_right:.1f} (> 55)"))
        else:
            results.append((False, f"Right outlets mean lean: {mean_right:.1f} (expected > 55)"))

    return results


# ---------------------------------------------------------------------------
# Snapshot regression
# ---------------------------------------------------------------------------

def load_snapshot() -> dict:
    if not os.path.exists(_SNAPSHOT_PATH):
        return {}
    try:
        with open(_SNAPSHOT_PATH, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_snapshot(data: dict) -> None:
    with open(_SNAPSHOT_PATH, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Snapshot saved to {_SNAPSHOT_PATH}")


def check_regression(
    fixture_id: str,
    axis: str,
    current_score: int,
    current_grade: str,
    snapshot: dict,
) -> tuple[bool, str] | None:
    """
    Compare current score/grade against snapshot.

    Returns None if no snapshot data, else (passed, message).
    """
    key = f"{fixture_id}.{axis}"
    if key not in snapshot:
        return None

    prev = snapshot[key]
    prev_score = prev.get("score")
    prev_grade = prev.get("grade")

    messages = []
    passed = True

    if prev_score is not None:
        delta = abs(current_score - prev_score)
        if delta > 5:
            passed = False
            messages.append(f"score shift {prev_score}→{current_score} (Δ{delta})")

    if prev_grade is not None:
        if prev_grade in ("CORRECT", "ACCEPTABLE") and current_grade in ("WRONG", "CATASTROPHIC"):
            passed = False
            messages.append(f"grade regression {prev_grade}→{current_grade}")

    if not messages:
        return True, f"stable (score={current_score}, grade={current_grade})"
    return passed, "; ".join(messages)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

AXES = ["lean", "sens", "opinion", "rigor", "framing"]
AXIS_LABELS = {
    "lean":    "Political Lean  ",
    "sens":    "Sensationalism  ",
    "opinion": "Opinion/Fact    ",
    "rigor":   "Factual Rigor   ",
    "framing": "Framing         ",
}


def run_validation(
    category_filter: str | None = None,
    verbose: bool = False,
    quick: bool = False,
    update_snapshot: bool = False,
    json_output: bool = False,
) -> int:
    """
    Run the full validation suite.

    Returns 0 on success, 1 if CATASTROPHIC failures found.
    """
    fixtures = FIXTURES
    if category_filter:
        fixtures = [f for f in FIXTURES if f["category"] == category_filter]
        if not fixtures:
            print(f"No fixtures found for category '{category_filter}'.")
            print(f"Available categories: {sorted(set(f['category'] for f in FIXTURES))}")
            return 1

    snapshot = load_snapshot() if not update_snapshot else {}
    new_snapshot: dict = {}

    # Aggregate tracking
    axis_grades = {ax: {g: 0 for g in GRADE_ORDER} for ax in AXES}
    all_grades = {g: 0 for g in GRADE_ORDER}
    allsides_passed = 0
    allsides_total = 0
    axis_scores: dict[str, list[int]] = {ax: [] for ax in AXES}
    lean_baselines: list[str] = []
    all_decompositions: list[dict] = []
    worst_failures: list[dict] = []
    regression_issues: list[str] = []
    all_results: list[dict] = []  # for JSON output

    if not json_output:
        print("=" * 72)
        print("BIAS ENGINE VALIDATION REPORT")
        print(
            f"Date: {date.today()}  |  "
            f"Articles: {len(fixtures)}  |  "
            f"Axes: {len(AXES)}  |  "
            f"Checks: {len(fixtures) * len(AXES)}"
        )
        print("=" * 72)
        print()

    for fixture in fixtures:
        fid = fixture["id"]
        fname = fixture["name"]
        category = fixture["category"]
        art_dict = fixture["article"]
        src_dict = fixture["source"]
        expected = fixture["expected"]
        cross_ref = fixture.get("cross_ref", {})

        # Build article dict (same shape as analyzers expect)
        article = {
            "title":    art_dict.get("title", ""),
            "full_text": art_dict.get("full_text", ""),
            "summary":  art_dict.get("summary", ""),
            "url":      art_dict.get("url", ""),
            "section":  art_dict.get("section", ""),
            "source_id": src_dict.get("slug", ""),
        }

        # Run all 5 analyzers
        lean_result    = analyze_political_lean(article, src_dict)
        sens_result    = analyze_sensationalism(article, src_dict)
        opinion_result = analyze_opinion(article, src_dict)
        rigor_result   = analyze_factual_rigor(article, src_dict)
        framing_result = analyze_framing(article, source=src_dict)

        scores = {
            "lean":    lean_result["score"],
            "sens":    sens_result["score"],
            "opinion": opinion_result["score"],
            "rigor":   rigor_result["score"],
            "framing": framing_result["score"],
        }
        rationales = {
            "lean":    lean_result["rationale"],
            "sens":    sens_result["rationale"],
            "opinion": opinion_result["rationale"],
            "rigor":   rigor_result["rationale"],
            "framing": framing_result["rationale"],
        }

        # Signal decompositions
        decomps = {
            "lean":    decompose_lean(rationales["lean"], scores["lean"]),
            "sens":    decompose_sensationalism(rationales["sens"], scores["sens"]),
            "opinion": decompose_opinion(rationales["opinion"], scores["opinion"]),
            "rigor":   decompose_rigor(rationales["rigor"], scores["rigor"]),
            "framing": decompose_framing(rationales["framing"], scores["framing"]),
        }
        for ax in AXES:
            all_decompositions.append(decomps[ax])

        # Grade each axis
        fixture_grades: dict[str, str] = {}
        fixture_worst = "CORRECT"
        fixture_worst_detail: dict = {}

        for ax in AXES:
            score = scores[ax]
            exp = expected[ax]
            lo, hi = exp["range"]
            grade, gap = grade_axis(score, lo, hi)

            axis_grades[ax][grade] += 1
            all_grades[grade] += 1
            axis_scores[ax].append(score)
            fixture_grades[ax] = grade

            # Snapshot tracking
            snap_key = f"{fid}.{ax}"
            new_snapshot[snap_key] = {"score": score, "grade": grade}

            # Regression check
            reg_result = check_regression(fid, ax, score, grade, snapshot)
            if reg_result is not None:
                reg_passed, reg_msg = reg_result
                if not reg_passed:
                    regression_issues.append(f"{fid}.{ax}: {reg_msg}")

            # Track worst grade for this fixture
            if GRADE_ORDER.index(grade) > GRADE_ORDER.index(fixture_worst):
                fixture_worst = grade
                fixture_worst_detail = {
                    "axis": ax, "score": score,
                    "expected": [lo, hi], "gap": gap,
                    "rationale": exp.get("rationale", ""),
                }

        # AllSides cross-reference
        allsides_rating = cross_ref.get("allsides")
        if allsides_rating:
            allsides_total += 1
            xref_ok, xref_msg = check_allsides_alignment(
                scores["lean"], allsides_rating, fid,
                category=category,
            )
            if xref_ok:
                allsides_passed += 1

        lean_baselines.append(src_dict.get("political_lean_baseline", "center"))

        if fixture_worst in ("WRONG", "CATASTROPHIC"):
            worst_failures.append({
                "name": fname, "id": fid, "category": category,
                "grade": fixture_worst, **fixture_worst_detail,
            })

        # Per-fixture output
        if not json_output:
            print(f"--- [{category}] {fname} ---")
            for ax in AXES:
                score = scores[ax]
                exp = expected[ax]
                lo, hi = exp["range"]
                grade = fixture_grades[ax]
                gap = (lo - score) if score < lo else (score - hi) if score > hi else 0
                status = {"CORRECT": "PASS", "ACCEPTABLE": "~OK~", "WRONG": "FAIL",
                          "CATASTROPHIC": "CRIT"}[grade]
                print(f"  [{status}] {AXIS_LABELS[ax]}: {score:3d}  exp [{lo},{hi}]  {grade}",
                      end="")
                if gap > 0:
                    print(f"  gap={gap}", end="")
                print()

                if verbose:
                    print(f"         {summarize_decomposition(decomps[ax], ax)}")

            # AllSides
            if allsides_rating:
                xref_ok, xref_msg = check_allsides_alignment(
                    scores["lean"], allsides_rating, fid,
                    category=category,
                )
                status = "PASS" if xref_ok else "FAIL"
                print(f"  [{status}] AllSides: {xref_msg}")
            print()

        # JSON accumulation
        all_results.append({
            "id": fid, "name": fname, "category": category,
            "scores": scores, "grades": fixture_grades,
            "expected": {ax: expected[ax]["range"] for ax in AXES},
        })

    # ---------------------------------------------------------------------------
    # Distribution health checks
    # ---------------------------------------------------------------------------
    dist_results: dict[str, list[tuple[bool, str]]] = {}
    directional_results: list[tuple[bool, str]] = []
    correlation_results: list[tuple[bool, str]] = []

    if not quick:
        for ax in AXES:
            baselines_for_dist = [f["source"]["political_lean_baseline"] for f in fixtures]
            tiers_for_dist = [f["source"].get("tier", "us_major") for f in fixtures]
            dist_results[ax] = check_distribution_health(
                ax, axis_scores[ax], tiers_for_dist, baselines_for_dist
            )

        directional_results = check_directional_invariants(
            axis_scores["lean"], lean_baselines
        )

        correlation_results = check_cross_axis_correlation(axis_scores)

    # Dead signal detection
    dead_signals = detect_dead_signals(all_decompositions)

    # ---------------------------------------------------------------------------
    # Print report
    # ---------------------------------------------------------------------------
    total_checks = len(fixtures) * len(AXES)
    correct = all_grades["CORRECT"]
    acceptable = all_grades["ACCEPTABLE"]
    wrong = all_grades["WRONG"]
    catastrophic = all_grades["CATASTROPHIC"]
    accuracy_pct = round((correct + acceptable) / max(total_checks, 1) * 100, 1)

    if not json_output:
        print("=" * 72)
        print("GROUND-TRUTH RESULTS:")
        print(f"  CORRECT:      {correct:3d}/{total_checks} ({correct/total_checks*100:.1f}%)")
        print(f"  ACCEPTABLE:   {acceptable:3d}/{total_checks} ({acceptable/total_checks*100:.1f}%)")
        print(f"  WRONG:        {wrong:3d}/{total_checks} ({wrong/total_checks*100:.1f}%)")
        print(f"  CATASTROPHIC: {catastrophic:3d}/{total_checks} ({catastrophic/total_checks*100:.1f}%)")
        print(f"  ACCURACY:     {correct+acceptable}/{total_checks} ({accuracy_pct}%)")
        print()

        print("PER-AXIS ACCURACY:")
        for ax in AXES:
            ag = axis_grades[ax]
            n = len(fixtures)
            ax_acc = round((ag["CORRECT"] + ag["ACCEPTABLE"]) / max(n, 1) * 100, 1)
            print(f"  {AXIS_LABELS[ax]}: "
                  f"C={ag['CORRECT']} A={ag['ACCEPTABLE']} W={ag['WRONG']} X={ag['CATASTROPHIC']}"
                  f"  ({ax_acc}%)")
        print()

        print(f"CROSS-REFERENCE CHECKS:")
        print(f"  AllSides alignment: {allsides_passed}/{allsides_total} passed "
              f"({allsides_passed/max(allsides_total,1)*100:.1f}%)")
        print()

        if not quick:
            print("DISTRIBUTION HEALTH:")
            for ax in AXES:
                print(f"  [{ax.upper()}]")
                for passed, msg in dist_results.get(ax, []):
                    status = "PASS" if passed else "FAIL"
                    print(f"    [{status}] {msg}")
            print()
            print("DIRECTIONAL INVARIANTS:")
            for passed, msg in directional_results:
                status = "PASS" if passed else "FAIL"
                print(f"  [{status}] {msg}")
            print()

            print("CROSS-AXIS CORRELATION (redundancy threshold: 0.70):")
            for passed, msg in correlation_results:
                status = "PASS" if passed else "FAIL"
                print(f"  [{status}] {msg}")
            print()

        if dead_signals:
            print("DEAD SIGNALS:")
            for sig in dead_signals:
                print(f"  [WARN] {sig}")
        else:
            print("DEAD SIGNALS: None detected")
        print()

        if regression_issues:
            print("REGRESSION FLAGS:")
            for issue in regression_issues:
                print(f"  [WARN] {issue}")
            print()

        if worst_failures:
            print("WORST FAILURES:")
            for i, f in enumerate(worst_failures[:10], 1):
                ax = f.get("axis", "?")
                score = f.get("score", "?")
                exp = f.get("expected", ["?", "?"])
                gap = f.get("gap", "?")
                print(f"  {i}. [{f['grade']}] \"{f['name']}\" — "
                      f"{ax}: score={score}, expected [{exp[0]},{exp[1]}], gap={gap}")
                if f.get("rationale"):
                    print(f"     rationale: {f['rationale']}")
        else:
            print("WORST FAILURES: None — all axes within tolerance")

        print()
        print("=" * 72)

    # ---------------------------------------------------------------------------
    # JSON output mode
    # ---------------------------------------------------------------------------
    if json_output:
        output = {
            "date": str(date.today()),
            "articles": len(fixtures),
            "axes": len(AXES),
            "checks": total_checks,
            "results": {
                "correct": correct, "acceptable": acceptable,
                "wrong": wrong, "catastrophic": catastrophic,
                "accuracy_pct": accuracy_pct,
            },
            "per_axis": {
                ax: {
                    "correct": axis_grades[ax]["CORRECT"],
                    "acceptable": axis_grades[ax]["ACCEPTABLE"],
                    "wrong": axis_grades[ax]["WRONG"],
                    "catastrophic": axis_grades[ax]["CATASTROPHIC"],
                }
                for ax in AXES
            },
            "allsides": {
                "passed": allsides_passed,
                "total": allsides_total,
                "pct": round(allsides_passed / max(allsides_total, 1) * 100, 1),
            },
            "dead_signals": dead_signals,
            "cross_axis_correlation": [
                {"pair": msg.split(":")[0].strip(), "passed": ok, "detail": msg}
                for ok, msg in correlation_results
            ],
            "regression_issues": regression_issues,
            "worst_failures": worst_failures[:10],
            "fixture_results": all_results,
        }
        print(json.dumps(output, indent=2))

    # ---------------------------------------------------------------------------
    # Snapshot update
    # ---------------------------------------------------------------------------
    if update_snapshot:
        save_snapshot(new_snapshot)
        if not json_output:
            print(f"Snapshot updated: {len(new_snapshot)} entries.")

    return 1 if catastrophic > 0 else 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bias Engine Cross-Reference Validation Runner (Tier 3)"
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="Skip distribution health checks (faster)",
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Show per-signal decomposition for each article",
    )
    parser.add_argument(
        "--update-snapshot", action="store_true",
        help="Update the regression baseline snapshot",
    )
    parser.add_argument(
        "--category", type=str, default=None,
        help="Only run fixtures in the specified category",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output",
        help="Output results as JSON (for CI integration)",
    )
    args = parser.parse_args()

    exit_code = run_validation(
        category_filter=args.category,
        verbose=args.verbose,
        quick=args.quick,
        update_snapshot=args.update_snapshot,
        json_output=args.json_output,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
