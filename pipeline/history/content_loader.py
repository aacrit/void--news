"""
void --history content loader.

Reads YAML event files from data/history/events/ and upserts them
to the Supabase history_events, history_perspectives, history_media,
and history_connections tables.

Usage:
    python -m pipeline.history.content_loader
    python -m pipeline.history.content_loader --file data/history/events/partition-of-india.yaml
"""

import argparse
import json
import sys
from pathlib import Path

import yaml

# Use the existing Supabase client from pipeline utils
from pipeline.utils.supabase_client import supabase


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "history" / "events"

# Fields that map directly from YAML to the history_events table
EVENT_FIELDS = [
    "slug", "title", "subtitle", "date_display", "date_sort", "date_precision",
    "era", "region", "country", "category", "severity", "summary", "significance",
    "death_toll", "affected_population", "duration", "key_figures", "legacy_points",
    "primary_source_excerpts", "coordinates", "hero_image_url",
    "hero_image_attribution", "map_image_url", "related_event_slugs",
    "display_order", "is_published",
]


def load_yaml(filepath: Path) -> dict:
    """Load and parse a YAML file."""
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def upsert_event(data: dict) -> str:
    """
    Upsert a history event and return its UUID.

    Uses slug as the conflict key for idempotent re-runs.
    """
    event = {}
    for field in EVENT_FIELDS:
        if field in data:
            val = data[field]
            # Convert Python lists/dicts to JSON-compatible types for JSONB columns
            if field in ("key_figures", "legacy_points", "primary_source_excerpts", "coordinates"):
                event[field] = json.loads(json.dumps(val)) if val else val
            else:
                event[field] = val

    # Default is_published to true for loader-created events
    if "is_published" not in event:
        event["is_published"] = True

    result = (
        supabase.table("history_events")
        .upsert(event, on_conflict="slug")
        .execute()
    )
    if not result.data:
        raise RuntimeError(f"Failed to upsert event: {data.get('slug')}")

    return result.data[0]["id"]


def upsert_perspectives(event_id: str, perspectives: list[dict]) -> int:
    """
    Delete existing perspectives for the event and insert fresh ones.

    Returns the number of perspectives inserted.
    """
    # Clear existing to allow re-runs
    supabase.table("history_perspectives").delete().eq("event_id", event_id).execute()

    count = 0
    for i, p in enumerate(perspectives):
        row = {
            "event_id": event_id,
            "viewpoint": p["viewpoint"],
            "viewpoint_type": p["viewpoint_type"],
            "region_origin": p["region_origin"],
            "narrative": p["narrative"],
            "key_arguments": p.get("key_arguments", []),
            "sources": p.get("sources", []),
            "notable_quotes": p.get("notable_quotes", []),
            "emphasized": p.get("emphasized", []),
            "omitted": p.get("omitted", []),
            "display_order": p.get("display_order", i),
        }
        supabase.table("history_perspectives").insert(row).execute()
        count += 1

    return count


def upsert_media(event_id: str, media_items: list[dict]) -> int:
    """
    Delete existing media for the event and insert fresh ones.

    Returns the number of media items inserted.
    """
    supabase.table("history_media").delete().eq("event_id", event_id).execute()

    count = 0
    for i, m in enumerate(media_items):
        row = {
            "event_id": event_id,
            "media_type": m["media_type"],
            "title": m["title"],
            "description": m.get("description"),
            "source_url": m["source_url"],
            "thumbnail_url": m.get("thumbnail_url"),
            "attribution": m["attribution"],
            "license": m.get("license", "public-domain"),
            "creator": m.get("creator"),
            "creation_date": m.get("creation_date"),
            "display_order": m.get("display_order", i),
        }
        supabase.table("history_media").insert(row).execute()
        count += 1

    return count


def upsert_connections(event_id: str, slug: str, connections: list[dict]) -> int:
    """
    Upsert connections from this event to other events.

    Looks up target events by slug. Skips connections where the target
    event does not yet exist (it may be loaded in a later run).

    Returns the number of connections created.
    """
    # Clear outbound connections from this event
    supabase.table("history_connections").delete().eq("event_a_id", event_id).execute()

    count = 0
    for conn in connections:
        target_slug = conn["target_slug"]
        # Look up target event ID
        result = (
            supabase.table("history_events")
            .select("id")
            .eq("slug", target_slug)
            .execute()
        )
        if not result.data:
            print(f"    [skip] Connection target not found: {target_slug}")
            continue

        target_id = result.data[0]["id"]
        row = {
            "event_a_id": event_id,
            "event_b_id": target_id,
            "connection_type": conn["connection_type"],
            "description": conn.get("description"),
        }
        try:
            supabase.table("history_connections").insert(row).execute()
            count += 1
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                print(f"    [skip] Duplicate connection: {slug} -> {target_slug}")
            else:
                raise

    return count


def process_file(filepath: Path) -> None:
    """Process a single YAML event file."""
    print(f"\n  Loading: {filepath.name}")
    data = load_yaml(filepath)
    slug = data["slug"]

    # 1. Upsert event
    event_id = upsert_event(data)
    print(f"    Event: {slug} -> {event_id}")

    # 2. Perspectives
    perspectives = data.get("perspectives", [])
    p_count = upsert_perspectives(event_id, perspectives)
    print(f"    Perspectives: {p_count}")

    # 3. Media
    media_items = data.get("media", [])
    m_count = upsert_media(event_id, media_items)
    print(f"    Media: {m_count}")

    # 4. Connections (may skip if target events not yet loaded)
    connections = data.get("connections", [])
    c_count = upsert_connections(event_id, slug, connections)
    print(f"    Connections: {c_count} (of {len(connections)} defined)")


def main():
    parser = argparse.ArgumentParser(description="Load history events into Supabase")
    parser.add_argument(
        "--file",
        type=str,
        help="Load a single YAML file instead of all files",
    )
    args = parser.parse_args()

    print("void --history content loader")
    print("=" * 40)

    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"  [error] File not found: {filepath}")
            sys.exit(1)
        process_file(filepath)
    else:
        yaml_files = sorted(DATA_DIR.glob("*.yaml"))
        if not yaml_files:
            print(f"  [warn] No YAML files found in {DATA_DIR}")
            sys.exit(0)

        print(f"  Found {len(yaml_files)} event files")
        for filepath in yaml_files:
            try:
                process_file(filepath)
            except Exception as e:
                print(f"    [error] Failed to process {filepath.name}: {e}")

    print("\n  Done.")


if __name__ == "__main__":
    main()
