"""
Maps and geospatial data API clients.

APIs: Wikidata (GeoJSON via SPARQL), Pleiades (ancient places).
All free, no API keys required.

Note: CShapes, Natural Earth, David Rumsey are download-based datasets, not APIs.
The archive-cartographer agent handles those directly. This module provides
the API-queryable sources only.
"""

from .base import BaseHistoryAPI, EnrichmentResult


class WikidataGeoAPI(BaseHistoryAPI):
    """Wikidata SPARQL -- geospatial queries for historical places.

    Docs: https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service
    Rate limit: 60 req/min, max 30s query time.
    """
    API_NAME = "wikidata_geo"
    CATEGORY = "map"
    BASE_URL = "https://query.wikidata.org/sparql"
    RATE_LIMIT_DELAY = 2.0

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        # SPARQL query for places matching the query with coordinates
        sparql = f"""
        SELECT ?place ?placeLabel ?coord ?description WHERE {{
          ?place wdt:P31/wdt:P279* wd:Q2221906 .
          ?place rdfs:label ?label .
          FILTER(LANG(?label) = "en")
          FILTER(CONTAINS(LCASE(?label), LCASE("{query[:50]}")))
          OPTIONAL {{ ?place wdt:P625 ?coord . }}
          OPTIONAL {{ ?place schema:description ?description . FILTER(LANG(?description) = "en") }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" . }}
        }}
        LIMIT {min(max_results, 20)}
        """

        try:
            self._rate_limit()
            resp = self._session.get(self.BASE_URL, params={
                "query": sparql,
                "format": "json",
            }, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            # Fall back to simpler entity search
            return self._fallback_search(query, max_results)

        results = []
        for binding in data.get("results", {}).get("bindings", [])[:max_results]:
            label = binding.get("placeLabel", {}).get("value", "")
            if not label:
                continue

            entity_url = binding.get("place", {}).get("value", "")
            coord = binding.get("coord", {}).get("value", "")
            desc = binding.get("description", {}).get("value", "")

            # Parse Point(lon lat) from WKT
            lat, lon = None, None
            if coord and "Point(" in coord:
                try:
                    coords = coord.replace("Point(", "").replace(")", "").split()
                    lon, lat = float(coords[0]), float(coords[1])
                except (ValueError, IndexError):
                    pass

            results.append(EnrichmentResult(
                category=self.CATEGORY,
                api_source=self.API_NAME,
                title=label,
                description=desc[:300] if desc else "",
                url=entity_url,
                license="cc0",  # Wikidata is CC0
                metadata={
                    "coordinates": {"lat": lat, "lon": lon} if lat is not None else None,
                    "wikidata_id": entity_url.split("/")[-1] if entity_url else "",
                },
            ))

        return results

    def _fallback_search(self, query: str, max_results: int) -> list[EnrichmentResult]:
        """Simpler Wikidata entity search when SPARQL fails."""
        try:
            data = self._get("https://www.wikidata.org/w/api.php", params={
                "action": "wbsearchentities",
                "search": query,
                "language": "en",
                "limit": str(min(max_results, 10)),
                "format": "json",
            })
        except Exception:
            return []

        results = []
        for item in data.get("search", []):
            results.append(EnrichmentResult(
                category=self.CATEGORY,
                api_source=self.API_NAME,
                title=item.get("label", ""),
                description=item.get("description", ""),
                url=item.get("concepturi", ""),
                license="cc0",
                metadata={"wikidata_id": item.get("id", "")},
            ))
        return results


class PleiadesAPI(BaseHistoryAPI):
    """Pleiades -- ancient places gazetteer. Free, no key needed.

    Docs: https://pleiades.stoa.org/help/api
    Rate limit: Be polite (1 req/s).

    Note: Best for ancient/classical/medieval events. Returns empty for modern events.
    """
    API_NAME = "pleiades"
    CATEGORY = "map"
    BASE_URL = "https://pleiades.stoa.org"
    RATE_LIMIT_DELAY = 1.5

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        # Pleiades search endpoint
        data = self._get(f"{self.BASE_URL}/search_kml", params={
            "SearchableText": query,
            "portal_type": "Place",
            "review_state": "published",
        })

        # Pleiades returns KML, but the JSON search is more practical
        # Use the JSON places endpoint instead
        try:
            self._rate_limit()
            resp = self._session.get(f"{self.BASE_URL}/search", params={
                "SearchableText": query,
                "portal_type": "Place",
                "review_state": "published",
            }, headers={"Accept": "application/json"}, timeout=20)
            if resp.status_code != 200:
                return []
            # Pleiades may not return JSON for search; fall back to known-good API
            return self._search_via_json(query, max_results)
        except Exception:
            return self._search_via_json(query, max_results)

    def _search_via_json(self, query: str, max_results: int) -> list[EnrichmentResult]:
        """Use Pleiades JSON API for individual place lookups."""
        # Pleiades doesn't have a great search API; this is a best-effort approach
        # For production, we'd use their CSV/GeoJSON dump files
        results = []
        try:
            self._rate_limit()
            resp = self._session.get(
                f"https://pleiades.stoa.org/search_rss",
                params={"SearchableText": query, "portal_type": "Place"},
                timeout=20,
            )
            if resp.status_code != 200:
                return []

            # Parse RSS response
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.text)
            for item in root.findall(".//item")[:max_results]:
                title = item.findtext("title", "")
                link = item.findtext("link", "")
                desc = item.findtext("description", "")
                if title and link:
                    results.append(EnrichmentResult(
                        category=self.CATEGORY,
                        api_source=self.API_NAME,
                        title=title[:200],
                        description=desc[:300] if desc else "",
                        url=link,
                        license="cc-by",  # Pleiades is CC-BY
                        metadata={"source": "Pleiades gazetteer"},
                    ))
        except Exception as e:
            print(f"  [{self.API_NAME}] RSS parse error: {e}")

        return results


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

GEODATA_APIS = {
    "wikidata_geo": WikidataGeoAPI,
    "pleiades": PleiadesAPI,
}
