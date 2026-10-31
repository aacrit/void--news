#!/usr/bin/env python3
"""The lean validation suite must actually test the TEXT engine.

WHY THIS GATE EXISTS. `pipeline/validation/runner.py` reports 100% on political
lean across 43 fixtures, with AllSides agreement 40/43. Measured 2026-09-22,
that number means almost nothing: replace the entire text engine with the
outlet's 7-value baseline label, score nothing at all from the article, and
**42 of the 43 fixtures still land inside their expected range (97.7%)**. The
one fixture the text engine earns is `wsj-opinion-tax-2026`.

The mechanism is the tolerances. Every expected lean range is at least 20
points wide on a 0-100 axis, median 25. A 7-row lookup table clears them.

That is why the lexicon could fire about 0.3 terms per article, read exactly
50.0 on 37% of full-length articles, and return a mean absolute text shift of
1.93 points, for months, with a green suite. The test could not see it.

WHAT THIS GATE ASSERTS. Not accuracy: the suite already claims that. It asserts
DISCRIMINATION, meaning the fixture set contains cases a baseline-only model
gets WRONG, so that a change to the text engine can register at all. It is a
ratchet: the floor may only be raised, never lowered, and raising it means
adding fixtures whose expected range is tight enough, or whose text is charged
enough, that the outlet label alone does not satisfy them.

Today the floor is 1, which is the honest record of the debt rather than a
target anyone should be proud of. A suite that genuinely tested this axis would
have a baseline-only model failing a large share of it.

Stdlib plus the fixtures and BASELINE_MAP. No spaCy, no DB, no scoring, so this
runs in seconds anywhere.

    python3 tests/test_lean_suite_discriminates.py
"""
import os
import statistics
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "pipeline"))

from analyzers.political_lean import BASELINE_MAP  # noqa: E402
from validation.fixtures import FIXTURES  # noqa: E402

# Fixtures a baseline-only model must FAIL. Ratchet: raise it when fixtures are
# added, never lower it. Measured 2026-09-22: exactly 1.
MIN_TEXT_DISCRIMINATING = 1

# No expected lean range may be wider than this without being counted as a
# tolerance that a lookup table walks through. Recorded, not yet enforced as a
# hard cap, because tightening 43 ranges is an editorial exercise.
WIDE_RANGE = 20

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"[ ok ] {name}")
    else:
        failures.append(name)
        print(f"[FAIL] {name}{': ' + detail if detail else ''}")


widths = []
discriminating = []
covered = 0
for f in FIXTURES:
    rng = ((f.get("expected") or {}).get("lean") or {}).get("range")
    if not rng:
        continue
    covered += 1
    widths.append(rng[1] - rng[0])
    baseline = BASELINE_MAP.get(
        str((f.get("source") or {}).get("political_lean_baseline", "")).lower())
    if baseline is None or not (rng[0] <= baseline <= rng[1]):
        discriminating.append((f["id"], baseline, rng))

null_pass = covered - len(discriminating)
print(f"       fixtures with a lean range: {covered}")
print(f"       baseline-only null model passes: {null_pass}/{covered} "
      f"({null_pass / covered:.1%})" if covered else "")
print(f"       expected-range width: min {min(widths)}, "
      f"median {statistics.median(widths):.0f}, max {max(widths)}")

check("the suite contains text-discriminating fixtures",
      len(discriminating) >= MIN_TEXT_DISCRIMINATING,
      f"only {len(discriminating)} fixture(s) fail a baseline-only model; "
      f"the floor is {MIN_TEXT_DISCRIMINATING}. A suite this permissive cannot "
      f"detect a regression in the lean TEXT engine.")

for fid, baseline, rng in discriminating:
    print(f"       discriminating: {fid} (baseline {baseline} vs {rng})")

wide = [w for w in widths if w > WIDE_RANGE]
print(f"       ranges wider than {WIDE_RANGE} points: {len(wide)} of {covered} "
      f"(recorded, not enforced)")

check("the ratchet is honest about where it stands",
      MIN_TEXT_DISCRIMINATING <= len(discriminating),
      "the floor has drifted above the measured value")

print()
if failures:
    print(f"FAIL: {len(failures)} check(s) failed")
    raise SystemExit(1)
print(f"OK: {len(discriminating)} of {covered} lean fixtures test the text engine "
      f"(floor {MIN_TEXT_DISCRIMINATING}); raise the floor when fixtures are added")
