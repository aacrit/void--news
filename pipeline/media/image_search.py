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
# Wikimedia asks clients to identify themselves and give a way to reach the
# operator; a generic agent is throttled first and hardest. The old value named
# a github url that does not resolve.
_SESSION.headers.update({
    "User-Agent": "VoidNews/1.0 (https://news.voidvision.org; aacrit@gmail.com)"
})

# ---------------------------------------------------------------------------
# Minimum-resolution gate (shared across APIs)
# History event pages render the image large (Lightbox object-fit: contain,
# which never upscales), so modest sources look tiny. Reject anything that
# won't fill a large frame and request the highest-res render each API offers.
# ---------------------------------------------------------------------------
MIN_WIDTH = 1200          # Unsplash / Pexels: skip candidates narrower than this
MIN_HEIGHT = 600          # paired height floor where a height is known
WIKI_MIN_WIDTH = 800      # Wikimedia: raised from the old 200x150 floor
WIKI_MIN_HEIGHT = 600
# Wikimedia now serves only a fixed set of thumbnail widths and refuses the
# rest ("Use thumbnail sizes listed on https://w.wiki/GHai"). 1280 is in that
# set and verified to return bytes; an off-list width yields a url that 400s
# when the browser actually fetches it, which is a broken image on the page
# rather than an error anyone would see here.
WIKI_RENDER_WIDTH = 1280
UNSPLASH_RENDER_WIDTH = 2000  # width param appended to the raw URL
PEXELS_RENDER_WIDTH = 2000    # informational; Pexels 'original' is full-res


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
    """Search Wikimedia Commons for freely licensed images. No API key required.

    Retries through the throttle: Commons returns HTTP 429 readily, and a single
    failed attempt here used to mean the weekly silently found no cover image
    and fell through to whatever was next. That is how a wire photograph ended
    up on Issue #26.
    """
    data = None
    delay = 4.0
    for attempt in range(4):
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
                    "iiurlwidth": str(WIKI_RENDER_WIDTH),
                    "format": "json",
                },
                timeout=20,
            )
            if resp.status_code in (429, 503) and attempt < 3:
                print(f"  [media] Commons throttled ({resp.status_code}); waiting {delay:.0f}s")
                time.sleep(delay)
                delay *= 2
                continue
            resp.raise_for_status()
            data = resp.json()
            break
        except Exception as e:
            if attempt == 3:
                print(f"  [media] Wikimedia search failed: {e}")
                return []
            time.sleep(delay)
            delay *= 2
    if data is None:
        return []

    pages = data.get("query", {}).get("pages", {})
    results = []
    dropped_res = 0

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

        # Skip low-resolution images (raised from the old 200x150 floor so
        # sources fill the large Lightbox frame without upscaling).
        w = info.get("width", 0)
        h = info.get("height", 0)
        if w < WIKI_MIN_WIDTH or h < WIKI_MIN_HEIGHT:
            dropped_res += 1
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

    if dropped_res:
        print(f"  [media] Wikimedia '{query}': dropped {dropped_res} candidate(s) below "
              f"{WIKI_MIN_WIDTH}x{WIKI_MIN_HEIGHT}px min-resolution floor")

    return results


def _extract_wiki_text(html_str: str) -> str:
    """Strip HTML tags from Wikimedia metadata values."""
    import re
    return re.sub(r"<[^>]+>", "", html_str).strip()


#: License fragments that make an image unpublishable HERE, whatever else the
#: string says. Checked BEFORE the permissive patterns, because every one of
#: them contains a permissive pattern as a substring.
_NON_FREE_MARKERS = ("-nc", " nc", "noncommercial", "non-commercial",
                     "-nd", " nd", "noderiv", "no-deriv",
                     "fair use", "non-free", "all rights reserved")


def _normalize_wiki_license(license_str: str) -> str:
    """Normalize a Commons LicenseShortName to one of our standard keys.

    Anything this does not recognise falls through as the raw string, which the
    caller's allowlist then rejects. That fail-closed default is the design and
    it held, but two patterns were slipping THROUGH it in the accepting
    direction, which is the only direction that costs anything:

      "CC BY-NC 4.0"  ->  "cc-by"  ->  ACCEPTED   (NonCommercial)
      "CC BY-ND 4.0"  ->  "cc-by"  ->  ACCEPTED   (NoDerivatives)

    because `"cc by" in "cc by-nc 4.0"` is true. NonCommercial forbids exactly
    what Void does with it, and NoDerivatives is at best arguable once the
    image is re-rendered at WIKI_RENDER_WIDTH. Both are now rejected outright,
    before any permissive pattern is tested.

    The public-domain test was `"pd" in ls`, a two-letter substring that any
    license string could contain by accident, returning the single most
    permissive key we have. It is anchored to the real PD template prefixes
    now. Publishing a copyrighted photograph under a public-domain claim is
    the DMCA 1202(b) exposure that retired the cluster_image_cacher in rev 60;
    the cost of being wrong here is not a broken image, it is a takedown.
    """
    ls = license_str.lower().strip()
    if any(m in ls for m in _NON_FREE_MARKERS):
        return f"non-free:{ls}"
    if "public domain" in ls or ls == "pd" or ls.startswith("pd-"):
        return "public-domain"
    if "cc0" in ls:
        return "cc0"
    if "cc-by-sa" in ls or "cc by-sa" in ls:
        return "cc-by-sa"
    if "cc-by" in ls or "cc by" in ls:
        return "cc-by"
    return ls  # unrecognized: the caller's allowlist rejects it


# ---------------------------------------------------------------------------
# Unsplash (free API key required)
# ---------------------------------------------------------------------------

def search_unsplash(query: str, per_page: int = 5) -> list[ImageResult]:
    """Search Unsplash. Requires UNSPLASH_ACCESS_KEY in env."""
    key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not key:
        return []

    # Over-fetch so the min-resolution filter has headroom and still returns
    # up to per_page usable results.
    fetch_n = min(per_page + 4, 30)
    try:
        resp = _SESSION.get(
            "https://api.unsplash.com/search/photos",
            params={"query": query, "per_page": str(fetch_n), "orientation": "landscape"},
            headers={"Authorization": f"Client-ID {key}"},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [media] Unsplash search failed: {e}")
        return []

    results = []
    dropped_res = 0
    for photo in data.get("results", []):
        if len(results) >= per_page:
            break
        w = photo.get("width", 0)
        h = photo.get("height", 0)
        # Skip low-resolution originals so the served image fills a large frame.
        if w and w < MIN_WIDTH:
            dropped_res += 1
            continue

        user = photo.get("user", {})
        name = user.get("name", "Unknown")
        urls = photo.get("urls", {})
        # Request a high-res render: Unsplash 'raw' accepts dynamic sizing params;
        # fall back to 'full' then 'regular' (~1080px) if raw is absent.
        hi_res = _unsplash_hi_res_url(urls)
        results.append(ImageResult(
            url=hi_res,
            thumbnail_url=urls.get("small", ""),
            width=w,
            height=h,
            alt_text=photo.get("alt_description", "") or photo.get("description", "") or query,
            photographer=name,
            source="unsplash",
            source_url=photo.get("links", {}).get("html", ""),
            license="unsplash-license",
            attribution=f"Photo by {name} on Unsplash",
        ))

    if dropped_res:
        print(f"  [media] Unsplash '{query}': dropped {dropped_res} candidate(s) below "
              f"{MIN_WIDTH}px min-width floor")

    return results


def _unsplash_hi_res_url(urls: dict) -> str:
    """Build a ~2000px-wide render from the Unsplash 'raw' URL.

    'raw' already carries query params (?ixid=...), so append sizing with '&'.
    Falls back to 'full' then 'regular' (~1080px) when 'raw' is unavailable.
    """
    raw = urls.get("raw", "")
    if raw:
        sep = "&" if "?" in raw else "?"
        return f"{raw}{sep}w={UNSPLASH_RENDER_WIDTH}&fit=max&q=80&fm=jpg"
    return urls.get("full", "") or urls.get("regular", "")


# ---------------------------------------------------------------------------
# Pexels (free API key required)
# ---------------------------------------------------------------------------

def search_pexels(query: str, per_page: int = 5) -> list[ImageResult]:
    """Search Pexels. Requires PEXELS_API_KEY in env."""
    key = os.environ.get("PEXELS_API_KEY", "")
    if not key:
        return []

    # Over-fetch so the min-resolution filter has headroom and still returns
    # up to per_page usable results.
    fetch_n = min(per_page + 4, 30)
    try:
        resp = _SESSION.get(
            "https://api.pexels.com/v1/search",
            params={"query": query, "per_page": str(fetch_n), "orientation": "landscape"},
            headers={"Authorization": key},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        print(f"  [media] Pexels search failed: {e}")
        return []

    results = []
    dropped_res = 0
    for photo in data.get("photos", []):
        if len(results) >= per_page:
            break
        w = photo.get("width", 0)
        h = photo.get("height", 0)
        # Skip low-resolution originals so the served image fills a large frame.
        if w and w < MIN_WIDTH:
            dropped_res += 1
            continue

        src = photo.get("src", {})
        # Prefer the full-res 'original'; fall back to 'large2x' (~1880px wide).
        hi_res = src.get("original", "") or src.get("large2x", "")
        results.append(ImageResult(
            url=hi_res,
            thumbnail_url=src.get("medium", ""),
            width=w,
            height=h,
            alt_text=photo.get("alt", "") or query,
            photographer=photo.get("photographer", "Unknown"),
            source="pexels",
            source_url=photo.get("url", ""),
            license="pexels-license",
            attribution=f"Photo by {photo.get('photographer', 'Unknown')} on Pexels",
        ))

    if dropped_res:
        print(f"  [media] Pexels '{query}': dropped {dropped_res} candidate(s) below "
              f"{MIN_WIDTH}px min-width floor")

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
    """Find a cover image for a weekly cover story that Void is allowed to publish.

    Freely licensed sources ONLY, in order: Wikimedia Commons (public domain or
    permissive CC, keyless), then Unsplash and Pexels if keys are configured.
    Returns dict with url, attribution, source, or None when nothing licensed
    fits, which is the correct outcome rather than a fallback.

    This USED to try the publisher's og:image first and reached the free sources
    only if that failed. That is backwards, and it shipped: Issue #26 carried an
    AFP TOPSHOT photograph hotlinked off a Nigerian newspaper's CDN, credited
    "Image via Punch Nigeria". Wire photographs are the highest-risk images on
    the internet to republish, and a publisher putting one in an og:image tag
    grants nothing to anyone who scrapes it. The same reasoning retired the
    cluster_image_cacher in rev 60. `cluster_id` and `supabase_client` are kept
    so the call site is unchanged; neither is read any more.
    """
    if not cluster_title:
        return None

    # Wikimedia Commons. search_wikimedia already refuses anything that is not
    # cc0 / public-domain / cc-by / cc-by-sa.
    for best in search_wikimedia(cluster_title, max_results=3):
        # Serve the WIKI_RENDER_WIDTH render, not the Commons original. The
        # original is the camera's full-resolution file and is routinely tens of
        # megabytes; hotlinking it puts that on the cover of every weekly page
        # load. `iiurlwidth` is requested precisely so `thumburl` exists, and it
        # was being computed and then discarded here.
        url = best.thumbnail_url or best.url
        if verify_image(url):
            return {
                "url": url,
                "attribution": best.attribution,
                "source": "wikimedia",
            }

    # Unsplash / Pexels, whose licences permit commercial use. Only reachable
    # when an API key is configured; both are absent by default.
    for src in ("unsplash", "pexels"):
        fn = _SEARCH_FNS.get(src)
        if not fn:
            continue
        try:
            results = fn(cluster_title, per_page=3)
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
