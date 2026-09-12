"""
Base API client with shared session, rate limiting, and result types.

All history source enrichment APIs inherit from BaseHistoryAPI.
"""

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Optional

import requests


# ---------------------------------------------------------------------------
# Shared result types
# ---------------------------------------------------------------------------

@dataclass
class EnrichmentResult:
    """A single enrichment finding from any API category."""
    category: str          # "primary_source" | "scholarly" | "media" | "map" | "statistical" | "oral_history" | "structured_data"
    api_source: str        # e.g. "openalex", "loc", "wikimedia_commons", "wikidata"
    title: str
    description: str
    url: str
    date: Optional[str] = None
    creator: Optional[str] = None
    license: Optional[str] = None
    relevance_note: str = ""    # Why this result matters for this event
    metadata: dict = field(default_factory=dict)  # API-specific extra fields

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None and v != "" and v != {}}


# ---------------------------------------------------------------------------
# Base API client
# ---------------------------------------------------------------------------

class BaseHistoryAPI(ABC):
    """Base class for all history source enrichment API clients."""

    # Subclasses set these
    API_NAME: str = "base"
    CATEGORY: str = "unknown"
    BASE_URL: str = ""
    RATE_LIMIT_DELAY: float = 1.0  # seconds between requests
    MAX_RESULTS_PER_QUERY: int = 10

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "void-news-history/1.0 (source-enricher; academic research; +https://github.com/void-news)",
        })
        self._last_request_time: float = 0

    def _rate_limit(self):
        """Enforce minimum delay between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.RATE_LIMIT_DELAY:
            time.sleep(self.RATE_LIMIT_DELAY - elapsed)
        self._last_request_time = time.time()

    def _get(self, url: str, params: dict = None, timeout: int = 20) -> dict:
        """Rate-limited GET request returning JSON."""
        self._rate_limit()
        resp = self._session.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
        return resp.json()

    @abstractmethod
    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        """Search this API for sources relevant to the given query/event."""
        ...

    def search_safe(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        """Search with error handling -- never crashes the enricher."""
        try:
            return self.search(query, event_slug, max_results)
        except requests.exceptions.Timeout:
            print(f"  [{self.API_NAME}] Timeout for query: {query[:60]}")
            return []
        except requests.exceptions.HTTPError as e:
            print(f"  [{self.API_NAME}] HTTP {e.response.status_code} for query: {query[:60]}")
            return []
        except Exception as e:
            print(f"  [{self.API_NAME}] Error: {e}")
            return []
