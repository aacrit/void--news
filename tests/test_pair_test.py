#!/usr/bin/env python3
"""The pair test's arithmetic is right, and its corpus holds no article text.

`scripts/roster/pair_test.py` decides whether the derive-our-own-baselines
programme proceeds (AUC >= 0.75) or stops (AUC < 0.65). A decision gate whose
arithmetic nobody checked is a coin with a threshold painted on it, so the pure
core is pinned here against hand-computed cases. No network, no spaCy.
"""
from __future__ import annotations

import glob
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts" / "roster"))

import pair_test as pt  # noqa: E402

failures: list[str] = []


def check(name, ok, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not ok else ""))
    if not ok:
        failures.append(name)


check("AUC counts right > left as 1, a tie as 1/2, a loss as 0",
      pt.auc([(60, 50), (50, 50), (40, 50), (55, 45)]) == (1 + 0.5 + 0 + 1) / 4)
check("an instrument that reads every article as 50 scores exactly 0.5",
      pt.auc([(50.0, 50.0)] * 30) == 0.5)
check("no pairs is no AUC, not zero", pt.auc([]) is None)
check("the gate: 0.75 proceeds", pt.verdict(0.75, 40) == "proceed")
check("the gate: just under 0.65 stops", pt.verdict(0.649, 40) == "stop")
check("the gate: between is inconclusive", pt.verdict(0.70, 40) == "inconclusive")
check("under twenty pairs no verdict is given", pt.verdict(0.95, 19) == "insufficient pairs")
check("the thresholds are the programme's (0.75 / 0.65)",
      (pt.PROCEED_AUC, pt.STOP_AUC) == (0.75, 0.65))
ci = pt.bootstrap_ci([(60, 50)] * 10 + [(40, 50)] * 10)
check("a bootstrap interval brackets its own AUC", ci and ci[0] <= 0.5 <= ci[1], str(ci))

# De-duplication across collections, and the score bar applied at load time.
with tempfile.TemporaryDirectory() as d:
    saved = pt.OUT_DIR
    pt.OUT_DIR = pathlib.Path(d)
    m = lambda s, a, b: {"score": s, "right": {"url": a, "title": "t"},  # noqa: E731
                         "left": {"url": b, "title": "t"}}
    for i, rows in enumerate([[m(20, "r1", "l1"), m(15, "r2", "l2")],
                              [m(20, "r1", "l1"), m(25, "r3", "l3")]]):
        (pt.OUT_DIR / f"{i}.json").write_text(json.dumps(
            {"pairs": {"uk-tabloids": {"matches": rows}}}))
    got = pt.load_matches(18)["uk-tabloids"]
    pt.OUT_DIR = saved
check("a pair seen in two collections is counted once, and the bar drops the weak one",
      sorted(x["right"]["url"] for x in got) == ["r1", "r3"], str(got))

# The committed corpus: URLs, headlines and scores only.
PROSE_KEYS = {"summary", "description", "full_text", "body", "text"}
bad = []
for path in glob.glob(str(ROOT / "data" / "roster" / "pair-test" / "*.json")):
    doc = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    for rec in doc.get("pairs", {}).values():
        for mm in rec.get("matches", []):
            for side in ("right", "left"):
                if set(mm[side]) & PROSE_KEYS or len(mm[side].get("title", "").split()) > 40:
                    bad.append(path)
check("no committed pair-test file carries article text", not bad, str(bad[:3]))
check("every pair is (higher-rated, lower-rated) on the roster", all(
    {"far-left": 10, "left": 20, "center-left": 35, "center": 50, "center-right": 65,
     "right": 80, "far-right": 90}[pt.roster()[r]["political_lean_baseline"]]
    > {"far-left": 10, "left": 20, "center-left": 35, "center": 50, "center-right": 65,
       "right": 80, "far-right": 90}[pt.roster()[l]["political_lean_baseline"]]
    for _, r, l in pt.PAIRS))

if failures:
    print(f"\nFAIL  {len(failures)} pair-test check(s)")
    sys.exit(1)
print("\nPASS  the pair test's arithmetic is right and its corpus holds no text")
