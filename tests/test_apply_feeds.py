#!/usr/bin/env python3
"""A dry run must write nothing, and a real run must not clobber a record.

`apply_feeds.py --dry-run` printed "data/sources.json untouched" and meant it,
but it wrote `feed-changes-<date>.json` and `feed-review-<date>.json`
UNCONDITIONALLY, before reading the flag. Two guard tests run against an
unrelated input file therefore overwrote the committed 2026-09-22 record in
place: 129 applied feed changes became 35, and the review file's two named
groups (`native_language_feed`, `failed_domain_check`) became a flat list. That
record is the only thing that makes those 129 changes reversible without
reading git, and it is what this session had been citing for which 8 feeds were
rejected as hijacked. Recovered from git.

The shape of the mistake is worth naming: the flag was checked at the point of
the DANGEROUS action and not at the point of every side effect. A dry run is a
promise about all of them.

It also went unnoticed because the script was not exercisable: its paths came
from `__file__`, so running it at all meant writing into the real roster. It
takes `VOID_ROSTER_DATA` now, and this file runs it against a throwaway tree.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "roster" / "apply_feeds.py"

failures: list[str] = []


def check(name: str, cond: bool, detail: str = "") -> None:
    if cond:
        print(f"PASS  {name}")
    else:
        failures.append(f"{name}: {detail}" if detail else name)
        print(f"FAIL  {name} {detail}")


def row(rid, name, host):
    return {"id": rid, "name": name, "url": f"https://{host}",
            "rss_url": "https://news.google.com/rss/search?q=x",
            "country": "US", "tier": "independent", "type": "digital",
            "political_lean_baseline": "center", "credibility_notes": "fixture"}


# Both verified rows must be ON the roster, or the second is counted `absent`
# and never reaches the review branch. That is correct behaviour (a verified
# record for an outlet nobody carries is neither applied nor held), and it is
# what the first version of this fixture got wrong.
ROSTER = [row("probe-daily", "Probe Daily", "probe.example"),
          row("thin-weekly", "Thin Weekly", "thin.example")]

# One verified record that clears the bar, one that does not.
VERIFIED = [
    {"id": "probe-daily", "name": "Probe Daily", "url": "https://probe.example",
     "feed": "https://probe.example/feed", "expected_domain": "probe.example",
     "status": 200, "items": 25, "on_expected": 25, "articles": 25,
     "title": "Probe Daily", "named": True,
     "sample": "https://probe.example/2026/09/a-story-here"},
    {"id": "thin-weekly", "name": "Thin Weekly", "url": "https://thin.example",
     "feed": "https://thin.example/feed", "expected_domain": "thin.example",
     "status": 200, "items": 3, "on_expected": 3, "articles": 3,
     "title": "Thin Weekly", "named": True, "sample": None},
]


def fixture() -> pathlib.Path:
    tmp = pathlib.Path(tempfile.mkdtemp())
    (tmp / "roster").mkdir()
    (tmp / "sources.json").write_text(json.dumps(ROSTER, indent=2), encoding="utf-8")
    (tmp / "verified.jsonl").write_text(
        "\n".join(json.dumps(v) for v in VERIFIED) + "\n", encoding="utf-8")
    return tmp


def run(tmp: pathlib.Path, *args) -> subprocess.CompletedProcess:
    env = dict(os.environ, VOID_ROSTER_DATA=str(tmp))
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args, str(tmp / "verified.jsonl")],
        capture_output=True, text=True, env=env, cwd=str(ROOT))


def snapshot(tmp: pathlib.Path) -> dict:
    out = {}
    for path in sorted(tmp.rglob("*")):
        if path.is_file():
            out[str(path.relative_to(tmp))] = path.read_bytes()
    return out


# --- 1. a dry run writes nothing -------------------------------------------
tmp = fixture()
before = snapshot(tmp)
r = run(tmp, "--dry-run")
after = snapshot(tmp)
check("the dry run exits cleanly", r.returncode == 0, r.stderr[-300:])
check("the dry run changes no file and creates none", before == after,
      f"created/changed: {sorted(set(after) ^ set(before)) or 'contents differ'}")
check("the dry run says what a real run would write",
      "nothing written" in r.stdout and "feed-changes-" in r.stdout, r.stdout[-200:])
check("the dry run still reports the decision",
      "1" in r.stdout and "held" in r.stdout, r.stdout[-200:])
shutil.rmtree(tmp)

# --- 2. a real run applies, and records --------------------------------------
tmp = fixture()
r = run(tmp, "--apply")
check("the real run exits cleanly", r.returncode == 0, r.stderr[-300:])
rows = json.loads((tmp / "sources.json").read_text(encoding="utf-8"))
check("the row above the bar got its direct feed",
      rows[0]["rss_url"] == "https://probe.example/feed", rows[0]["rss_url"])
changes = list((tmp / "roster").glob("feed-changes-*.json"))
review = list((tmp / "roster").glob("feed-review-*.json"))
check("a change record was written", len(changes) == 1, str(changes))
check("a review record was written", len(review) == 1, str(review))
if changes:
    rec = json.loads(changes[0].read_text(encoding="utf-8"))
    check("the change record keeps the previous feed, so it is reversible",
          rec and "news.google.com" in rec[0]["was"], str(rec)[:200])
    check("the change record carries the roster id, not just the name",
          rec and rec[0].get("id") == "probe-daily", str(rec)[:200])
if review:
    held = json.loads(review[0].read_text(encoding="utf-8"))
    check("the held row records WHY it was held, not just its name",
          held and held[0].get("why_held"), str(held)[:200])

# --- 3. a second real run must not clobber the record ------------------------
first = {p.name: p.read_bytes() for p in (tmp / "roster").glob("*.json")}
r2 = run(tmp, "--apply")
again = {p.name: p.read_bytes() for p in (tmp / "roster").glob("*.json")}
check("a second run refuses rather than overwriting", r2.returncode == 2,
      f"exit {r2.returncode}")
check("the existing record is untouched", first == again)
check("the refusal names the file and its size",
      "already exists and holds" in r2.stdout, r2.stdout[-200:])

# --- 4. --label writes beside it, --force replaces it ------------------------
r3 = run(tmp, "--apply", "--label=second")
check("--label writes a separate record", r3.returncode == 0, r3.stdout[-200:])
check("the labelled record exists",
      any("second" in p.name for p in (tmp / "roster").glob("*.json")),
      str(sorted(p.name for p in (tmp / "roster").glob("*.json"))))
check("the original record survived the labelled run",
      first == {p.name: p.read_bytes() for p in (tmp / "roster").glob("*.json")
                if p.name in first})
r4 = run(tmp, "--apply", "--force")
check("--force is allowed to replace", r4.returncode == 0, r4.stdout[-200:])
shutil.rmtree(tmp)

# --- 5. discovery output is refused by shape ---------------------------------
tmp = fixture()
(tmp / "verified.jsonl").write_text(json.dumps(
    {"name": "Probe Daily", "url": "https://probe.example",
     "found": {"feed": "https://probe.example/feed", "items": 25,
               "own_domain_links": 25}, "why": "ok"}) + "\n", encoding="utf-8")
before = snapshot(tmp)
r = run(tmp, "--apply")
check("discover_feeds output is refused", r.returncode == 2, f"exit {r.returncode}")
check("the refusal names the tool to run first",
      "verify_feeds.py" in r.stdout, r.stdout[-200:])
check("nothing was written when the input was refused",
      before == snapshot(tmp))
shutil.rmtree(tmp)

if failures:
    print(f"\nFAIL  {len(failures)} apply-feeds check(s)")
    sys.exit(1)
print("\nPASS  a dry run writes nothing, and a record is never silently replaced")
