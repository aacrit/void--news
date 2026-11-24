#!/usr/bin/env python3
"""The roster's size must come from the roster, in one place.

"1,016 sources" was hand-written in nine files under `frontend/app/` plus the
served `manifest.json`, four docs, two pipeline modules and two tests. The
three credibility tiers were literals too (43 / 373 / 600), rendered as exact
counts on `/about` and `/sources`. Adding 48 international outlets on
2026-09-22 would have left the site asserting 373 while the roster held 421,
and a breakdown that does not sum to its own total is an error a reader can
check without leaving the page.

`frontend/config/feed.json` read through `app/lib/feedConfig.ts` already solved
this for the feed size, and that file's own header says "never restate these
numbers as literals in a component". The prose restated them anyway, which is
how the site said "50 stories" for two weeks after the feed became 20. Rule 1
calls a number that goes stale a future error wherever a durable formulation
exists.

So `frontend/config/roster.json` is generated from `data/sources.json` by
`scripts/roster/emit_roster_config.py`, which runs inside
`scripts/roster/add_sources.py --apply`. This file is what makes that
generation trustworthy: a generated file nobody checks is just one more place
to be wrong.
"""
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROSTER = ROOT / "data" / "sources.json"
CONFIG = ROOT / "frontend" / "config" / "roster.json"
READER = ROOT / "frontend" / "app" / "lib" / "rosterConfig.ts"

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"PASS  {name}")
    else:
        failures.append(f"{name}: {detail}" if detail else name)
        print(f"FAIL  {name} {detail}")


rows = json.loads(ROSTER.read_text(encoding="utf-8"))
check("the generated config exists", CONFIG.exists(),
      f"{CONFIG.relative_to(ROOT)} missing; run "
      f"scripts/roster/emit_roster_config.py")
if not CONFIG.exists():
    sys.exit(1)
cfg = json.loads(CONFIG.read_text(encoding="utf-8"))

check("the config's source count is the roster's",
      cfg.get("sources") == len(rows),
      f"config {cfg.get('sources')}, roster {len(rows)}")
countries = {r["country"] for r in rows if r.get("country")}
check("the config's country count is the roster's",
      cfg.get("countries") == len(countries),
      f"config {cfg.get('countries')}, roster {len(countries)}")

TIERS = ("us_major", "international", "independent")
for tier in TIERS:
    live = sum(1 for r in rows if str(r.get("tier") or "").lower() == tier)
    check(f"the config's {tier} count is the roster's",
          cfg.get(tier) == live, f"config {cfg.get(tier)}, roster {live}")

# The reader's job is to be checkable arithmetic, not three numbers that
# happen to look right.
check("the tier breakdown sums to the total",
      sum(cfg.get(t, 0) for t in TIERS) == cfg.get("sources"),
      f"{[cfg.get(t) for t in TIERS]} sums to "
      f"{sum(cfg.get(t, 0) for t in TIERS)}, total is {cfg.get('sources')}")

# Every key the TypeScript reader exports must exist, or the frontend builds
# with `undefined` printed into page copy.
src = READER.read_text(encoding="utf-8")
for key in re.findall(r"cfg\.(\w+)", src):
    check(f"rosterConfig.ts reads a key the config has: {key}",
          key in cfg, f"{key!r} is not in {CONFIG.name}")
check("rosterConfig.ts exports the formatted count",
      "ROSTER_SOURCES_TEXT" in src)

# No component may go back to writing the number out. copy-facts.test.mjs
# catches the `N sources` phrasing; this catches the bare literal reappearing
# anywhere the count or a tier count is printed.
APP = ROOT / "frontend" / "app"
LITERALS = {str(cfg["sources"]), f"{cfg['sources']:,}",
            str(cfg["international"]), str(cfg["independent"]),
            str(cfg["us_major"])}
# The counts collide with ordinary magic numbers: 600 is a timeout in four
# Games components and an independent-tier count here. So a literal only
# offends NEAR a word that makes it a roster claim. Bounded at 40 characters
# either side, which reaches across a JSX tag boundary
# (`<div>1,064</div> <div>sources`) without reaching into unrelated code.
ROSTER_WORD = r"source|outlet|countr|us[ _-]?major|international|independent|tier"
offenders = []
for path in sorted(APP.rglob("*.ts")) + sorted(APP.rglob("*.tsx")):
    if path.name in ("rosterConfig.ts",):
        continue
    text = path.read_text(encoding="utf-8")
    # Comments may say what they like; a comment lies to the next engineer,
    # not to a reader, and belongs to a different check.
    text = re.sub(r"/\*[\s\S]*?\*/", "", text)
    text = re.sub(r"^\s*//.*$", "", text, flags=re.M)
    for lit in LITERALS:
        lit_re = re.escape(lit)
        near = (rf"\b{lit_re}\b[\s\S]{{0,40}}?(?:{ROSTER_WORD})"
                rf"|(?:{ROSTER_WORD})[\s\S]{{0,40}}?\b{lit_re}\b")
        if re.search(near, text, re.I):
            offenders.append(f"{path.relative_to(ROOT)}: {lit}")
check("no component restates the roster's counts as a literal",
      not offenders, f"{len(offenders)}: {offenders[:4]}")

# ---------------------------------------------------------------------------
# One row per outlet, one name per row
# ---------------------------------------------------------------------------
# Two rows shared a name until 2026-09-22. "The Conversation" was two real
# editions (US and global) that a reader could not tell apart, so on the Bench
# and in the source picker they collapsed into one outlet. "Ukrainska Pravda
# (English)" was one outlet twice, on the SAME url, and the duplicate was the
# worse row on both axes that matter: Google-fed, so unscoreable on its text at
# a median of 11 words, and `unrated`, so dropped from the lean aggregate. Its
# articles were being counted as a second independent source for the same
# reporting, which is exactly the double-count the Bench exists to avoid.
by_name, by_id, by_feed = {}, {}, {}
for r in rows:
    by_name.setdefault(r["name"], []).append(r["id"])
    by_id.setdefault(r["id"], []).append(r["name"])
    by_feed.setdefault(r["rss_url"], []).append(r["id"])
for label, index in (("name", by_name), ("id", by_id), ("feed url", by_feed)):
    shared = {k: v for k, v in index.items() if len(v) > 1}
    check(f"no two rows share a {label}", not shared,
          f"{len(shared)}: {list(shared.items())[:3]}")

# ---------------------------------------------------------------------------
# A hand-written alias may not contradict the file that created the name
# ---------------------------------------------------------------------------
# `add_sources.py` disambiguates a generic masthead when it writes a row: the
# target "ABC" becomes "ABC (Spain)", "BusinessDay (SA)" becomes
# "BusinessDay (South Africa)". `audit_majors.py` reads that mapping out of the
# metadata files, and its hand-written ALIAS table wins over it, which is
# correct for the equivalences a human checked.
#
# It is not correct when the hand entry is STALE. `"BusinessDay (SA)":
# "BusinessDay"` pointed at a row that does not exist, so after the real row
# was written it overrode the mapping and the audit reported an outlet it had
# just added as absent. A stale alias beats the file that knows, so it has to
# fail here rather than be noticed by eye.
sys.path.insert(0, str(ROOT / "scripts" / "roster"))
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "audit_majors", ROOT / "scripts" / "roster" / "audit_majors.py")
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)

roster_names = {r["name"] for r in rows}
conflicts, dangling = [], []
for target, roster_name in audit.metadata_aliases().items():
    hand = audit.ALIAS.get(target)
    if hand is None:
        continue
    if hand != roster_name and roster_name in roster_names:
        conflicts.append(f"{target!r}: ALIAS says {hand!r}, the metadata that "
                         f"wrote the row says {roster_name!r}")
for target, hand in audit.ALIAS.items():
    if hand not in roster_names:
        dangling.append(f"{target!r} -> {hand!r}")
check("no hand-written alias contradicts the metadata that wrote the row",
      not conflicts, "; ".join(conflicts))
check("every hand-written alias points at a row that exists",
      not dangling, f"{len(dangling)}: {dangling[:4]}")

if failures:
    print(f"\nFAIL  {len(failures)} roster-config check(s)")
    sys.exit(1)
print(f"\nPASS  one roster, one config: {cfg['sources']} sources, "
      f"{cfg['countries']} countries, "
      f"{'/'.join(str(cfg[t]) for t in TIERS)} by tier")
