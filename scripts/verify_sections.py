#!/usr/bin/env python3
"""Served-output gate for History, Weekly and Paper: does production serve them?

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
  H-05  the served /history/ carries no em or en dash, in its prose OR in an
        aria-label. A screen reader's output is written editorial output.
  H-06  the served /history/ is a page and not a shell: exactly one <h1>, and
        at least 60 event card links.
  W-08  the served /weekly carries no em or en dash outside its <title>.
  W-09  the audio edition ships an ordered chapter rail and its sidecar.
  W-10  the served /weekly prose carries no kill-list term (the shared list in
        pipeline/utils/prohibited_terms.py) outside <blockquote> and <q>.
  W-01  data/weekly.json carries an issue number and a Monday-to-Sunday week
  W-03  the cover image, if present, comes from a freely licensed source.
        Issue #26 shipped an AFP wire photograph hotlinked off a publisher CDN.
  W-02  the issue is not stale: three consecutive missed Mondays means the
        weekly job is broken, not merely late
  PR-01 /press/ states the feed size the config holds. The press kit said
        "50" and "fifty" for two weeks after the feed became 20, under a
        heading telling journalists to copy it as written, and no served gate
        fetched the one page whose whole job is to be quoted.
  P-01  /paper/ resolves to itself, not to the launch-hiding 301 to home
  P-02  /paper/ carries exactly the front page's headlines, in the same order
  P-03  no em or en dash in the served /paper/ prose
  P-04  none of the five untrue strings the pre-relaunch Paper served

Exit 1 on any failure; prints one line per check. Run by verify-production.yml.
"""

from __future__ import annotations

import datetime as dt
import html
import re
import json
import sys
from pathlib import Path
import urllib.error
import urllib.request
from html import unescape

MIN_EVENTS = 70          # the catalog is 78; a real regression drops it far below
MAX_WEEKLY_AGE_DAYS = 21  # three missed Mondays
SAMPLE_SLUGS = 8          # H-04 spot-checks rather than fetching all 78
# Mirrors weekly_parse.MAX_HEADLINE_CHARS. Duplicated rather than imported
# because this script is stdlib-only and runs against the LIVE site with no
# repo on the path; tests/test_weekly.py asserts the two agree.
MAX_HEADLINE_CHARS = 120
# Mirrors frontend/config/feed.json `displayed`, duplicated for the same reason
# MAX_HEADLINE_CHARS is: this script is stdlib-only and runs against the LIVE
# site with no repo on the path. tests/test_paper.py asserts the two agree.
FEED_DISPLAYED = 20

# Paper prints the front page's headlines; the front page renders its two leads
# as .lead-headline__text (or .lead-story__headline-text when the split headline
# is off) and every remaining card as .story-card__headline-text, in that
# document order. Paper wraps each headline in .np-article__headline-text.
HOME_HEADLINE_RE = (
    r'class="(?:lead-headline__text|lead-story__headline-text'
    r'|story-card__headline-text)"[^>]*>([^<]*)<'
)
PAPER_HEADLINE_RE = r'class="np-article__headline-text"[^>]*>([^<]*)<'

# Strings the pre-relaunch Paper served that were not true: a category-to-city
# dateline (a Ukraine story datelined BEIRUT), a source count off by 816, a
# cadence that was never twice daily, a next-edition promise, and a joke
# weather forecast. P-04 is the lock on all five.
PAPER_BANNED = ("BEIRUT", "200 curated", "twice daily", "Next edition at dawn",
                "Weather")

# Mirrors pipeline/utils/prohibited_terms.py SIGNIFICANCE_WORDS and
# SLOP_PATTERN, verbatim, for the same reason as MAX_HEADLINE_CHARS above;
# tests/test_weekly.py asserts the copies agree.
SIGNIFICANCE_WORDS = (
    r"significantly|significant|notably|notable|crucially|crucial|"
    r"remarkably|strikingly|importantly|interestingly|markedly"
)
SLOP_PATTERN = (
    r"\b(?:"
    r"underscor(?:e|es|ed|ing)|robust(?:ly)?|navigat(?:e|es|ed|ing)|nuanced|pivotal|"
    r"delv(?:e|es|ed|ing)|multifaceted|tapestry|"
    r"pav(?:e|es|ed|ing)\s+the\s+way|"
    r"(?:send|sends|sent|sending)\s+a\s+clear\s+(?:message|signal)|"
    r"a\s+testament\s+to|"
    r"(?:shed|sheds|shedding)\s+light\s+on|"
    r"mark(?:s|ed|ing)?\s+a\s+(?:key|pivotal|significant)\s+moment|"
    r"complex\s+interplay|"
    r"this\s+(?:isn['\u2019]t|is\s+not)\s+just\s+about|"
    # The weekly's own list, kept so nothing it caught before is lost.
    r"game-changing|should\s+chill|in\s+conclusion|to\s+summarize|"
    r"all\s+things\s+considered|noteworthy|what\s+you\s+need\s+to\s+know|"
    r"here['\u2019]?s\s+what|let['\u2019]?s\s+break\s+down|let['\u2019]?s\s+dive|"
    r"it\s+bears\s+mentioning|it\s+should\s+be\s+noted|"
    r"it\s+(?:is|['\u2019]s)\s+worth\s+noting"
    r")\b"
)
_KILL_SIGNIFICANCE_RE = re.compile(
    r"\b(?P<neg>no|not|without|little|any|minimal|hardly|barely)?\s*"
    r"(?:(?:most|more|very|highly|particularly|quite|so|the\s+most)\s+)?"
    r"(?P<word>" + SIGNIFICANCE_WORDS + r")\b", re.I,
)
_KILL_SLOP_RE = re.compile(SLOP_PATTERN, re.I)

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


def history_body(html: str) -> str:
    """The served /history/ with its chrome removed.

    The whole <head> goes, not just <title>: og:title and og:description are
    chrome in the same way a tab label is. Scripts go because Next inlines the
    RSC payload into them, which is a data blob rather than prose a reader is
    shown. This mirrors W-08's treatment of /weekly exactly.
    """
    body = re.sub(r"<head\b.*?</head>", "", html, flags=re.S)
    return re.sub(r"<script.*?</script>", "", body, flags=re.S)


def check_h05(html: str) -> None:
    """H-05 - no em or en dash in the served prose OR in an accessible name.

    CLAUDE.md bans both in generated copy AND in frontend microcopy, and W-08
    enforced it on /weekly only. /history served six era ranges ("3000 BCE -
    500 BCE" with an em dash) and four aria-labels joining a title to its date
    with one. An aria-label is checked separately because it lives inside a
    tag, where the prose scan below would never look.
    """
    body = history_body(html)

    labels = re.findall(r'aria-label="([^"]*)"', html)
    bad_labels = [t for t in labels if "\u2014" in t or "\u2013" in t]

    visible = re.sub(r"<[^>]+>", " ", body)
    dashes = visible.count("\u2014") + visible.count("\u2013")

    sample = ""
    m = re.search(r".{50}[\u2014\u2013].{50}", visible)
    if m:
        sample = ": ..." + m.group().replace("\n", " ")

    report("H-05", dashes == 0 and not bad_labels,
           "no dash in the served text or any accessible name"
           if dashes == 0 and not bad_labels
           else f"{dashes} dash(es) in visible text{sample}"
                + (f"; {len(bad_labels)} aria-label(s): {bad_labels[:2]}" if bad_labels else ""))


def check_h06(html: str, catalog_size: int) -> None:
    """H-06 - the landing is a page, not a shell.

    /history mounted a client component that fetched data/history.json in an
    effect, so the served <main> was one italic line and the section had no
    <h1> at all: nothing for a crawler, and a blank screen until the round trip
    landed. Counting the heading and the event links is the only check that
    proves the landing is prerendered, the same way W-04 proves it for
    /weekly. More than one <h1> is its own defect, so the count is exact.
    """
    h1s = len(re.findall(r"<h1[\s>]", html))
    links = set(re.findall(r'href="(?:https?://[^/"]+)?/history/([a-z0-9][a-z0-9-]*)/"', html))
    # era/, region/ and threads/ are browse routes, not events.
    events = {s_ for s_ in links if s_ not in ("era", "region", "threads")}

    floor = min(60, catalog_size) if catalog_size else 60
    report("H-06", h1s == 1 and len(events) >= floor,
           f"{h1s} <h1> and {len(events)} event card link(s) (floor {floor})"
           + ("" if h1s == 1 and len(events) >= floor
              else "  <- client-only shell, or a heading went missing"))


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

    # H-05/H-06 - the served landing itself. One fetch, two checks.
    try:
        _, _, hhtml = fetch(f"{base}/history/")
        check_h05(hhtml)
        check_h06(hhtml, len(events))
    except Exception as e:
        report("H-05", False, f"could not fetch /history/: {type(e).__name__}: {e}")
        report("H-06", False, "skipped (no page)")

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

    # W-10: no kill-list term in the SERVED prose. W-08 proved the pattern:
    # the two published issues carried 34 kill-list hits across 104 fields
    # because five of six weekly generators measured nothing and the sixth
    # shipped whatever the one regeneration returned (brand audit F-03). The
    # generator now drops a section that still carries one; this is the check
    # that the page agrees. Quotation is exempt: a columnist quoting a source
    # who said "robust" is reporting, not writing it.
    try:
        status, _, whtml = fetch(f"{base}/weekly/")
        hits = kill_list_hits(whtml)
        report("W-10", not hits,
               "no kill-list term in the served prose" if not hits
               else f"{len(hits)} kill-list hit(s) in served prose: " + "; ".join(hits[:6]))
    except Exception as e:
        report("W-10", False, f"could not fetch /weekly/: {type(e).__name__}: {e}")

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

    # P-01..P-04 — Paper, the printable front page.
    check_paper(base)

    # TH-01..TH-04 — a published History thesis page, if any.
    check_thesis(base)

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
    """PR-01: every count of stories on the served /press/ is the configured
    feed size, as a number or as a word. Any other count next to "stories"
    is the stale one; "50" survived in a stat ledger where the number and
    the noun sat in different tags, so the match runs on visible text."""
    displayed = _feed_displayed(base)
    if displayed is None:
        report("PR-01", False, "could not determine the configured feed size")
        return
    try:
        status, final, html = fetch(f"{base}/press/")
    except urllib.error.HTTPError as e:
        report("PR-01", False, f"/press/ returned HTTP {e.code}")
        return
    except Exception as e:
        report("PR-01", False, f"/press/ failed: {type(e).__name__}: {e}")
        return
    if status != 200 or not final.rstrip("/").endswith("/press"):
        report("PR-01", False, f"/press/ returned {status} at {final}")
        return
    text = _visible_text(html)
    counts = re.findall(
        r"\b(\d{1,3}|" + "|".join(w for w in _ONES[1:] + _TENS[2:] if w)
        + r"(?:-(?:one|two|three|four|five|six|seven|eight|nine))?)"
        r"\s+(?:most important\s+)?stories\b",
        text, flags=re.I)
    want = {str(displayed), _number_word(displayed)}
    wrong = [c for c in counts if c.lower() not in want]
    report("PR-01", bool(counts) and not wrong,
           f"/press/ counts stories as {sorted(set(c.lower() for c in counts))} "
           f"(config says {displayed}, {_number_word(displayed)!r})"
           + ("" if counts else "  <- no story count on the page at all")
           + ("" if not wrong else f"  <- stale: {sorted(set(wrong))}"))

def kill_list_hits(page_html: str) -> list[str]:
    """Kill-list terms in the visible prose of a served page, with context.

    Head, scripts, styles and JSON payloads are chrome; <blockquote> and <q>
    are somebody else's words. Everything else is Void's prose. A negated
    significance word ("no significant damage") carries a fact and is not a
    hit, the same rule the pipeline's sanitizer applies.
    """
    body = re.sub(r"<head\b.*?</head>", " ", page_html, flags=re.S)
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<(blockquote|q)\b.*?</\1>", " ", body, flags=re.S | re.I)
    text = html.unescape(re.sub(r"<[^>]+>", " ", body))
    text = re.sub(r"\s+", " ", text)
    hits = []
    for m in _KILL_SIGNIFICANCE_RE.finditer(text):
        if m.group("neg"):
            continue
        hits.append(f"{m.group('word').lower()!r} in ...{text[max(0, m.start() - 40):m.end() + 40]}...")
    for m in _KILL_SLOP_RE.finditer(text):
        hits.append(f"{m.group(0).lower()!r} in ...{text[max(0, m.start() - 40):m.end() + 40]}...")
    return hits
def strip_chrome(doc: str) -> str:
    """The served page minus <head> and every <script>: what a reader is shown.

    Same treatment W-08 gives /weekly. A <title>, an og:description and a JSON
    payload are chrome, not prose.
    """
    body = re.sub(r"<head\b.*?</head>", "", doc, flags=re.S)
    return re.sub(r"<script.*?</script>", "", body, flags=re.S)


def check_paper(base: str) -> None:
    """P-01..P-04 — /paper prints the front page and nothing it cannot support.

    P-01  /paper/ resolves to itself (200, not the launch-hiding 301 to home)
    P-02  it carries exactly FEED_DISPLAYED articles whose headlines equal the
          front page's, in the same order. Paper's whole claim is "the same
          stories in the same order"; nothing else on the site checks it, and
          the page spent its first life reading a 150-row window the homepage
          deliberately excluded 130 of.
    P-03  no em or en dash in the served prose (CLAUDE.md, same as W-08)
    P-04  none of the five untrue strings the pre-relaunch Paper served
    """
    try:
        status, final, paper = fetch(f"{base}/paper/")
    except urllib.error.HTTPError as e:
        report("P-01", False, f"HTTP {e.code}")
        for code in ("P-02", "P-03", "P-04"):
            report(code, False, "skipped (no page)")
        return
    except Exception as e:
        report("P-01", False, f"{type(e).__name__}: {e}")
        for code in ("P-02", "P-03", "P-04"):
            report(code, False, "skipped (no page)")
        return

    landed = final.rstrip("/").endswith("/paper")
    report("P-01", status == 200 and landed,
           f"{status} at {final}"
           + ("" if landed else " (redirected away from Paper)"))

    # P-02 — the same headlines, in the same order, as the front page.
    paper_heads = [unescape(h).strip()
                   for h in re.findall(PAPER_HEADLINE_RE, paper)]
    try:
        _, _, home = fetch(f"{base}/")
        home_heads = [unescape(h).strip()
                      for h in re.findall(HOME_HEADLINE_RE, home)]
    except Exception as e:
        home_heads = []
        report("P-02", False, f"could not fetch the front page: {type(e).__name__}: {e}")
    else:
        if len(paper_heads) != FEED_DISPLAYED:
            report("P-02", False,
                   f"{len(paper_heads)} article(s) on /paper/, expected {FEED_DISPLAYED}")
        elif paper_heads == home_heads[:FEED_DISPLAYED]:
            report("P-02", True,
                   f"{FEED_DISPLAYED} articles, headlines match the front page in order")
        else:
            first = next((i for i, (p, h) in
                          enumerate(zip(paper_heads, home_heads)) if p != h), 0)
            report("P-02", False,
                   f"{len(paper_heads)} article(s) vs {len(home_heads)} on the front "
                   f"page; first divergence at position {first + 1}: "
                   f'paper "{paper_heads[first][:60]}" vs '
                   f'home "{(home_heads[first] if first < len(home_heads) else "(missing)")[:60]}"')

    body = strip_chrome(paper)

    # P-03 — the dash ban, on the served prose.
    dashes = body.count("—") + body.count("–")
    m = re.search(r".{50}[—–].{50}", body)
    report("P-03", dashes == 0,
           "no dash in the served prose" if dashes == 0
           else f"{dashes} dash(es) in served prose: ..."
                + (m.group().replace("\n", " ") if m else ""))

    # P-04 — the five untrue strings. Checked against Paper's OWN furniture:
    # the story <article> elements and the Brief body are pipeline copy, and a
    # real hurricane story saying "Weather" is not a Paper defect. Everything
    # left is masthead, standfirst, colophon and button, which is exactly where
    # all five lived.
    chrome = re.sub(r"<article\b.*?</article>", "", body, flags=re.S)
    chrome = re.sub(r'<div class="np-brief__text".*?</div>', "", chrome, flags=re.S)
    found = [s for s in PAPER_BANNED if s in chrome]
    report("P-04", not found,
           "none of the retired strings are served"
           if not found else f"still serving: {found}")


def _insecure_hosts() -> set[str]:
    """The http-only hosts a ledger may cite, from frontend/config/insecure-origins.json."""
    cfg = Path(__file__).resolve().parents[1] / "frontend/config/insecure-origins.json"
    try:
        return {str(h.get("host")) for h in json.loads(cfg.read_text(encoding="utf-8")).get("hosts", [])}
    except (OSError, ValueError):
        return set()


def check_thesis(base: str) -> None:
    """TH-01..TH-04 — a served thesis page (docs/proposals/HISTORY-THESIS-PAGE.md §9).

    The exporter writes data/history-theses.json listing every PUBLISHED thesis
    with the note and exhibit counts its page must carry. With no thesis
    published the checks report that and pass: a draft has no page. Set
    VOID_THESIS_SAMPLE=<slug> to check a local draft export instead.

    TH-01  one <h1>, and the question text present: a page, not a shell
    TH-02  the page carries exactly the index's note count, and every note
           anchor a citation points at exists on the page
    TH-03  every exhibit carries a provenance line
    TH-04  every source link is absolute, and no em or en dash in the page's
           own prose or in any accessible name. Verbatim extracts are quotations
           (<blockquote>) and keep the dashes their documents print, exactly as
           W-10 spares a columnist quoting a source.
    TH-05  the controls: every source mark is a link with a name that says what
           it opens ("Open the free copy of ..."), no note prints its own
           RETURN link, and the page carries exactly one return control
           (2026-09-25: FREE COPY and RETURN were printed as text on every
           note, a hundred times each on Srebrenica).
    """
    import os
    sample = os.environ.get("VOID_THESIS_SAMPLE")
    expect_notes = None
    question = ""
    if not sample:
        try:
            _, _, raw = fetch(f"{base}/data/history-theses.json")
            index = json.loads(raw) or {}
        except Exception as e:
            report("TH-01", False, f"could not read data/history-theses.json: {type(e).__name__}: {e}")
            for code in ("TH-02", "TH-03", "TH-04", "TH-05"):
                report(code, False, "skipped (no index)")
            return
        theses = index.get("theses") or []
        if not theses:
            for code in ("TH-01", "TH-02", "TH-03", "TH-04", "TH-05"):
                report(code, True, "no thesis published yet; every event still renders the Hearing")
            return
        sample = theses[0]["slug"]
        expect_notes = theses[0].get("notes")
        question = str(theses[0].get("question") or "")
    try:
        status, final, page = fetch(f"{base}/history/{sample}/")
    except Exception as e:
        report("TH-01", False, f"/history/{sample}/ failed: {type(e).__name__}: {e}")
        for code in ("TH-02", "TH-03", "TH-04", "TH-05"):
            report(code, False, "skipped (no page)")
        return
    body = strip_chrome(page)
    h1s = len(re.findall(r"<h1[\s>]", page))
    is_thesis = 'class="hist-event-detail hist-hearing-page hist-thesis-page"' in page
    has_q = (not question) or any(v in page for v in html_escape_variants(question[:60]))
    report("TH-01", status == 200 and h1s == 1 and is_thesis and has_q,
           f"/history/{sample}/ is a thesis page with {h1s} <h1>"
           + ("" if has_q else "  <- the question text is missing")
           + ("" if is_thesis else "  <- the route rendered the Hearing"))

    notes = set(re.findall(r'id="n(\d+)"', body))
    refs = set(re.findall(r'href="#n(\d+)"', body))
    dangling = sorted(refs - notes, key=int)
    count_ok = expect_notes is None or len(notes) == expect_notes
    report("TH-02", count_ok and not dangling,
           f"{len(notes)} notes on the page"
           + (f" (index says {expect_notes})" if expect_notes is not None else "")
           + (f"; {len(dangling)} citation(s) point at no note: {dangling[:5]}" if dangling else ", every citation resolves"))

    exhibits = len(re.findall(r'class="hist-th-exhibit"', body))
    provs = len(re.findall(r'class="hist-th-exhibit__prov"', body))
    report("TH-03", exhibits > 0 and exhibits == provs,
           f"{provs} of {exhibits} exhibits carry a provenance line")

    src_block = re.search(r'<section id="sources".*?</section>', body, re.S)
    src_links = re.findall(r'href="([^"]*)"', src_block.group(0)) if src_block else []
    # Hosts that serve a free copy only over http are allowed as plain http
    # links, from frontend/config/insecure-origins.json (each with the reason
    # and the date it was checked; tests/test_insecure_origins.py keeps the
    # list to the hosts it names). Everything else must be https or an anchor.
    insecure_hosts = _insecure_hosts()
    relative = [u for u in src_links if not u.startswith("https://") and not u.startswith("#")
                and not (u.startswith("http://") and u.split("/")[2] in insecure_hosts)]
    prose = re.sub(r"<blockquote\b.*?</blockquote>", " ", body, flags=re.S)
    visible = unescape(re.sub(r"<[^>]+>", " ", prose))
    dashes = visible.count("—") + visible.count("–")
    labels = [t for t in re.findall(r'aria-label="([^"]*)"', page) if "—" in t or "–" in t]
    m = re.search(r".{40}[—–].{40}", visible)
    report("TH-04", not relative and dashes == 0 and not labels,
           f"{len(src_links)} source links, all absolute; no dash in prose or accessible names"
           if not relative and dashes == 0 and not labels
           else f"{len(relative)} relative source link(s) {relative[:2]}; {dashes} dash(es) in prose"
                + (f": ...{m.group().replace(chr(10), ' ')}" if m else "")
                + (f"; {len(labels)} dashed aria-label(s)" if labels else ""))

    ok5, detail5 = _thesis_controls(page)
    report("TH-05", ok5, detail5)


def _thesis_controls(page):
    """TH-05 on one served page. Returns (ok, detail)."""
    marks = re.findall(r'<a\b[^>]*class="hist-th-srcmark hist-th-srcmark--link[^"]*"[^>]*>', page)
    unnamed = [m for m in marks
               if not re.search(r'aria-label="Open the (?:free copy|file page) of [^"]+"', m)]
    backs = len(re.findall(r'class="hist-th-note__back"', page))
    returns = len(re.findall(r'class="hist-th-return"', page))
    ok = bool(marks) and not unnamed and backs == 0 and returns == 1
    return ok, (f"{len(marks)} source marks, {len(unnamed)} unnamed; "
                f"{backs} per-note return link(s); {returns} return control(s)")


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
