"""
Web scraper for extracting full article text from news pages.

Two-tier extraction:
  Tier 1: requests + BeautifulSoup (fast, ~0.5s per article)
  Tier 2: Playwright headless browser (JS rendering, ~3s per article)

Tier 2 activates as a fallback when Tier 1 returns <500 chars — this
catches JS-rendered sites (NYT, WaPo, etc.) that serve empty HTML shells.
Playwright is imported lazily so the pipeline works without it installed.

Extraction strategies (both tiers):
- JSON-LD structured data parsing (Article schema)
- Broader CSS selectors for major news sites
- Meta description fallback
- Better paragraph aggregation

Quality gates:
- Paywall/cookie/JS-required content detection and stripping
- Title-as-body detection (redirect captures)
- Minimum word-count threshold with RSS summary fallback
- Single retry on transient failures (timeout, 5xx)
"""

import json
import re
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

from utils.safe_requests import safe_get


# ---------------------------------------------------------------------------
# Image credit / photo caption stripping (UAT-006)
# These patterns match common photo credit lines that some scrapers pick up
# as the first line of article text. They are stripped before storage.
# ---------------------------------------------------------------------------
_IMAGE_CREDIT_PATTERNS = [
    # "Patrick Grehan / Corbis via Getty Images —"
    # "Name Name / Agency — "
    re.compile(
        r"^[A-Z][a-zA-Z\-'\.]+([ ][A-Z][a-zA-Z\-'\.]+)?"  # 1-3 capitalized name parts
        r"\s*/\s*"                                            # slash separator
        r"[A-Za-z][\w\s,\.\-]+"                              # agency name(s)
        r"\s*[\u2014\u2013\-\|]\s*",                         # em-dash/en-dash/hyphen/pipe
        re.UNICODE,
    ),
    # "Photo: Name / Agency" or "Photo credit: ..."
    re.compile(r"^Photo(?:\s+credit)?:\s*.{0,120}\n?", re.IGNORECASE),
    # "Image: ..."
    re.compile(r"^Image:\s*.{0,120}\n?", re.IGNORECASE),
    # "Credit: ..."
    re.compile(r"^Credit:\s*.{0,120}\n?", re.IGNORECASE),
    # "Getty Images —", "Reuters —", "AP Photo —"
    re.compile(
        r"^(?:Getty Images?|Reuters|AP Photo|AFP|Shutterstock|Alamy)"
        r"\s*[\u2014\u2013\-\|]\s*",
        re.UNICODE,
    ),
    # Bare "AP", "AFP", "Reuters" at start of a line followed by content
    re.compile(r"^\((?:AP|AFP|Reuters|PA)\)\s*[\u2014\u2013\-]\s*", re.UNICODE),
]


def _strip_image_credits(text: str) -> str:
    """
    Remove leading image credit / photo attribution lines from article text.

    Only strips from the very beginning of the text (or after a leading
    newline), so legitimate article content starting with a name is preserved.
    Maximum strip length is 200 characters to avoid accidentally removing a
    real opening sentence.
    """
    if not text:
        return text

    stripped = text.lstrip("\n\r\t ")
    # Only attempt to strip from the first 200 characters
    prefix = stripped[:200]

    for pattern in _IMAGE_CREDIT_PATTERNS:
        m = pattern.match(prefix)
        if m and m.end() < 180:  # safety: don't strip more than 180 chars
            stripped = stripped[m.end():].lstrip()
            break  # only strip one credit block at the start

    return stripped


# ---------------------------------------------------------------------------
# Paywall / garbage content detection
# Patterns that indicate extracted text is a paywall wall, cookie consent,
# JS-required notice, or redirect stub rather than actual article content.
# When detected, the text is discarded so the RSS summary fallback can
# provide usable content for NLP analysis.
# ---------------------------------------------------------------------------
_PAYWALL_INDICATORS = [
    # Paywall / subscription gates
    re.compile(r"subscribe\s+(?:to\s+)?(?:continue|read|unlock|access)", re.I),
    re.compile(r"(?:sign|log)\s*in\s+to\s+(?:continue|read|access|view)", re.I),
    re.compile(r"(?:create|need)\s+(?:a\s+)?(?:free\s+)?account\s+to", re.I),
    re.compile(r"already\s+a\s+(?:subscriber|member)\s*\?", re.I),
    re.compile(r"this\s+(?:article|content|story)\s+is\s+(?:for|available\s+to)\s+(?:subscribers|members|premium)", re.I),
    re.compile(r"unlimited\s+(?:digital\s+)?access", re.I),
    re.compile(r"start\s+your\s+(?:free\s+)?(?:trial|subscription)", re.I),
    # Cookie consent
    re.compile(r"we\s+use\s+cookies\s+to", re.I),
    re.compile(r"cookie\s+(?:consent|policy|preferences|settings)", re.I),
    re.compile(r"(?:accept|manage)\s+(?:all\s+)?cookies", re.I),
    re.compile(r"by\s+(?:continuing|using)\s+(?:this|our)\s+(?:site|website)\s*,?\s*you\s+(?:agree|consent)", re.I),
    # JavaScript required
    re.compile(r"javascript\s+(?:is\s+)?(?:required|disabled|not\s+enabled|must\s+be\s+enabled)", re.I),
    re.compile(r"please\s+enable\s+javascript", re.I),
    re.compile(r"this\s+(?:page|site)\s+requires\s+javascript", re.I),
    re.compile(r"you\s+need\s+to\s+enable\s+javascript", re.I),
    # Redirect / error stubs
    re.compile(r"you\s+are\s+being\s+redirected", re.I),
    re.compile(r"if\s+you\s+are\s+not\s+redirected", re.I),
    re.compile(r"click\s+here\s+(?:to\s+)?(?:continue|proceed|be\s+redirected)", re.I),
    re.compile(r"page\s+(?:not\s+found|has\s+(?:moved|been\s+removed))", re.I),
    # Access denied / geo-block
    re.compile(r"access\s+(?:denied|restricted|blocked)", re.I),
    re.compile(r"(?:not\s+)?available\s+in\s+your\s+(?:region|country|area)", re.I),
    re.compile(r"4(?:03|51)\s+(?:forbidden|unavailable)", re.I),
]

# Minimum fraction of text that must survive paywall stripping to be usable
_MIN_QUALITY_WORDS = 80


def _detect_paywall_garbage(text: str) -> bool:
    """
    Return True if the text appears to be paywall, cookie consent, JS notice,
    or redirect stub rather than real article content.

    Only flags short texts (< 500 words) where paywall indicators make up a
    significant fraction. Long texts may legitimately mention cookies in a
    footer paragraph — we don't want to discard a 2000-word article because
    it has a cookie notice at the bottom.
    """
    if not text:
        return True

    words = text.split()
    word_count = len(words)

    # Long articles are almost certainly real content even if they mention
    # cookies or subscriptions somewhere in the body
    if word_count > 500:
        return False

    # For short texts, check how many paywall indicators fire
    hits = sum(1 for pat in _PAYWALL_INDICATORS if pat.search(text))

    # 2+ indicators in a short text = very likely garbage
    if hits >= 2:
        return True

    # Single indicator in very short text (< 100 words) = likely garbage
    if hits >= 1 and word_count < 100:
        return True

    return False


def _is_title_echo(text: str, title: str) -> bool:
    """
    Return True if the extracted text is just the title repeated or a trivial
    variation (redirect capture, RSS stub).

    Catches patterns like:
    - "- assign.handelsblatt.com"
    - "CTVNews - CTV News"
    - Title repeated 2-3 times with minor additions
    """
    if not text or not title:
        return False

    text_clean = re.sub(r'\s+', ' ', text.strip().lower())
    title_clean = re.sub(r'\s+', ' ', title.strip().lower())

    # Exact match or text is substring of title
    if text_clean == title_clean or text_clean in title_clean:
        return True

    # Title is the majority of the text (> 80% overlap by length)
    if len(title_clean) > 10 and len(text_clean) < len(title_clean) * 2.5:
        # Check if title appears in the text
        if title_clean in text_clean:
            return True

    # Text is very short and starts with or ends with title
    if len(text.split()) < 30 and (
        text_clean.startswith(title_clean) or text_clean.endswith(title_clean)
    ):
        return True

    return False


# Use a realistic browser User-Agent — news sites commonly block identifiable
# bot UAs. The scraper respects robots.txt and rate-limits regardless.
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)
REQUEST_TIMEOUT = 12  # seconds — balanced: 8s was too aggressive for CDN-heavy sites
MAX_RETRIES = 1  # single retry on transient failures (timeout, 5xx)

# Cache for robots.txt parsers (keyed by domain)
_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}


def _check_robots_txt(url: str) -> bool:
    """
    Check if the URL is allowed by the site's robots.txt.
    Results are cached per domain to avoid repeated fetches.
    """
    parsed = urlparse(url)
    domain = f"{parsed.scheme}://{parsed.netloc}"

    if domain not in _robots_cache:
        rp = urllib.robotparser.RobotFileParser()
        robots_url = f"{domain}/robots.txt"
        try:
            # Use the SSRF-hardened session (refuses private/loopback IPs on
            # any redirect hop). Timeout still set to 5s — robots.txt is small.
            resp = safe_get(robots_url, timeout=5, headers={"User-Agent": USER_AGENT})
            if resp.status_code == 200:
                rp.parse(resp.text.splitlines())
            else:
                _robots_cache[domain] = None
                return True
        except Exception:
            _robots_cache[domain] = None
            return True
        _robots_cache[domain] = rp

    rp = _robots_cache[domain]
    if rp is None:
        # Permissive: if robots.txt is unreachable (network error, 404, etc.),
        # assume allowed. The alternative — refusing to scrape any site whose
        # robots.txt we can't fetch — blocks too many legitimate sources and
        # is the primary cause of word_count=0 on valid articles.
        return True

    return rp.can_fetch("*", url)


def _extract_json_ld_text(soup: BeautifulSoup) -> str:
    """
    Extract article text from JSON-LD structured data (schema.org Article).
    Many major news sites embed full article text in JSON-LD.
    """
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            # Handle both single object and array of objects
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    # Check @type for Article variants
                    item_type = item.get("@type", "")
                    if isinstance(item_type, list):
                        item_type = " ".join(item_type)
                    if "Article" in str(item_type) or "NewsArticle" in str(item_type):
                        body = item.get("articleBody", "")
                        if body and len(body) > 100:
                            return body
                    # Check @graph array
                    for graph_item in item.get("@graph", []):
                        if isinstance(graph_item, dict):
                            gt = graph_item.get("@type", "")
                            if "Article" in str(gt):
                                body = graph_item.get("articleBody", "")
                                if body and len(body) > 100:
                                    return body
        except (json.JSONDecodeError, TypeError, AttributeError):
            continue
    return ""


def _extract_meta_description(soup: BeautifulSoup) -> str:
    """Extract meta description or og:description as last-resort text."""
    for attr in [
        {"property": "og:description"},
        {"name": "description"},
        {"name": "twitter:description"},
    ]:
        tag = soup.find("meta", attrs=attr)
        if tag and tag.get("content") and len(tag["content"]) > 50:
            return tag["content"]
    return ""


def _extract_article_text(soup: BeautifulSoup) -> str:
    """
    Extract the main article text from a parsed HTML page.

    Tries multiple strategies in order of reliability:
    1. JSON-LD structured data (most reliable for major sites)
    2. <article> tag
    3. <main> tag
    4. Common CSS selectors for news site content areas
    5. Largest div with paragraph text
    6. Meta description fallback
    """
    # Remove non-content elements
    for tag in soup.find_all([
        "script", "style", "nav", "header", "footer", "aside",
        "form", "iframe", "noscript", "svg",
    ]):
        # Don't decompose JSON-LD scripts (needed for Strategy 1)
        if tag.name == "script" and tag.get("type") == "application/ld+json":
            continue
        tag.decompose()

    # Strategy 1: JSON-LD structured data
    text = _extract_json_ld_text(soup)
    if text:
        return text

    # Strategy 2: <article> tag
    article = soup.find("article")
    if article:
        text = article.get_text(separator="\n", strip=True)
        if len(text) > 100:
            return text

    # Strategy 3: <main> tag
    main = soup.find("main")
    if main:
        text = main.get_text(separator="\n", strip=True)
        if len(text) > 100:
            return text

    # Strategy 4: Common article content selectors (expanded for major outlets)
    content_selectors = [
        # Generic patterns
        '[itemprop="articleBody"]',
        '[data-testid="article-body"]',
        '[data-component="text-block"]',
        ".post-content", ".article-content", ".article-body",
        ".entry-content", ".story-body", ".story-content",
        ".content-body", ".article__body", ".article__content",
        "#article-body", "#story-body", "#storytext",
        # Major outlet specific
        ".story-body__inner",          # BBC
        ".article-page",              # Reuters
        ".pg-rail-tall__body",        # CNN
        ".article-text",              # Al Jazeera
        ".article__text",             # The Guardian
        ".caas-body",                 # Yahoo News
        ".body-content",              # NBC News
        ".article-body-text",         # CBS News
        ".articleBody",               # Generic schema
        ".RichTextStoryBody",         # NPR
        ".premium-content",           # Premium content area
        ".article-wrap",              # Generic
        ".detail-body",               # Fox News
        ".article-page__content",     # Washington Post
        "#article-content",           # Generic
        "#content-body",              # Generic
        "#main-content",              # Generic
        ".story__content",            # ProPublica
        ".postContent",               # Blog-style
    ]
    for selector in content_selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(separator="\n", strip=True)
            if len(text) > 100:
                return text

    # Strategy 5: Find the div with the most paragraph text
    best_text = ""
    for div in soup.find_all("div"):
        paragraphs = div.find_all("p", recursive=True)
        if len(paragraphs) >= 2:  # At least 2 paragraphs for it to be an article
            text = "\n".join(
                p.get_text(strip=True) for p in paragraphs
                if len(p.get_text(strip=True)) > 20  # Skip tiny paragraphs
            )
            if len(text) > len(best_text):
                best_text = text

    if best_text and len(best_text) > 100:
        return best_text

    # Strategy 6: Aggregate all <p> tags on the page
    all_paragraphs = soup.find_all("p")
    if len(all_paragraphs) >= 3:
        text = "\n".join(
            p.get_text(strip=True) for p in all_paragraphs
            if len(p.get_text(strip=True)) > 30
        )
        if len(text) > 200:
            return text

    # Strategy 7: Meta description as absolute last resort
    return _extract_meta_description(soup)


def _extract_image_url(soup: BeautifulSoup, base_url: str) -> str | None:
    """Extract the main image URL from the article page."""
    # Try Open Graph image
    og_image = soup.find("meta", property="og:image")
    if og_image and og_image.get("content"):
        return og_image["content"]

    # Try Twitter card image
    twitter_image = soup.find("meta", attrs={"name": "twitter:image"})
    if twitter_image and twitter_image.get("content"):
        return twitter_image["content"]

    # Try first large image in article
    article = soup.find("article") or soup.find("main") or soup
    for img in article.find_all("img", src=True):
        src = img["src"]
        width = img.get("width")
        height = img.get("height")
        if width and height:
            try:
                if int(width) >= 200 and int(height) >= 150:
                    return src
            except ValueError:
                pass
        if not any(skip in src.lower() for skip in [
            "icon", "logo", "avatar", "pixel", "tracker", "1x1",
            "spacer", "blank", "loading", "spinner",
        ]):
            return src

    return None


_PLAYWRIGHT_AVAILABLE: bool | None = None  # lazy-checked once


def _scrape_with_playwright(url: str) -> str:
    """
    Fallback scraper using Playwright headless Chromium for JS-rendered sites.

    Returns extracted article text, or empty string on failure.
    Lazy-imports playwright so the module works without it installed.
    """
    global _PLAYWRIGHT_AVAILABLE
    if _PLAYWRIGHT_AVAILABLE is False:
        return ""

    try:
        from playwright.sync_api import sync_playwright
        _PLAYWRIGHT_AVAILABLE = True
    except ImportError:
        _PLAYWRIGHT_AVAILABLE = False
        # Log once — this fires the first time a JS-heavy page needs Tier 2
        print("  [scraper] Playwright not available — Tier 2 JS-rendering disabled. "
              "Articles needing JS will fall back to RSS summary text.")
        return ""

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/131.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()
            page.goto(url, wait_until="domcontentloaded", timeout=15000)
            # Wait for article content to render — 1s is enough for most sites;
            # reduced from 2500ms to avoid padding every JS-rendered page load.
            page.wait_for_timeout(1000)

            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        text = _extract_article_text(soup)
        return text
    except Exception:
        return ""


def _fetch_page(url: str) -> requests.Response | None:
    """
    Fetch a page with retry on transient failures (timeout, 5xx).

    Returns the Response on success, None on failure.
    Retries once after a 2-second pause for timeout or 5xx errors.
    """
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        # Sec-Fetch headers mimic a real browser navigation
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
    }

    last_exc = None
    for attempt in range(1 + MAX_RETRIES):
        try:
            response = safe_get(
                url,
                headers=headers,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )
            # Retry on 5xx server errors (transient)
            if response.status_code >= 500 and attempt < MAX_RETRIES:
                time.sleep(2)
                continue
            response.raise_for_status()
            return response
        except requests.exceptions.Timeout:
            last_exc = "timeout"
            if attempt < MAX_RETRIES:
                time.sleep(2)
                continue
        except requests.RequestException:
            # 4xx, connection refused, DNS failure — don't retry
            return None

    return None


def scrape_article(url: str, title: str = "", rss_summary: str = "") -> dict:
    """
    Scrape an article page to extract full text, word count, and image URL.

    Three-tier extraction with quality gates:
      Tier 1: requests + BeautifulSoup (fast, ~0.5s)
      Tier 2: Playwright headless browser (JS rendering, ~3s)
      Tier 3: RSS summary fallback (if scrape produces garbage)

    Quality gates applied after extraction:
      - Paywall/cookie/JS-required content detection
      - Title-as-body echo detection (redirect captures)
      - Minimum word count threshold

    Args:
        url: Article URL to scrape.
        title: Article title (for title-echo detection). Optional.
        rss_summary: RSS feed summary/description text. Used as fallback
            when scraping fails or produces garbage. Optional.

    Returns:
        Dict with keys: full_text, word_count, image_url, canonical_url.
        canonical_url is the final URL after any redirects.
    """
    result = {
        "full_text": "",
        "word_count": 0,
        "image_url": None,
        "canonical_url": url,  # default: same as input
    }

    # Check robots.txt
    if not _check_robots_txt(url):
        # Even if robots.txt blocks us, we can still use the RSS summary
        if rss_summary and len(rss_summary) > 50:
            result["full_text"] = rss_summary
            result["word_count"] = len(rss_summary.split())
        return result

    response = _fetch_page(url)
    if response is None:
        # Scrape failed entirely — fall back to RSS summary
        if rss_summary and len(rss_summary) > 50:
            result["full_text"] = rss_summary
            result["word_count"] = len(rss_summary.split())
        return result

    # Capture canonical URL: final URL after following redirects.
    # Google News RSS entries have 'link' fields pointing to
    # news.google.com/rss/articles/CBMi... which redirect to the original
    # article. Storing the canonical URL ensures deduplication works across
    # pipeline runs and avoids storing ephemeral Google redirect URLs.
    final_url = response.url
    if final_url and final_url != url:
        result["canonical_url"] = final_url

    # Ensure we got HTML
    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type.lower() and "xml" not in content_type.lower():
        if rss_summary and len(rss_summary) > 50:
            result["full_text"] = rss_summary
            result["word_count"] = len(rss_summary.split())
        return result

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract article text, then strip leading image credits
    full_text = _extract_article_text(soup)
    full_text = _strip_image_credits(full_text)

    # Tier 2 fallback: if BeautifulSoup got too little text, retry with
    # Playwright headless browser (renders JavaScript like a real browser).
    # Threshold 500 chars — below that, the page likely needs JS rendering.
    if len(full_text) < 500:
        pw_text = _scrape_with_playwright(url)
        if len(pw_text) > len(full_text):
            full_text = _strip_image_credits(pw_text)

    # --- Quality gates ---

    # Gate 1: Paywall / garbage content detection
    # If the extracted text is a paywall wall, cookie consent, JS notice,
    # or redirect stub, discard it entirely.
    if _detect_paywall_garbage(full_text):
        full_text = ""

    # Gate 2: Title-echo detection
    # If the text is just the title repeated (redirect capture, RSS stub),
    # discard it — the RSS summary will be more informative.
    if full_text and title and _is_title_echo(full_text, title):
        full_text = ""

    # Gate 3: Minimum quality threshold with RSS fallback
    # If scraped text is below the quality threshold and we have a decent
    # RSS summary, prefer the RSS summary. A 100-word RSS summary with real
    # content is far better for NLP than a 30-word cookie notice.
    word_count = len(full_text.split()) if full_text else 0
    rss_word_count = len(rss_summary.split()) if rss_summary else 0

    if word_count < _MIN_QUALITY_WORDS and rss_summary and len(rss_summary) > 50:
        # RSS summary is better than garbage scrape
        if rss_word_count > word_count:
            full_text = rss_summary
            word_count = rss_word_count

    result["full_text"] = full_text
    result["word_count"] = word_count

    # Extract image
    result["image_url"] = _extract_image_url(soup, url)

    return result
