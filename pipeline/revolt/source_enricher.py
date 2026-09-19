"""
void --revolt source enricher.

Reads revolution YAML from data/revolt/events/ and gathers free, open-license
research material (scholarly works, primary sources, public-domain images,
Wikidata entities, geodata, World Bank indicators) into a JSON dossier per
revolution at data/revolt/enrichment/<slug>.json for EDITORIAL REVIEW. Nothing
is auto-inserted into the YAML or the DB.

Reuses the event-agnostic API package from void --history (pipeline.history.apis)
verbatim, so there is one source of truth for the API wrappers. Only the
query-building and the country/year handling are revolt-specific. The World Bank
call is guarded against pre-1960 revolutions (WB series start ~1960).

Usage:
    python -m pipeline.revolt.source_enricher --event french-revolution
    python -m pipeline.revolt.source_enricher --all
    python -m pipeline.revolt.source_enricher --list-apis
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from pipeline.history.apis.base import EnrichmentResult  # noqa: F401 (parity)
from pipeline.history.apis.archives import ARCHIVE_APIS
from pipeline.history.apis.scholarly import SCHOLARLY_APIS
from pipeline.history.apis.media import MEDIA_APIS
from pipeline.history.apis.geodata import GEODATA_APIS
from pipeline.history.apis.statistics import STATISTICS_APIS
from pipeline.history.apis.structured import STRUCTURED_APIS

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVENTS_DIR = _PROJECT_ROOT / "data" / "revolt" / "events"
ENRICHMENT_DIR = _PROJECT_ROOT / "data" / "revolt" / "enrichment"

# World Bank data begins ~1960; a revolution whose window ends before this gets
# no usable indicators, so we skip the request rather than waste it.
WORLD_BANK_MIN_YEAR = 1960

CATEGORY_REGISTRY = {
    "scholarly": SCHOLARLY_APIS,
    "primary": ARCHIVE_APIS,
    "images": MEDIA_APIS,
    "wikidata": {"wikidata": STRUCTURED_APIS["wikidata"]},
    "geodata": GEODATA_APIS,
    "statistics": STATISTICS_APIS,
    "conflict": {"slave_voyages": STRUCTURED_APIS["slave_voyages"]},
}
VALID_CATEGORIES = tuple(CATEGORY_REGISTRY.keys())

# Country name -> ISO alpha-3 for the World Bank query (covers the seed bench;
# unknown or multi-country entries fall back to a free-text country search).
_COUNTRY_ISO = {
    "france": "FRA", "russia": "RUS", "soviet union": "RUS", "iran": "IRN",
    "haiti": "HTI", "saint-domingue": "HTI", "united states": "USA",
    "philippines": "PHL", "myanmar": "MMR", "burma": "MMR", "sudan": "SDN",
    "venezuela": "VEN", "egypt": "EGY", "tunisia": "TUN", "syria": "SYR",
    "mexico": "MEX", "cuba": "CUB", "nicaragua": "NIC", "algeria": "DZA",
    "portugal": "PRT", "south africa": "ZAF", "ukraine": "UKR", "china": "CHN",
}


def _country_to_iso(country: str) -> str:
    if not country:
        return ""
    key = country.strip().lower()
    if "," in key or "(" in key:  # multi-country / annotated -> free-text fallback
        return ""
    return _COUNTRY_ISO.get(key, "")


def _load_event_yaml(filepath: Path) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_queries(event_data: dict) -> dict[str, list[str]]:
    """Build per-category query lists from a revolution's fields."""
    title = event_data.get("title", "")
    country = event_data.get("country", "")
    year = event_data.get("date_end") or event_data.get("date_start")
    figure_names = [f.get("name", "") for f in event_data.get("key_figures", []) if f.get("name")]

    queries: dict[str, list[str]] = {
        "scholarly": [title, f"{title} causes", *figure_names[:2]],
        "primary": [title, country] if country else [title],
        "images": [title] + ([country] if country else []),
        "wikidata": [title, *figure_names[:2]],
        "geodata": [country] if country and "," not in country else [],
        "conflict": [title],
    }

    # Statistics: World Bank, guarded for pre-1960 revolutions.
    iso = _country_to_iso(country)
    if iso and isinstance(year, int) and (year + 10) >= WORLD_BANK_MIN_YEAR:
        start = max(WORLD_BANK_MIN_YEAR, year)
        queries["statistics"] = [f"{iso}:{start}-{start + 10}"]
    else:
        queries["statistics"] = []  # pre-1960 or multi-country: no WB data

    return {k: [q for q in v if q] for k, v in queries.items()}


def _dedup_by_url(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        url = it.get("url") or json.dumps(it, sort_keys=True, default=str)
        if url in seen:
            continue
        seen.add(url)
        out.append(it)
    return out


def enrich_event(event_path: Path, categories: list[str] | None = None, max_results: int = 5) -> dict:
    data = _load_event_yaml(event_path)
    slug = data["slug"]
    queries = generate_queries(data)
    active = categories or list(VALID_CATEGORIES)
    api_stats: dict[str, int] = {}

    def _collect(api_name, api_class, cat_queries) -> list[dict]:
        client = api_class()
        results: list[dict] = []
        for query in cat_queries:
            try:
                hits = client.search_safe(query, slug, max_results)
            except Exception:  # search_safe already guards, belt-and-suspenders
                hits = []
            for h in hits or []:
                d = h.to_dict()
                d["search_query"] = query
                results.append(d)
            if hits:
                api_stats[api_name] = api_stats.get(api_name, 0) + len(hits)
        return results

    buckets: dict[str, list[dict]] = {
        "scholarly_works": [], "primary_sources": [], "images": [],
        "geodata": [], "statistics": [], "conflict_data": [],
    }
    cat_to_bucket = {
        "scholarly": "scholarly_works", "primary": "primary_sources", "images": "images",
        "geodata": "geodata", "statistics": "statistics", "conflict": "conflict_data",
    }
    for cat, bucket in cat_to_bucket.items():
        if cat not in active:
            continue
        for api_name, api_class in CATEGORY_REGISTRY[cat].items():
            buckets[bucket].extend(_collect(api_name, api_class, queries.get(cat, [])))

    wikidata_section = {"key_figures": [], "coordinates": [], "related_events": []}
    if "wikidata" in active:
        for api_name, api_class in CATEGORY_REGISTRY["wikidata"].items():
            for d in _collect(api_name, api_class, queries.get("wikidata", [])):
                meta = d.get("metadata", {}) or {}
                claims = meta.get("claims", meta)
                if claims.get("coordinates"):
                    wikidata_section["coordinates"].append(d)
                elif any(k in claims for k in ("start_date", "point_in_time", "end_date")):
                    wikidata_section["key_figures"].append(d)
                else:
                    wikidata_section["related_events"].append(d)

    result = {
        "event_slug": slug,
        "event_title": data.get("title", ""),
        "enriched_at": datetime.now(timezone.utc).isoformat(),
        "scholarly_works": _dedup_by_url(buckets["scholarly_works"]),
        "primary_sources": _dedup_by_url(buckets["primary_sources"]),
        "images": _dedup_by_url(buckets["images"]),
        "wikidata": wikidata_section,
    }
    for optional in ("conflict_data", "geodata", "statistics"):
        if buckets[optional]:
            result[optional] = _dedup_by_url(buckets[optional])
    result["api_stats"] = api_stats
    result["total_results"] = sum(api_stats.values())
    return result


def save_enrichment(result: dict) -> Path:
    ENRICHMENT_DIR.mkdir(parents=True, exist_ok=True)
    out = ENRICHMENT_DIR / f"{result['event_slug']}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, default=str)
    return out


def list_apis() -> None:
    print("void --revolt enrichment APIs (reused from pipeline.history.apis)")
    for cat in VALID_CATEGORIES:
        names = ", ".join(CATEGORY_REGISTRY[cat].keys()) or "(none)"
        print(f"  {cat:12s} -> {names}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich revolt events with free-API research")
    parser.add_argument("--event", type=str, help="Enrich a single revolution by slug")
    parser.add_argument("--all", action="store_true", help="Enrich every YAML in the events dir")
    parser.add_argument("--category", type=str, choices=VALID_CATEGORIES, action="append",
                        help="Limit to one or more categories (repeatable)")
    parser.add_argument("--max-results", type=int, default=5)
    parser.add_argument("--list-apis", action="store_true")
    args = parser.parse_args()

    if args.list_apis:
        list_apis()
        return

    if args.event:
        paths = [EVENTS_DIR / f"{args.event}.yaml"]
    elif args.all:
        paths = sorted(EVENTS_DIR.glob("*.yaml"))
    else:
        parser.error("provide --event <slug>, --all, or --list-apis")
        return

    for path in paths:
        if not path.exists():
            print(f"  [error] not found: {path}")
            continue
        print(f"\n  Enriching: {path.name}")
        result = enrich_event(path, categories=args.category, max_results=args.max_results)
        out = save_enrichment(result)
        print(f"    {result['total_results']} results -> {out}")
        for api, n in sorted(result["api_stats"].items()):
            print(f"      {api}: {n}")

    print("\n  Done. Review the JSON dossiers before curating anything into YAML.")


if __name__ == "__main__":
    main()
