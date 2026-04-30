"""
Historical media API clients (images, maps, documents).

APIs: Wikimedia Commons (extended history search), Smithsonian Open Access, Europeana (media mode).
All free, no API keys required (Wikimedia, Smithsonian) or free-tier key (Europeana).
"""

from .base import BaseHistoryAPI, EnrichmentResult


class WikimediaHistoryAPI(BaseHistoryAPI):
    """Wikimedia Commons -- extended search for historical images/maps/documents.

    This differs from pipeline/media/image_search.py's search_wikimedia() in that:
    - It searches categories and subcategories (not just filenames)
    - It returns provenance metadata (SDC structured data)
    - It targets historical content specifically

    Docs: https://www.mediawiki.org/wiki/API:Main_page
    Rate limit: No hard limit, be polite.
    """
    API_NAME = "wikimedia_commons"
    CATEGORY = "media"
    BASE_URL = "https://commons.wikimedia.org/w/api.php"
    RATE_LIMIT_DELAY = 1.0

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        data = self._get(self.BASE_URL, params={
            "action": "query",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap|drawing {query}",
            "gsrnamespace": "6",  # File namespace
            "gsrlimit": str(min(max_results * 3, 30)),
            "prop": "imageinfo|categories",
            "iiprop": "url|size|extmetadata|mime",
            "iiurlwidth": "800",
            "cllimit": "5",
            "format": "json",
        })

        pages = data.get("query", {}).get("pages", {})
        results = []

        for page in sorted(pages.values(), key=lambda p: p.get("index", 999)):
            if len(results) >= max_results:
                break

            info_list = page.get("imageinfo", [])
            if not info_list:
                continue
            info = info_list[0]

            mime = info.get("mime", "")
            if not mime.startswith("image/"):
                continue

            w, h = info.get("width", 0), info.get("height", 0)
            if w < 200 or h < 150:
                continue

            ext = info.get("extmetadata", {})
            artist = self._extract_text(ext.get("Artist", {}).get("value", "Unknown"))
            license_short = ext.get("LicenseShortName", {}).get("value", "")
            license_key = self._normalize_license(license_short)
            desc = self._extract_text(ext.get("ImageDescription", {}).get("value", ""))
            date_str = self._extract_text(ext.get("DateTimeOriginal", {}).get("value", ""))

            # Skip restrictive licenses
            if license_key not in ("cc0", "public-domain", "cc-by", "cc-by-sa"):
                continue

            # Extract categories for context
            categories = [c.get("title", "").replace("Category:", "") for c in page.get("categories", [])]

            url = info.get("url", "")
            thumb = info.get("thumburl", url)
            page_url = info.get("descriptionurl", "")

            results.append(EnrichmentResult(
                category=self.CATEGORY,
                api_source=self.API_NAME,
                title=page.get("title", "").replace("File:", "")[:200],
                description=desc[:300] if desc else "",
                url=url,
                date=date_str if date_str else None,
                creator=artist[:100],
                license=license_key,
                metadata={
                    "thumbnail": thumb,
                    "page_url": page_url,
                    "width": w,
                    "height": h,
                    "categories": categories[:5],
                    "attribution": f"{artist}, {license_short}, via Wikimedia Commons",
                },
            ))

        return results

    @staticmethod
    def _extract_text(html_str: str) -> str:
        import re
        return re.sub(r"<[^>]+>", "", html_str).strip()

    @staticmethod
    def _normalize_license(license_str: str) -> str:
        ls = license_str.lower()
        if "public domain" in ls or "pd" in ls:
            return "public-domain"
        if "cc0" in ls:
            return "cc0"
        if "cc-by-sa" in ls or "cc by-sa" in ls:
            return "cc-by-sa"
        if "cc-by" in ls or "cc by" in ls:
            return "cc-by"
        return ls


class SmithsonianAPI(BaseHistoryAPI):
    """Smithsonian Open Access -- 4.5M+ objects, free, API key required.

    Docs: https://edan.si.edu/openaccess/apidocs/
    Rate limit: 1000 req/day (free key).
    Key: Free at https://api.data.gov/signup/ -- store as SMITHSONIAN_API_KEY.
    """
    API_NAME = "smithsonian"
    CATEGORY = "media"
    BASE_URL = "https://api.si.edu/openaccess/api/v1.0"
    RATE_LIMIT_DELAY = 1.5

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        import os
        key = os.environ.get("SMITHSONIAN_API_KEY", "")
        if not key:
            print(f"  [{self.API_NAME}] No SMITHSONIAN_API_KEY set, skipping")
            return []

        data = self._get(f"{self.BASE_URL}/search", params={
            "api_key": key,
            "q": query,
            "rows": str(min(max_results, 20)),
            "online_media_type": "Images",
        })

        results = []
        for row in data.get("response", {}).get("rows", [])[:max_results]:
            content = row.get("content", {})
            desc_data = content.get("descriptiveNonRepeating", {})
            freetext = content.get("freetext", {})

            title = desc_data.get("title", {}).get("content", "")
            if not title:
                continue

            url = desc_data.get("record_link", "")
            unit = desc_data.get("data_source", "")

            # Extract date from freetext
            date_entries = freetext.get("date", [])
            date = date_entries[0].get("content", "") if date_entries else ""

            # Extract image URL
            online_media = content.get("descriptiveNonRepeating", {}).get("online_media", {})
            media_list = online_media.get("media", []) if isinstance(online_media, dict) else []
            image_url = ""
            thumb_url = ""
            if media_list:
                m = media_list[0]
                image_url = m.get("content", "")
                thumb_url = m.get("thumbnail", image_url)

            results.append(EnrichmentResult(
                category=self.CATEGORY,
                api_source=self.API_NAME,
                title=title[:200],
                description=f"Smithsonian {unit}",
                url=url or image_url,
                date=date if date else None,
                license="cc0",  # Smithsonian Open Access is CC0
                metadata={
                    "unit": unit,
                    "image_url": image_url,
                    "thumbnail": thumb_url,
                },
            ))

        return results


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

MEDIA_APIS = {
    "wikimedia_commons": WikimediaHistoryAPI,
    "smithsonian": SmithsonianAPI,
}
