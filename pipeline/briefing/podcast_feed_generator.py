"""
Podcast RSS feed generator for void --onair.

Generates one RSS 2.0 + iTunes namespace XML feed per edition (world, us).
Queries ``daily_briefs`` for recent episodes with audio, writes static XML
files to ``frontend/public/`` so they are served by GitHub Pages.

Podcast directories (Apple Podcasts, Spotify, etc.) poll the feed URL and
ingest new episodes automatically.

Pure stdlib Python — no external dependencies.
"""

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

PODCAST_EDITIONS = ["world", "us"]
EPISODES_PER_FEED = 50

# Base URL where GitHub Pages serves the frontend.
# Override with PODCAST_SITE_URL env var if using a custom domain.
SITE_URL = os.environ.get(
    "PODCAST_SITE_URL", "https://aacrit.github.io/void--news"
)

SHOW_META = {
    "world": {
        "title": "void --onair: World Brief",
        "description": (
            "Twice-daily world news briefing. Two journalists, 419 curated sources, "
            "every story scored for bias on six axes. No ads. No paywall."
        ),
    },
    "us": {
        "title": "void --onair: US Brief",
        "description": (
            "Twice-daily US news briefing. Two journalists, 150 curated US sources, "
            "every story scored for bias on six axes. No ads. No paywall."
        ),
    },
}

ITUNES_NS = "http://www.itunes.com/dtds/podcast-1.0.dtd"
PODCAST_NS = "https://podcastindex.org/namespace/1.0"
CONTENT_NS = "http://purl.org/rss/1.0/modules/content/"

AUTHOR = "void --news"
LANGUAGE = "en"
CATEGORY = "News"
SUBCATEGORY = "Daily News"
CONTACT_EMAIL = os.environ.get("PODCAST_EMAIL", "void.news.dev@gmail.com")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rfc2822(dt: datetime) -> str:
    """Convert a datetime to RFC 2822 format for RSS <pubDate>."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return formatdate(mktime(dt.timetuple()), usegmt=True)


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


def _episode_title(brief: dict) -> str:
    """Build a descriptive episode title from the brief data."""
    created = brief.get("created_at", "")
    # Parse ISO timestamp → readable date
    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
        date_str = dt.strftime("%B %-d, %Y")
        slot = "Morning" if dt.hour < 12 else "Evening"
    except (ValueError, AttributeError):
        date_str = created[:10] if created else "Unknown"
        slot = ""

    headline = brief.get("tldr_headline", "")
    edition_label = brief.get("edition", "world").upper()

    if headline:
        return f"{headline} — {edition_label} {slot} Brief"
    return f"{edition_label} Brief — {date_str} ({slot})"


def _episode_description(brief: dict) -> str:
    """Build episode description from TL;DR text."""
    tldr = brief.get("tldr_text", "")
    edition = brief.get("edition", "world")
    # Truncate to ~4000 chars (Apple limit) and add deep-link
    desc = tldr[:3800] if tldr else "Today's news briefing."
    desc += f"\n\nFull bias analysis and source spectrum: {SITE_URL}/{edition}/"
    return desc


# ---------------------------------------------------------------------------
# Feed builder
# ---------------------------------------------------------------------------

def _build_feed(edition: str, episodes: list[dict]) -> bytes:
    """Build RSS 2.0 XML bytes for a single edition."""
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
    SubElement(channel, "link").text = f"{SITE_URL}/{edition}/"
    SubElement(channel, "language").text = LANGUAGE
    SubElement(channel, "description").text = meta["description"]
    SubElement(channel, "generator").text = "void --news pipeline"
    SubElement(channel, "lastBuildDate").text = _rfc2822(datetime.now(timezone.utc))

    # iTunes metadata
    SubElement(channel, f"{{{ITUNES_NS}}}author").text = AUTHOR
    owner = SubElement(channel, f"{{{ITUNES_NS}}}owner")
    SubElement(owner, f"{{{ITUNES_NS}}}name").text = AUTHOR
    SubElement(owner, f"{{{ITUNES_NS}}}email").text = CONTACT_EMAIL

    cover_url = f"{SITE_URL}/podcast-cover-{edition}.jpg"
    SubElement(channel, f"{{{ITUNES_NS}}}image", {"href": cover_url})

    cat = SubElement(channel, f"{{{ITUNES_NS}}}category", {"text": CATEGORY})
    SubElement(cat, f"{{{ITUNES_NS}}}category", {"text": SUBCATEGORY})

    SubElement(channel, f"{{{ITUNES_NS}}}explicit").text = "false"
    SubElement(channel, f"{{{ITUNES_NS}}}type").text = "episodic"

    # Podcast namespace
    SubElement(channel, f"{{{PODCAST_NS}}}locked").text = "no"

    # Episodes
    for i, brief in enumerate(episodes):
        audio_url = brief.get("audio_url", "")
        if not audio_url:
            continue

        # Strip cache-bust param for podcast enclosure (some apps treat ?v= as different URL)
        clean_url = audio_url.split("?")[0] if "?" in audio_url else audio_url

        item = SubElement(channel, "item")
        SubElement(item, "title").text = _episode_title(brief)
        SubElement(item, "description").text = _episode_description(brief)

        file_size = str(brief.get("audio_file_size", 0))
        SubElement(item, "enclosure", {
            "url": clean_url,
            "length": file_size,
            "type": "audio/mpeg",
        })

        # Use the brief's UUID as a stable, unique GUID
        guid = brief.get("id", f"{edition}-{i}")
        SubElement(item, "guid", {"isPermaLink": "false"}).text = guid

        # Publication date
        created = brief.get("created_at", "")
        try:
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            SubElement(item, "pubDate").text = _rfc2822(dt)
        except (ValueError, AttributeError):
            pass

        # iTunes episode metadata
        duration = brief.get("audio_duration_seconds")
        SubElement(item, f"{{{ITUNES_NS}}}duration").text = _itunes_duration(duration)
        SubElement(item, f"{{{ITUNES_NS}}}episodeType").text = "full"
        SubElement(item, f"{{{ITUNES_NS}}}summary").text = (
            brief.get("tldr_text", "")[:3999]
        )

    # Serialize with XML declaration
    xml_bytes = tostring(rss, encoding="unicode", xml_declaration=False)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n' + xml_bytes).encode("utf-8")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_podcast_feeds(editions: list[str] | None = None) -> dict[str, str]:
    """Generate podcast RSS feeds for the given editions.

    Queries ``daily_briefs`` from Supabase, builds XML, writes to
    ``frontend/public/podcast-{edition}.xml``.

    Returns dict mapping edition → output file path.
    """
    editions = editions or PODCAST_EDITIONS

    try:
        from utils.supabase_client import supabase
    except ImportError:
        print("  [podcast] Supabase client not available — skipping feed generation")
        return {}

    output_dir = Path(__file__).parent.parent.parent / "frontend" / "public"
    output_dir.mkdir(parents=True, exist_ok=True)

    results: dict[str, str] = {}

    for edition in editions:
        try:
            resp = supabase.table("daily_briefs").select(
                "id,edition,created_at,tldr_headline,tldr_text,"
                "audio_url,audio_duration_seconds,audio_file_size,audio_voice_label"
            ).eq(
                "edition", edition
            ).not_.is_(
                "audio_url", "null"
            ).order(
                "created_at", desc=True
            ).limit(EPISODES_PER_FEED).execute()

            episodes = resp.data if resp.data else []
            if not episodes:
                print(f"  [podcast] No audio episodes for {edition} — skipping")
                continue

            xml_bytes = _build_feed(edition, episodes)
            out_path = output_dir / f"podcast-{edition}.xml"
            out_path.write_bytes(xml_bytes)

            results[edition] = str(out_path)
            print(f"  [podcast] {edition}: {len(episodes)} episodes → {out_path.name}")

        except Exception as e:
            print(f"  [warn][podcast] Feed generation failed for {edition}: {e}")

    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Generating podcast feeds...")
    results = generate_podcast_feeds()
    for ed, path in results.items():
        print(f"  {ed}: {path}")
    if not results:
        print("  No feeds generated.")
