"""
Podcast RSS feed generator for Void News audio.

Three shows, three feeds, all written as static XML into ``frontend/public/``
so the Pages CDN serves them next to the MP3s:

  podcast-world.xml    Void News: On Air        daily, from ``daily_briefs``
  podcast-weekly.xml   Void Weekly: The Argument Sundays, from the deploy tree
  podcast-history.xml  Void News: History       one event per episode, from
                                                 the history audio manifest

Podcast directories (Apple Podcasts, Spotify, etc.) poll the feed URL and
ingest new episodes automatically. Everything they need is in the item:
the enclosure URL, its byte length, the duration and a GUID that never changes.

An enclosure that 404s gets a show rejected by Apple outright, so the daily
and weekly feeds list only episodes whose MP3 is present in the working tree
(``_write_audio_static`` rotates the daily edition down to the last two dated
files, which is what left seven of nine world items pointing at nothing on
2026-09-20). History MP3s are gitignored and fetched from a GitHub Release at
deploy, so that feed trusts the manifest instead.

Pure stdlib Python plus PyYAML for the event files. No database is touched
unless the daily feed is asked for; the shim import is lazy for that reason,
so ``--history --weekly`` runs without VOID_SQLITE_PATH.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from email.utils import formatdate
from pathlib import Path
from time import mktime
from xml.etree.ElementTree import Element, SubElement, tostring, register_namespace

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# "us" was retired with Supabase Storage: its MP3s lived on the dead host and
# nothing has written one since. An edition is only generated when at least
# one of its MP3s exists under frontend/public/audio/<edition>/, so adding it
# back here does nothing until audio ships again.
PODCAST_EDITIONS = ["world"]
EPISODES_PER_FEED = 50

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PUBLIC_DIR = REPO_ROOT / "frontend" / "public"
AUDIO_DIR = PUBLIC_DIR / "audio"

# Base URL of the live site (Cloudflare Pages, root basePath). audio_url is
# site-relative since the 2026-09 static move, so enclosures are SITE_URL +
# audio_url. Override with PODCAST_SITE_URL.
SITE_URL = os.environ.get(
    "PODCAST_SITE_URL", "https://news.voidvision.org"
).rstrip("/")

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
PODCAST_NS = "https://podcastindex.org/namespace/1.0"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"

AUTHOR = "Void News"
GENERATOR = "Void News pipeline"
LANGUAGE = "en"
CONTACT_EMAIL = os.environ.get("PODCAST_EMAIL", "void.news.dev@gmail.com")

# Cover art. Apple wants 1400 to 3000 px square JPG or PNG; the world cover
# is 3000x3000. The weekly and history SVGs exist next to it but this sandbox
# has no renderer, so until their JPGs are drawn `_cover_for` falls back to
# the world art (a feed pointing at a 404 is rejected). Render with:
#   node brand/ci/render_svg.mjs jobs.json   (jobs: {svg, out, width: 3000})
# then convert the PNG to JPG under 512 KB and drop it in frontend/public/.
SHOW_META = {
    "world": {
        "title": "Void News: On Air",
        "link": f"{SITE_URL}/onair/",
        "label": "On Air",
        "category": "News",
        "subcategory": "Daily News",
        "description": (
            "The daily radio edition of Void News: the day's top stories read "
            "for the ear, then the editorial. Every story scored for bias on "
            "six axes, both the outlet and its words. No ads. No paywall."
        ),
    },
    "weekly": {
        "title": "Void Weekly: The Argument",
        "link": f"{SITE_URL}/weekly/",
        "label": "The Argument",
        "category": "News",
        # A weekly magazine listed under "Daily News" is wrong in a public
        # directory.
        "subcategory": "News Commentary",
        "description": (
            "The Sunday edition of Void News, read by three voices. The week's "
            "cover story, then the two columnists who disagree about it, "
            "reading their own published words at each other across a held "
            "pause. Then what each of them leaves out, the week's coverage "
            "measured, and the question it leaves open. No ads. No paywall."
        ),
    },
    "history": {
        "title": "Void News: History",
        "link": f"{SITE_URL}/history/",
        "label": "History",
        "category": "History",
        "subcategory": None,
        "description": (
            "One event per episode, about a quarter of an hour each. What "
            "happened, who said what at the time, and how the accounts still "
            "differ. Read from the written record, every claim sourced. "
            "No ads. No paywall."
        ),
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rfc2822(dt: datetime) -> str:
    """Convert a datetime to RFC 2822 format for RSS <pubDate>."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return formatdate(mktime(dt.timetuple()), usegmt=True)


def _parse_iso(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _itunes_duration(seconds: float | None) -> str:
    """Convert seconds to HH:MM:SS or MM:SS for <itunes:duration>."""
    if not seconds:
        return "00:00"
    total = int(seconds)
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _clean_url(audio_url: str) -> str:
    """Absolute enclosure URL with the cache-bust query stripped.

    Some apps treat ?v= as a different episode, and the GUID is what should
    carry identity anyway.
    """
    clean = audio_url.split("?", 1)[0]
    if clean.startswith("/"):
        clean = f"{SITE_URL}{clean}"
    return clean


def _local_audio_path(clean_url: str) -> Path | None:
    """Map an absolute enclosure URL back to its file under frontend/public."""
    prefix = f"{SITE_URL}/"
    if not clean_url.startswith(prefix):
        return None
    rel = clean_url[len(prefix):]
    if not rel or ".." in rel.split("/"):
        return None
    return PUBLIC_DIR / rel


def _sanitize(text: str) -> str:
    """The shared editorial sanitiser (no em dashes, no significance words),
    with a dash-only fallback when the utils package is not importable."""
    if not text:
        return ""
    try:
        from utils.prohibited_terms import sanitize_editorial_text
        return sanitize_editorial_text(text) or ""
    except Exception:
        for dash in ("\u2014", "\u2013"):
            text = text.replace(f" {dash} ", ", ").replace(dash, ", ")
        return text


def _cover_for(edition: str) -> str:
    """Absolute cover URL. Own art when its JPG exists, the world cover
    otherwise (see the SHOW_META comment for the render step)."""
    own = f"podcast-cover-{edition}.jpg"
    if (PUBLIC_DIR / own).exists():
        return f"{SITE_URL}/{own}"
    return f"{SITE_URL}/podcast-cover-world.jpg"


def _episode_title(brief: dict) -> str:
    """Build a descriptive episode title from the brief data."""
    edition = brief.get("edition", "world")
    label = SHOW_META.get(edition, SHOW_META["world"])["label"]
    dt = _parse_iso(brief.get("created_at", ""))
    if dt is not None:
        date_str = dt.strftime("%B %-d, %Y")
    else:
        created = brief.get("created_at") or ""
        date_str = created[:10] if created else "Undated"

    headline = (brief.get("tldr_headline") or "").strip()
    if headline:
        return f"{headline}: {label}, {date_str}"
    return f"{label}: {date_str}"


def _episode_description(brief: dict) -> str:
    """Build episode description from TL;DR text."""
    tldr = brief.get("tldr_text", "")
    edition = brief.get("edition", "world")
    link = SHOW_META.get(edition, SHOW_META["world"])["link"]
    # Truncate to ~4000 chars (Apple limit) and add deep-link
    desc = tldr[:3800] if tldr else "Today's news briefing."
    desc += f"\n\nFull bias analysis and source spectrum: {link}"
    return desc


# ---------------------------------------------------------------------------
# Feed builder
# ---------------------------------------------------------------------------

def _channel(edition: str) -> tuple[Element, Element]:
    """The <rss><channel> skeleton every show shares."""
    # Register namespaces so ElementTree uses itunes:/podcast: prefixes
    # instead of auto-generated ns0:/ns1: (critical for Apple/Spotify parsing)
    register_namespace("itunes", ITUNES_NS)
    register_namespace("podcast", PODCAST_NS)
    register_namespace("content", CONTENT_NS)

    meta = SHOW_META.get(edition, SHOW_META["world"])

    rss = Element("rss", {"version": "2.0"})
    channel = SubElement(rss, "channel")

    # Channel-level metadata
    SubElement(channel, "title").text = meta["title"]
    SubElement(channel, "link").text = meta["link"]
    SubElement(channel, "language").text = LANGUAGE
    SubElement(channel, "description").text = meta["description"]
    SubElement(channel, "generator").text = GENERATOR
    SubElement(channel, "lastBuildDate").text = _rfc2822(datetime.now(timezone.utc))

    # iTunes metadata
    SubElement(channel, f"{{{ITUNES_NS}}}author").text = AUTHOR
    owner = SubElement(channel, f"{{{ITUNES_NS}}}owner")
    SubElement(owner, f"{{{ITUNES_NS}}}name").text = AUTHOR
    SubElement(owner, f"{{{ITUNES_NS}}}email").text = CONTACT_EMAIL
    SubElement(channel, f"{{{ITUNES_NS}}}image", {"href": _cover_for(edition)})

    cat = SubElement(channel, f"{{{ITUNES_NS}}}category", {"text": meta["category"]})
    if meta.get("subcategory"):
        SubElement(cat, f"{{{ITUNES_NS}}}category", {"text": meta["subcategory"]})

    SubElement(channel, f"{{{ITUNES_NS}}}explicit").text = "false"
    SubElement(channel, f"{{{ITUNES_NS}}}type").text = "episodic"

    # Podcast namespace
    SubElement(channel, f"{{{PODCAST_NS}}}locked").text = "no"
    return rss, channel


def _serialize(rss: Element) -> bytes:
    xml_text = tostring(rss, encoding="unicode", xml_declaration=False)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n' + xml_text).encode("utf-8")


def _playable(episodes: list[dict], edition: str) -> list[dict]:
    """Keep the episodes whose MP3 is in the working tree, one per URL.

    The rotation in ``_write_audio_static`` keeps the last two dated files,
    and a brief row can carry a URL that has since been rotated out (or the
    same URL as a later re-run of the same slot). Order is preserved, so with
    rows newest-first the first row wins a duplicate.
    """
    seen: set[str] = set()
    kept: list[dict] = []
    for brief in episodes:
        audio_url = brief.get("audio_url") or ""
        if not audio_url:
            continue
        clean = _clean_url(audio_url)
        if clean in seen:
            continue
        local = _local_audio_path(clean)
        if local is None or not local.is_file():
            continue
        seen.add(clean)
        kept.append(brief)
    if len(kept) != len(episodes):
        print(f"  [podcast] {edition}: {len(episodes) - len(kept)} of "
              f"{len(episodes)} rows dropped (no local MP3 or duplicate URL)")
    return kept


def _build_feed(edition: str, episodes: list[dict]) -> bytes:
    """Build RSS 2.0 XML bytes for a daily or weekly edition."""
    rss, channel = _channel(edition)

    for i, brief in enumerate(episodes):
        audio_url = brief.get("audio_url", "")
        if not audio_url:
            continue
        clean_url = _clean_url(audio_url)

        item = SubElement(channel, "item")
        SubElement(item, "title").text = _episode_title(brief)
        SubElement(item, "description").text = _episode_description(brief)

        file_size = str(brief.get("audio_file_size") or 0)
        SubElement(item, "enclosure", {
            "url": clean_url,
            "length": file_size,
            "type": "audio/mpeg",
        })

        # Use the brief's UUID as a stable, unique GUID
        guid = brief.get("id") or f"{edition}-{i}"
        SubElement(item, "guid", {"isPermaLink": "false"}).text = str(guid)

        dt = _parse_iso(brief.get("created_at", ""))
        if dt is not None:
            SubElement(item, "pubDate").text = _rfc2822(dt)

        # iTunes episode metadata
        duration = brief.get("audio_duration_seconds")
        SubElement(item, f"{{{ITUNES_NS}}}duration").text = _itunes_duration(duration)
        SubElement(item, f"{{{ITUNES_NS}}}episodeType").text = "full"
        SubElement(item, f"{{{ITUNES_NS}}}summary").text = (
            (brief.get("tldr_text") or "")[:3999]
        )

        # Podcasting 2.0 chapters: the radio show writes a JSON sidecar next to
        # the MP3 (<stem>.chapters.json). Apple reads the ID3 CHAP frames instead.
        chapters = brief.get("audio_chapters")
        if isinstance(chapters, str):
            try:
                chapters = json.loads(chapters)
            except (ValueError, TypeError):
                chapters = None
        # The weekly archive row does not carry audio_chapters, but the
        # sidecar is committed next to the MP3, so its presence counts too.
        if clean_url.endswith(".mp3"):
            sidecar = _local_audio_path(clean_url[:-4] + ".chapters.json")
            if chapters or (sidecar is not None and sidecar.is_file()):
                SubElement(item, f"{{{PODCAST_NS}}}chapters", {
                    "url": clean_url[:-4] + ".chapters.json",
                    "type": "application/json+chapters",
                })

    return _serialize(rss)


# ---------------------------------------------------------------------------
# Public API: the daily feed
# ---------------------------------------------------------------------------

def generate_podcast_feeds(editions: list[str] | None = None) -> dict[str, str]:
    """Generate podcast RSS feeds for the given editions.

    Queries ``daily_briefs`` through the SQLite shim, keeps the rows whose MP3
    exists under ``frontend/public/audio/<edition>/``, writes
    ``frontend/public/podcast-{edition}.xml``.

    Returns dict mapping edition to output file path.
    """
    editions = editions or PODCAST_EDITIONS

    # Lazy: the shim raises EnvironmentError without VOID_SQLITE_PATH, and
    # the weekly and history feeds must not need it.
    try:
        from utils.supabase_client import supabase
    except (ImportError, EnvironmentError) as e:
        print(f"  [podcast] database client not available, skipping daily feeds: {e}")
        return {}

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, str] = {}

    for edition in editions:
        try:
            if not any((AUDIO_DIR / edition).glob("*.mp3")):
                print(f"  [podcast] no local MP3 under audio/{edition}/, skipping")
                continue

            resp = supabase.table("daily_briefs").select(
                "id,edition,created_at,tldr_headline,tldr_text,"
                "audio_url,audio_duration_seconds,audio_file_size,audio_voice_label,"
                "audio_chapters"
            ).eq(
                "edition", edition
            ).not_.is_(
                "audio_url", "null"
            ).order(
                "created_at", desc=True
            ).limit(EPISODES_PER_FEED).execute()

            episodes = _playable(resp.data if resp.data else [], edition)
            if not episodes:
                print(f"  [podcast] No playable audio episodes for {edition}, skipping")
                continue

            xml_bytes = _build_feed(edition, episodes)
            out_path = PUBLIC_DIR / f"podcast-{edition}.xml"
            out_path.write_bytes(xml_bytes)

            results[edition] = str(out_path)
            print(f"  [podcast] {edition}: {len(episodes)} episodes -> {out_path.name}")

        except Exception as e:
            print(f"  [warn][podcast] Feed generation failed for {edition}: {e}")

    return results


# ---------------------------------------------------------------------------
# The weekly feed
#
# It reads the DEPLOY TREE, not the database, and that is not a shortcut.
# `weekly-digest.yml` restores the state DB and never saves it back, so the
# weekly row is written into a database that is discarded when the job ends.
# `build-data/weekly-issues.json` is the archive of record, the same file the
# prerendered /weekly/<week> pages read, which makes it the only place a back
# catalogue of episodes actually exists.
#
# `audio_url`, duration, file size, cover and `created_at` were already every
# field an <enclosure> needs, sitting in that file, with nothing reading them.
# ---------------------------------------------------------------------------

WEEKLY_ISSUES = REPO_ROOT / "frontend" / "build-data" / "weekly-issues.json"


def _weekly_episode(issue: dict) -> dict:
    """Map an issue onto the episode shape `_build_feed` already consumes."""
    no = issue.get("issue_number")
    headline = (issue.get("cover_headline") or "").strip()
    week = issue.get("week_start") or ""
    title = f"Issue #{no}: {headline}" if headline else f"Issue #{no}"
    body = (issue.get("opinion_text") or "").strip()
    covers = [c for c in (issue.get("cover_text") or []) if isinstance(c, dict)]
    if covers and covers[0].get("text"):
        body = covers[0]["text"].strip()
    return {
        "id": issue.get("id"),
        "edition": "weekly",
        "created_at": issue.get("created_at") or f"{week}T12:00:00+00:00",
        "tldr_headline": title,
        "tldr_text": body,
        "audio_url": issue.get("audio_url"),
        "audio_duration_seconds": issue.get("audio_duration_seconds"),
        "audio_file_size": issue.get("audio_file_size"),
        "audio_voice_label": issue.get("audio_voice_label"),
        "audio_chapters": issue.get("audio_chapters"),
    }


def generate_weekly_podcast_feed() -> str | None:
    """Write frontend/public/podcast-weekly.xml from the archive of record."""
    if not WEEKLY_ISSUES.exists():
        print("  [podcast] no weekly archive, skipping the Sunday feed")
        return None
    try:
        rows = json.loads(WEEKLY_ISSUES.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  [warn][podcast] weekly archive unreadable: {e}")
        return None
    issues = [r for r in rows if isinstance(r, dict) and r.get("audio_url")]
    if not issues:
        print("  [podcast] no weekly issue carries audio yet, skipping")
        return None
    issues.sort(key=lambda r: r.get("week_start") or "", reverse=True)
    episodes = _playable([_weekly_episode(i) for i in issues[:EPISODES_PER_FEED]],
                         "weekly")
    if not episodes:
        print("  [podcast] no weekly MP3 in the working tree, skipping")
        return None

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    out = PUBLIC_DIR / "podcast-weekly.xml"
    out.write_bytes(_build_feed("weekly", episodes))
    print(f"  [podcast] weekly: {len(episodes)} episodes -> {out.name}")
    return str(out)


# ---------------------------------------------------------------------------
# The History feed
#
# `frontend/public/data/history-audio.json` is the manifest `publish_audio.py`
# writes: one entry per rendered episode with the site-relative MP3 URL, its
# byte length, duration, chapters and the publish time. The MP3s themselves
# are gitignored and fetched from a GitHub Release at deploy, so the working
# tree is NOT the test of presence here; the manifest is. Titles and the
# episode description come from the event's YAML in data/history/events.
# ---------------------------------------------------------------------------

HISTORY_AUDIO = PUBLIC_DIR / "data" / "history-audio.json"
HISTORY_EVENTS = REPO_ROOT / "data" / "history" / "events"


def _history_event(slug: str) -> dict:
    path = HISTORY_EVENTS / f"{slug}.yaml"
    if not path.exists():
        return {}
    try:
        import yaml
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as e:
        print(f"  [warn][podcast] history event {slug} unreadable: {e}")
        return {}


def _first_paragraph(text: str) -> str:
    for para in (text or "").split("\n"):
        para = para.strip()
        if para:
            return para
    return ""


def _history_description(event: dict, episode: dict) -> str:
    subtitle = (event.get("subtitle") or "").strip()
    lead = _first_paragraph(event.get("summary") or "")
    parts = [p for p in (subtitle, lead) if p]
    if not parts:
        parts = [episode.get("title") or ""]
    return _sanitize("\n\n".join(parts))[:3900]


def generate_history_podcast_feed() -> str | None:
    """Write frontend/public/podcast-history.xml from the audio manifest."""
    if not HISTORY_AUDIO.exists():
        print("  [podcast] no history audio manifest, skipping the History feed")
        return None
    try:
        manifest = json.loads(HISTORY_AUDIO.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  [warn][podcast] history manifest unreadable: {e}")
        return None

    episodes = manifest.get("episodes") if isinstance(manifest, dict) else None
    if not isinstance(episodes, dict) or not episodes:
        print("  [podcast] no history episode rendered yet, skipping")
        return None

    rows = []
    for slug, ep in episodes.items():
        if not isinstance(ep, dict) or not ep.get("url"):
            continue
        rows.append((slug, ep))
    rows.sort(key=lambda r: r[1].get("publishedAt") or "", reverse=True)

    rss, channel = _channel("history")
    seen: set[str] = set()
    count = 0
    for slug, ep in rows:
        clean_url = _clean_url(ep["url"])
        if clean_url in seen:
            continue
        seen.add(clean_url)
        event = _history_event(slug)
        title = (event.get("title") or ep.get("title") or slug).strip()

        item = SubElement(channel, "item")
        SubElement(item, "title").text = _sanitize(title)
        SubElement(item, "link").text = f"{SITE_URL}/history/{slug}/"
        description = _history_description(event, ep)
        SubElement(item, "description").text = description
        SubElement(item, "enclosure", {
            "url": clean_url,
            "length": str(int(ep.get("bytes") or 0)),
            "type": "audio/mpeg",
        })
        SubElement(item, "guid", {"isPermaLink": "false"}).text = f"history:{slug}"
        dt = _parse_iso(ep.get("publishedAt"))
        if dt is not None:
            SubElement(item, "pubDate").text = _rfc2822(dt)
        SubElement(item, f"{{{ITUNES_NS}}}duration").text = (
            _itunes_duration(ep.get("durationSeconds"))
        )
        SubElement(item, f"{{{ITUNES_NS}}}episodeType").text = "full"
        SubElement(item, f"{{{ITUNES_NS}}}summary").text = description
        chapters_url = ep.get("chaptersUrl")
        if chapters_url:
            SubElement(item, f"{{{PODCAST_NS}}}chapters", {
                "url": _clean_url(chapters_url),
                "type": "application/json+chapters",
            })
        elif clean_url.endswith(".mp3"):
            SubElement(item, f"{{{PODCAST_NS}}}chapters", {
                "url": clean_url[:-4] + ".chapters.json",
                "type": "application/json+chapters",
            })
        count += 1

    if not count:
        print("  [podcast] no history episode carries a URL, skipping")
        return None

    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    out = PUBLIC_DIR / "podcast-history.xml"
    out.write_bytes(_serialize(rss))
    print(f"  [podcast] history: {count} episodes -> {out.name}")
    return str(out)


# ---------------------------------------------------------------------------
# CLI entry point
#
#   python3 pipeline/briefing/podcast_feed_generator.py --history --weekly
#
# needs no database. With no flag every feed is attempted and the daily one
# is skipped, with a message, when VOID_SQLITE_PATH is unset.
# ---------------------------------------------------------------------------

def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write the Void News podcast feeds.")
    parser.add_argument("--daily", action="store_true",
                        help="podcast-world.xml from daily_briefs (needs VOID_SQLITE_PATH)")
    parser.add_argument("--weekly", action="store_true",
                        help="podcast-weekly.xml from build-data/weekly-issues.json")
    parser.add_argument("--history", action="store_true",
                        help="podcast-history.xml from data/history-audio.json")
    args = parser.parse_args(argv)
    want_all = not (args.daily or args.weekly or args.history)

    print("Generating podcast feeds...")
    results: dict[str, str] = {}
    if want_all or args.daily:
        results.update(generate_podcast_feeds())
    if want_all or args.weekly:
        weekly = generate_weekly_podcast_feed()
        if weekly:
            results["weekly"] = weekly
    if want_all or args.history:
        history = generate_history_podcast_feed()
        if history:
            results["history"] = history
    for ed, path in results.items():
        print(f"  {ed}: {path}")
    if not results:
        print("  No feeds generated.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main())
