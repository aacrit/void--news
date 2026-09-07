#!/usr/bin/env python3
"""One planted defect per rule in docs/EDITORIAL-STANDARD.md.

A validator that has never rejected anything is not a validator. Each case
below plants exactly ONE defect and asserts the rule with that ID fires, and a
clean control asserts none of them fires on good prose. The clean control is
the half that catches an over-eager regex: E-10's first draft flagged
"Mudslides Kill Dozens" as a headline whose location the summary omitted, which
is why that rule is now model-checked (L-07) instead of a regex.

Run: python tests/test_editorial_standard.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.editorial import standard as std  # noqa: E402

CLEAN_SUMMARY = (
    "The central bank raised its benchmark rate by half a point on Tuesday, the "
    "third increase this quarter. Governor Adeyemi said the decision was "
    "unanimous and that the committee would meet again in November. Mortgage "
    "applications fell 12 percent in the week after the announcement, according "
    "to the national lenders association. Two of the five largest banks passed "
    "the increase to savers within a day."
)
CLEAN_TITLE = "Central Bank Raises Rate Half a Point in Third Increase This Quarter"

# (id, candidate, what was planted)
CASES = [
    ("S-01", {"title": CLEAN_TITLE, "summary": CLEAN_SUMMARY,
              "href": "/?story=1f4d8c2a-9b31-4e57-8a0d-6c2f5b7e91a4"},
     "archive-miss homepage query link"),
    ("S-02", {"title": CLEAN_TITLE, "summary": "The rate rose. Markets reacted."},
     "two-sentence summary (the satire-as-news shape)"),
    ("S-03", {"title": CLEAN_TITLE, "summary": CLEAN_SUMMARY.rstrip(".") + " and the"},
     "summary cut off mid-sentence"),
    ("S-04", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY + ' Adeyemi called it "a necessary correction.'},
     "unbalanced quotation mark"),
    ("S-05", {"title": "Bank Raises Rate", "summary": "TheThe committee met on Tuesday. " + CLEAN_SUMMARY},
     "doubled capitalized word"),
    ("S-06", {"title": CLEAN_TITLE, "summary": "The U. S. central bank moved first. " + CLEAN_SUMMARY},
     "broken abbreviation spacing"),
    ("E-03", {"title": CLEAN_TITLE, "summary": "The decision affects our borrowers directly. " + CLEAN_SUMMARY},
     "first-person pronoun outside quotes"),
    ("E-04", {"title": CLEAN_TITLE, "summary": CLEAN_SUMMARY + " although the committee was unanimous."},
     "orphan subordinate clause"),
    ("E-05", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY + " Adeyemi was charged with fraud in 2019."},
     "criminal allegation with no attribution"),
    ("E-07", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY + " The funds were traced to the Iranian terror regime."},
     "contested terminology in Void's voice"),
    ("E-08", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY + " The committee is described as the most hawkish in a decade."},
     "unattributed passive evaluation"),
    ("E-09", {"title": "Army Base Blasts Leave Two Dead",
              "summary": (
                  "Two people died and 14 are missing after explosions at an army base. "
                  "The exact cause of the explosions remains under investigation. "
                  "Details of the unit involved have not been immediately released. "
                  "The number of dead and missing is based on initial reports from the scene. "
                  "Investigations are ongoing to determine the sequence of events. "
                  "The full extent of the damage is still being evaluated.")},
     "a card that is mostly absence of information"),
    ("E-11", {"title": CLEAN_TITLE,
              "summary": CLEAN_SUMMARY + " Adeyemi told the committee to keep your projections conservative."},
     "second-person pronoun outside quotes"),
]


def main() -> int:
    ok = True

    # Clean control: a good card trips nothing.
    clean = std.validate_candidate({
        "title": CLEAN_TITLE, "summary": CLEAN_SUMMARY,
        "href": "/story/1f4d8c2a-9b31-4e57-8a0d-6c2f5b7e91a4/",
    })
    if clean:
        print(f"FAIL: clean control tripped {[str(f) for f in clean]}")
        ok = False
    else:
        print("PASS: clean control trips no rule")

    for rule_id, candidate, planted in CASES:
        findings = std.validate_candidate(candidate)
        ids = {f.id for f in findings}
        if rule_id not in ids:
            print(f"FAIL: {rule_id} did not fire on {planted}; got {sorted(ids) or 'nothing'}")
            ok = False
        else:
            extra = ids - {rule_id}
            note = f" (also {sorted(extra)})" if extra else ""
            print(f"PASS: {rule_id} fired on {planted}{note}")

    # Feed-level rules.
    dupes = std.f02_duplicate_headlines([
        "Senate Passes Border Funding Bill After Overnight Session",
        "Border Funding Bill Passes Senate in Overnight Session",
        "Wildfire Forces Evacuation of Three Coastal Towns",
    ])
    if not any(f.id == "F-02" for f in dupes):
        print("FAIL: F-02 did not fire on two headlines of the same story")
        ok = False
    else:
        print("PASS: F-02 fired on two headlines of the same story")

    if std.f02_duplicate_headlines([
        "Wildfire Forces Evacuation of Three Coastal Towns",
        "Central Bank Raises Rate Half a Point in Third Increase",
    ]):
        print("FAIL: F-02 fired on two unrelated headlines")
        ok = False
    else:
        print("PASS: F-02 quiet on unrelated headlines")

    counts = std.f04_count_match(header_count=12, rendered=12, expected=20)
    if not any("configured feed size" in f.message for f in counts):
        print("FAIL: F-04 did not fire on a self-consistent short render")
        ok = False
    else:
        print("PASS: F-04 fired on a self-consistent short render")

    # Every ID in the registry must have a case or be model-checked.
    covered = {c[0] for c in CASES} | {"F-02", "F-04"}
    missing = [v.id for v in std.VALIDATORS if v.id not in covered]
    if missing:
        print(f"FAIL: no planted defect for {missing}")
        ok = False
    else:
        print(f"PASS: every one of the {len(std.VALIDATORS)} validators has a planted defect")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
