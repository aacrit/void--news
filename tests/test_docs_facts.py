#!/usr/bin/env python3
"""Self-descriptive numbers in CLAUDE.md must match what is on disk.

Rule 1 says nothing Void publishes may contain a factual error. The document
that states rule 1 broke it twice: it claimed 62 of 78 History scripts were
written and 49 rendered, when both were 78, and its layout block repeated the
62. Nothing regenerates these numbers, so they rot silently.

This is the same defect class as the "50 stories" copy that survived the feed
moving to 20 in September: a count restated in prose, far from the thing it
counts. `frontend/test/copy-facts.test.mjs` gates that class in the frontend.
This gates it in the docs.
"""
import glob
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
CLAUDE = ROOT / "CLAUDE.md"

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if not cond:
        failures.append(f"{name}: {detail}" if detail else name)


text = CLAUDE.read_text()

# ---------------------------------------------------------------- real counts
scripts = len(glob.glob(str(ROOT / "data/history/scripts/*.txt")))
events = len(glob.glob(str(ROOT / "data/history/events/*.yaml")))

manifest = ROOT / "frontend/public/data/history-audio.json"
rendered = 0
if manifest.exists():
    rendered = len(json.loads(manifest.read_text()).get("episodes", []))

roster = ROOT / "data/sources.json"
sources = 0
if roster.exists():
    blob = json.loads(roster.read_text())
    entries = blob.get("sources", blob) if isinstance(blob, dict) else blob
    sources = len(entries)

# ------------------------------------------------- "N/78 scripts written" etc.
# The denominator is the event catalogue; the numerator is what exists.
NUMERATORS = {"scripts written": scripts, "rendered": rendered}

for numer, denom, label in re.findall(
    r"(\d+)\s*/\s*(\d+)\s+(scripts written|rendered)", text
):
    check(
        f"CLAUDE.md '{numer}/{denom} {label}'",
        int(numer) == NUMERATORS[label] and int(denom) == events,
        f"disk says {NUMERATORS[label]}/{events}",
    )

# --------------------------------------------------- the layout block's counts
LAYOUT = {
    r"history/events \((\d[\d,]*)\)": ("history/events", events),
    r"history/scripts \((\d[\d,]*)\)": ("history/scripts", scripts),
    r"sources\.json \((\d[\d,]*)\)": ("sources.json", sources),
}
for pattern, (label, actual) in LAYOUT.items():
    for claimed in re.findall(pattern, text):
        check(
            f"CLAUDE.md layout '{label} ({claimed})'",
            int(claimed.replace(",", "")) == actual,
            f"disk says {actual}",
        )

# ------------------------------------------------- the prose event count, once
for claimed in re.findall(r"Live, (\d+) events, static JSON", text):
    check(
        f"CLAUDE.md 'Live, {claimed} events'",
        int(claimed) == events,
        f"disk says {events}",
    )

# --------------------------------------------- the source count in the tagline
for claimed in re.findall(r"\*\*([\d,]+) sources\*\*|^([\d,]+) sources", text, re.M):
    got = claimed[0] or claimed[1]
    check(
        f"CLAUDE.md '{got} sources'",
        int(got.replace(",", "")) == sources,
        f"roster says {sources}",
    )

if failures:
    print(f"FAIL  {len(failures)} docs-facts check(s)")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)

print(
    f"PASS  docs facts: {scripts} scripts, {rendered} rendered, "
    f"{events} events, {sources} sources"
)
