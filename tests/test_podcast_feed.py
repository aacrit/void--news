#!/usr/bin/env python3
"""Gates for the three podcast feeds. Stdlib only; no DB, no key, no network.

    python tests/test_podcast_feed.py

What reached the served XML before this file existed (brand audit
2026-09-21, F-2, F-12, E-04, E-16..E-19):

  - all three feeds fronted ONE cover, and it was a pre-rebrand raster reading
    "void --onair", "WORLD BRIEF", "409 sources"; the weekly and history JPGs
    did not exist and `_cover_for` fell back to the world art in silence
  - the weekly channel was "Void Weekly: The Argument" under an author of
    "Void News"; the site's brand rule says Weekly is a section
  - a History description read "...expelled in thirty years On August 4,
    1964..." because the subtitle was joined to the summary without a stop
  - the weekly item said "Issue #26" where the page said "Vol. I, No. 1", and
    carried a cover headline the served issue no longer had

Three tiers, like tests/test_weekly.py:

  1. Pure functions   the description join, the cover lookup, the issue label
  2. Cross-file       format.ts vs weekly_parse.py; layout.tsx vs the XML
  3. Committed files  the XML, JPG and SVG that ship
"""

from __future__ import annotations

import json
import re
import struct
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))

from briefing import podcast_feed_generator as pfg  # noqa: E402
from briefing.weekly_parse import (  # noqa: E402
    WEEKLY_LAUNCH_ISSUE, WEEKS_PER_VOLUME, issue_label, roman_numeral,
)

PUBLIC = ROOT / "frontend" / "public"
FORMAT_TS = ROOT / "frontend" / "app" / "weekly" / "format.ts"
LAYOUT_TSX = ROOT / "frontend" / "app" / "layout.tsx"
DIST_MD = ROOT / "docs" / "PODCAST-DISTRIBUTION.md"
ISSUES_JSON = ROOT / "frontend" / "build-data" / "weekly-issues.json"

ITUNES = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
SVG = "{http://www.w3.org/2000/svg}"
TERMINAL = (".", "!", "?", '."', '!"', '?"', ".)", ".”", "!”", "?”")

# What each cover must say, and the edition its file name carries.
PROGRAMME = {"world": "On Air", "weekly": "The Argument", "history": "History"}

_failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    flag = "ok  " if ok else "FAIL"
    print(f"[{flag}] {name}" + (f": {detail}" if detail else ""))
    if not ok:
        _failures.append(name)


def jpeg_size(path: Path) -> tuple[int, int] | None:
    """(width, height) from the first SOF marker; no image library needed."""
    data = path.read_bytes()
    if data[:2] != b"\xff\xd8":
        return None
    i = 2
    while i < len(data) - 9:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
            i += 2
            continue
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
            h, w = struct.unpack(">HH", data[i + 5:i + 9])
            return w, h
        i += 2 + length
    return None


def svg_text(path: Path) -> str:
    """Every <text> node's content, joined. Comments and attributes are not
    artwork; the XML comment delimiters would otherwise read as "--"."""
    tree = ET.parse(path)
    return " | ".join(
        "".join(t.itertext()).strip() for t in tree.iter(f"{SVG}text")
    )


def feeds() -> list[tuple[str, Path, ET.Element]]:
    out = []
    for xml in sorted(PUBLIC.glob("podcast-*.xml")):
        edition = xml.stem[len("podcast-"):]
        out.append((edition, xml, ET.parse(xml).getroot().find("channel")))
    return out


# ---------------------------------------------------------------------------
# 1. Pure functions
# ---------------------------------------------------------------------------

def test_history_description():
    print("\nP-T01  History description closes the subtitle before the join (F-12)")
    joined = pfg._history_description(
        {"subtitle": "The third foreign army they expelled in thirty years",
         "summary": "On August 4, 1964, the destroyer reported an attack.\n\nMore."},
        {"title": "Planted"})
    # The shared sanitiser may collapse the paragraph break; the stop is the
    # point, and "years. On August" is what a listener's app shows.
    check("a subtitle without a stop gets one",
          re.match(r"The third foreign army they expelled in thirty years\.\s+On August", joined)
          is not None, repr(joined[:70]))
    left = pfg._history_description({"subtitle": "Is it over?", "summary": "No."}, {"title": "x"})
    check("a subtitle that already ends a sentence is left alone",
          re.match(r"Is it over\?\s+No\.$", left) is not None, repr(left))
    long = pfg._history_description(
        {"subtitle": "Planted.", "summary": ("A sentence of some length here. " * 200).strip()},
        {"title": "x"})
    check("a description over the cap is cut at a sentence, not mid-word",
          len(long) <= 3900 and long.endswith("here."), repr(long[-30:]))
    check("the composed text ends in terminal punctuation",
          joined.endswith(TERMINAL), repr(joined[-20:]))
    try:
        pfg._history_description({"subtitle": "A line", "summary": "A lead with no stop"},
                                 {"title": "Planted"})
        check("S-03 runs on the composed description and fails the build", False,
              "no ValueError for a lead without a stop")
    except ValueError as e:
        check("S-03 runs on the composed description and fails the build",
              "S-03" in str(e) or "terminal punctuation" in str(e), str(e)[:80])


def test_cover_lookup():
    print("\nP-T02  A feed fronts its own cover, or the build stops (E-16)")
    for edition in PROGRAMME:
        try:
            url = pfg._cover_for(edition)
            check(f"{edition}: own cover", url.endswith(f"/podcast-cover-{edition}.jpg"), url)
        except FileNotFoundError as e:
            check(f"{edition}: own cover", False, str(e)[:90])
    try:
        pfg._cover_for("planted-no-such-show")
        check("a missing cover raises instead of borrowing the world art", False)
    except FileNotFoundError:
        check("a missing cover raises instead of borrowing the world art", True)


def test_issue_label():
    print("\nP-T03  One issue label, computed from one constant (E-04)")
    ts = FORMAT_TS.read_text(encoding="utf-8")
    m = re.search(r"^export const WEEKLY_LAUNCH_ISSUE = (\d+);", ts, re.M)
    check("format.ts declares WEEKLY_LAUNCH_ISSUE", bool(m))
    if m:
        check("format.ts and weekly_parse agree on the launch issue",
              int(m.group(1)) == WEEKLY_LAUNCH_ISSUE,
              f"format.ts {m.group(1)} vs weekly_parse {WEEKLY_LAUNCH_ISSUE}")
    m = re.search(r"^export const WEEKS_PER_VOLUME = (\d+);", ts, re.M)
    check("format.ts declares WEEKS_PER_VOLUME", bool(m))
    if m:
        check("format.ts and weekly_parse agree on the volume length",
              int(m.group(1)) == WEEKS_PER_VOLUME,
              f"format.ts {m.group(1)} vs weekly_parse {WEEKS_PER_VOLUME}")
    cases = {
        WEEKLY_LAUNCH_ISSUE: "Vol. I, No. 1",
        WEEKLY_LAUNCH_ISSUE - 1: "Pilot issue",
        WEEKLY_LAUNCH_ISSUE + WEEKS_PER_VOLUME - 1: f"Vol. I, No. {WEEKS_PER_VOLUME}",
        WEEKLY_LAUNCH_ISSUE + WEEKS_PER_VOLUME: "Vol. II, No. 1",
        None: "Pilot issue",
        "x": "Pilot issue",
    }
    for raw, want in cases.items():
        check(f"issue_label({raw!r}) == {want!r}", issue_label(raw) == want, issue_label(raw))
    check("roman_numeral(4) == 'IV'", roman_numeral(4) == "IV")
    check("roman_numeral(0) == ''", roman_numeral(0) == "")

    ep = pfg._weekly_episode({"issue_number": WEEKLY_LAUNCH_ISSUE,
                              "cover_headline": "Planted Headline",
                              "week_start": "2026-09-14",
                              "created_at": "2026-09-20T17:52:22+00:00",
                              "audio_url": "/audio/weekly-world/x.mp3"})
    title = pfg._episode_title(ep)
    check("weekly item title carries the page's label, not the epoch count",
          title.startswith("Vol. I, No. 1: Planted Headline") and "Issue #" not in title, title)


# ---------------------------------------------------------------------------
# 2. Cross-file
# ---------------------------------------------------------------------------

def test_channel_titles():
    print("\nP-T04  Every channel is 'Void News: <programme>' (E-17)")
    titles = {}
    for edition, xml, channel in feeds():
        title = (channel.findtext("title") or "").strip()
        titles[edition] = title
        check(f"{xml.name}: title starts with 'Void News: '", title.startswith("Void News: "), title)
        check(f"{xml.name}: title is SHOW_META's",
              title == pfg.SHOW_META.get(edition, {}).get("title"), title)
        check(f"{xml.name}: title names the programme",
              title == f"Void News: {PROGRAMME.get(edition)}", title)
    layout = LAYOUT_TSX.read_text(encoding="utf-8")
    for edition, title in titles.items():
        check(f"layout.tsx advertises {edition} under the same title",
              f'url: "/podcast-{edition}.xml", title: "{title}"' in layout, title)
    if DIST_MD.exists():
        doc = DIST_MD.read_text(encoding="utf-8")
        for edition, title in titles.items():
            check(f"PODCAST-DISTRIBUTION.md names {edition} as {title!r}", title in doc)
    for name in ("Void Weekly", "Void History", "void --"):
        check(f"no feed says {name!r}",
              not any(name in xml.read_text(encoding="utf-8") for _, xml, _ in feeds()))


# ---------------------------------------------------------------------------
# 3. Committed files
# ---------------------------------------------------------------------------

def test_covers():
    print("\nP-T05  Each feed's cover exists, is square, and says the right thing (F-2)")
    for edition, xml, channel in feeds():
        itunes = channel.find(f"{ITUNES}image")
        href = itunes.get("href") if itunes is not None else ""
        check(f"{xml.name}: itunes:image present", bool(href), href)
        rss_image = channel.find("image")
        check(f"{xml.name}: RSS <image> present beside itunes:image (E-19)",
              rss_image is not None and (rss_image.findtext("url") or "") == href
              and (rss_image.findtext("title") or "") == (channel.findtext("title") or ""),
              "" if rss_image is None else (rss_image.findtext("url") or ""))
        name = href.rsplit("/", 1)[-1]
        check(f"{xml.name}: cover is its own ({name})", name == f"podcast-cover-{edition}.jpg", name)
        jpg = PUBLIC / name
        check(f"{name} exists in frontend/public", jpg.is_file())
        if not jpg.is_file():
            continue
        size = jpeg_size(jpg)
        check(f"{name} is a square JPEG between 1400 and 3000 px",
              size is not None and size[0] == size[1] and 1400 <= size[0] <= 3000, str(size))
        check(f"{name} is under 512 KB (Apple's limit)", jpg.stat().st_size < 512_000,
              f"{jpg.stat().st_size:,} bytes")
        svg = jpg.with_suffix(".svg")
        check(f"{svg.name} exists beside the JPG", svg.is_file())
        if not svg.is_file():
            continue
        text = svg_text(svg)
        check(f"{svg.name}: no '--'", "--" not in text, text)
        check(f"{svg.name}: no source count", not re.search(r"\d[\d,]*\s*sources", text, re.I), text)
        check(f"{svg.name}: no edition name", "WORLD BRIEF" not in text.upper(), text)
        check(f"{svg.name}: no lowercase 'void'", not re.search(r"\bvoid\b", text), text)
        check(f"{svg.name}: reads VOID NEWS", "VOID NEWS" in text, text)
        check(f"{svg.name}: names the programme", PROGRAMME[edition] in text, text)
    check("no US cover left in frontend/public (E-19)",
          not list(PUBLIC.glob("podcast-cover-us.*")) and not (PUBLIC / "podcast-us.xml").exists())


def test_descriptions():
    print("\nP-T06  Every item description ends a sentence (F-12)")
    for edition, xml, channel in feeds():
        items = channel.findall("item")
        check(f"{xml.name}: carries at least one item", bool(items), str(len(items)))
        bad = []
        for item in items:
            for tag in ("description", f"{ITUNES}summary"):
                text = (item.findtext(tag) or "").strip()
                if text and not text.endswith(TERMINAL):
                    bad.append((item.findtext("title"), tag.replace(ITUNES, "itunes:"), text[-40:]))
        check(f"{xml.name}: every description and summary ends in terminal punctuation",
              not bad, "; ".join(f"{t!r} {tag}: ...{tail!r}" for t, tag, tail in bad[:3]))
        joined = [item for item in items
                  if re.search(r"[a-z]\s+On [A-Z][a-z]+ \d", item.findtext("description") or "")]
        check(f"{xml.name}: no subtitle runs into its summary",
              not joined, "; ".join((i.findtext("title") or "")[:40] for i in joined[:3]))
        dashes = xml.read_text(encoding="utf-8")
        check(f"{xml.name}: no em or en dash",
              "—" not in dashes and "–" not in dashes)


def test_weekly_feed_matches_archive():
    print("\nP-T07  The weekly item is the served issue (E-04, E-18)")
    xml = PUBLIC / "podcast-weekly.xml"
    if not xml.exists() or not ISSUES_JSON.exists():
        check("weekly feed and archive both present", False)
        return
    rows = [r for r in json.loads(ISSUES_JSON.read_text(encoding="utf-8"))
            if isinstance(r, dict) and r.get("audio_url")]
    rows.sort(key=lambda r: r.get("week_start") or "", reverse=True)
    if not rows:
        check("an archive issue carries audio", False)
        return
    newest = rows[0]
    channel = ET.parse(xml).getroot().find("channel")
    items = channel.findall("item")
    if not items:
        check("weekly feed carries an item", False)
        return
    first = items[0]
    want = pfg._episode_title(pfg._weekly_episode(newest))
    got = (first.findtext("title") or "").strip()
    check("first item title is what the archive of record produces", got == want,
          f"feed {got!r} vs archive {want!r}")
    check("item title carries the served cover headline",
          (newest.get("cover_headline") or "") in got, got)
    check("item title carries the page's issue label",
          got.startswith(issue_label(newest.get("issue_number"))), got)
    enclosure = first.find("enclosure")
    check("enclosure is the archive's audio_url",
          enclosure is not None
          and enclosure.get("url") == pfg._clean_url(newest.get("audio_url") or ""),
          "" if enclosure is None else enclosure.get("url") or "")
    check("no item is numbered by the epoch count",
          not any("Issue #" in (i.findtext("title") or "") for i in items))


if __name__ == "__main__":
    test_history_description()
    test_cover_lookup()
    test_issue_label()
    test_channel_titles()
    test_covers()
    test_descriptions()
    test_weekly_feed_matches_archive()
    if _failures:
        print(f"\n{len(_failures)} podcast feed check(s) failed:")
        for f in _failures:
            print(f"  - {f}")
        sys.exit(1)
    print("\nall podcast feed checks passed")
