"""
void --history source enricher.

CLI tool that queries free APIs to discover primary sources, scholarly works,
images, and structured data for historical events. Output is JSON files in
data/history/enrichment/ for editorial review — nothing is auto-inserted
into event YAML.

APIs integrated (all free, $0):
  Scholarly:   OpenAlex (271M works), Semantic Scholar (200M papers), Crossref
  Primary:     Library of Congress, DPLA, Europeana, Smithsonian, Gallica (BnF)
  Images:      Wikimedia Commons
  Wikidata:    Wikidata SPARQL (key figures, coordinates, related events)
  Geodata:     Wikidata Geo, Pleiades
  Statistics:  World Bank
  Conflict:    Slave Voyages
  Oral history: Curated collection references

Usage:
    python pipeline/history/source_enricher.py --event partition-of-india
    python pipeline/history/source_enricher.py --all
    python pipeline/history/source_enricher.py --event rwandan-genocide --category scholarly
    python pipeline/history/source_enricher.py --list-apis
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

# ---------------------------------------------------------------------------
# Fix imports: add project root and pipeline root to sys.path so both
# `pipeline.history.apis` and direct execution work.
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_PIPELINE_DIR = _SCRIPT_DIR.parent
_PROJECT_ROOT = _PIPELINE_DIR.parent

for p in [str(_PROJECT_ROOT), str(_PIPELINE_DIR)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from pipeline.history.apis.base import EnrichmentResult  # noqa: E402
from pipeline.history.apis.archives import ARCHIVE_APIS  # noqa: E402
from pipeline.history.apis.scholarly import SCHOLARLY_APIS  # noqa: E402
from pipeline.history.apis.media import MEDIA_APIS  # noqa: E402
from pipeline.history.apis.geodata import GEODATA_APIS  # noqa: E402
from pipeline.history.apis.statistics import STATISTICS_APIS  # noqa: E402
from pipeline.history.apis.structured import STRUCTURED_APIS  # noqa: E402
from pipeline.history.apis.oral_history import ORAL_HISTORY_APIS  # noqa: E402


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

EVENTS_DIR = _PROJECT_ROOT / "data" / "history" / "events"
ENRICHMENT_DIR = _PROJECT_ROOT / "data" / "history" / "enrichment"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="  %(levelname)-5s %(message)s",
)
log = logging.getLogger("source_enricher")

# ---------------------------------------------------------------------------
# API category registry
# ---------------------------------------------------------------------------

CATEGORY_REGISTRY = {
    "scholarly": SCHOLARLY_APIS,
    "primary": ARCHIVE_APIS,
    "images": MEDIA_APIS,
    "wikidata": STRUCTURED_APIS,
    "geodata": GEODATA_APIS,
    "statistics": STATISTICS_APIS,
    "conflict": {},  # Slave Voyages is in STRUCTURED_APIS, mapped here for CLI
    "oral_history": ORAL_HISTORY_APIS,
}

VALID_CATEGORIES = tuple(CATEGORY_REGISTRY.keys())


# ---------------------------------------------------------------------------
# Query generation from YAML event data
# ---------------------------------------------------------------------------

def _load_event_yaml(filepath: Path) -> dict:
    """Load and parse a YAML event file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _country_to_iso(country: str) -> str:
    """Map common country names to ISO 3166-1 alpha-3 codes for World Bank API."""
    mapping = {
        "india": "IND", "pakistan": "PAK", "japan": "JPN", "germany": "DEU",
        "france": "FRA", "rwanda": "RWA", "united states": "USA", "china": "CHN",
        "united kingdom": "GBR", "israel": "ISR", "palestine": "PSE",
        "south africa": "ZAF", "nigeria": "NGA", "egypt": "EGY", "turkey": "TUR",
        "russia": "RUS", "soviet union": "RUS", "brazil": "BRA", "mexico": "MEX",
        "iran": "IRN", "iraq": "IRQ", "afghanistan": "AFG", "vietnam": "VNM",
        "cambodia": "KHM", "indonesia": "IDN", "korea": "KOR",
    }
    return mapping.get(country.lower().strip(), "")


def generate_queries(event_data: dict) -> dict[str, list[str]]:
    """Generate category-specific search queries from event YAML data.

    Returns a dict mapping category name to list of search queries.
    """
    slug = event_data.get("slug", "")
    title = event_data.get("title", "")
    region = event_data.get("region", "")
    country = event_data.get("country", "")
    date_sort = event_data.get("date_sort", "")

    # Extract key figure names
    figures = [
        f.get("name", "")
        for f in event_data.get("key_figures", [])
        if f.get("name")
    ]

    # Extract authors from perspective sources
    viewpoint_authors = []
    for p in event_data.get("perspectives", []):
        for src in p.get("sources", []):
            if src.get("author"):
                viewpoint_authors.append(src["author"])

    queries = {}

    # Scholarly: title + historiographic variants
    queries["scholarly"] = [title]
    if country:
        queries["scholarly"].append(f"{title} {country}")
    for author in viewpoint_authors[:2]:
        queries["scholarly"].append(f"{author} {title}")

    # Primary sources: title + key figures
    queries["primary"] = [title]
    if country:
        queries["primary"].append(f"{title} {country}")
    for fig in figures[:2]:
        queries["primary"].append(fig)

    # Images: title + location + figures
    queries["images"] = [title]
    if country:
        queries["images"].append(f"{title} {country} historical")
    for fig in figures[:2]:
        queries["images"].append(f"{fig} historical photograph")

    # Wikidata: entities
    queries["wikidata"] = [title]
    for fig in figures[:3]:
        queries["wikidata"].append(fig)

    # Geodata: location-focused
    queries["geodata"] = [title]
    if country:
        queries["geodata"].append(country)

    # Statistics: country code + year range
    if country and date_sort:
        country_code = _country_to_iso(country)
        if country_code:
            year = int(date_sort) if isinstance(date_sort, (int, float)) else int(str(date_sort)[:4])
            queries["statistics"] = [f"{country_code}:{year - 5}-{year + 5}"]
        else:
            queries["statistics"] = [country]
    else:
        queries["statistics"] = [title]

    # Conflict: event slug used for relevance check
    queries["conflict"] = [title]

    # Oral history: event slug (matched to collection map)
    queries["oral_history"] = [title]

    return queries


# ---------------------------------------------------------------------------
# Enrichment orchestrator
# ---------------------------------------------------------------------------

def enrich_event(
    event_path: Path,
    categories: list[str] | None = None,
    max_results: int = 5,
) -> dict:
    """
    Enrich a single event by querying all configured APIs.

    Args:
        event_path: Path to the event YAML file.
        categories: If set, only query APIs in these categories.
        max_results: Max results per API per query.

    Returns the enrichment result dict in the canonical output format.
    """
    event_data = _load_event_yaml(event_path)
    slug = event_data.get("slug", "")
    title = event_data.get("title", "")

    log.info("Enriching: %s (%s)", title, slug)

    queries = generate_queries(event_data)
    active_categories = categories or list(CATEGORY_REGISTRY.keys())

    # Collect results per output section
    scholarly_works: list[dict] = []
    primary_sources: list[dict] = []
    images: list[dict] = []
    wikidata_results: dict = {"key_figures": [], "coordinates": [], "related_events": []}
    conflict_data: list[dict] = []
    geodata: list[dict] = []
    statistics: list[dict] = []
    oral_history: list[dict] = []
    api_stats: dict[str, int] = {}

    def _collect(api_name: str, api_class: type, cat_queries: list[str]) -> list[dict]:
        """Query a single API and return list of result dicts."""
        client = api_class()
        results = []
        for query in cat_queries:
            hits = client.search_safe(query, slug, max_results)
            if hits:
                log.info("  [%s] '%s' -> %d results", api_name, query[:60], len(hits))
                for h in hits:
                    d = h.to_dict()
                    d["search_query"] = query
                    results.append(d)
                api_stats[api_name] = api_stats.get(api_name, 0) + len(hits)
        return results

    # --- Scholarly ---
    if "scholarly" in active_categories:
        for api_name, api_class in SCHOLARLY_APIS.items():
            scholarly_works.extend(_collect(api_name, api_class, queries.get("scholarly", [])))

    # --- Primary sources ---
    if "primary" in active_categories:
        for api_name, api_class in ARCHIVE_APIS.items():
            primary_sources.extend(_collect(api_name, api_class, queries.get("primary", [])))

    # --- Images ---
    if "images" in active_categories:
        for api_name, api_class in MEDIA_APIS.items():
            images.extend(_collect(api_name, api_class, queries.get("images", [])))

    # --- Wikidata (structured) ---
    if "wikidata" in active_categories:
        for api_name, api_class in STRUCTURED_APIS.items():
            results = _collect(api_name, api_class, queries.get("wikidata", []))
            # Classify wikidata results into sub-sections
            for r in results:
                claims = r.get("metadata", {}).get("claims", {})
                coords = claims.get("coordinates", "")
                entry = {
                    "name": r.get("title", ""),
                    "wikidata_id": r.get("metadata", {}).get("wikidata_id", ""),
                    "description": r.get("description", ""),
                    "url": r.get("url", ""),
                }
                if coords:
                    try:
                        lat, lon = coords.split(",")
                        wikidata_results["coordinates"].append({
                            "label": r.get("title", ""),
                            "latitude": float(lat.strip()),
                            "longitude": float(lon.strip()),
                        })
                    except (ValueError, AttributeError):
                        pass
                # Key figures (entities with dates)
                if claims.get("start_date") or claims.get("point_in_time") or claims.get("end_date"):
                    entry.update({k: v for k, v in claims.items() if v})
                    wikidata_results["key_figures"].append(entry)
                else:
                    wikidata_results["related_events"].append(entry)

    # --- Geodata ---
    if "geodata" in active_categories:
        for api_name, api_class in GEODATA_APIS.items():
            geodata.extend(_collect(api_name, api_class, queries.get("geodata", [])))

    # --- Statistics ---
    if "statistics" in active_categories:
        for api_name, api_class in STATISTICS_APIS.items():
            statistics.extend(_collect(api_name, api_class, queries.get("statistics", [])))

    # --- Conflict ---
    if "conflict" in active_categories:
        # Slave Voyages is in STRUCTURED_APIS; query it directly
        if "slave_voyages" in STRUCTURED_APIS:
            conflict_data.extend(
                _collect("slave_voyages", STRUCTURED_APIS["slave_voyages"],
                         queries.get("conflict", []))
            )

    # --- Oral history ---
    if "oral_history" in active_categories:
        for api_name, api_class in ORAL_HISTORY_APIS.items():
            oral_history.extend(_collect(api_name, api_class, queries.get("oral_history", [])))

    # Deduplicate by URL within each section
    scholarly_works = _dedup_by_url(scholarly_works)
    primary_sources = _dedup_by_url(primary_sources)
    images = _dedup_by_url(images)

    total = (
        len(scholarly_works) + len(primary_sources) + len(images)
        + len(wikidata_results["key_figures"]) + len(wikidata_results["coordinates"])
        + len(wikidata_results["related_events"])
        + len(conflict_data) + len(geodata) + len(statistics) + len(oral_history)
    )

    log.info("  Total: %d unique results for %s", total, slug)

    result = {
        "event_slug": slug,
        "event_title": title,
        "enriched_at": datetime.now(timezone.utc).isoformat(),
        "total_results": total,
        "api_stats": api_stats,
        "scholarly_works": scholarly_works,
        "primary_sources": primary_sources,
        "images": images,
        "wikidata": wikidata_results,
    }

    # Include optional sections only if populated
    if conflict_data:
        result["conflict_data"] = conflict_data
    if geodata:
        result["geodata"] = geodata
    if statistics:
        result["statistics"] = statistics
    if oral_history:
        result["oral_history"] = oral_history

    return result


def _dedup_by_url(items: list[dict]) -> list[dict]:
    """Remove duplicate items based on URL."""
    seen = set()
    deduped = []
    for item in items:
        url = item.get("url", "")
        if url and url in seen:
            continue
        if url:
            seen.add(url)
        deduped.append(item)
    return deduped


# ---------------------------------------------------------------------------
# File I/O
# ---------------------------------------------------------------------------

def save_enrichment(result: dict) -> Path:
    """Save enrichment result to JSON file."""
    ENRICHMENT_DIR.mkdir(parents=True, exist_ok=True)
    slug = result["event_slug"]
    output_path = ENRICHMENT_DIR / f"{slug}.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    return output_path


# ---------------------------------------------------------------------------
# CLI: --list-apis
# ---------------------------------------------------------------------------

def list_apis() -> None:
    """Print a table of available APIs and their status."""
    print()
    print("void --history source enricher -- API registry")
    print("=" * 72)

    # Build flat list with status
    api_env_map = {
        "europeana": "EUROPEANA_API_KEY",
        "dpla": "DPLA_API_KEY",
        "smithsonian": "SMITHSONIAN_API_KEY",
    }

    for cat_name, cat_apis in CATEGORY_REGISTRY.items():
        if not cat_apis:
            continue
        print(f"\n  {cat_name.upper()}:")
        for api_name, api_class in cat_apis.items():
            client = api_class()
            env_var = api_env_map.get(api_name)
            if env_var:
                has_key = bool(os.environ.get(env_var, "").strip())
                auth_str = f"{env_var}"
                status = "ready" if has_key else "needs key"
            else:
                auth_str = "none (open)"
                status = "ready"
            delay = f"{client.RATE_LIMIT_DELAY}s"
            print(f"    {api_name:<25s} auth: {auth_str:<25s} rate: {delay:<6s} [{status}]")

    # Summary
    total_apis = sum(len(apis) for apis in CATEGORY_REGISTRY.values())
    print()
    print(f"  Total APIs: {total_apis}")
    print(f"  Categories: {', '.join(c for c, apis in CATEGORY_REGISTRY.items() if apis)}")
    print(f"  Events dir: {EVENTS_DIR}")
    print(f"  Output dir: {ENRICHMENT_DIR}")
    print()


# ---------------------------------------------------------------------------
# CLI main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="void --history source enricher -- discover primary sources, "
                    "scholarly works, images, and data for historical events",
    )
    parser.add_argument(
        "--event",
        type=str,
        help="Event slug to enrich (e.g., partition-of-india)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Enrich all events in data/history/events/",
    )
    parser.add_argument(
        "--category",
        type=str,
        choices=VALID_CATEGORIES,
        help="Only query APIs in this category",
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
        help="Max results per API per query (default: 5)",
    )
    parser.add_argument(
        "--list-apis",
        action="store_true",
        help="List available APIs and their status",
    )

    args = parser.parse_args()

    # --list-apis mode
    if args.list_apis:
        list_apis()
        return

    # Validate args
    if not args.event and not args.all:
        parser.print_help()
        print("\nSpecify --event <slug>, --all, or --list-apis")
        sys.exit(1)

    # Determine categories
    categories = [args.category] if args.category else None

    # Determine event files
    if args.event:
        event_path = EVENTS_DIR / f"{args.event}.yaml"
        if not event_path.exists():
            log.error("Event file not found: %s", event_path)
            available = sorted(p.stem for p in EVENTS_DIR.glob("*.yaml"))
            if available:
                log.info("Available events: %s", ", ".join(available))
            sys.exit(1)
        event_paths = [event_path]
    else:
        event_paths = sorted(EVENTS_DIR.glob("*.yaml"))
        if not event_paths:
            log.error("No YAML files found in %s", EVENTS_DIR)
            sys.exit(1)

    # Header
    print()
    print("void --history source enricher")
    print("=" * 50)
    print(f"  Events:       {len(event_paths)}")
    print(f"  Categories:   {categories or 'all'}")
    print(f"  Max results:  {args.max_results}/API/query")
    print()

    # Process events
    for event_path in event_paths:
        try:
            result = enrich_event(
                event_path,
                categories=categories,
                max_results=args.max_results,
            )
            output_path = save_enrichment(result)

            # Per-event summary
            stats = result.get("api_stats", {})
            print()
            print(f"  [{result['event_slug']}] {result['total_results']} total results")
            for api_id, count in sorted(stats.items()):
                print(f"    {api_id}: {count}")
            print(f"    -> {output_path}")

        except Exception as e:
            log.error("Failed to enrich %s: %s", event_path.name, e)
            import traceback
            traceback.print_exc()

    print()
    print("  Done. Review results in data/history/enrichment/ before incorporating into YAML.")


if __name__ == "__main__":
    main()
