"""
Unified free-image API client for void --news.

Searches Wikimedia Commons, Unsplash, Pexels, and Pixabay.
Returns standardized ImageResult objects with full attribution.

Usage:
    from pipeline.media.image_search import search_images, search_wikimedia
    results = search_images("Federal Reserve building", sources=["wikimedia", "unsplash"])

All APIs are free tier. $0 cost.
"""

import os
import time
from dataclasses import dataclass, asdict
from urllib.parse import quote_plus

import requests

_SESSION = requests.Session()
_SESSION.headers.update({"User-Agent": "void-news/1.0 (media-curator; +https://github.com/void-news)"})


@dataclass
class ImageResult:
    """Standardized image result across all APIs."""
    url: str
    thumbnail_url: str
    width: int
    height: int
    alt_text: str
    photographer: str
    source: str          # "wikimedia" | "unsplash" | "pexels" | "pixabay"
    source_url: str      # link to image page on platform
    license: str         # "cc0" | "unsplash-license" | "pexels-license" | "cc-by" | "cc-by-sa" | "public-domain"
    attribution: str     # formatted attribution string

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Wikimedia Commons (no API key needed)
# ---------------------------------------------------------------------------

def search_wikimedia(query: str, max_results: int = 5) -> list[ImageResult]:
    """Search Wikimedia Commons for images. No API key required."""
    try:
        resp = _SESSION.get(
            "https://commons.wikimedia.org/w/api.php",
            params={
                "action": "query",
                "generator": "search",
                "gsrsearch": f"filetype:bitmap {query}",
                "gsrnamespace": "6",  # File namespace
                "gsrlimit": str(min(max_results * 2, 20)),  # fetch extra to filter
                "prop": "imageinfo",
                "iiprop": "url|size|extmetadata|mime",
                "iiurlwidth": "800",
                "format": "json",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [media] Wikimedia search failed: {e}")
        return []

    pages = data.get("query", {}).get("pages", {})
    results = []

    for page in sorted(pages.values(), key=lambda p: p.get("index", 999)):
        if len(results) >= max_results:
            break

        info_list = page.get("imageinfo", [])
        if not info_list:
            continue
        info = info_list[0]

        # Skip non-image types
        mime = info.get("mime", "")
        if not mime.startswith("image/"):
            continue

        # Skip tiny images
        w = info.get("width", 0)
        h = info.get("height", 0)
        if w < 200 or h < 150:
            continue

        ext = info.get("extmetadata", {})
        artist = _extract_wiki_text(ext.get("Artist", {}).get("value", "Unknown"))
        license_short = ext.get("LicenseShortName", {}).get("value", "")
        license_key = _normalize_wiki_license(license_short)
        desc = _extract_wiki_text(ext.get("ImageDescription", {}).get("value", ""))

        # Skip non-free licenses
        if license_key not in ("cc0", "public-domain", "cc-by", "cc-by-sa"):
            continue

        thumb = info.get("thumburl", info.get("url", ""))
        full_url = info.get("url", thumb)
        page_url = info.get("descriptionurl", f"https://commons.wikimedia.org/wiki/File:{page.get('title', '')}")

        results.append(ImageResult(
            url=full_url,
            thumbnail_url=thumb,
            width=w,
            height=h,
            alt_text=desc[:200] if desc else query,
            photographer=artist[:100],
            source="wikimedia",
            source_url=page_url,
            license=license_key,
            attribution=f"{artist}, {license_short}, via Wikimedia Commons",
        ))

    return results


def _extract_wiki_text(html_str: str) -> str:
    """Strip HTML tags from Wikimedia metadata values."""
    import re
    return re.sub(r"<[^>]+>", "", html_str).strip()


def _normalize_wiki_license(license_str: str) -> str:
    """Normalize Wikimedia license strings to our standard keys."""
    ls = license_str.lower()
    if "public domain" in ls or "pd" in ls:
        return "public-domain"
    if "cc0" in ls:
        return "cc0"
    if "cc-by-sa" in ls or "cc by-sa" in ls:
        return "cc-by-sa"
    if "cc-by" in ls or "cc by" in ls:
        return "cc-by"
    return ls  # return raw if unrecognized


# ---------------------------------------------------------------------------
# Unsplash (free API key required)
# ---------------------------------------------------------------------------

def search_unsplash(query: str, per_page: int = 5) -> list[ImageResult]:
    """Search Unsplash. Requires UNSPLASH_ACCESS_KEY in env."""
    key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not key:
        return []

    try:
        resp = _SESSION.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": str(per_page), "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {key}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [media] Unsplash search failed: {e}")
        return []

    results = []
    for photo in data.get("results", [])[:per_page]:
        user = photo.get("user", {})
        name = user.get("name", "Unknown")
        results.append(ImageResult(
            url=photo.get("urls", {}).get("regular", ""),
            thumbnail_url=photo.get("urls", {}).get("small", ""),
            width=photo.get("width", 0),
            height=photo.get("height", 0),
            alt_text=photo.get("alt_description", "") or photo.get("description", "") or query,
            photographer=name,
            source="unsplash",
            source_url=photo.get("links", {}).get("html", ""),
            license="unsplash-license",
            attribution=f"Photo by {name} on Unsplash",
        ))

    return results


# ---------------------------------------------------------------------------
# Pexels (free API key required)
# ---------------------------------------------------------------------------

def search_pexels(query: str, per_page: int = 5) -> list[ImageResult]:
    """Search Pexels. Requires PEXELS_API_KEY in env."""
    key = os.environ.get("PEXELS_API_KEY", "")
    if not key:
        return []

    try:
        resp = _SESSION.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": str(per_page), "orientation": "landscape"},
            headers={"Authorization": key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [media] Pexels search failed: {e}")
        return []

    results = []
    for photo in data.get("photos", [])[:per_page]:
        results.append(ImageResult(
            url=photo.get("src", {}).get("large2x", ""),
            thumbnail_url=photo.get("src", {}).get("medium", ""),
            width=photo.get("width", 0),
            height=photo.get("height", 0),
            alt_text=photo.get("alt", "") or query,
            photographer=photo.get("photographer", "Unknown"),
            source="pexels",
            source_url=photo.get("url", ""),
            license="pexels-license",
            attribution=f"Photo by {photo.get('photographer', 'Unknown')} on Pexels",
        ))

    return results


# ---------------------------------------------------------------------------
# Pixabay (free API key required)
# ---------------------------------------------------------------------------

def search_pixabay(query: str, per_page: int = 5) -> list[ImageResult]:
    """Search Pixabay. Requires PIXABAY_API_KEY in env."""
    key = os.environ.get("PIXABAY_API_KEY", "")
    if not key:
        return []

    try:
        resp = _SESSION.get(
            "https://pixabay.com/api/",
            params={
                "key": key,
                "q": query,
                "per_page": str(per_page),
                "orientation": "horizontal",
                "image_type": "photo",
                "safesearch": "true",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [media] Pixabay search failed: {e}")
        return []

    results = []
    for hit in data.get("hits", [])[:per_page]:
        results.append(ImageResult(
            url=hit.get("largeImageURL", ""),
            thumbnail_url=hit.get("webformatURL", ""),
            width=hit.get("imageWidth", 0),
            height=hit.get("imageHeight", 0),
            alt_text=hit.get("tags", "") or query,
            photographer=hit.get("user", "Unknown"),
            source="pixabay",
            source_url=hit.get("pageURL", ""),
            license="pixabay-license",
            attribution=f"Image by {hit.get('user', 'Unknown')} on Pixabay",
        ))

    return results


# ---------------------------------------------------------------------------
# Unified search
# ---------------------------------------------------------------------------

_SEARCH_FNS = {
    "wikimedia": search_wikimedia,
    "unsplash": search_unsplash,
    "pexels": search_pexels,
    "pixabay": search_pixabay,
}

_DEFAULT_ORDER = ["wikimedia", "unsplash", "pexels", "pixabay"]


def search_images(
    query: str,
    sources: list[str] | None = None,
    max_results: int = 5,
) -> list[ImageResult]:
    """Search across multiple free image APIs.

    Args:
        query: Search terms
        sources: List of API sources to search (default: all available)
        max_results: Max total results to return

    Returns:
        List of ImageResult sorted by source priority
    """
    order = sources or _DEFAULT_ORDER
    results: list[ImageResult] = []

    for src in order:
        if len(results) >= max_results:
            break
        fn = _SEARCH_FNS.get(src)
        if not fn:
            continue
        remaining = max_results - len(results)
        try:
            batch = fn(query, per_page=remaining) if src != "wikimedia" else fn(query, max_results=remaining)
            results.extend(batch)
        except Exception as e:
            print(f"  [media] {src} search error: {e}")
        time.sleep(0.5)  # polite delay between APIs

    return results[:max_results]


def verify_image(url: str, timeout: int = 10) -> bool:
    """HEAD request to verify image URL is accessible."""
    try:
        resp = _SESSION.head(url, timeout=timeout, allow_redirects=True)
        content_type = resp.headers.get("content-type", "")
        return resp.status_code == 200 and "image" in content_type
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Cover image selection for weekly digest
# ---------------------------------------------------------------------------

def find_cover_image_for_cluster(
    cluster_id: str,
    cluster_title: str,
    supabase_client=None,
) -> dict | None:
    """Find the best cover image for a weekly cover story.

    Strategy:
    1. Try og:image from cluster's highest-ranked article (publisher-curated, $0)
    2. Fallback: search Wikimedia Commons (free, no key needed)
    3. Fallback: search Unsplash/Pexels if keys available

    Returns dict with url, attribution, source or None.
    """
    if not supabase_client:
        return None

    # Step 1: Try og:image from cluster articles
    try:
        article_ids_resp = supabase_client.table("cluster_articles").select(
            "article_id"
        ).eq("cluster_id", cluster_id).execute()

        article_ids = [r["article_id"] for r in (article_ids_resp.data or [])]

        if article_ids:
            articles_resp = supabase_client.table("articles").select(
                "image_url,title,source_id"
            ).in_("id", article_ids[:20]).not_.is_("image_url", "null").execute()

            for art in (articles_resp.data or []):
                img_url = art.get("image_url", "")
                if img_url and _is_valid_og_image(img_url):
                    # Look up source name for attribution
                    source_name = ""
                    if art.get("source_id"):
                        try:
                            src_resp = supabase_client.table("sources").select(
                                "name"
                            ).eq("id", art["source_id"]).single().execute()
                            source_name = src_resp.data.get("name", "") if src_resp.data else ""
                        except Exception:
                            pass

                    return {
                        "url": img_url,
                        "attribution": f"Image via {source_name}" if source_name else "Publisher image",
                        "source": "og_image",
                    }
    except Exception as e:
        print(f"  [media] og:image lookup failed: {e}")

    # Step 2: Wikimedia Commons (free, no key)
    wiki_results = search_wikimedia(cluster_title, max_results=3)
    if wiki_results:
        best = wiki_results[0]
        if verify_image(best.url):
            return {
                "url": best.url,
                "attribution": best.attribution,
                "source": "wikimedia",
            }

    # Step 3: Unsplash / Pexels (if keys available)
    for src in ["unsplash", "pexels"]:
        fn = _SEARCH_FNS.get(src)
        if not fn:
            continue
        try:
            results = fn(cluster_title, per_page=3) if src != "wikimedia" else fn(cluster_title, max_results=3)
            if results and verify_image(results[0].url):
                return {
                    "url": results[0].url,
                    "attribution": results[0].attribution,
                    "source": src,
                }
        except Exception:
            pass

    return None


def _is_valid_og_image(url: str) -> bool:
    """Filter out common non-editorial og:image URLs."""
    skip_patterns = [
        "logo", "icon", "favicon", "avatar", "default", "placeholder",
        "1x1", "pixel", "blank", "spacer", "share-", "og-default",
        "social-share", "twitter-card",
    ]
    url_lower = url.lower()
    return not any(pat in url_lower for pat in skip_patterns)
