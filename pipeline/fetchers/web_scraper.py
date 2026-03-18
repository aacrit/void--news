"""
Web scraper for extracting full article text from news pages.

Uses BeautifulSoup + requests to extract article content. Respects
robots.txt and uses a polite User-Agent.
"""

import urllib.robotparser
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


USER_AGENT = "VoidNews/1.0 (+https://github.com/aacrit/void--news)"
REQUEST_TIMEOUT = 15  # seconds

# Cache for robots.txt parsers (keyed by domain)
_robots_cache: dict[str, urllib.robotparser.RobotFileParser] = {}


def _check_robots_txt(url: str) -> bool:
    """
    Check if the URL is allowed by the site's robots.txt.

    Results are cached per domain to avoid repeated fetches.

    Args:
        url: The URL to check.

    Returns:
        True if crawling is allowed, False otherwise.
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
            # If we can't fetch robots.txt, assume allowed
            _robots_cache[domain] = None
            return True
        _robots_cache[domain] = rp

    rp = _robots_cache[domain]
    if rp is None:
        return True

    return rp.can_fetch(USER_AGENT, url)


def _extract_article_text(soup: BeautifulSoup) -> str:
    """
    Extract the main article text from a parsed HTML page.

    Tries common article page structures in order of specificity:
    1. <article> tag
    2. <main> tag
    3. Elements with common article class names
    4. Fallback to largest <div> with substantial text

    Args:
        soup: Parsed BeautifulSoup object.

    Returns:
        Extracted article text as a string.
    """
    # Remove script, style, nav, header, footer elements
    for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()

    # Strategy 1: <article> tag
    article = soup.find("article")
    if article:
        text = article.get_text(separator="\n", strip=True)
        if len(text) > 100:
            return text

    # Strategy 2: <main> tag
    main = soup.find("main")
    if main:
        text = main.get_text(separator="\n", strip=True)
        if len(text) > 100:
            return text

    # Strategy 3: Common article content class names
    content_selectors = [
        ".post-content",
        ".article-content",
        ".article-body",
        ".entry-content",
        ".story-body",
        ".story-content",
        ".content-body",
        ".article__body",
        ".article__content",
        '[itemprop="articleBody"]',
        "#article-body",
        "#story-body",
    ]
    for selector in content_selectors:
        element = soup.select_one(selector)
        if element:
            text = element.get_text(separator="\n", strip=True)
            if len(text) > 100:
                return text

    # Strategy 4: Find the div with the most paragraph text
    best_text = ""
    for div in soup.find_all("div"):
        paragraphs = div.find_all("p")
        if paragraphs:
            text = "\n".join(p.get_text(strip=True) for p in paragraphs)
            if len(text) > len(best_text):
                best_text = text

    return best_text


def _extract_image_url(soup: BeautifulSoup, base_url: str) -> str | None:
    """
    Extract the main image URL from the article page.

    Tries Open Graph meta tag first, then looks for large images
    within the article content.

    Args:
        soup: Parsed BeautifulSoup object.
        base_url: The article URL (for resolving relative paths).

    Returns:
        Image URL string, or None if not found.
    """
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
        # Skip tiny images (icons, trackers)
        width = img.get("width")
        height = img.get("height")
        if width and height:
            try:
                if int(width) >= 200 and int(height) >= 150:
                    return src
            except ValueError:
                pass
        # If no dimensions, take first image with a reasonable src
        if not any(skip in src.lower() for skip in ["icon", "logo", "avatar", "pixel", "tracker", "1x1"]):
            return src

    return None


def scrape_article(url: str) -> dict:
    """
    Scrape an article page to extract full text, word count, and image URL.

    Checks robots.txt before scraping. Returns partial results if some
    extraction steps fail.

    Args:
        url: The full URL of the article page to scrape.

    Returns:
        Dict with keys:
            - full_text: str (extracted article text, empty string on failure)
            - word_count: int (number of words in full_text)
            - image_url: str | None (main article image URL)
    """
    result = {
        "full_text": "",
        "word_count": 0,
        "image_url": None,
    }

    # Check robots.txt
    if not _check_robots_txt(url):
        print(f"  [robots] Blocked by robots.txt: {url}")
        return result

    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
            allow_redirects=True,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  [error] Failed to fetch {url}: {e}")
        return result

    # Ensure we got HTML
    content_type = response.headers.get("Content-Type", "")
    if "html" not in content_type.lower():
        print(f"  [skip] Non-HTML content at {url}: {content_type}")
        return result

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract article text
    full_text = _extract_article_text(soup)
    result["full_text"] = full_text
    result["word_count"] = len(full_text.split()) if full_text else 0

    # Extract image
    result["image_url"] = _extract_image_url(soup, url)

    return result
