"""
Primary source / archival API clients.

APIs: Library of Congress, Europeana, DPLA, Gallica (BnF).
All free, no API keys required (LOC, Gallica) or free-tier key (Europeana, DPLA).
"""

from .base import BaseHistoryAPI, EnrichmentResult


class LibraryOfCongressAPI(BaseHistoryAPI):
    """Library of Congress -- free, no key needed.

    Docs: https://www.loc.gov/apis/
    Rate limit: Be polite (1 req/s recommended).
    """
    API_NAME = "loc"
    CATEGORY = "primary_source"
    BASE_URL = "https://www.loc.gov"
    RATE_LIMIT_DELAY = 1.5

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        data = self._get(f"{self.BASE_URL}/search/", params={
            "q": query,
            "fo": "json",
            "c": str(min(max_results * 2, 25)),  # fetch extra, filter later
            "fa": "online-format:image|online-format:text",
        })

        results = []
        for item in data.get("results", [])[:max_results * 2]:
            if len(results) >= max_results:
                break

            title = item.get("title", "")
            if not title:
                continue

            url = item.get("url", "") or item.get("id", "")
            date = item.get("date", "")
            description = item.get("description", [""])[0] if isinstance(item.get("description"), list) else item.get("description", "")

            # Extract contributor/creator
            contributors = item.get("contributor", [])
            creator = contributors[0] if contributors else ""

            # Determine format
            formats = item.get("online_format", [])

            results.append(EnrichmentResult(
                category=self.CATEGORY,
                api_source=self.API_NAME,
                title=title[:200],
                description=description[:300] if description else "",
                url=url,
                date=date if date else None,
                creator=creator[:100] if creator else None,
                license="public-domain",  # LOC digitized materials are generally PD
                metadata={
                    "formats": formats[:5],
                    "collection": item.get("partof", [""])[0] if item.get("partof") else "",
                    "subjects": item.get("subject", [])[:5],
                },
            ))

        return results


class EuropeanaAPI(BaseHistoryAPI):
    """Europeana -- European cultural heritage. Free API key required.

    Docs: https://pro.europeana.eu/page/search
    Rate limit: 10 req/s with API key.
    Key: Free at https://pro.europeana.eu/page/get-api -- store as EUROPEANA_API_KEY.
    """
    API_NAME = "europeana"
    CATEGORY = "primary_source"
    BASE_URL = "https://api.europeana.eu/record/v2"
    RATE_LIMIT_DELAY = 1.0

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        import os
        key = os.environ.get("EUROPEANA_API_KEY", "")
        if not key:
            print(f"  [{self.API_NAME}] No EUROPEANA_API_KEY set, skipping")
            return []

        data = self._get(f"{self.BASE_URL}/search.json", params={
            "wskey": key,
            "query": query,
            "rows": str(min(max_results, 20)),
            "profile": "standard",
            "reusability": "open",  # only openly licensed content
        })

        results = []
        for item in data.get("items", [])[:max_results]:
            title_list = item.get("title", [""])
            title = title_list[0] if title_list else ""
            if not title:
                continue

            # Europeana item URL
            item_id = item.get("id", "")
            url = f"https://www.europeana.eu/item{item_id}" if item_id else ""

            # Thumbnail
            edmPreview = item.get("edmPreview", [""])
            thumb = edmPreview[0] if edmPreview else ""

            # Creator
            creators = item.get("dcCreator", [])
            creator = creators[0] if creators else ""

            # Date
            dates = item.get("year", [])
            date = dates[0] if dates else None

            # Rights
            rights_list = item.get("rights", [""])
            rights = rights_list[0] if rights_list else ""

            results.append(EnrichmentResult(
                category=self.CATEGORY,
                api_source=self.API_NAME,
                title=title[:200],
                description=f"Provider: {item.get('dataProvider', [''])[0]}",
                url=url,
                date=date,
                creator=creator[:100] if creator else None,
                license=_normalize_europeana_rights(rights),
                metadata={
                    "thumbnail": thumb,
                    "type": item.get("type", ""),
                    "provider": item.get("dataProvider", [""])[0] if item.get("dataProvider") else "",
                    "country": item.get("country", [""])[0] if item.get("country") else "",
                },
            ))

        return results


class DPLAAPI(BaseHistoryAPI):
    """Digital Public Library of America -- free, API key required.

    Docs: https://pro.dp.la/developers/api-codex
    Rate limit: 200 req/day (free tier).
    Key: Free at https://dp.la/info/developers/codex -- store as DPLA_API_KEY.
    """
    API_NAME = "dpla"
    CATEGORY = "primary_source"
    BASE_URL = "https://api.dp.la/v2"
    RATE_LIMIT_DELAY = 2.0  # conservative given 200/day limit

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        import os
        key = os.environ.get("DPLA_API_KEY", "")
        if not key:
            print(f"  [{self.API_NAME}] No DPLA_API_KEY set, skipping")
            return []

        data = self._get(f"{self.BASE_URL}/items", params={
            "api_key": key,
            "q": query,
            "page_size": str(min(max_results, 20)),
        })

        results = []
        for doc in data.get("docs", [])[:max_results]:
            source_resource = doc.get("sourceResource", {})
            titles = source_resource.get("title", [])
            title = titles[0] if isinstance(titles, list) and titles else str(titles) if titles else ""
            if not title:
                continue

            url = doc.get("isShownAt", "") or doc.get("@id", "")
            dates = source_resource.get("date", [{}])
            date = dates[0].get("displayDate", "") if isinstance(dates, list) and dates else ""
            creators = source_resource.get("creator", [])
            creator = creators[0] if isinstance(creators, list) and creators else ""
            descriptions = source_resource.get("description", [])
            description = descriptions[0] if isinstance(descriptions, list) and descriptions else ""

            results.append(EnrichmentResult(
                category=self.CATEGORY,
                api_source=self.API_NAME,
                title=title[:200],
                description=description[:300] if description else "",
                url=url,
                date=date if date else None,
                creator=creator[:100] if creator else None,
                license="varies",  # DPLA aggregates; rights vary
                metadata={
                    "provider": doc.get("provider", {}).get("name", ""),
                    "data_provider": doc.get("dataProvider", ""),
                    "type": source_resource.get("type", ""),
                },
            ))

        return results


class GallicaAPI(BaseHistoryAPI):
    """Gallica (BnF) -- French national library. Free, no key needed.

    Docs: https://api.bnf.fr/api-gallica-de-recherche
    Rate limit: Be polite (1 req/s).
    """
    API_NAME = "gallica"
    CATEGORY = "primary_source"
    BASE_URL = "https://gallica.bnf.fr/SRU"
    RATE_LIMIT_DELAY = 1.5

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        import xml.etree.ElementTree as ET

        self._rate_limit()
        try:
            resp = self._session.get(self.BASE_URL, params={
                "operation": "searchRetrieve",
                "version": "1.2",
                "query": f'dc.title all "{query}" or dc.subject all "{query}"',
                "maximumRecords": str(min(max_results, 15)),
                "recordSchema": "dc",
            }, timeout=20)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [{self.API_NAME}] Request failed: {e}")
            return []

        # Parse XML response
        results = []
        try:
            root = ET.fromstring(resp.text)
            ns = {
                "srw": "http://www.loc.gov/zing/srw/",
                "dc": "http://purl.org/dc/elements/1.1/",
            }
            for record in root.findall(".//srw:record", ns)[:max_results]:
                rec_data = record.find(".//srw:recordData", ns)
                if rec_data is None:
                    continue

                title_el = rec_data.find(".//dc:title", ns)
                title = title_el.text if title_el is not None and title_el.text else ""
                if not title:
                    continue

                id_el = rec_data.find(".//dc:identifier", ns)
                url = id_el.text if id_el is not None and id_el.text else ""

                creator_el = rec_data.find(".//dc:creator", ns)
                creator = creator_el.text if creator_el is not None else ""

                date_el = rec_data.find(".//dc:date", ns)
                date = date_el.text if date_el is not None else ""

                desc_el = rec_data.find(".//dc:description", ns)
                description = desc_el.text if desc_el is not None else ""

                results.append(EnrichmentResult(
                    category=self.CATEGORY,
                    api_source=self.API_NAME,
                    title=title[:200],
                    description=description[:300] if description else "",
                    url=url,
                    date=date if date else None,
                    creator=creator[:100] if creator else None,
                    license="public-domain",  # Gallica digitizations are generally PD
                    metadata={
                        "source": "Bibliotheque nationale de France",
                    },
                ))
        except ET.ParseError as e:
            print(f"  [{self.API_NAME}] XML parse error: {e}")

        return results


def _normalize_europeana_rights(rights_url: str) -> str:
    """Map Europeana rights URLs to standard keys."""
    if not rights_url:
        return "unknown"
    r = rights_url.lower()
    if "publicdomain" in r or "/pdm/" in r:
        return "public-domain"
    if "cc0" in r:
        return "cc0"
    if "by-sa" in r:
        return "cc-by-sa"
    if "by-nc" in r:
        return "cc-by-nc"  # flagged but not used
    if "/by/" in r:
        return "cc-by"
    return "unknown"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ARCHIVE_APIS = {
    "loc": LibraryOfCongressAPI,
    "europeana": EuropeanaAPI,
    "dpla": DPLAAPI,
    "gallica": GallicaAPI,
}
