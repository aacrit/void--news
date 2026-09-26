#!/usr/bin/env python3
"""Desk furniture must not reach the clusterer.

A newsroom's own scaffolding carries no event, so the clusterer has nothing to
place it by and it lands wherever the TF-IDF noise points. The 2026-09-06 feed
shipped "Morning recap" inside the Trump / Pickaxe Mountain cluster,
"Saturday's Final Word" inside a murder trial, and a local paper's TV listing
inside a BYU football card.

The keep list is the point of this file. The rule has to be narrow enough that
a real story whose headline happens to contain one of these words survives:
"Iran war latest: Iranian oil tanker targeted in US strike" is a real story
with a real headline after the colon.

Run: python pipeline/validation/test_desk_furniture_filter.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from categorizer.newsworthiness import is_evergreen_junk, newsworthiness  # noqa: E402

_DROP = [
    "Morning recap",
    "Saturday's Final Word",
    "Evening roundup",
    "Today's Briefing",
    "The Weekend Digest",
    "News rundown",
    "Sports on the air: Here's what games are on TV and radio for the week of Sept. 6-12",
    # Every weekday, not just the weekend. "Tuesday's Final Word" reached the
    # Iran strike cluster on the 2026-09-09 production feed because the first
    # version of this rule named only saturday and sunday.
    "Tuesday's Final Word",
    "Monday Briefing",
    "Wednesday roundup",
    "Thursday recap",
    "Friday's Final Word",
    "Nightly Digest",
    # Also reached a cluster on 09-09.
    "Today in Germany: A roundup of the latest news on Wednesday",
    # The three members of the rank-17 card on the 2026-09-09 feed: a service
    # guide, an affiliate-commerce page and a photo gallery, clustered on the
    # word "hair" and published as news with a cosmetic clinic quoted in the
    # summary. Dropping these three leaves the cluster below the 3-source
    # display minimum, so the card cannot form.
    "The dos and don'ts of body hair: Experts reveal how to flaunt your fuzz "
    "without looking scruffy as stars make it a red carpet trend",
    "Alec Baldwin refreshes his hair color and more star snaps",
    "In pictures: the week that was",
    "Photos of the day",
    "What to watch on TV tonight",
]

_KEEP = [
    # a real story with a real headline after the colon
    "Iran war latest: Iranian oil tanker targeted in US strike, says state media",
    # a recap OF something specific, not the desk's own recap slot
    "Recap: Every goal from Liverpool's 4-3 win over Newcastle",
    "Election night roundup shows AfD leading in three eastern states",
    # "briefing" as an event
    "Pentagon briefing turns hostile as reporters press on leak inquiry",
    "Trump's morning press briefing cut short after two questions",
    # hard news that merely mentions television
    "Egyptian TV Presenter Sarah Khalifa Sentenced to Death in Drug Case",
    "Passenger Duct-Taped to Seat After Mid-Flight Outburst Identified",
    # the words appear, but the title is long and carries an event
    "Government headlines new investment package for coastal towns",
    # A weekday name in a real headline must survive. These are the cases the
    # weekday addition could plausibly have broken.
    "Friday deadline passes as union rejects final offer",
    "Wednesday trading halted after circuit breaker triggers",
    "Sunday Times investigation reveals offshore accounts",
    "Election night roundup shows AfD leading in three eastern states",
]


# (title, url) cases where the URL carries the signal.
_DROP_BY_URL = [
    ("Does it feel like your hair is always greasy? Here's why it could be happening",
     "https://www.nbcnews.com/select/shopping/why-hair-greasy-how-fix-rcna596612"),
]

# An agency dateline is three commas of metadata before the headline begins.
# Without stripping it, the comma-catalog rule reads a real AFP story as a
# catalog on its provenance alone. This was one of exactly two false positives
# when the filter was swept over the 955 article titles behind the 09-09 feed.
_KEEP_DATELINED = [
    "Washington, United States, Sept 8, 2026 (AFP) - Smithsonian secretary to "
    "retire as Trump pressures institution",
    "PARIS, Sept 9, 2026 (AFP) - French unions call third strike over pensions",
    "NEW DELHI, Sep 9, 2026 (PTI) - Parliament passes finance bill after debate",
]

# The catalog rule must still catch an actual catalog.
_DROP_CATALOG = [
    "Latest Stock and Share Market News, Sensex, Nifty, NSE, BSE Live News",
    "Gold rate today, silver price, forex, commodities, market wrap",
]


def test_commerce_and_gallery_urls_are_dropped():
    for t, u in _DROP_BY_URL:
        assert is_evergreen_junk({"title": t, "url": u}) is True, f"should DROP: {u!r}"


def test_agency_datelines_survive():
    for t in _KEEP_DATELINED:
        v = newsworthiness({"title": t})
        assert v["is_junk"] is False, (
            f"agency dateline read as a catalog: {t[:60]!r} {v['signals']}")


def test_real_catalogs_still_drop():
    for t in _DROP_CATALOG:
        assert is_evergreen_junk({"title": t}) is True, f"should DROP: {t!r}"


def test_furniture_is_dropped():
    for t in _DROP:
        assert is_evergreen_junk({"title": t}) is True, f"should DROP: {t!r}"


def test_real_stories_are_kept():
    for t in _KEEP:
        v = newsworthiness({"title": t})
        assert v["is_junk"] is False, (
            f"should KEEP but dropped: {t!r} (signals {v['signals']})")


def test_furniture_survives_a_news_verb():
    # A news verb raises the bar to VETO_THRESHOLD, so furniture weighted 3
    # must NOT drop a title that also reads as an event. This is the guard
    # against the rule ever eating a real story.
    v = newsworthiness({"title": "Morning recap: 12 killed as floods hit Nepal"})
    assert v["is_junk"] is False, "a recap OF a real event must survive"


def test_missing_title_fails_open():
    assert is_evergreen_junk({"title": ""}) is False
    assert is_evergreen_junk({}) is False


def _run() -> int:
    failures = 0
    for fn in (test_furniture_is_dropped,
               test_real_stories_are_kept,
               test_furniture_survives_a_news_verb,
               test_commerce_and_gallery_urls_are_dropped,
               test_agency_datelines_survive,
               test_real_catalogs_still_drop,
               test_missing_title_fails_open):
        try:
            fn()
            print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {fn.__name__}: {e}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(_run())
