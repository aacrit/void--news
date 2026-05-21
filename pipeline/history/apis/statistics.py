"""
Statistical data API clients.

APIs: World Bank, V-Dem (Varieties of Democracy).
All free, no API keys required.

Note: Our World in Data is download-based (GitHub CSVs), not an API.
Maddison Project data is download-based (Excel). Both are referenced
in enrichment results as manual-lookup suggestions when relevant.
"""

from .base import BaseHistoryAPI, EnrichmentResult


class WorldBankAPI(BaseHistoryAPI):
    """World Bank Open Data -- 16,000+ development indicators. Free, no key.

    Docs: https://datahelpdesk.worldbank.org/knowledgebase/topics/125589
    Rate limit: No published limit, be polite.
    """
    API_NAME = "world_bank"
    CATEGORY = "statistical"
    BASE_URL = "https://api.worldbank.org/v2"
    RATE_LIMIT_DELAY = 1.0

    # Indicators relevant to historical events
    RELEVANT_INDICATORS = {
        "SP.POP.TOTL": "Population, total",
        "NY.GDP.MKTP.CD": "GDP (current US$)",
        "SP.DYN.LE00.IN": "Life expectancy at birth",
        "SE.ADT.LITR.ZS": "Literacy rate, adult total",
        "SH.DYN.MORT": "Mortality rate, under-5",
        "SM.POP.REFG.OR": "Refugee population by country of origin",
        "VC.IDP.TOTL.HE": "Internally displaced persons",
    }

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        """Search for country-level indicators relevant to the event.

        For statistical APIs, 'query' should be formatted as:
        "country_code:year_range" e.g. "IND:1945-1950" or "DEU:1989-1991"
        Falls back to country search if format doesn't match.
        """
        results = []

        # Parse country code and year range from query
        parts = query.split(":")
        if len(parts) == 2:
            country = parts[0].strip()
            year_range = parts[1].strip()
        else:
            # Try to find country data via free-text
            return self._search_countries(query, max_results)

        # Fetch key indicators for the country/period
        for indicator, label in list(self.RELEVANT_INDICATORS.items())[:max_results]:
            try:
                data = self._get(
                    f"{self.BASE_URL}/country/{country}/indicator/{indicator}",
                    params={
                        "date": year_range,
                        "format": "json",
                        "per_page": "50",
                    }
                )

                # World Bank returns [metadata, data] tuple
                if not isinstance(data, list) or len(data) < 2:
                    continue

                records = data[1]
                if not records:
                    continue

                # Find non-null data points
                values = [(r["date"], r["value"]) for r in records if r.get("value") is not None]
                if not values:
                    continue

                country_name = records[0].get("country", {}).get("value", country)
                value_summary = "; ".join(f"{y}: {v:,.0f}" if isinstance(v, (int, float)) else f"{y}: {v}" for y, v in values[:5])

                results.append(EnrichmentResult(
                    category=self.CATEGORY,
                    api_source=self.API_NAME,
                    title=f"{label} -- {country_name} ({year_range})",
                    description=value_summary,
                    url=f"https://data.worldbank.org/indicator/{indicator}?locations={country}",
                    date=year_range,
                    license="cc-by",  # World Bank data is CC-BY 4.0
                    metadata={
                        "indicator": indicator,
                        "country_code": country,
                        "data_points": len(values),
                        "values": {y: v for y, v in values[:10]},
                    },
                ))
            except Exception as e:
                print(f"  [{self.API_NAME}] {indicator} failed: {e}")
                continue

        return results[:max_results]

    def _search_countries(self, query: str, max_results: int) -> list[EnrichmentResult]:
        """Fallback: search for countries matching query."""
        try:
            data = self._get(f"{self.BASE_URL}/country", params={
                "format": "json",
                "per_page": "300",
            })
            if not isinstance(data, list) or len(data) < 2:
                return []

            query_lower = query.lower()
            matches = [
                c for c in data[1]
                if query_lower in c.get("name", "").lower() or query_lower in c.get("region", {}).get("value", "").lower()
            ]

            return [
                EnrichmentResult(
                    category=self.CATEGORY,
                    api_source=self.API_NAME,
                    title=f"World Bank data available: {c['name']}",
                    description=f"Region: {c.get('region', {}).get('value', '')}. "
                               f"Income: {c.get('incomeLevel', {}).get('value', '')}.",
                    url=f"https://data.worldbank.org/country/{c.get('id', '')}",
                    license="cc-by",
                    metadata={"country_code": c.get("id", ""), "iso2": c.get("iso2Code", "")},
                )
                for c in matches[:max_results]
            ]
        except Exception:
            return []


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

STATISTICS_APIS = {
    "world_bank": WorldBankAPI,
}
