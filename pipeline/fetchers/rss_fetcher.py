"""
RSS feed fetcher for the void --news pipeline.

Fetches articles from RSS feeds using feedparser, with parallel
execution via ThreadPoolExecutor.
"""

import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone

import defusedxml
# Harden Python's stdlib XML parsers (sax, etree, expat, pulldom, etc.) against
# billion-laughs / external-entity attacks. feedparser falls back to several of
# these when its preferred parser isn't available, so we route them through
# defusedxml's safe replacements before any feed parsing happens.
defusedxml.defuse_stdlib()

import feedparser
import requests

from utils.safe_requests import safe_get

# Dead-feed quarantine (migration 051). Sources with >=5 consecutive failures
# are skipped this run; we never auto-resurrect — only a successful fetch
# (which won't happen if we skip) OR a manual /sources reset clears them.
QUARANTINE_THRESHOLD = 5


# --- Junk content filters (applied before scraping to save time) ---

# URLs that are not news articles (pagination, author pages, admin, etc.)
JUNK_URL_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r'/page/\d+',           # Pagination (slash-separated)
        r'page-\d+',            # Pagination (hyphenated, e.g. Chicago Tribune)
        r'/author/',            # Author pages
        r'/tag/',               # Tag listing pages
        r'/category/',          # Category listing pages
        r'/search\?',           # Search results
        r'/wp-admin',           # WordPress admin pages
        r'/feed/?$',            # Feed pages themselves
        r'/gallery/',           # Photo galleries (not articles)
        r'/slideshow/',         # Slideshows
    )
]

# Titles that signal non-article content
JUNK_TITLE_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r'^donate',             # Donation pages
        r'^subscribe',          # Subscription pages
        r'^sign\s*up',          # Sign up pages
        r'^sponsored[:\s]',     # Sponsored content
        r'- page \d+',          # Pagination in title
        r'page \d+.*chicago tribune',  # Chicago Tribune pagination pages
        r'^[\w\s]+ - page \d+',  # Generic "Name - Page N" pagination
        r'^developing story$',  # Generic placeholder title
        r'^newsletter',         # Non-news newsletter content
        r'^top news.*latest',   # RSS feed index pages
        r'^latest videos',      # Video index pages ("Latest Videos - CNN")
        r'^(world|europe|asia|americas?|business|sport|science)\s*[-–—]\s*', # RSS section pages ("Europe - The Economist")
        r'^photo:?\s',          # Photo captions
        r'^video:?\s',          # Video-only content
        r'^photos?:?\s',        # Photo galleries
        r'^gallery:?\s',        # Gallery pages
        r'everything you need to know about .+ day\b',  # Commerce/shopping roundups
        r'\bbest .+ deals\b',   # Shopping deal roundups
        r'\bbest .+ gifts\b',   # Gift guide roundups
        # Economist/outlet section-page entries: "Finance & economics - The Economist"
        # Catches titles that are bare category labels (1-4 words, no verb/number)
        # followed by " - <Outlet Name>" with no actual news content
        r'^[\w\s&]+\s+[-–—]\s+the\s+economist\s*$',  # "Finance & economics - The Economist"
        # Wire-service digest / roundup titles (not individual stories)
        r'\bnews\s+(?:summary|digest|wrap(?:up)?|roundup|bulletin)\b',  # "Yonhap news summary"
        r'\bdaily\s+(?:briefing|digest|roundup|bulletin|wrap)\b',       # "Daily briefing"
        r'\bmorning\s+(?:briefing|digest|roundup|bulletin)\b',          # "Morning briefing"
        r'\bevening\s+(?:briefing|digest|roundup|bulletin)\b',          # "Evening briefing"
        # Puzzle/crossword/game entries slipping through from magazine feeds
        r'\b(?:mini\s+)?crossword\b',   # "Mini crossword for Mar 19th 2026"
        r'\bobituaries?\s*[-–—]',       # "Notable obituaries - The Economist"
    )
]

# Maximum article age in days (reject stale evergreen content)
MAX_ARTICLE_AGE_DAYS = 2

# Minimum title length (catches junk like "CNN", "BTS", etc.)
MIN_TITLE_LENGTH = 10


# Patterns to strip from the beginning of RSS summaries
# Photo credits, file photo prefixes, and image attributions
_PHOTO_CREDIT_PATTERN = re.compile(
    r"^(?:FILE\s*(?:PHOTO\s*)?[-\u2014\u2013]\s*)"  # FILE - , FILE PHOTO -
    r"|^(?:(?:Photo|Image|Credit|Caption)\s*:\s*)"    # Photo: , Image: , Credit:
    r"|^(?:[\w\s,.']+\s+(?:/|via)\s+[\w\s,.]+(?:Images?|Photos?|Press|News|AFP|Reuters|AP|Getty|Corbis|Sipa|Alamy|EPA|Zuma|Anadolu|Xinhua)\s*)"  # Name / Agency
, re.IGNORECASE | re.MULTILINE)


def _clean_summary(summary: str) -> str:
    """Strip photo credits and file photo prefixes from the start of summaries."""
    if not summary:
        return summary
    # Apply pattern repeatedly (some summaries stack credits)
    cleaned = summary
    for _ in range(3):
        new = _PHOTO_CREDIT_PATTERN.sub("", cleaned, count=1).strip()
        if new == cleaned:
            break
        cleaned = new
    return cleaned


# Maximum number of parallel feed fetches
# RSS fetching is pure I/O — 50 workers for 419 sources keeps throughput high
MAX_WORKERS = 50

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

    # Strip photo credits and file photo prefixes from start of summary
    summary = _clean_summary(summary)

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


def _fetch_single_feed(source: dict) -> tuple[list[dict], str]:
    """
    Fetch and parse a single RSS feed.

    Args:
        source: Source dict with at least 'id', 'rss_url', 'name'.

    Returns:
        Tuple of (articles, status):
            articles: List of parsed article dicts (empty on failure).
            status: One of: 'ok' | 'timeout' | 'http_4xx' | 'http_5xx'
                    | 'parse_error' | 'other' — used to update
                    sources.last_fetch_status and consecutive_fetch_failures.
    """
    rss_url = source.get("rss_url")
    if not rss_url:
        return [], "other"

    try:
        # Fetch via SSRF-hardened session (handles redirects, auth, encoding
        # better than feedparser's raw fetch, and refuses to connect to
        # private/loopback/link-local/cloud-metadata addresses on any hop).
        resp = safe_get(rss_url, headers=HEADERS, timeout=FEED_TIMEOUT, allow_redirects=True)
        resp.raise_for_status()

        # Parse the fetched content
        feed = feedparser.parse(resp.content)

        if feed.bozo and not feed.entries:
            # Try parsing as text if content parse failed
            feed = feedparser.parse(resp.text)

        if not feed.entries:
            print(f"  [warn] No entries in feed for {source.get('name', 'unknown')} ({rss_url})")
            return [], "parse_error"

        articles = []
        skipped = 0
        # Limit to the 30 most-recent entries per feed. RSS feeds are ordered
        # newest-first; entries beyond 30 are typically older than MAX_ARTICLE_AGE_DAYS
        # and will be filtered anyway. Capping here avoids downloading and parsing
        # large feeds (100-200 entries) that produce minimal net new articles.
        for entry in feed.entries[:30]:
            # --- Junk content filtering (before parse/scrape) ---
            url = entry.get("link", "")
            title = entry.get("title", "") or ""

            # A. Reject junk URLs (pagination, author pages, etc.)
            if url and any(p.search(url) for p in JUNK_URL_PATTERNS):
                skipped += 1
                continue

            # B. Reject junk titles
            if title and any(p.search(title) for p in JUNK_TITLE_PATTERNS):
                skipped += 1
                continue

            # C. Minimum title length
            if len(title.strip()) < MIN_TITLE_LENGTH:
                skipped += 1
                continue

            # D. Reject stale content (older than MAX_ARTICLE_AGE_DAYS)
            published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            if published_parsed:
                try:
                    pub_dt = datetime(*published_parsed[:6], tzinfo=timezone.utc)
                    cutoff = datetime.now(timezone.utc) - timedelta(days=MAX_ARTICLE_AGE_DAYS)
                    if pub_dt < cutoff:
                        skipped += 1
                        continue
                except (TypeError, ValueError):
                    pass  # Can't parse date — don't filter, let it through

            article = _parse_entry(entry, source)
            if article["url"]:
                articles.append(article)

        if skipped:
            print(f"  [filter] {source.get('name', 'unknown')}: skipped {skipped} junk/stale entries")

        return articles, "ok"

    except requests.exceptions.Timeout:
        print(f"  [timeout] {source.get('name', 'unknown')}: timed out after {FEED_TIMEOUT}s")
        return [], "timeout"
    except requests.exceptions.HTTPError as e:
        status = getattr(e.response, "status_code", 0) or 0
        print(f"  [http] {source.get('name', 'unknown')}: {status}")
        return [], ("http_4xx" if 400 <= status < 500 else "http_5xx" if status >= 500 else "other")
    except Exception as e:
        print(f"  [error] {source.get('name', 'unknown')}: {e}")
        return [], "other"


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

    # Dead-feed quarantine: skip sources with >=QUARANTINE_THRESHOLD consecutive
    # failures. We never auto-resurrect; quarantined feeds need a manual
    # /sources admin reset (out of scope for this fix).
    quarantined: list[str] = []
    eligible: list[dict] = []
    for s in sources_with_rss:
        cff = s.get("consecutive_fetch_failures", 0) or 0
        if cff >= QUARANTINE_THRESHOLD:
            quarantined.append(f"{s.get('name', '?')} ({cff} consecutive failures)")
            continue
        eligible.append(s)

    if quarantined:
        print(f"  [quarantine] Skipping {len(quarantined)} dead feed(s):")
        for q in quarantined[:20]:  # cap log noise
            print(f"     quarantined: {q}")
        if len(quarantined) > 20:
            print(f"     ... and {len(quarantined) - 20} more")

    print(f"Fetching RSS from {len(eligible)} sources ({MAX_WORKERS} workers)...")

    # Collect per-source status to flush back to sources table in one batch
    # at the end. Maps source-id → 'ok' | failure-status string.
    status_by_source_id: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_source = {
            executor.submit(_fetch_single_feed, source): source
            for source in eligible
        }

        # as_completed raises TimeoutError during iteration if any futures
        # are still pending after the timeout. Catch it gracefully so one
        # hung feed doesn't crash the entire pipeline.
        try:
            for future in as_completed(future_to_source, timeout=FEED_TIMEOUT * 2):
                source = future_to_source[future]
                source_id = source.get("db_id") or source.get("id")
                try:
                    articles, status = future.result(timeout=FEED_TIMEOUT)
                    all_articles.extend(articles)
                    if source_id:
                        status_by_source_id[source_id] = status
                    if status == "ok":
                        print(f"  [ok] {source.get('name', 'unknown')}: {len(articles)} articles")
                except TimeoutError:
                    error_msg = f"Timeout after {FEED_TIMEOUT}s"
                    print(f"  [timeout] {source.get('name', 'unknown')}: {error_msg}")
                    if source_id:
                        status_by_source_id[source_id] = "timeout"
                    errors.append({
                        "source": source.get("name", "unknown"),
                        "error": error_msg,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                except Exception as e:
                    error_msg = str(e)
                    print(f"  [error] {source.get('name', 'unknown')}: {error_msg}")
                    if source_id:
                        status_by_source_id[source_id] = "other"
                    errors.append({
                        "source": source.get("name", "unknown"),
                        "error": error_msg,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
        except TimeoutError:
            # Some futures still pending after global timeout — log and continue
            # with whatever articles we collected so far.
            pending = [(s.get("db_id") or s.get("id"), s.get("name", "?"))
                       for f, s in future_to_source.items() if not f.done()]
            print(f"  [warn] Global timeout: {len(pending)} feeds still pending, continuing with {len(all_articles)} articles")
            for sid, name in pending:
                if sid:
                    status_by_source_id[sid] = "timeout"
                errors.append({
                    "source": name,
                    "error": "Global fetch timeout — feed still pending",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

    # Persist health counters. One UPDATE per source; small N relative to fetch
    # time. Silent on missing column (migration 051 not yet applied).
    _update_source_health(status_by_source_id)

    print(f"RSS fetch complete: {len(all_articles)} articles from {len(eligible)} sources"
          f" ({len(quarantined)} quarantined)")
    return all_articles, errors


def _update_source_health(status_by_source_id: dict[str, str]) -> None:
    """Persist consecutive_fetch_failures + last_fetch_status to the sources
    table. On a successful fetch the counter resets to 0; on any failure it
    increments. Silent + best-effort — never blocks pipeline progress.

    Requires migration 051 (source health columns). On a fresh environment
    without 051 the UPDATE will fail PGRST204 and we just skip.
    """
    if not status_by_source_id:
        return
    try:
        from utils.supabase_client import supabase
    except Exception:
        return

    now_iso = datetime.now(timezone.utc).isoformat()
    ok_ids = [sid for sid, st in status_by_source_id.items() if st == "ok"]
    fail_items = [(sid, st) for sid, st in status_by_source_id.items() if st != "ok"]

    # Reset successful sources in one batch UPDATE
    if ok_ids:
        try:
            supabase.table("sources").update({
                "consecutive_fetch_failures": 0,
                "last_fetch_at": now_iso,
                "last_fetch_status": "ok",
            }).in_("id", ok_ids).execute()
        except Exception as e:
            err_l = str(e).lower()
            if "does not exist" in err_l or "schema cache" in err_l or "pgrst204" in err_l:
                return  # migration 051 not yet applied — silent skip
            print(f"  [warn] source-health update (ok batch) failed: {e}")
            return

    # Failures need per-row read-modify-write to increment the counter
    if fail_items:
        try:
            existing = supabase.table("sources").select(
                "id,consecutive_fetch_failures"
            ).in_("id", [s for s, _ in fail_items]).execute()
            cff_map = {r["id"]: (r.get("consecutive_fetch_failures") or 0)
                       for r in (existing.data or [])}
            for sid, st in fail_items:
                new_cff = cff_map.get(sid, 0) + 1
                try:
                    supabase.table("sources").update({
                        "consecutive_fetch_failures": new_cff,
                        "last_fetch_at": now_iso,
                        "last_fetch_status": st,
                    }).eq("id", sid).execute()
                    if new_cff == QUARANTINE_THRESHOLD:
                        print(f"  [quarantine] source {sid[:8]} hit threshold ({new_cff} consecutive failures) — will be skipped next run")
                except Exception:
                    pass
        except Exception as e:
            err_l = str(e).lower()
            if "does not exist" in err_l or "schema cache" in err_l or "pgrst204" in err_l:
                return  # migration 051 not yet applied
            print(f"  [warn] source-health update (fail batch) failed: {e}")
