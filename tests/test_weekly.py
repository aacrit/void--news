#!/usr/bin/env python3
"""Gates for void --weekly. Pure: no DB, no LLM key, no network.

The weekly had ZERO tests before this file, and not through neglect:
`weekly_digest_generator` imports `utils.supabase_client`, which raises
`EnvironmentError` without `VOID_SQLITE_PATH`, so the module could not be
imported in CI at all. `pipeline/briefing/weekly_parse.py` exists to break that
wall; this suite exercises it directly.

Three tiers, in the order the real defects were found:

  1. Pure functions      — the headline guard and the week/issue math.
  2. Static cross-file   — two source files that must agree, compared as text.
  3. Committed artifact  — what the published snapshot actually contains.

Tier 2 is where the shipped bugs live. `cover_timelines` and `cover_numbers`
ship to browsers as unparsed JSON strings today purely because the exporter's
list and the frontend reader's list drifted apart, and nothing compared them.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from briefing.weekly_parse import (  # noqa: E402
    MAX_HEADLINE_CHARS,
    clean_headline,
    looks_like_headline,
    parse_essay,
    parse_recap,
    weekly_window,
)
from briefing.weekly_parse import build_weekly_row  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
WEEKLY_JSON = ROOT / "frontend" / "public" / "data" / "weekly.json"
EXPORT_PY = ROOT / "pipeline" / "export_static.py"
READER_TS = ROOT / "frontend" / "app" / "lib" / "supabase.ts"

_failures = []


def check(name, ok, detail=""):
    print(f"  [{'ok' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        _failures.append(name)


# ---------------------------------------------------------------------------
# W-T01  The headline guard
# ---------------------------------------------------------------------------
def test_headline_guard():
    print("\nW-T01  headline guard")

    r = parse_essay("Arctic Sovereignty, Contested Control\n\nOn Friday the deal landed.")
    check("normal essay splits", r["headline"] == "Arctic Sovereignty, Contested Control"
          and r["text"] == "On Friday the deal landed.")

    # The live defect, verbatim. Issue #26 set this 698-character paragraph as a
    # display-size red <h2> and as coverline #1, and the essay lost its lede.
    fx = json.loads((FIXTURES / "weekly_issue26_headline_defect.json").read_text())
    bad = fx["defect_headline_line"]
    r = parse_essay(bad + "\n\n" + fx["following_body"])
    check("issue-26 paragraph is not a headline", r["headline"] == "",
          f"{len(bad)} chars, {len(bad.split())} words")
    check("issue-26 lede survives in the body", r["text"].startswith(bad[:60]),
          "the paragraph must stay in the essay, not be eaten")

    long_ok = "Denmark and Greenland Affirm Sovereignty After US Arctic Security Deal"
    r = parse_essay(long_ok + "\n\nBody follows here.")
    check("a real 69-char headline survives", r["headline"] == long_ok)

    r = parse_essay("Rates rose. The Bank held.\n\nBody follows here.")
    check("interior sentence boundary rejected", r["headline"] == "")

    check("trailing period allowed", looks_like_headline("The Bank held."))
    check("empty line rejected", not looks_like_headline("   "))
    check("over char cap rejected", not looks_like_headline("x" * (MAX_HEADLINE_CHARS + 1)))

    check("HEADLINE: label stripped", clean_headline("HEADLINE: Foo") == "Foo")
    check("'Headline inflation' survives", clean_headline("Headline inflation") == "Headline inflation")

    r = parse_essay("Title\n\nBody.\n\nNUMBERS\n15 million | crossed the border\n$4.2bn | annual cost",
                    want_numbers=True)
    check("NUMBERS block parses", r["numbers"] == [
        {"stat": "15 million", "context": "crossed the border"},
        {"stat": "$4.2bn", "context": "annual cost"},
    ], str(r["numbers"]))
    check("NUMBERS stripped from body", "NUMBERS" not in r["text"])

    r = parse_essay("Title\n\nBody.\n\nNUMBERS\n15 million | crossed", want_numbers=False)
    check("NUMBERS left alone when not wanted", "NUMBERS" in r["text"])

    r = parse_recap("###\n" + bad + "\nAnd the rest of the brief.")
    check("parse_recap rejects a paragraph headline", r["stories"][0]["headline"] == "")

    r = parse_recap("###\nBank of Japan Raises Rate\nThe BOJ moved to 1.25 percent.")
    check("parse_recap keeps a real headline",
          r["stories"][0]["headline"] == "Bank of Japan Raises Rate")


# ---------------------------------------------------------------------------
# W-T02  Week window and issue number
# ---------------------------------------------------------------------------
def test_weekly_window():
    print("\nW-T02  week window")
    from datetime import datetime, timezone

    # The real cron moment: Monday 2026-09-21 12:00 UTC.
    now = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)

    start, end, issue = weekly_window(now, 0)
    check("offset 0 starts on a Monday", start.weekday() == 0, start.strftime("%Y-%m-%d %a"))
    check("offset 0 is the COMPLETED week", start.strftime("%Y-%m-%d") == "2026-09-14",
          f"got {start:%Y-%m-%d} (the week that just ended, not the one starting today)")
    check("span is exactly 6 days", (end.date() - start.date()).days == 6)
    check("offset 0 yields issue 26", issue == 26, f"got {issue}")

    s1, _, i1 = weekly_window(now, 1)
    check("offset 1 is 7 days earlier", (start.date() - s1.date()).days == 7)
    check("offset 1 decrements the issue", i1 == issue - 1, f"got {i1}")

    sm1, _, im1 = weekly_window(now, -1)
    check("offset -1 is the current week", (sm1.date() - start.date()).days == 7)
    check("offset -1 increments the issue", im1 == issue + 1, f"got {im1}")

    # Saturday 2026-09-19, the moment Issue #26 was actually generated. Offset
    # -1 is what a mid-week refresh must use to reach the in-progress week.
    sat = datetime(2026, 9, 19, 23, 26, tzinfo=timezone.utc)
    s, _, i = weekly_window(sat, -1)
    check("Saturday + offset -1 reaches issue 26",
          s.strftime("%Y-%m-%d") == "2026-09-14" and i == 26, f"{s:%Y-%m-%d} #{i}")

    # Every Monday in a year must resolve to a Monday start. A sign or rounding
    # slip shows up here and nowhere else until production.
    from datetime import timedelta
    bad = [d for d in (datetime(2026, 1, 5, 12, tzinfo=timezone.utc) + timedelta(weeks=w)
                       for w in range(52))
           if weekly_window(d, 0)[0].weekday() != 0]
    check("52 Mondays all resolve to a Monday start", not bad, f"{len(bad)} bad")


# ---------------------------------------------------------------------------
# W-T03  Export and reader must parse the same JSON fields
# ---------------------------------------------------------------------------
def _weekly_pjson_fields():
    src = EXPORT_PY.read_text()
    block = src[src.index('if want("weekly")'):]
    block = block[:block.index("wj(PUBLIC_DIR")]
    m = re.search(r"for k in \(([^)]*)\):\s*\n\s*if k in weekly", block, re.S)
    return set(re.findall(r'"([^"]+)"', m.group(1))) if m else set()


def _reader_json_fields():
    src = READER_TS.read_text()
    block = src[src.index("export async function fetchWeeklyDigest"):]
    m = re.search(r"const jsonFields = \[([^\]]*)\]", block, re.S)
    return set(re.findall(r"'([^']+)'", m.group(1))) if m else set()


VERIFY_PY = ROOT / "scripts" / "verify_sections.py"


def test_constant_parity():
    """verify_sections runs against the live site and cannot import the repo,
    so it carries its own copy of MAX_HEADLINE_CHARS. Copies drift."""
    m = re.search(r"^MAX_HEADLINE_CHARS = (\d+)", VERIFY_PY.read_text(), re.M)
    check("verify_sections declares MAX_HEADLINE_CHARS", bool(m))
    if m:
        check("the two MAX_HEADLINE_CHARS agree", int(m.group(1)) == MAX_HEADLINE_CHARS,
              f"verify_sections {m.group(1)} vs weekly_parse {MAX_HEADLINE_CHARS}")


def test_export_reader_parity():
    print("\nW-T03  export/reader JSON-field parity")
    test_constant_parity()
    exp, rdr = _weekly_pjson_fields(), _reader_json_fields()
    check("exporter field list found", bool(exp), f"{len(exp)} fields")
    check("reader field list found", bool(rdr), f"{len(rdr)} fields")
    check("the two lists are identical", exp == rdr,
          f"exporter-only={sorted(exp - rdr)} reader-only={sorted(rdr - exp)}")


# ---------------------------------------------------------------------------
# W-T04  The committed snapshot
# ---------------------------------------------------------------------------
LICENSED_IMAGE_HOSTS = (
    "upload.wikimedia.org", "thumb.wikimedia.org",
    "images.unsplash.com", "images.pexels.com",
)


def test_committed_snapshot():
    print("\nW-T04  committed weekly.json")
    if not WEEKLY_JSON.exists():
        check("weekly.json exists", False, str(WEEKLY_JSON))
        return
    d = json.loads(WEEKLY_JSON.read_text())

    from datetime import date
    start = date.fromisoformat(str(d["week_start"])[:10])
    check("week_start is a Monday", start.weekday() == 0, str(start))

    _, _, expected = weekly_window(
        __import__("datetime").datetime.combine(
            start, __import__("datetime").time(12),
            tzinfo=__import__("datetime").timezone.utc) +
        __import__("datetime").timedelta(days=7))
    check("issue_number matches the epoch formula", d["issue_number"] == expected,
          f"snapshot #{d['issue_number']} vs computed #{expected}")

    # The fact-1 lock at the data layer: no cover headline may be a paragraph.
    over = [(i, len(c.get("headline") or ""))
            for i, c in enumerate(d.get("cover_text") or [])
            if len(c.get("headline") or "") > MAX_HEADLINE_CHARS]
    check("no cover headline is a paragraph", not over,
          "; ".join(f"cover_text[{i}] is {n} chars" for i, n in over))

    # Every field the exporter parses must be structured, never a raw string.
    for k in sorted(_weekly_pjson_fields()):
        if k in d and d[k] is not None:
            check(f"{k} is parsed, not a string", not isinstance(d[k], str),
                  "" if not isinstance(d[k], str) else "shipped as a raw JSON string")

    # The cover image is Void's to publish, or there is none. A publisher's
    # og:image is usually a wire photograph and grants nothing to whoever
    # scrapes it; issue #26 shipped an AFP TOPSHOT off a Nigerian CDN.
    cover = str(d.get("cover_image_url") or "")
    if cover:
        check("cover image is freely licensed",
              any(h in cover for h in LICENSED_IMAGE_HOSTS)
              and d.get("cover_image_source") != "og_image",
              f"{d.get('cover_image_source')}: {cover[:70]}")
    else:
        check("cover image absent (acceptable)", True, "better than an unlicensed one")



# ---------------------------------------------------------------------------
# W-T05  The persistence contract
# ---------------------------------------------------------------------------
def test_build_weekly_row():
    print("\nW-T05  build_weekly_row")
    fx = json.loads((FIXTURES / "weekly_inputs.json").read_text())
    row = build_weekly_row(**{k: v for k, v in fx.items() if not k.startswith("_")})

    # The headline defect: these two departments were generated every week and
    # the row had only a comment where the write should have been.
    depts = json.loads(row["departments"])
    check("departments persisted", len(depts) == 2, f"{len(depts)} department(s)")
    check("departments are ordered tech then sports",
          [d["slug"] for d in depts] == ["tech", "sports"], str([d["slug"] for d in depts]))
    check("every department is complete",
          all(d.get("slug") and d.get("label") and d.get("headline") and d.get("text")
              for d in depts))

    ops = json.loads(row["opinions"])
    check("all five opinions persisted", len(ops) == 5, f"{len(ops)}")
    check("every opinion carries a lean", all(o.get("lean") for o in ops))

    paired = [o for o in ops if o.get("paired")]
    check("exactly two opinions are paired", len(paired) == 2, f"{len(paired)}")
    check("the paired two share one pair_id",
          len({o.get("pair_id") for o in paired}) == 1,
          str([o.get("pair_id") for o in paired]))
    check("the paired two argue opposite sides",
          {o["lean"] for o in paired} == {"left", "right"},
          str(sorted(o["lean"] for o in paired)))
    check("the paired two argue the SAME story",
          len({o.get("cluster_id") for o in paired}) == 1)

    # The legacy buckets must be a PARTITION of the flat array. This is the
    # assertion that catches a refactor silently dropping an essay — which is
    # exactly what the page did: it read [0] of each of three buckets, and the
    # two extra center essays were never rendered by anything.
    buckets = []
    for k in ("opinion_left", "opinion_center", "opinion_right"):
        buckets.extend(json.loads(row[k]))
    check("buckets and flat array have the same count",
          len(buckets) == len(ops), f"{len(buckets)} vs {len(ops)}")
    key = lambda o: (o.get("position"), o.get("headline"))
    check("buckets are a partition of the flat array",
          sorted(map(key, buckets)) == sorted(map(key, ops)))

    # Everything the exporter parses must be valid JSON coming out of here.
    for k in sorted(_weekly_pjson_fields()):
        if k in row and row[k] is not None:
            try:
                json.loads(row[k])
                ok, why = True, ""
            except (TypeError, ValueError) as e:
                ok, why = False, str(e)
            check(f"row[{k}] is valid JSON", ok, why)

    # No cover headline may be a paragraph, at the moment of writing.
    covers = json.loads(row["cover_text"])
    check("no cover headline written as a paragraph",
          all(len(c.get("headline") or "") <= MAX_HEADLINE_CHARS for c in covers))

    check("audio_script is still written to the DB", row["audio_script"] is not None,
          "the exporter drops it from the browser payload, not from storage")



# ---------------------------------------------------------------------------
# W-T06  CSS class parity
# ---------------------------------------------------------------------------
WEEKLY_CSS = ROOT / "frontend" / "app" / "styles" / "weekly.css"
WEEKLY_TSX = ROOT / "frontend" / "app" / "weekly"

# Nothing is exempt. The extractor reads template literals inside className, so
# a state class applied conditionally is still seen at its use site; if this
# ever needs an entry, the class is probably dead.
# The only two classes the extractor genuinely cannot see: they are built as
# `wk-opinion--${side}`, so the name never appears whole in the source. Every
# other state class is written out inside a template literal and IS seen, which
# is why this list is two entries and not thirty.
_COMPOSED = {"wk-opinion--left", "wk-opinion--right"}
def _css_classes():
    return set(re.findall(r"\.(wk-[A-Za-z0-9_-]+)", WEEKLY_CSS.read_text()))


def _class_expressions(src):
    """Yield the text of every className={...} / className="..." expression.

    Only className is read. A bare "wk-..." string literal elsewhere in the
    file is an element id or an aria-labelledby target — a jump anchor, which
    needs no CSS rule — and counting those as classes made the gate demand
    rules for things like wk-bias-heading.
    """
    for m in re.finditer(r"className=", src):
        i = m.end()
        if src[i] == '"':
            j = src.index('"', i + 1)
            yield src[i + 1:j]
        elif src[i] == "{":
            depth, j = 0, i
            while j < len(src):
                if src[j] == "{":
                    depth += 1
                elif src[j] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            yield src[i + 1:j]


def _markup_classes():
    used = set()
    for f in sorted(WEEKLY_TSX.rglob("*.tsx")):
        for expr in _class_expressions(f.read_text()):
            used.update(re.findall(r"wk-[A-Za-z0-9_-]*[A-Za-z0-9]", expr))
    return used


def test_class_parity():
    """Catch both halves of the dead-code problem in one comparison.

    Before this gate, 44 of 142 `.wk-` classes had CSS and no markup (~400
    lines: a masthead, a timeline UI and an inline audio player, all deleted
    with their components left behind) while all 8 `.wk-contested__*` classes
    had markup and NO CSS — a section that would have rendered unstyled had its
    data ever existed. Nothing compared the two lists, so neither was noticed.
    """
    print("\nW-T06  CSS class parity")
    css, markup = _css_classes(), _markup_classes()
    undefined = sorted(markup - css)
    unused = sorted(css - markup - _COMPOSED)
    check("every class in the markup has a rule", not undefined,
          ", ".join(undefined))
    check("every rule in weekly.css has markup", not unused,
          ", ".join(unused))


# ---------------------------------------------------------------------------
# W-T08  Document structure: one h1, no skipped level, no dead contents anchor
# ---------------------------------------------------------------------------
def _strip_comments(src):
    """Drop /* ... */ blocks. These files DISCUSS their heading levels, and a
    comment reading "the issue's own <h1>" is not a rendered heading."""
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)


def _headings():
    """Every heading the weekly tree renders, as (file, level)."""
    out = []
    for f in sorted(WEEKLY_TSX.rglob("*.tsx")):
        for m in re.finditer(r"<h([1-6])[\s>]", _strip_comments(f.read_text())):
            out.append((f.name, int(m.group(1))))
    return out


def test_document_structure():
    """The audit found four structural defects here at once, none of them visible.

    `CoverOpening` hard-coded <h1> and is rendered once per cover feature, so
    the document had two; the cover headline, the largest text on the page, was
    a <p>; the polarized label was an <h4> directly under an <h2> plate; and
    Back Issues took a folio without ever being pushed into the contents, so
    the contents claimed the issue ended a section early.

    Source-level deliberately: it runs with no build, no browser and no
    network, which is what lets it sit in front of a merge. The built page is
    checked separately by the headless suite.
    """
    print("\nW-T08  document structure")
    hs = _headings()
    h1s = [f for f, lv in hs if lv == 1]
    check("exactly one h1 in the weekly tree", len(h1s) == 1, ", ".join(h1s))

    # Plates are h2 and each piece's own headline is h3. Anything deeper skips
    # a level, since nothing in the tree renders an h3-level container.
    deep = sorted({f"{f}:h{lv}" for f, lv in hs if lv > 3})
    check("no heading below h3", not deep, ", ".join(deep))

    # Every literal in-page anchor the contents offers must exist as an id.
    src = (WEEKLY_TSX / "WeeklyIssue.tsx").read_text()
    hrefs = set(re.findall(r'href:\s*"#(wk-[A-Za-z0-9_-]+)"', src))
    ids = set()
    for f in sorted(WEEKLY_TSX.rglob("*.tsx")):
        ids.update(re.findall(r'id=[{"`\s]*"?(wk-[A-Za-z0-9_-]+)', f.read_text()))
    dead = sorted(hrefs - ids)
    check("every contents anchor names a real section", not dead, ", ".join(dead))
    check("contents offers the back issues", "wk-archive" in hrefs)


# ---------------------------------------------------------------------------
# W-T07  The back-issue archive
# ---------------------------------------------------------------------------
ISSUES_JSON = ROOT / "frontend" / "build-data" / "weekly-issues.json"
ARCHIVE_JSON = ROOT / "frontend" / "public" / "data" / "weekly-archive.json"
AUDIO_DIR = ROOT / "frontend" / "public" / "audio"


def test_archive():
    """The archive is the ONLY durable record a past issue has.

    The weekly job restores the Actions cache and never saves it back (the
    daily pipeline is usually still running at 12:00 UTC and a save would lose
    a day), so the row it writes dies with the container. If an append-merge
    bug drops an issue here, that issue is gone.
    """
    print("\nW-T07  back-issue archive")
    if not ISSUES_JSON.exists():
        check("weekly-issues.json exists", False, str(ISSUES_JSON))
        return
    issues = json.loads(ISSUES_JSON.read_text())
    check("archive is a non-empty list", isinstance(issues, list) and bool(issues),
          f"{len(issues) if isinstance(issues, list) else '?'} issue(s)")

    from datetime import date
    keys = [(i.get("edition"), i.get("week_start")) for i in issues]
    check("every (edition, week) is unique", len(keys) == len(set(keys)))
    bad_days = [k[1] for k in keys
                if not k[1] or date.fromisoformat(str(k[1])[:10]).weekday() != 0]
    check("every week_start is a Monday", not bad_days, str(bad_days))

    mismatched = [i["week_start"] for i in issues
                  if i.get("issue_number") != weekly_window(
                      __import__("datetime").datetime.fromisoformat(
                          i["week_start"] + "T12:00:00+00:00")
                      + __import__("datetime").timedelta(days=7))[2]]
    check("every issue_number matches its week", not mismatched, str(mismatched))

    over = [(i["week_start"], len(c.get("headline") or ""))
            for i in issues for c in (i.get("cover_text") or [])
            if isinstance(c, dict) and len(c.get("headline") or "") > MAX_HEADLINE_CHARS]
    check("no archived cover headline is a paragraph", not over, str(over))

    # The newest archived issue and the published snapshot are the same issue.
    if WEEKLY_JSON.exists():
        live = json.loads(WEEKLY_JSON.read_text())
        newest = issues[0] if issues else {}
        check("newest archive entry matches weekly.json",
              newest.get("week_start") == live.get("week_start"),
              f"archive {newest.get('week_start')} vs live {live.get('week_start')}")

    # Every claimed enclosure has a committed file. Dead audio in the playlist
    # is worse than no audio: Supabase-hosted URLs from before the
    # decommission are cleared rather than carried.
    if ARCHIVE_JSON.exists():
        index = json.loads(ARCHIVE_JSON.read_text())
        check("archive index matches the issue list", len(index) == len(issues),
              f"{len(index)} vs {len(issues)}")
        missing = []
        for row in index:
            url = str(row.get("audio_url") or "")
            if not url.startswith("/audio/"):
                if url:
                    missing.append(f"{row.get('week_start')}: not a local path")
                continue
            path = AUDIO_DIR / url.split("?")[0][len("/audio/"):]
            if not path.exists():
                missing.append(f"{row.get('week_start')}: {path.name} not committed")
        check("every archived audio_url has a committed file", not missing,
              "; ".join(missing))


def main():
    print("void --weekly gates")
    test_headline_guard()
    test_weekly_window()
    test_export_reader_parity()
    test_committed_snapshot()
    test_build_weekly_row()
    test_class_parity()
    test_document_structure()
    test_archive()
    print()
    if _failures:
        print(f"FAILED ({len(_failures)}): " + ", ".join(_failures))
        return 1
    print("All weekly gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
