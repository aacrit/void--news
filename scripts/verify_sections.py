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
  W-08  the served /weekly carries no em or en dash outside its <title>.
  W-09  the audio edition ships an ordered chapter rail and its sidecar.
  W-01  data/weekly.json carries an issue number and a Monday-to-Sunday week
  W-03  the cover image, if present, comes from a freely licensed source.
        Issue #26 shipped an AFP wire photograph hotlinked off a publisher CDN.
  W-02  the issue is not stale: three consecutive missed Mondays means the
        weekly job is broken, not merely late
  P-01  /press/ states the feed size the config holds. The press kit said
        "50" and "fifty" for two weeks after the feed became 20, under a
        heading telling journalists to copy it as written, and no served gate
        fetched the one page whose whole job is to be quoted.

Exit 1 on any failure; prints one line per check. Run by verify-production.yml.
"""

from __future__ import annotations

import datetime as dt
import re
import json
import sys
from pathlib import Path
import urllib.error
import urllib.request

MIN_EVENTS = 70          # the catalog is 78; a real regression drops it far below
MAX_WEEKLY_AGE_DAYS = 21  # three missed Mondays
SAMPLE_SLUGS = 8          # H-04 spot-checks rather than fetching all 78
# Mirrors weekly_parse.MAX_HEADLINE_CHARS. Duplicated rather than imported
# because this script is stdlib-only and runs against the LIVE site with no
# repo on the path; tests/test_weekly.py asserts the two agree.
MAX_HEADLINE_CHARS = 120

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

    # P-01 — the press kit says the feed size the config holds.
    check_press(base)

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
    # A cover "headline" longer than a headline means `parse_essay` ate an
    # essay's lede again. Issue #26 shipped a 698-character paragraph set as a
    # display-size red <h2>; the parser guards against it now, and this is the
    # production lock on that guard.
    long_heads = [len(c.get("headline") or "")
                  for c in (weekly.get("cover_text") or [])
                  if isinstance(c, dict) and len(c.get("headline") or "") > MAX_HEADLINE_CHARS]
    report("W-01",
           bool(issue) and start is not None and start.weekday() == 0 and not long_heads,
           f"issue #{issue}, week starting {start_raw or '(none)'}"
           + ("" if start and start.weekday() == 0 else " (week_start is not a Monday)")
           + ("" if not long_heads
              else f"  <- {len(long_heads)} cover headline(s) are paragraphs: {long_heads}"))

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

    # W-04 — /weekly actually PRERENDERS. The page was a client shell that
    # fetched weekly.json in a useEffect, so the served HTML carried no issue
    # content and every issue shared one OG card. Grepping the cover headline
    # out of the served markup is the only check that proves it is fixed.
    head = str(weekly.get("cover_headline") or "").strip()
    try:
        _, _, html = fetch(f"{base}/weekly/")
        needle = html_escape_variants(head[:60])
        report("W-04", bool(head) and any(n in html for n in needle),
               f"served /weekly/ is {len(html):,} bytes and "
               + ("carries the cover headline" if any(n in html for n in needle)
                  else "does NOT carry the cover headline  <- client-only shell?"))
    except Exception as e:
        report("W-04", False, f"could not fetch /weekly/: {type(e).__name__}: {e}")

    # W-05/W-06 — the back-issue archive. The weekly job restores the Actions
    # cache and never saves it back, so the deploy tree is the ONLY durable
    # record a past issue has: a broken append silently loses an issue forever.
    try:
        _, _, raw = fetch(f"{base}/data/weekly-archive.json")
        index = json.loads(raw) or []
    except Exception as e:
        report("W-05", False, f"could not read data/weekly-archive.json: {type(e).__name__}: {e}")
        report("W-06", False, "skipped (no archive)")
        index = []

    if index:
        newest = index[0]
        report("W-05",
               len(index) >= 1 and newest.get("issue_number") == issue,
               f"{len(index)} issue(s); newest is #{newest.get('issue_number')} "
               + ("matching weekly.json" if newest.get("issue_number") == issue
                  else f"but weekly.json says #{issue}  <- archive append is broken"))

        # The previous issue's permalink must be a real page, not just a row in
        # a list. This is what proves the archive is reachable.
        prev = next((r for r in index[1:] if r.get("week_start")), None)
        if not prev:
            report("W-06", True, "only one issue published so far; nothing to link back to")
        else:
            try:
                status, _, phtml = fetch(f"{base}/weekly/{prev['week_start']}/")
                ph = str(prev.get("cover_headline") or "").strip()[:60]
                has = bool(ph) and any(n in phtml for n in html_escape_variants(ph))
                report("W-06", status == 200 and has,
                       f"/weekly/{prev['week_start']}/ returned {status}"
                       + ("" if has else " and does not carry its own headline"))
            except Exception as e:
                report("W-06", False,
                       f"/weekly/{prev['week_start']}/ failed: {type(e).__name__}: {e}")

    # W-07 — the browser payload carries what a browser needs and nothing else.
    # audio_script is ~12 KB of TTS source rendered nowhere; cover_timelines and
    # cover_numbers shipped as raw JSON STRINGS because the exporter's parse
    # list and the frontend reader's mirror list had drifted apart.
    leaked = [k for k in ("audio_script", "opinion_audio_script") if weekly.get(k)]
    stringly = [k for k in ("cover_timelines", "cover_numbers", "departments", "opinions")
                if isinstance(weekly.get(k), str)]
    report("W-07", not leaked and not stringly,
           "payload is clean"
           if not leaked and not stringly
           else f"unrendered TTS source: {leaked}; shipped as raw strings: {stringly}")

    # W-08 — no em or en dash in the SERVED prose. CLAUDE.md bans both in
    # generated copy AND frontend microcopy, and until 2026-09-20 exactly one
    # of six weekly generators enforced anything, so the live page carried
    # seven. The title is excluded because a <title> is chrome, not copy, and
    # the JSON payload because a raw data blob is not prose a reader sees.
    try:
        status, _, whtml = fetch(f"{base}/weekly/")
        # The whole <head> goes, not just <title>: og:title and og:description
        # are chrome in the same way a tab label is, and a page name reading
        # "Issue #8: ... — Void Weekly" is not prose a reader is shown.
        body = re.sub(r"<head\b.*?</head>", "", whtml, flags=re.S)
        body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
        dashes = body.count("\u2014") + body.count("\u2013")
        sample = ""
        m = re.search(r".{50}[\u2014\u2013].{50}", body)
        if m:
            sample = ": ..." + m.group().replace("\n", " ")
        report("W-08", dashes == 0,
               "no dash in the served prose" if dashes == 0
               else f"{dashes} dash(es) in served prose{sample}")
    except Exception as e:
        report("W-08", False, f"could not fetch /weekly/: {type(e).__name__}: {e}")

    # W-09 — the Sunday audio edition, if the issue has one, ships its chapter
    # sidecar and the rail is ordered from zero. A chapter rail that starts
    # late or runs backwards is a player that jumps to the wrong movement, and
    # it is invisible until someone uses it.
    chs = weekly.get("audio_chapters")
    if not weekly.get("audio_url"):
        report("W-09", True, "this issue has no audio (acceptable)")
    elif isinstance(chs, str):
        report("W-09", False, "audio_chapters shipped as a raw JSON string")
    elif not chs:
        # Was: report(..., True, "legacy two-voice read, no chapter rail
        # (acceptable)"). It was not acceptable, and hard-coding it to pass is
        # how the section shipped every scheduled week on the legacy read while
        # a gate named W-09 reported green. There is no legacy read any more.
        report("W-09", False,
               "audio with no chapter rail: The Argument always emits one, so "
               "this is a legacy or partial render")
    else:
        times = [c.get("startTime") for c in chs if isinstance(c, dict)]
        ordered = times == sorted(times) and times and times[0] == 0
        sidecar = weekly["audio_url"].split("?")[0].rsplit(".", 1)[0] + ".chapters.json"
        try:
            sstatus, _, _ = fetch(base.rstrip("/") + sidecar)
        except Exception:
            sstatus = 0
        report("W-09", bool(ordered) and sstatus == 200,
               f"{len(chs)} chapters, ordered from zero, sidecar {sstatus}"
               if ordered and sstatus == 200
               else f"chapters ordered={bool(ordered)}, sidecar returned {sstatus}")

    return 0 if ok else 1


# The feed size the site is configured to show. This script runs against the
# live site and cannot import the frontend, so it reads the same JSON file
# feedConfig.ts reads when the checkout is beside it, and otherwise takes the
# served front page's JSON-LD ItemList, which page.tsx sets from the same
# constant. Restating the number here would be the drift P-01 exists to catch.
def _feed_displayed(base: str) -> int | None:
    cfg = Path(__file__).resolve().parents[1] / "frontend" / "config" / "feed.json"
    try:
        return int(json.loads(cfg.read_text(encoding="utf-8"))["displayed"])
    except Exception:
        pass
    try:
        _, _, home = fetch(f"{base}/")
        m = re.search(r'"numberOfItems"\s*:\s*(\d+)', home)
        return int(m.group(1)) if m else None
    except Exception:
        return None


_ONES = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight",
         "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
         "sixteen", "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
         "eighty", "ninety"]


def _number_word(n: int) -> str:
    """The word form press/page.tsx sets for the same number ("twenty")."""
    if not 0 <= n <= 99:
        return str(n)
    if n < 20:
        return _ONES[n]
    tens, ones = divmod(n, 10)
    return _TENS[tens] + (f"-{_ONES[ones]}" if ones else "")


def _visible_text(html: str) -> str:
    """What a reader sees: tags, scripts and styles removed, spacing collapsed.
    The same reduction verify_production.py makes."""
    out = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    out = re.sub(r"<!--.*?-->", " ", out, flags=re.S)
    out = re.sub(r"<[^>]+>", " ", out)
    return re.sub(r"\s+", " ", out).strip()


def check_press(base: str) -> None:
    """P-01: every count of stories on the served /press/ is the configured
    feed size, as a number or as a word. Any other count next to "stories"
    is the stale one; "50" survived in a stat ledger where the number and
    the noun sat in different tags, so the match runs on visible text."""
    displayed = _feed_displayed(base)
    if displayed is None:
        report("P-01", False, "could not determine the configured feed size")
        return
    try:
        status, final, html = fetch(f"{base}/press/")
    except urllib.error.HTTPError as e:
        report("P-01", False, f"/press/ returned HTTP {e.code}")
        return
    except Exception as e:
        report("P-01", False, f"/press/ failed: {type(e).__name__}: {e}")
        return
    if status != 200 or not final.rstrip("/").endswith("/press"):
        report("P-01", False, f"/press/ returned {status} at {final}")
        return
    text = _visible_text(html)
    counts = re.findall(
        r"\b(\d{1,3}|" + "|".join(w for w in _ONES[1:] + _TENS[2:] if w)
        + r"(?:-(?:one|two|three|four|five|six|seven|eight|nine))?)"
        r"\s+(?:most important\s+)?stories\b",
        text, flags=re.I)
    want = {str(displayed), _number_word(displayed)}
    wrong = [c for c in counts if c.lower() not in want]
    report("P-01", bool(counts) and not wrong,
           f"/press/ counts stories as {sorted(set(c.lower() for c in counts))} "
           f"(config says {displayed}, {_number_word(displayed)!r})"
           + ("" if counts else "  <- no story count on the page at all")
           + ("" if not wrong else f"  <- stale: {sorted(set(wrong))}"))


def html_escape_variants(text):
    """The same text as it may appear in served HTML.

    React escapes quotes and ampersands in text nodes, so a headline carrying
    an apostrophe never matches raw. Checking both spellings keeps W-04 from
    failing on punctuation.
    """
    out = [text]
    out.append(text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    out.append(text.replace("'", "&#x27;").replace('"', "&quot;"))
    return out


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "https://news.voidvision.org/"))
