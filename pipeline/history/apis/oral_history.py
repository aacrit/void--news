"""
Oral history and testimony API/reference clients.

Most oral history archives do not expose free search APIs. This module
provides structured reference links and, where APIs exist, search
functionality.

Archives: 1947 Partition Archive, Shoah Foundation (USC), StoryCorps.
"""

from .base import BaseHistoryAPI, EnrichmentResult


class OralHistoryReference(BaseHistoryAPI):
    """Reference-based oral history enrichment.

    Rather than querying APIs (most oral history archives lack public search APIs),
    this client matches event slugs to known oral history collections and returns
    structured references with direct URLs to relevant collections.
    """
    API_NAME = "oral_history"
    CATEGORY = "oral_history"
    BASE_URL = ""
    RATE_LIMIT_DELAY = 0  # no network requests for static matches

    # Map event slugs to known oral history collections
    COLLECTION_MAP: dict[str, list[dict]] = {
        "partition-of-india": [
            {
                "title": "1947 Partition Archive -- Oral Testimonies",
                "description": "10,000+ recorded testimonies from Partition survivors and their descendants. Citizen-history project founded by Guneeta Singh Bhalla in 2010.",
                "url": "https://www.1947partitionarchive.org/",
                "creator": "1947 Partition Archive",
                "license": "restricted-access",
                "metadata": {"testimony_count": "10,000+", "languages": "Hindi, Urdu, Punjabi, Bengali, English"},
            },
            {
                "title": "British Library -- Oral History of the British Raj",
                "description": "200+ recordings from British officials, military personnel, and Indian civil servants. Recorded 1970s-1990s.",
                "url": "https://www.bl.uk/collection-guides/oral-history-of-the-british-raj",
                "creator": "British Library Sound Archive",
                "license": "restricted-access",
                "metadata": {"recording_count": "200+", "period": "1970s-1990s"},
            },
        ],
        "rwandan-genocide": [
            {
                "title": "Genocide Archive of Rwanda -- Testimonies",
                "description": "Survivor testimonies collected by the Kigali Genocide Memorial and Aegis Trust.",
                "url": "https://genocidearchiverwanda.org.rw/",
                "creator": "Aegis Trust / Kigali Genocide Memorial",
                "license": "restricted-access",
            },
            {
                "title": "USC Shoah Foundation -- Rwanda Collection",
                "description": "Testimonies from Rwandan genocide survivors in the Visual History Archive.",
                "url": "https://sfi.usc.edu/collections/rwandan",
                "creator": "USC Shoah Foundation",
                "license": "restricted-access",
                "metadata": {"note": "Access via university library partnerships"},
            },
        ],
        "hiroshima-nagasaki": [
            {
                "title": "Hiroshima Peace Memorial Museum -- Survivor Testimonies",
                "description": "Hibakusha (atomic bomb survivor) testimonies. Written and video accounts.",
                "url": "https://hpmmuseum.jp/",
                "creator": "Hiroshima Peace Memorial Museum",
                "license": "restricted-access",
            },
            {
                "title": "Atomic Heritage Foundation -- Voices of the Manhattan Project",
                "description": "400+ oral histories from scientists, military personnel, and civilians involved in the Manhattan Project.",
                "url": "https://www.atomicheritage.org/oral-histories",
                "creator": "Atomic Heritage Foundation",
                "license": "open-access",
                "metadata": {"recording_count": "400+"},
            },
        ],
        "transatlantic-slave-trade": [
            {
                "title": "Born in Slavery: Slave Narratives (LOC)",
                "description": "2,300+ first-person accounts of slavery collected by the Federal Writers' Project, 1936-1938.",
                "url": "https://www.loc.gov/collections/slave-narratives-from-the-federal-writers-project-1936-to-1938/",
                "creator": "Library of Congress / Federal Writers' Project",
                "license": "public-domain",
                "metadata": {"narrative_count": "2,300+", "date_collected": "1936-1938"},
            },
        ],
        "trail-of-tears": [
            {
                "title": "Indian Removal Oral Histories (Sequoyah National Research Center)",
                "description": "Oral histories from Cherokee, Chickasaw, Choctaw, Creek, and Seminole descendants.",
                "url": "https://ualr.edu/sequoyah/",
                "creator": "Sequoyah National Research Center, UALR",
                "license": "restricted-access",
            },
        ],
        "fall-of-berlin-wall": [
            {
                "title": "Memory and History Archive (Bundesstiftung Aufarbeitung)",
                "description": "Oral histories from East German citizens, border guards, and political prisoners.",
                "url": "https://www.bundesstiftung-aufarbeitung.de/",
                "creator": "Bundesstiftung zur Aufarbeitung der SED-Diktatur",
                "license": "restricted-access",
            },
            {
                "title": "StoryCorps -- Berlin Wall Oral Histories",
                "description": "Selected oral histories from German-Americans and Berlin residents.",
                "url": "https://storycorps.org/",
                "creator": "StoryCorps",
                "license": "cc-by-nc",
            },
        ],
        "french-revolution": [
            {
                "title": "Archives parlementaires (National Assembly debates)",
                "description": "Transcripts of French National Assembly debates 1789-1794. Digitized by Stanford/BnF.",
                "url": "https://frda.stanford.edu/",
                "creator": "Stanford University / BnF",
                "license": "open-access",
            },
        ],
    }

    def search(self, query: str, event_slug: str, max_results: int = 5) -> list[EnrichmentResult]:
        collections = self.COLLECTION_MAP.get(event_slug, [])

        results = []
        for c in collections[:max_results]:
            results.append(EnrichmentResult(
                category=self.CATEGORY,
                api_source=self.API_NAME,
                title=c["title"],
                description=c["description"],
                url=c["url"],
                creator=c.get("creator"),
                license=c.get("license", "varies"),
                metadata=c.get("metadata", {}),
            ))

        return results


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ORAL_HISTORY_APIS = {
    "oral_history": OralHistoryReference,
}
