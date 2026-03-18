"""
Web scraper for extracting full article text from news pages.

Uses BeautifulSoup + requests to extract article content. Respects
robots.txt and uses a polite User-Agent.

Improved extraction with:
- Broader CSS selectors for major news sites
- JSON-LD structured data parsing (Article schema)
- Meta description fallback
- Better paragraph aggregation
"""

import json
import urllib.robotparser
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


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
        ".paywall",                   # Paywalled content area
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


def scrape_article(url: str) -> dict:
    """
    Scrape an article page to extract full text, word count, and image URL.

    Checks robots.txt before scraping. Returns partial results if some
    extraction steps fail.
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

    # Extract article text
    full_text = _extract_article_text(soup)
    result["full_text"] = full_text
    result["word_count"] = len(full_text.split()) if full_text else 0

    # Extract image
    result["image_url"] = _extract_image_url(soup, url)

    return result
