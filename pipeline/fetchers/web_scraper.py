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
"""

import json
import re
import urllib.robotparser
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


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


# Use a browser-like User-Agent — many news sites block bot-like agents
USER_AGENT = (
    "Mozilla/5.0 (compatible; VoidNews/1.0; "
    "+https://github.com/aacrit/void--news)"
)
REQUEST_TIMEOUT = 15  # seconds

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
        rp.set_url(robots_url)
        try:
            rp.read()
        except Exception:
            _robots_cache[domain] = None
            return True
        _robots_cache[domain] = rp

    rp = _robots_cache[domain]
    if rp is None:
        # Conservative: if robots.txt is unreachable, assume disallowed
        return False

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
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
            # Wait for article content to render (most sites load within 2s)
            page.wait_for_timeout(2500)

            html = page.content()
            browser.close()

        soup = BeautifulSoup(html, "html.parser")
        text = _extract_article_text(soup)
        return text
    except Exception:
        return ""


def scrape_article(url: str) -> dict:
    """
    Scrape an article page to extract full text, word count, and image URL.

    Two-tier: tries requests+BeautifulSoup first (fast). If text < 500 chars,
    retries with Playwright headless browser (handles JS-rendered sites).
    Checks robots.txt before scraping.
    """
    result = {
        "full_text": "",
        "word_count": 0,
        "image_url": None,
    }

    # Check robots.txt
    if not _check_robots_txt(url):
        return result

    try:
        response = requests.get(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            },
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException:
        return result

    # Ensure we got HTML
    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type.lower() and "xml" not in content_type.lower():
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

    result["full_text"] = full_text
    result["word_count"] = len(full_text.split()) if full_text else 0

    # Extract image
    result["image_url"] = _extract_image_url(soup, url)

    return result
