"""
Structured data API clients.

APIs: Wikidata SPARQL (entity data), Slave Voyages (Trans-Atlantic).
All free, no API keys required.
"""

from .base import BaseHistoryAPI, EnrichmentResult


class WikidataEntityAPI(BaseHistoryAPI):
    """Wikidata SPARQL -- structured entity data (people, events, places).

    Distinct from WikidataGeoAPI (geodata.py) which focuses on coordinates.
    This client extracts structured facts: dates, participants, outcomes, statistics.

    Docs: https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service
    Rate limit: 60 req/min, max 30s query time.
    """
    API_NAME = "wikidata"
    CATEGORY = "structured_data"
    BASE_URL = "https://query.wikidata.org/sparql"
    RATE_LIMIT_DELAY = 2.0

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        # Search for entities matching the query
        try:
            data = self._get("https://www.wikidata.org/w/api.php", params={
                "action": "wbsearchentities",
                "search": query,
                "language": "en",
                "limit": str(min(max_results, 10)),
                "format": "json",
            })
        except Exception as e:
            print(f"  [{self.API_NAME}] Entity search failed: {e}")
            return []

        results = []
        for item in data.get("search", [])[:max_results]:
            entity_id = item.get("id", "")
            label = item.get("label", "")
            desc = item.get("description", "")

            if not label:
                continue

            # Fetch key claims for this entity
            claims = self._get_key_claims(entity_id)

            results.append(EnrichmentResult(
                category=self.CATEGORY,
                api_source=self.API_NAME,
                title=label,
                description=desc[:300] if desc else "",
                url=f"https://www.wikidata.org/wiki/{entity_id}",
                license="cc0",
                metadata={
                    "wikidata_id": entity_id,
                    "claims": claims,
                },
            ))

        return results

    def _get_key_claims(self, entity_id: str) -> dict:
        """Fetch structured claims for an entity (dates, coordinates, etc.)."""
        try:
            data = self._get("https://www.wikidata.org/w/api.php", params={
                "action": "wbgetentities",
                "ids": entity_id,
                "props": "claims",
                "format": "json",
            })
        except Exception:
            return {}

        entity = data.get("entities", {}).get(entity_id, {})
        claims = entity.get("claims", {})

        # Extract key properties
        extracted = {}
        property_map = {
            "P580": "start_date",
            "P582": "end_date",
            "P585": "point_in_time",
            "P625": "coordinates",
            "P17": "country",
            "P1120": "number_of_deaths",
            "P1590": "number_of_casualties",
        }

        for prop_id, label in property_map.items():
            if prop_id in claims:
                claim = claims[prop_id][0]
                mainsnak = claim.get("mainsnak", {})
                datavalue = mainsnak.get("datavalue", {})
                if datavalue:
                    extracted[label] = self._extract_value(datavalue)

        return extracted

    @staticmethod
    def _extract_value(datavalue: dict) -> str:
        """Extract human-readable value from Wikidata datavalue."""
        val_type = datavalue.get("type", "")
        value = datavalue.get("value", "")

        if val_type == "time":
            return value.get("time", "")[:11].lstrip("+")  # e.g. "1947-08-15"
        elif val_type == "quantity":
            return value.get("amount", "").lstrip("+")
        elif val_type == "globecoordinate":
            return f"{value.get('latitude', 0)}, {value.get('longitude', 0)}"
        elif val_type == "wikibase-entityid":
            return f"Q{value.get('numeric-id', '')}"
        elif val_type == "string":
            return str(value)
        return str(value)


class SlaveVoyagesAPI(BaseHistoryAPI):
    """Slave Voyages (Trans-Atlantic Slave Trade Database). Free, no key.

    Docs: https://www.slavevoyages.org/api/
    Rate limit: Be polite, no published limit.

    Relevant only for: transatlantic-slave-trade, scramble-for-africa, and
    related events. Returns empty for unrelated events.
    """
    API_NAME = "slave_voyages"
    CATEGORY = "structured_data"
    BASE_URL = "https://www.slavevoyages.org/api/v2"
    RATE_LIMIT_DELAY = 2.0

    # Events where this API is relevant
    RELEVANT_SLUGS = {
        "transatlantic-slave-trade",
        "scramble-for-africa",
        "haitian-revolution",
        "american-civil-war",
    }

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        if event_slug not in self.RELEVANT_SLUGS:
            return []

        # Search for voyages matching the query
        try:
            self._rate_limit()
            resp = self._session.post(
                f"{self.BASE_URL}/voyage/",
                json={"search_query": [{"op": "contains", "varName": "voyage_ship__ship_name", "searchTerm": query}]},
                headers={"Content-Type": "application/json"},
                timeout=20,
            )
            if resp.status_code != 200:
                # Fall back to providing a link to the database
                return [EnrichmentResult(
                    category=self.CATEGORY,
                    api_source=self.API_NAME,
                    title="Trans-Atlantic Slave Trade Database",
                    description="Interactive database of 36,000+ voyages with embarked/disembarked counts, ship details, and routes.",
                    url="https://www.slavevoyages.org/voyage/database",
                    license="open-access",
                    metadata={"note": "Use the interactive database for detailed voyage searches"},
                )]
        except Exception:
            return [EnrichmentResult(
                category=self.CATEGORY,
                api_source=self.API_NAME,
                title="Trans-Atlantic Slave Trade Database",
                description="36,000+ documented voyages. API available for programmatic access.",
                url="https://www.slavevoyages.org/voyage/database",
                license="open-access",
            )]

        return []


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

STRUCTURED_APIS = {
    "wikidata": WikidataEntityAPI,
    "slave_voyages": SlaveVoyagesAPI,
}
