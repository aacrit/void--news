#!/usr/bin/env python3
"""Served-output gate for History and Weekly: does production actually serve them?

    python scripts/verify_sections.py [https://news.voidvision.org/]

Both sections degrade SILENTLY when their data path breaks, which is exactly how
they rotted before rev 69: History fell back to ten hardcoded mock events when
its fetch returned nothing, and Weekly kept serving Issue #23 for three weeks
while the job that should have refreshed it wrote to a decommissioned database
and committed nothing. Neither failure turned anything red. These checks make
both loud.

Checks, against the LIVE site (stdlib only, like verify_production.py):
  H-01  /history/ and /weekly/ resolve (HTTP 200, not a redirect to home)
  H-02  data/history.json is a real catalog: >= 70 events, each with a slug,
        title and at least one perspective
  H-03  no event image points at Supabase Storage (that bucket is deleted; the
        originals are public-domain Wikimedia and must be hotlinked)
  H-04  every /history/<slug>/ in the catalog is actually prerendered
  W-01  data/weekly.json carries an issue number and a Monday-to-Sunday week
  W-02  the issue is not stale: three consecutive missed Mondays means the
        weekly job is broken, not merely late

Exit 1 on any failure; prints one line per check. Run by verify-production.yml.
"""

from __future__ import annotations

import datetime as dt
import json
import sys
import urllib.error
import urllib.request

MIN_EVENTS = 70          # the catalog is 78; a real regression drops it far below
MAX_WEEKLY_AGE_DAYS = 21  # three missed Mondays
SAMPLE_SLUGS = 8          # H-04 spot-checks rather than fetching all 78

ok = True


def report(code: str, passed: bool, detail: str) -> None:
    global ok
    if not passed:
        ok = False
    print(f"[{'ok  ' if passed else 'FAIL'}] {code}: {detail}")


def fetch(url: str, head: bool = False):
    req = urllib.request.Request(
        url,
        method="HEAD" if head else "GET",
        headers={"User-Agent": "void-verify-sections/1.0", "Cache-Control": "no-cache"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return r.status, r.geturl(), (b"" if head else r.read().decode("utf-8", "replace"))


def main(site: str) -> int:
    base = site.rstrip("/")

    # H-01 — the routes resolve, and resolve to THEMSELVES. A 301 to home is how
    # both sections were hidden, so a surviving redirect must read as a failure
    # rather than as a 200 on the homepage.
    for path in ("/history/", "/weekly/"):
        try:
            status, final, _ = fetch(f"{base}{path}")
            landed = final.rstrip("/").endswith(path.rstrip("/"))
            report(f"H-01{path}", status == 200 and landed,
                   f"{status} at {final}" + ("" if landed else " (redirected away from the section)"))
        except urllib.error.HTTPError as e:
            report(f"H-01{path}", False, f"HTTP {e.code}")
        except Exception as e:
            report(f"H-01{path}", False, f"{type(e).__name__}: {e}")

    # H-02/H-03/H-04 — the catalog behind /history.
    events: list[dict] = []
    try:
        _, _, raw = fetch(f"{base}/data/history.json")
        events = json.loads(raw)
    except Exception as e:
        report("H-02", False, f"could not read data/history.json: {type(e).__name__}: {e}")
        report("H-03", False, "skipped (no catalog)")
        report("H-04", False, "skipped (no catalog)")
        return 0 if ok else 1

    thin = [
        e.get("slug") or "(no slug)"
        for e in events
        if not e.get("slug") or not e.get("title") or not (e.get("perspectives") or [])
    ]
    report("H-02", len(events) >= MIN_EVENTS and not thin,
           f"{len(events)} events (floor {MIN_EVENTS})"
           + (f"; {len(thin)} incomplete: {thin[:5]}" if thin else ""))

    dead = [
        m.get("source_url")
        for e in events
        for m in (e.get("media") or [])
        if "supabase.co" in str(m.get("source_url") or "")
    ] + [
        e.get("hero_image_url")
        for e in events
        if "supabase.co" in str(e.get("hero_image_url") or "")
    ]
    report("H-03", not dead,
           "no Supabase Storage image URLs" if not dead
           else f"{len(dead)} image(s) still point at the deleted bucket: {dead[:3]}")

    # Spot-check that the catalog's slugs were actually prerendered. A catalog
    # that grows without generateStaticParams picking it up gives a 404 on a
    # page the landing grid links to.
    slugs = [e["slug"] for e in events if e.get("slug")]
    sample = slugs[:: max(1, len(slugs) // SAMPLE_SLUGS)][:SAMPLE_SLUGS]
    missing = []
    for slug in sample:
        try:
            status, _, _ = fetch(f"{base}/history/{slug}/", head=True)
            if status != 200:
                missing.append(f"{slug} ({status})")
        except Exception as e:
            missing.append(f"{slug} ({type(e).__name__})")
    report("H-04", not missing,
           f"{len(sample)} sampled event pages all render"
           if not missing else f"not prerendered: {missing}")

    # W-01/W-02 — the weekly snapshot.
    try:
        _, _, raw = fetch(f"{base}/data/weekly.json")
        weekly = json.loads(raw) or {}
    except Exception as e:
        report("W-01", False, f"could not read data/weekly.json: {type(e).__name__}: {e}")
        report("W-02", False, "skipped (no snapshot)")
        return 0 if ok else 1

    issue = weekly.get("issue_number")
    start_raw = str(weekly.get("week_start") or "")
    try:
        start = dt.date.fromisoformat(start_raw[:10])
    except ValueError:
        start = None
    report("W-01", bool(issue) and start is not None and start.weekday() == 0,
           f"issue #{issue}, week starting {start_raw or '(none)'}"
           + ("" if start and start.weekday() == 0 else " (week_start is not a Monday)"))

    if start is None:
        report("W-02", False, "skipped (no week_start)")
    else:
        age = (dt.date.today() - start).days
        report("W-02", age <= MAX_WEEKLY_AGE_DAYS,
               f"issue is {age} days old (limit {MAX_WEEKLY_AGE_DAYS}); "
               + ("fresh" if age <= MAX_WEEKLY_AGE_DAYS
                  else "the Monday weekly job has not landed in three weeks"))

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "https://news.voidvision.org/"))
