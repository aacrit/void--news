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

# ------------------------------------------ the voice bible describes the code
# Rev 1 of VOICE-BRAND.md described six Gemini-TTS hosts on a four-runs-a-day
# schedule for three months after the pipeline went to one Kokoro run a day,
# and used the em dash 59 times while banning it. A production prompt still
# obeyed the retired roster when the 2026-09-21 audit found it.
VOICE = ROOT / "docs/VOICE-BRAND.md"
voice = VOICE.read_text()
DASHES = {"—": "em dash", "–": "en dash"}
for ch, label in DASHES.items():
    n = voice.count(ch)
    check(f"VOICE-BRAND.md carries no {label}", n == 0, f"{n} found")
check("VOICE-BRAND.md names Kokoro", "Kokoro" in voice)
for retired in ("Gemini voice", "4 runs", "runs/day"):
    check(f"VOICE-BRAND.md does not say '{retired}'", retired not in voice)

# ---------------------------------------- the design system describes the code
# Rev 22 of DESIGN-SYSTEM.md was the reference every section built after it
# had, and it was four months stale: it named the product `void --x`,
# documented the edition tabs six revs after they were collapsed, and
# specified BiasLens and BiasInspector after both were deleted. The 2026-09-21
# brand audit traced the three-masthead, four-token-system drift back to it.
# These are the cheap, mechanical halves of that: a name, a retired control,
# a deleted component, and the dash ban the doc itself states.
DESIGN = ROOT / "docs/DESIGN-SYSTEM.md"
design = DESIGN.read_text()
for ch, label in DASHES.items():
    n = design.count(ch)
    check(f"DESIGN-SYSTEM.md carries no {label}", n == 0, f"{n} found")
for retired in ("void --news", "edition tab", "BiasLens", "BiasInspector"):
    check(
        f"DESIGN-SYSTEM.md does not say '{retired}'",
        retired not in design,
        "retired; see the 2026-09-21 brand audit",
    )
# A component the doc specifies must exist on disk.
COMPONENTS = ROOT / "frontend/app/components"
for name in sorted(set(re.findall(r"`(?:components/)?([A-Z][A-Za-z]+)\.tsx`", design))):
    check(
        f"DESIGN-SYSTEM.md names components/{name}.tsx",
        (COMPONENTS / f"{name}.tsx").exists(),
        "no such file",
    )

# ------------------------------------ retired infrastructure stated as current
# A doc that says "Supabase", "Gemini TTS" or "4x daily" in the present tense
# either carries the Historical banner under its title, or is listed here with
# the reason it may keep the words.
BANNER = (
    "> Historical. Written before the 2026-09-01 Supabase decommission and "
    "the Kokoro switch; the current state is CLAUDE.md."
)
STALE_TERMS = re.compile(r"Supabase|Gemini[ -]TTS|4x daily")
# A line that says the thing is gone is not a claim that it is current.
PAST_TENSE = re.compile(r"retired|decommission|historical|\bwas\b|\bwere\b|\bdead\b")
ALLOWED_WITHOUT_BANNER = {
    # Referenced from CLAUDE.md; each names the decommission as past.
    "CHANGELOG.md": "verbatim revision record",
    "OPEN-ITEMS.md": "describes Revolt's dead Supabase fallback as unfinished work",
    "HISTORY-AUDIO.md": "one line, on Revolt's dead fallback",
    "PODCAST-DISTRIBUTION.md": "explains why podcast-us.xml was deleted",
    # Dated reports, read as such by their titles.
    "EDITORIAL-AUDIT-2026-08-10.md": "dated report",
    "FEED-QUALITY-AUDIT-2026-06-28.md": "dated report",
    "INDEPENDENT-REVIEW-2026-06-11.md": "dated report",
    "PERF-REPORT-2026-03-22.md": "dated report",
    # Undated, not in the audit's banner list; candidates for the banner.
}
for path in sorted((ROOT / "docs").glob("*.md")):
    lines = path.read_text().split("\n")
    stale = [l for l in lines if STALE_TERMS.search(l) and not PAST_TENSE.search(l)]
    if not stale:
        continue
    if BANNER in lines[:3] or path.name in ALLOWED_WITHOUT_BANNER:
        continue
    check(
        f"docs/{path.name} states retired infrastructure as current",
        False,
        f"{len(stale)} line(s), first: {stale[0].strip()[:80]!r}; add the "
        "Historical banner under the title or list it in ALLOWED_WITHOUT_BANNER",
    )
for name in ALLOWED_WITHOUT_BANNER:
    check(f"allowlisted docs/{name} exists", (ROOT / "docs" / name).exists())

# ---------------------------------------------------------------------------
# The lean engine's text authority, as CLAUDE.md states it
# ---------------------------------------------------------------------------
# CLAUDE.md described the lean as a weighted blend, "~90/10 text-weighted on a
# full article". It is not a blend at all: it is a baseline plus a deviation
# bounded by delta_max, so a RATED outlet's article can move 10 points and no
# more, whatever it says and however long it is. The stated ratio was wrong in
# structure and inverted in magnitude, and it survived because nothing read the
# constants back. This does.
# READ FROM SOURCE, NOT IMPORTED. `political_lean` pulls in textblob and the
# spaCy chain, which the docs job does not install, so this raised
# ModuleNotFoundError in CI. It went unnoticed for as long as it did because the
# build step ahead of it was failing first and this gate never ran: a gate that
# cannot execute is not a gate, which is the same lesson as the pipeline
# committing a feed nothing had built.
#
# Only three integer constants are needed. Reading them out of the file keeps
# the assertion exact (a changed constant still fails) and costs no dependency.
def _delta_constants() -> dict:
    import ast
    src = (ROOT / "pipeline" / "analyzers" / "political_lean.py").read_text("utf-8")
    want = {"_TEXT_DELTA_MAX", "_CENTER_TEXT_DELTA_MAX", "_STATE_TEXT_DELTA_MAX",
            "_LENGTH_FULL_CONFIDENCE"}
    out = {}
    for node in ast.parse(src).body:
        if isinstance(node, ast.AnnAssign):
            target, value = node.target, node.value
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        else:
            continue
        if (isinstance(target, ast.Name) and target.id in want
                and isinstance(value, ast.Constant)):
            out[target.id] = value.value
    missing = want - set(out)
    if missing:
        # Never pass vacuously: an unreadable constant is a failed check, not a
        # skipped one.
        raise SystemExit(f"could not read {sorted(missing)} out of "
                         f"political_lean.py; this gate asserts CLAUDE.md against "
                         f"them and must not silently succeed")
    return out


_deltas = _delta_constants()

claude_md = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
for label, const in (("rated", _deltas["_TEXT_DELTA_MAX"]),
                     ("unrated", _deltas["_CENTER_TEXT_DELTA_MAX"]),
                     ("state-affiliated", _deltas["_STATE_TEXT_DELTA_MAX"])):
    # The table prints each bound as a reachable score or a plus-minus, so the
    # assertion is that the NUMBER appears in the lean section at all. A change
    # to a constant that nobody carried into the table fails here.
    check(f"CLAUDE.md's lean table carries the {label} delta_max "
          f"({const})",
          str(int(const)) in claude_md,
          f"_TEXT_DELTA_MAX-family constant {const} appears nowhere in CLAUDE.md")

# "90/10" may still APPEAR, because the correction quotes the wrong claim in
# order to refute it. What must not come back is the claim standing alone, so
# the assertion is that the refutation is present whenever the ratio is.
check("CLAUDE.md does not state a blend ratio for the lean engine as fact",
      "90/10" not in claude_md
      or "It is not a weighted blend" in claude_md,
      "the '~90/10 text-weighted' claim is back without its refutation")
check("the length-confidence divisor is stated",
      str(int(_deltas["_LENGTH_FULL_CONFIDENCE"])) in claude_md,
      f"{_deltas['_LENGTH_FULL_CONFIDENCE']} appears nowhere in CLAUDE.md")

if failures:
    print(f"FAIL  {len(failures)} docs-facts check(s)")
    for f in failures:
        print(f"  - {f}")
    sys.exit(1)

print(
    f"PASS  docs facts: {scripts} scripts, {rendered} rendered, "
    f"{events} events, {sources} sources"
)
