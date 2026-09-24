#!/usr/bin/env python3
"""The political lean prior may not be fed by the engine's own output.

`analyze_political_lean` used to blend the Axis 6 EMA into the outlet prior at
0.7/0.3. `topic_outlet_tracker.update_source_topic_lean` builds that EMA by
averaging `political_lean` over a batch, which is this engine's PUBLISHED
OUTPUT, defaulting a missing key to 50. Score fed the table, table fed the
score. No outside evidence enters anywhere in the cycle, so the loop cannot
correct an error, only compound one, and its fixed point is the mean of what it
has already emitted.

Measured 2026-09-22 before cutting, because a plausible mechanism is not a
cause: it was NOT the current centre pull (mean |published - label| for rated
non-centre outlets is 5.45 across all rows and 0.74 once default-tuple rows are
excluded; the compression is 6,256 unmeasured rows). It was cut because the
outlet-baseline programme wires a LEARNED per-outlet offset into the same
prior, and a self-fed term sitting beside a learned one corrupts the thing
being learned.

This file is the check that keeps it cut. Two properties, and the second is the
one that matters: the parameter must be inert, and no scoring path may read the
table that the engine writes.
"""
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))

from analyzers.political_lean import analyze_political_lean  # noqa: E402

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"PASS  {name}")
    else:
        failures.append(f"{name}: {detail}" if detail else name)
        print(f"FAIL  {name} {detail}")


# --- 1. the parameter is inert, on text of every length ---------------------
# Length matters: confidence is min(1, words/150), so a thin item sits almost
# on the prior and a long one moves off it. A blend that survived only on short
# items would be invisible in a single-length test.
TEXTS = {
    "empty": "",
    "wire snippet (11 words)": "Officials confirmed the vote was held on Tuesday in the capital.",
    "short (60 words)": "The minister said the policy would proceed. " * 8,
    "full (400 words)": ("Lawmakers debated the spending bill for six hours before "
                         "the committee voted to advance it to the floor. ") * 20,
}
SOURCES = [
    {"name": "Rated left", "political_lean_baseline": "left", "tier": "international"},
    {"name": "Rated center", "political_lean_baseline": "center", "tier": "us_major"},
    {"name": "Rated right", "political_lean_baseline": "right", "tier": "us_major"},
    {"name": "Unrated", "political_lean_baseline": "unrated", "tier": "independent"},
]
# The extremes of what the table could hold, plus the value it defaults to.
PROBES = [{"avg_lean": v} for v in (0.0, 10.0, 50.0, 90.0, 100.0)]

for label, text in TEXTS.items():
    for src in SOURCES:
        article = {"full_text": text, "title": "Committee advances spending bill",
                   "source_id": "s1"}
        base = analyze_political_lean(article, src)["score"]
        moved = []
        for probe in PROBES:
            got = analyze_political_lean(article, src, topic_lean_data=probe)["score"]
            if got != base:
                moved.append(f"avg_lean={probe['avg_lean']} -> {got}")
        check(f"{src['name']} on {label}: the topic prior moves nothing",
              not moved, f"baseline {base}, {moved}")

# The rationale must not report a prior that the blend has already moved,
# which is how the loop stayed invisible: `source_baseline` was overwritten.
r = analyze_political_lean({"full_text": TEXTS["full (400 words)"], "title": "T"},
                           SOURCES[0], topic_lean_data={"avg_lean": 95.0})
check("the reported source_baseline is the outlet's own",
      abs(float(r["rationale"]["source_baseline"]) - 20.0) < 0.01,
      str(r["rationale"]["source_baseline"]))

# --- 2. no scoring path reads the table the engine writes -------------------
# The inertness above is a property of today's code. This is the property that
# stops the loop being reintroduced: the table is written by Axis 6 for its own
# reporting, and `analyze_political_lean` must not name it.
SELF_FED = ("source_topic_lean", "avg_lean")
src_text = (ROOT / "pipeline" / "analyzers" / "political_lean.py").read_text(
    encoding="utf-8")
tree = ast.parse(src_text)

live: list[str] = []
for node in ast.walk(tree):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        if node.value in SELF_FED:
            live.append(f"line {node.lineno}: {node.value!r}")
check("the scorer names no field of its own output table",
      not live,
      f"{live} (a comment is fine, a string literal the code reads is not)")

# And the writer must still be a writer only: if the tracker ever imports the
# scorer, the cycle closes again from the other side.
tracker = (ROOT / "pipeline" / "analyzers" / "topic_outlet_tracker.py").read_text(
    encoding="utf-8")
check("the tracker does not import the scorer",
      "political_lean import" not in tracker and "import political_lean" not in tracker)

if failures:
    print(f"\nFAIL  {len(failures)} self-fed-prior check(s)")
    sys.exit(1)
print("\nPASS  the lean prior is not fed by the lean it publishes")
