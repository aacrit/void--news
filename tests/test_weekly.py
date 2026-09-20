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


def test_export_reader_parity():
    print("\nW-T03  export/reader JSON-field parity")
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


def main():
    print("void --weekly gates")
    test_headline_guard()
    test_weekly_window()
    test_export_reader_parity()
    test_committed_snapshot()
    print()
    if _failures:
        print(f"FAILED ({len(_failures)}): " + ", ".join(_failures))
        return 1
    print("All weekly gates passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
