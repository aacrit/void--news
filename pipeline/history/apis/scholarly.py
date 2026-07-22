"""
Scholarly works API clients.

APIs: OpenAlex, Semantic Scholar, CORE, Crossref, Unpaywall.
All free tier, no API keys required (OpenAlex, Crossref, Semantic Scholar public).
"""

from .base import BaseHistoryAPI, EnrichmentResult


class OpenAlexAPI(BaseHistoryAPI):
    """OpenAlex -- free scholarly metadata. 100K works, no key needed.

    Docs: https://docs.openalex.org/
    Rate limit: 10 req/s unauthenticated, 100 req/s with polite pool (mailto).
    """
    API_NAME = "openalex"
    CATEGORY = "scholarly"
    BASE_URL = "https://api.openalex.org"
    RATE_LIMIT_DELAY = 0.5

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        data = self._get(f"{self.BASE_URL}/works", params={
            "search": query,
            "per_page": str(min(max_results, 25)),
            "sort": "relevance_score:desc",
            "mailto": "void-news@proton.me",  # polite pool access
        })

        results = []
        for work in data.get("results", [])[:max_results]:
            title = work.get("title", "")
            if not title:
                continue

            # Extract open access URL if available
            oa = work.get("open_access", {})
            url = oa.get("oa_url") or work.get("doi", "") or work.get("id", "")
            if url and url.startswith("https://doi.org/"):
                pass  # keep DOI URL
            elif work.get("doi"):
                url = work["doi"]

            # Publication year
            year = work.get("publication_year")

            # Authors
            authors = []
            for authorship in work.get("authorships", [])[:3]:
                name = authorship.get("author", {}).get("display_name", "")
                if name:
                    authors.append(name)
            author_str = ", ".join(authors) if authors else "Unknown"

            # Cited-by count for relevance
            cited = work.get("cited_by_count", 0)

            results.append(EnrichmentResult(
                category=self.CATEGORY,
                api_source=self.API_NAME,
                title=title,
                description=f"Cited by {cited} works. {author_str} ({year})." if year else f"Cited by {cited} works. {author_str}.",
                url=url,
                date=str(year) if year else None,
                creator=author_str,
                license="open-access" if oa.get("is_oa") else "unknown",
                metadata={
                    "cited_by_count": cited,
                    "is_open_access": oa.get("is_oa", False),
                    "type": work.get("type", ""),
                    "openalex_id": work.get("id", ""),
                },
            ))

        return results


class SemanticScholarAPI(BaseHistoryAPI):
    """Semantic Scholar -- AI2's academic graph. Free, no key for basic search.

    Docs: https://api.semanticscholar.org/
    Rate limit: 100 req/5min unauthenticated.
    """
    API_NAME = "semantic_scholar"
    CATEGORY = "scholarly"
    BASE_URL = "https://api.semanticscholar.org/graph/v1"
    RATE_LIMIT_DELAY = 3.0  # conservative for unauthenticated

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        data = self._get(f"{self.BASE_URL}/paper/search", params={
            "query": query,
            "limit": str(min(max_results, 20)),
            "fields": "title,authors,year,citationCount,url,openAccessPdf,abstract",
        })

        results = []
        for paper in data.get("data", [])[:max_results]:
            title = paper.get("title", "")
            if not title:
                continue

            authors = [a.get("name", "") for a in paper.get("authors", [])[:3]]
            author_str = ", ".join(a for a in authors if a) or "Unknown"
            year = paper.get("year")
            cited = paper.get("citationCount", 0)
            url = paper.get("openAccessPdf", {}).get("url") or paper.get("url", "")

            results.append(EnrichmentResult(
                category=self.CATEGORY,
                api_source=self.API_NAME,
                title=title,
                description=f"Cited by {cited}. {author_str} ({year})." if year else f"Cited by {cited}. {author_str}.",
                url=url,
                date=str(year) if year else None,
                creator=author_str,
                license="open-access" if paper.get("openAccessPdf") else "unknown",
                metadata={
                    "cited_by_count": cited,
                    "abstract": (paper.get("abstract") or "")[:300],
                },
            ))

        return results


class CrossrefAPI(BaseHistoryAPI):
    """Crossref -- DOI metadata registry. Free, no key needed.

    Docs: https://api.crossref.org/
    Rate limit: 50 req/s with polite pool (mailto header).
    """
    API_NAME = "crossref"
    CATEGORY = "scholarly"
    BASE_URL = "https://api.crossref.org"
    RATE_LIMIT_DELAY = 1.0

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        data = self._get(f"{self.BASE_URL}/works", params={
            "query": query,
            "rows": str(min(max_results, 20)),
            "sort": "relevance",
            "mailto": "void-news@proton.me",
        })

        results = []
        for item in data.get("message", {}).get("items", [])[:max_results]:
            titles = item.get("title", [])
            title = titles[0] if titles else ""
            if not title:
                continue

            authors = []
            for a in item.get("author", [])[:3]:
                name = f"{a.get('given', '')} {a.get('family', '')}".strip()
                if name:
                    authors.append(name)
            author_str = ", ".join(authors) if authors else "Unknown"

            # Extract year from date-parts
            date_parts = item.get("published-print", {}).get("date-parts", [[]])
            if not date_parts[0]:
                date_parts = item.get("published-online", {}).get("date-parts", [[]])
            year = str(date_parts[0][0]) if date_parts and date_parts[0] else None

            doi = item.get("DOI", "")
            url = f"https://doi.org/{doi}" if doi else item.get("URL", "")

            results.append(EnrichmentResult(
                category=self.CATEGORY,
                api_source=self.API_NAME,
                title=title,
                description=f"{author_str} ({year}). {item.get('type', 'article')}." if year else f"{author_str}. {item.get('type', 'article')}.",
                url=url,
                date=year,
                creator=author_str,
                metadata={
                    "doi": doi,
                    "type": item.get("type", ""),
                    "references_count": item.get("references-count", 0),
                },
            ))

        return results


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

SCHOLARLY_APIS = {
    "openalex": OpenAlexAPI,
    "semantic_scholar": SemanticScholarAPI,
    "crossref": CrossrefAPI,
}
