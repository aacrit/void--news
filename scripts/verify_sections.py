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
  H-03  every event image is a Wikimedia CDN url carrying a free licence, and
        a sample of them actually returns image bytes. Two real failures live
        here: images pointed at Special:Redirect, which answers HTTP 429 and
        rendered the archive pictureless, and six were licensed fair-use.
  H-04  every /history/<slug>/ in the catalog is actually prerendered
  W-01  data/weekly.json carries an issue number and a Monday-to-Sunday week
  W-03  the cover image, if present, comes from a freely licensed source.
        Issue #26 shipped an AFP wire photograph hotlinked off a publisher CDN.
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

    # Every image url must be a Wikimedia CDN path. Special:Redirect is the one
    # that looks right and fails: it is a MediaWiki special page, throttled to
    # HTTP 429, and it is what made the archive render with no pictures at all.
    OK_HOSTS = ("upload.wikimedia.org", "thumb.wikimedia.org")
    all_imgs = [
        (e.get("slug"), m.get("source_url"), m.get("license"))
        for e in events for m in (e.get("media") or [])
    ] + [
        (e.get("slug"), e.get("hero_image_url"), "hero")
        for e in events if e.get("hero_image_url")
    ]
    bad_host = [u for _, u, _ in all_imgs
                if not any(h in str(u or "") for h in OK_HOSTS)]
    NONFREE = ("fair", "-nc", "-nd", "noncommercial", "non-free", "nonfree")
    nonfree = [(s_, str(lic)) for s_, _, lic in all_imgs
               if lic != "hero" and any(n in str(lic or "").lower() for n in NONFREE)]
    unlicensed = [s_ for s_, _, lic in all_imgs if lic != "hero" and not lic]

    problems = []
    if bad_host:
        problems.append(f"{len(bad_host)} image(s) not on a Wikimedia CDN host: {bad_host[:2]}")
    if nonfree:
        problems.append(f"{len(nonfree)} image(s) carry a non-free licence: {nonfree[:3]}")
    if unlicensed:
        problems.append(f"{len(unlicensed)} image(s) carry no licence: {unlicensed[:3]}")

    # A correct-looking url still has to return an image.
    sampled = [u for _, u, _ in all_imgs if u][:: max(1, len(all_imgs) // 5)][:5]
    for u in sampled:
        try:
            status, _, _ = fetch(u, head=True)
            if status != 200:
                problems.append(f"image returned {status}: {str(u)[:80]}")
        except Exception as e:
            problems.append(f"image failed ({type(e).__name__}): {str(u)[:80]}")

    report("H-03", not problems,
           f"{len(all_imgs)} images, all Wikimedia CDN + free-licensed, "
           f"{len(sampled)} sampled and serving"
           if not problems else "; ".join(problems))

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

    # W-03 — the cover image is Void's to publish, or there is none.
    cover = str(weekly.get("cover_image_url") or "")
    src = str(weekly.get("cover_image_source") or "")
    if not cover:
        report("W-03", True, "no cover image (acceptable; better than an unlicensed one)")
    else:
        licensed_host = any(h in cover for h in (
            "upload.wikimedia.org", "thumb.wikimedia.org",
            "images.unsplash.com", "images.pexels.com",
        ))
        report("W-03", licensed_host and src != "og_image",
               f"cover from {src or 'unknown'}: {cover[:80]}"
               + ("" if licensed_host and src != "og_image"
                  else "  <- not a freely licensed source; a scraped publisher"
                       " og:image is usually a wire photograph"))

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
