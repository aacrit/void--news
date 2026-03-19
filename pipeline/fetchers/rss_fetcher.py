"""
RSS feed fetcher for the void --news pipeline.

Fetches articles from RSS feeds using feedparser, with parallel
execution via ThreadPoolExecutor.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import feedparser
import requests


# Maximum number of parallel feed fetches
# RSS fetching is pure I/O — 20 workers for 97 sources keeps throughput high
MAX_WORKERS = 20

# Timeout per feed in seconds
# Most healthy feeds respond in <5s; 15s catches slow CDNs without blocking
FEED_TIMEOUT = 15

# Request headers
HEADERS = {
    "User-Agent": "VoidNews/1.0 (+https://github.com/aacrit/void--news)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def _parse_published_date(entry: dict) -> str | None:
    """
    Extract and normalize the published date from an RSS entry.

    Returns:
        ISO 8601 string or None if no date found.
    """
    published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if published_parsed:
        try:
            dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
            return dt.isoformat()
        except (TypeError, ValueError):
            pass

    # Fallback: try the raw string fields
    raw = entry.get("published") or entry.get("updated")
    if raw:
        return raw

    return None


def _parse_entry(entry: dict, source: dict) -> dict:
    """
    Parse a single RSS feed entry into an article dict.

    Args:
        entry: A feedparser entry.
        source: The source dict (must have 'id' key).

    Returns:
        Dict with keys: title, url, summary, author, published_at, source_id
    """
    # Extract summary, preferring the 'summary' field, then 'description'
    summary = entry.get("summary") or entry.get("description") or ""
    # Strip HTML tags from summary (basic cleanup)
    if "<" in summary:
        from bs4 import BeautifulSoup
        summary = BeautifulSoup(summary, "html.parser").get_text(strip=True)

    # Truncate very long summaries
    if len(summary) > 1000:
        summary = summary[:997] + "..."

    return {
        "source_id": source.get("db_id") or source.get("id", ""),
        "source_slug": source.get("id", ""),
        "url": entry.get("link", ""),
        "title": entry.get("title", "Untitled"),
        "summary": summary,
        "author": entry.get("author"),
        "published_at": _parse_published_date(entry),
    }


def _fetch_single_feed(source: dict) -> list[dict]:
    """
    Fetch and parse a single RSS feed.

    Args:
        source: Source dict with at least 'id', 'rss_url', 'name'.

    Returns:
        List of parsed article dicts.
    """
    rss_url = source.get("rss_url")
    if not rss_url:
        return []

    try:
        # Fetch via requests first (handles redirects, auth, encoding better)
        resp = requests.get(rss_url, headers=HEADERS, timeout=FEED_TIMEOUT, allow_redirects=True)
        resp.raise_for_status()

        # Parse the fetched content
        feed = feedparser.parse(resp.content)

        if feed.bozo and not feed.entries:
            # Try parsing as text if content parse failed
            feed = feedparser.parse(resp.text)

        if not feed.entries:
            print(f"  [warn] No entries in feed for {source.get('name', 'unknown')} ({rss_url})")
            return []

        articles = []
        for entry in feed.entries:
            article = _parse_entry(entry, source)
            if article["url"]:
                articles.append(article)

        return articles

    except requests.exceptions.Timeout:
        print(f"  [timeout] {source.get('name', 'unknown')}: timed out after {FEED_TIMEOUT}s")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"  [http] {source.get('name', 'unknown')}: {e.response.status_code}")
        return []
    except Exception as e:
        print(f"  [error] {source.get('name', 'unknown')}: {e}")
        return []


def fetch_from_rss(sources: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Fetch articles from RSS feeds for multiple sources in parallel.

    Uses ThreadPoolExecutor with up to MAX_WORKERS (10) threads.
    Each feed has a FEED_TIMEOUT of 30 seconds.

    Args:
        sources: List of source dicts. Each must have 'id', 'rss_url', 'name'.
            Sources without an 'rss_url' are skipped.

    Returns:
        Tuple of (articles, errors):
            - articles: List of article dicts ready for database insertion.
            - errors: List of error dicts with 'source', 'error', 'timestamp'.
    """
    all_articles = []
    errors = []
    sources_with_rss = [s for s in sources if s.get("rss_url")]

    print(f"Fetching RSS from {len(sources_with_rss)} sources ({MAX_WORKERS} workers)...")

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_source = {
            executor.submit(_fetch_single_feed, source): source
            for source in sources_with_rss
        }

        for future in as_completed(future_to_source, timeout=FEED_TIMEOUT * 2):
            source = future_to_source[future]
            try:
                articles = future.result(timeout=FEED_TIMEOUT)
                all_articles.extend(articles)
                print(f"  [ok] {source.get('name', 'unknown')}: {len(articles)} articles")
            except TimeoutError:
                error_msg = f"Timeout after {FEED_TIMEOUT}s"
                print(f"  [timeout] {source.get('name', 'unknown')}: {error_msg}")
                errors.append({
                    "source": source.get("name", "unknown"),
                    "error": error_msg,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                error_msg = str(e)
                print(f"  [error] {source.get('name', 'unknown')}: {error_msg}")
                errors.append({
                    "source": source.get("name", "unknown"),
                    "error": error_msg,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    print(f"RSS fetch complete: {len(all_articles)} articles from {len(sources_with_rss)} sources")
    return all_articles, errors
