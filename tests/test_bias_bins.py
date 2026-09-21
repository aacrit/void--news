#!/usr/bin/env python3
"""The lean ladder is one ladder, in two languages.

`leanToBucket` in `frontend/app/lib/biasColors.ts` decides what a score is
CALLED on the page. `compute_lean_histogram` in
`pipeline/utils/bias_aggregation.py` decides which bucket a score is COUNTED
in, and those counts are what the card's register and the Deep Dive bench are
drawn from. Nothing else compares them, so a drift between the two would show
as a card whose shape disagrees with its own label, silently.

Written 2026-09-21 alongside the fix for a real defect in both of them. The
boundaries were `<=20, <=35, <=45, <=55, <=65, <=80`, which put four of the
seven outlet baselines on a bucket's upper EDGE. On the right of the ladder
that edge is the most extreme end and the rung landed correctly by luck; on
the left it is the LEAST extreme end, so the rung landed one step too far out:

    an outlet the roster rates `left`        scores 20 -> the page said FAR LEFT
    an outlet the roster rates `center-left` scores 35 -> the page said LEFT

The error ran one way. A left-leaning outlet publishing unremarkable copy was
displayed as more extreme than this product's own roster rates it, while a
right-leaning one was not. `center-left` held no baseline at all: it was a
ten-point gap populated only by the skirt of the 35 spike. Measured on the
2026-09-21 feed, this moved 156 of 668 articles (23.4%) into a different
bucket, though only 11 (1.6%) changed their left/centre/right group.

Both sides now bin on the baselines themselves, nearest wins, and a score
exactly between two rungs takes the one nearer the centre.

Stdlib only apart from reading the TS file as text: no node, no build.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from utils.bias_aggregation import compute_lean_histogram  # noqa: E402

TS = ROOT / "frontend/app/lib/biasColors.ts"
#: bucket name in the pipeline -> the LeanCategory the frontend uses
PY_TO_TS = {
    "far_left": "far-left", "left": "left", "center_left": "center-left",
    "center": "center", "center_right": "center-right", "right": "right",
    "far_right": "far-right",
}
BASELINES = [("far-left", 10), ("left", 20), ("center-left", 35),
             ("center", 50), ("center-right", 65), ("right", 80),
             ("far-right", 90)]
ORDER = [n for n, _ in BASELINES]


def py_bucket(v):
    """Which bucket the PIPELINE counts this score in."""
    hist = compute_lean_histogram([v])["lean_buckets"]
    hit = [k for k, n in hist.items() if n]
    return PY_TO_TS[hit[0]] if len(hit) == 1 else f"AMBIGUOUS {hit}"


def ts_baselines():
    """The baselines the FRONTEND ladder is built from, read out of the TS."""
    src = TS.read_text()
    m = re.search(r"LEAN_BASELINES[^=]*=\s*\[(.*?)\]\s*as const", src, re.S)
    if not m:
        return None
    return [(n, int(v)) for n, v in
            re.findall(r'\["?([a-z-]+)"?,\s*(\d+)\]', m.group(1))]


def ts_bucket(v, rungs):
    """Mirror of leanToBucket: nearest baseline, ties toward the centre."""
    best, best_gap, best_pull = "center", float("inf"), float("inf")
    for name, base in rungs:
        gap, pull = abs(v - base), abs(base - 50)
        if gap < best_gap - 1e-9 or (abs(gap - best_gap) < 1e-9 and pull < best_pull):
            best, best_gap, best_pull = name, gap, pull
    return best


def check_the_frontend_declares_its_rungs():
    rungs = ts_baselines()
    if rungs is None:
        return ["biasColors.ts no longer exports a readable LEAN_BASELINES "
                "table, so the two ladders can no longer be compared here"]
    if rungs != BASELINES:
        return [f"frontend rungs {rungs} differ from {BASELINES}"]
    return []


def check_every_baseline_lands_on_its_own_name():
    """The defect this file exists for, asserted on both sides."""
    out = []
    rungs = ts_baselines() or BASELINES
    for name, base in BASELINES:
        got_py = py_bucket(base)
        got_ts = ts_bucket(base, rungs)
        if got_py != name:
            out.append(f"pipeline bins a {name} outlet's baseline ({base}) as "
                       f"{got_py}: it is displayed one rung from its own rating")
        if got_ts != name:
            out.append(f"frontend calls a {name} outlet's baseline ({base}) "
                       f"{got_ts}")
    return out


def check_the_two_agree_on_every_score():
    rungs = ts_baselines() or BASELINES
    bad = [(v, py_bucket(v), ts_bucket(v, rungs))
           for v in range(0, 101)
           if py_bucket(v) != ts_bucket(v, rungs)]
    if not bad:
        return []
    head = ", ".join(f"{v}: pipeline {p} vs frontend {t}" for v, p, t in bad[:6])
    return [f"{len(bad)} score(s) bin differently in the two languages. {head}"]


def check_the_ladder_is_symmetric():
    """A score N points left of centre sits as many rungs out as N points right.

    The original bug was exactly an asymmetry, so this is the shape of it
    rather than a restatement of the boundaries.
    """
    rungs = ts_baselines() or BASELINES
    out = []
    for d in range(1, 51):
        li = ORDER.index(ts_bucket(50 - d, rungs))
        ri = ORDER.index(ts_bucket(50 + d, rungs))
        if (3 - li) != (ri - 3):
            out.append(f"at +/-{d} the ladder is lopsided: "
                       f"{ts_bucket(50 - d, rungs)} against {ts_bucket(50 + d, rungs)}")
    return out[:6]


def check_the_ladder_never_steps_back():
    rungs = ts_baselines() or BASELINES
    out, prev = [], 0
    for v in range(0, 101):
        i = ORDER.index(ts_bucket(v, rungs))
        if i < prev:
            out.append(f"at {v} the ladder steps back toward the centre")
        prev = max(prev, i)
    return out[:6]


def check_the_collapse_is_three_even_groups():
    """left/centre/right must be three rungs, one rung, three rungs."""
    hist = compute_lean_histogram([10, 20, 35, 50, 65, 80, 90])
    if (hist["lean_left_count"], hist["lean_center_count"],
            hist["lean_right_count"]) != (3, 1, 3):
        return [f"one article on each rung collapses to "
                f"{hist['lean_left_count']}/{hist['lean_center_count']}/"
                f"{hist['lean_right_count']}, not 3/1/3"]
    return []


CHECKS = (
    ("the frontend declares its rungs", check_the_frontend_declares_its_rungs),
    ("every baseline lands on its own name", check_every_baseline_lands_on_its_own_name),
    ("pipeline and frontend agree on 0..100", check_the_two_agree_on_every_score),
    ("the ladder is symmetric", check_the_ladder_is_symmetric),
    ("the ladder never steps back", check_the_ladder_never_steps_back),
    ("left/centre/right collapses 3/1/3", check_the_collapse_is_three_even_groups),
)


def main() -> int:
    failures = []
    for name, fn in CHECKS:
        problems = fn()
        if problems:
            print(f"[FAIL] {name}")
            for p in problems:
                print(f"    - {p}")
            failures.extend(problems)
        else:
            print(f"[ ok ] {name}")
    if failures:
        print(f"\nFAILED: {len(failures)} ladder issue(s)")
        return 1
    print("\nOK: one ladder, two languages, seven rungs on their own baselines")
    return 0


if __name__ == "__main__":
    sys.exit(main())
