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

# ---------------------------------------------------------------------------
# looks_article, which has now been wrong three times
# ---------------------------------------------------------------------------
# Every one of these was found by a healthy feed it rejected, not by review:
#
#   the query string was dropped   Novinite serves every article as
#                                  `view_news.php?id=240715`, so `view_news.php`
#                                  remained and looked like a section front.
#                                  0 of 24 real articles accepted, and
#                                  Bulgaria's news agency stayed on a Google
#                                  feed with an 11-word median.
#   a short single segment         `/dangers-of-ai/`, `/protectdemocracy` and
#                                  `/irooj-mike-farewelled/` are articles and
#                                  failed all four of the old rule's tests,
#                                  holding three healthy feeds at 9 of 10.
#
# A heuristic wrong three times needs its cases written down, in BOTH
# directions: the point is not that more URLs pass, it is that section fronts
# still do not.
sys.path.insert(0, str(ROOT / "scripts" / "roster"))
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "verify_feeds", ROOT / "scripts" / "roster" / "verify_feeds.py")
vf = importlib.util.module_from_spec(_spec)
sys.modules["verify_feeds"] = vf
_spec.loader.exec_module(vf)

ARTICLE = [
    ("https://spectator.org/dangers-of-ai/", "short hyphenated slug"),
    ("https://sojo.net/protectdemocracy", "single word slug"),
    ("https://marshallislandsjournal.com/irooj-mike-farewelled/", "21-char slug"),
    ("https://www.novinite.com/view_news.php?id=240715", "id in the query"),
    ("https://www.stltoday.com/article_088787ec-8e42.html", "id in the filename"),
    ("https://example.com/news/2026/09/a-real-story", "dated path"),
    ("https://example.com/a-headline-long-enough-to-be-a-slug", "long slug"),
]
SECTION = [
    ("https://example.com/", "the homepage"),
    ("https://example.com/index.html", "an index page"),
    ("https://example.com/news", "a section front"),
    ("https://example.com/politics/", "a section front with a slash"),
    ("https://example.com/opinion", "a section front"),
    ("https://example.com/tag", "a tag index"),
    ("https://example.com/author", "an author index"),
]
for url, why in ARTICLE:
    check(f"looks_article accepts {why}", vf.looks_article(url) is True, url)
for url, why in SECTION:
    check(f"looks_article rejects {why}", vf.looks_article(url) is False, url)

# ---------------------------------------------------------------------------
# named(): the outlet's own domain counts, and a rival's does not
# ---------------------------------------------------------------------------
# A short name cannot clear the 4-character token floor at all. MIA (North
# Macedonia) titles its feed "Mia" and publishes on mia.mk, and was held
# because its only long words are "north" and "macedonia", which appear in
# neither. A name word of any length is accepted when it equals the DOMAIN'S
# OWN FIRST LABEL, which says the outlet's name is in its own registered
# domain. The negative cases are what make that safe: Pravda.sk's discovered
# feed titled "Slovak Spectator" on sme.sk must still be refused, because
# catching a discovery that landed on a DIFFERENT outlet is what this check is
# for.
NAMED = [
    ("MIA (North Macedonia)", "Mia", "mia.mk", True, "short name, own domain"),
    ("Lincoln Journal Star", "journalstar.com - RSS Results",
     "journalstar.com", True, "long token in the domain"),
    ("Sports Illustrated", "SI Feed", "si.com", False,
     "two-letter brand is NOT auto-accepted; it is declared instead"),
    ("Pravda.sk (English)", "Slovak Spectator", "sme.sk", False,
     "a different outlet must never match"),
    ("The Daily Star", "Some Feed", "randomsite.com", False,
     "nothing in common"),
]
for outlet, title, domain, want, why in NAMED:
    got = vf.named(outlet, title, domain)
    check(f"named() {'accepts' if want else 'refuses'}: {why}",
          got is want, f"{outlet!r} / {title!r} / {domain} -> {got}")

# ---------------------------------------------------------------------------
# The declared title tokens must name outlets that exist
# ---------------------------------------------------------------------------
# A feed titling itself with the outlet's own domain is accepted only when the
# equivalence is declared per outlet, because the title check is what caught a
# discovery pointing at a DIFFERENT outlet (Pravda.sk's feed resolved to
# sme.sk, titled "Slovak Spectator"). An entry keyed on an id nobody carries is
# a silent no-op, and six of the twelve ids in the first draft of that file
# were wrong.
TOKENS = ROOT / "data" / "roster" / "feed-title-tokens.json"
if TOKENS.exists():
    doc = json.loads(TOKENS.read_text(encoding="utf-8"))
    roster_ids = {r["id"] for r in json.loads(
        (ROOT / "data" / "sources.json").read_text(encoding="utf-8"))}
    declared = doc.get("tokens") or {}
    holds = doc.get("_not_listed_and_why") or {}
    unknown = sorted(set(declared) - roster_ids)
    check("every declared title token names a roster row", not unknown,
          f"{len(unknown)}: {unknown[:4]}")
    unknown_holds = sorted(set(holds) - roster_ids)
    check("every documented hold names a roster row", not unknown_holds,
          f"{len(unknown_holds)}: {unknown_holds[:4]}")
    check("every declared token is a non-empty list",
          all(isinstance(v, list) and v and all(isinstance(t, str) and t.strip()
                                                for t in v)
              for v in declared.values()),
          str({k: v for k, v in declared.items() if not v})[:120])
    check("the file says why each undeclared outlet was NOT declared",
          all(isinstance(v, str) and len(v) > 40 for v in holds.values()),
          "a hold with no reason teaches nobody anything")

if failures:
    print(f"\nFAIL  {len(failures)} apply-feeds check(s)")
    sys.exit(1)
print("\nPASS  a dry run writes nothing, and a record is never silently replaced")
