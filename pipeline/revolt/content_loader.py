"""
void --revolt content loader.

Reads YAML revolution files from data/revolt/events/ and upserts them to the
Supabase revolt_events, revolt_perspectives, revolt_media, revolt_connections,
and revolt_metrics tables.

Idempotent: events upsert on slug; children are delete-then-insert. A light
validation pass checks JSONB-internal enums, phase t_start/t_end bounds and
monotonicity, and warns (does not fail) on missing related_history_slugs / target
slugs so a partial load is order-tolerant.

Usage:
    python -m pipeline.revolt.content_loader
    python -m pipeline.revolt.content_loader --file data/revolt/events/french-revolution.yaml
    python -m pipeline.revolt.content_loader --validate-only
"""

import argparse
import json
import sys
from pathlib import Path

import yaml


def _sb():
    """Lazily import the service-role Supabase client so --validate-only runs
    offline (no DB stack / secrets required)."""
    from pipeline.utils.supabase_client import supabase
    return supabase


DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "revolt" / "events"

# Fields that map directly from YAML to the revolt_events table.
EVENT_FIELDS = [
    "slug", "title", "subtitle",
    "date_display", "date_start", "date_end", "date_precision",
    "era", "region", "country", "revolt_type", "status",
    "summary", "significance", "analytical_outlook",
    "grievances", "structural_pressures", "structural_indicators",
    "fiscal_crisis", "elite_fracture", "youth_bulge",
    "repression_level", "external_shock",
    "actors", "tactics", "resistance_type",
    "phases", "ate_its_children",
    "outcome", "peak_participation_pct", "peak_participation_display",
    "crossed_participation_threshold", "military_defection", "foreign_intervention",
    "duration_days", "death_toll", "death_toll_low", "death_toll_high",
    "regime_before", "regime_after", "democratization_delta", "success_factors",
    "key_figures", "legacy_points", "primary_source_excerpts", "coordinates",
    "hero_image_url", "hero_image_attribution", "map_image_url",
    "audio_url", "audio_duration_seconds",
    "related_revolt_slugs", "related_history_slugs", "live_query",
    "analysis_reviewed_at", "prediction_confidence",
    "display_order", "is_published",
]

# JSONB columns that must be round-tripped through json for the client.
JSONB_FIELDS = {
    "grievances", "structural_pressures", "structural_indicators",
    "actors", "tactics", "phases", "success_factors",
    "key_figures", "legacy_points", "primary_source_excerpts",
    "coordinates", "live_query",
}

# JSONB-internal enums validated here (not by DB CHECK), mirroring how history
# leaves viewpoint values inside JSONB unconstrained beyond the promoted column.
ACTOR_TYPES = {
    "vanguard", "masses", "organized-labor", "students-youth", "military-defectors",
    "security-forces", "old-regime", "regime", "counter-revolutionaries", "religious-clergy",
    "foreign-backer", "foreign-intervener", "diaspora",
}
TACTIC_TYPES = {
    "mass-demonstration", "general-strike", "occupation", "civil-disobedience",
    "boycott-noncooperation", "armed-insurgency", "guerrilla-warfare",
    "urban-uprising", "defection-fraternization", "digital-mobilization",
    "sabotage", "parallel-institutions", "elite-negotiation",
}
PHASE_KEYS = {
    "old-regime-crisis", "intellectual-desertion", "the-spark", "moderate-phase",
    "dual-power", "radical-phase", "terror-virtue", "thermidor", "consolidation",
}
FRAMEWORKS = {"chenoweth", "brinton", "skocpol", "goldstone", "tilly"}


def load_yaml(filepath: Path) -> dict:
    with open(filepath, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _jsonify(val):
    """Round-trip a Python list/dict to JSON-compatible types for JSONB columns."""
    if val is None:
        return val
    return json.loads(json.dumps(val))


def validate(data: dict) -> list[str]:
    """Return a list of warning strings for soft-invalid content. Empty = clean."""
    warnings: list[str] = []
    slug = data.get("slug", "<no-slug>")

    for a in data.get("actors", []) or []:
        t = a.get("actor_type")
        if t and t not in ACTOR_TYPES:
            warnings.append(f"{slug}: unknown actor_type '{t}'")

    for t in data.get("tactics", []) or []:
        tt = t.get("tactic_type")
        if tt and tt not in TACTIC_TYPES:
            warnings.append(f"{slug}: unknown tactic_type '{tt}'")

    prev_end = -1.0
    for ph in data.get("phases", []) or []:
        key = ph.get("phase")
        if key and key not in PHASE_KEYS:
            warnings.append(f"{slug}: unknown phase '{key}'")
        ts, te = ph.get("t_start"), ph.get("t_end")
        for name, v in (("t_start", ts), ("t_end", te)):
            if v is not None and not (0.0 <= float(v) <= 1.0):
                warnings.append(f"{slug}: phase {key} {name}={v} out of [0,1]")
        if ts is not None and te is not None and float(te) < float(ts):
            warnings.append(f"{slug}: phase {key} t_end {te} < t_start {ts}")
        if ts is not None and float(ts) < prev_end - 1e-6:
            warnings.append(f"{slug}: phase {key} t_start {ts} precedes prior t_end {prev_end}")
        if te is not None:
            prev_end = float(te)

    for f in data.get("success_factors", []) or []:
        fw = f.get("framework")
        if fw and fw not in FRAMEWORKS:
            warnings.append(f"{slug}: unknown success_factor framework '{fw}'")

    return warnings


def upsert_event(data: dict) -> str:
    """Upsert a revolt event on slug and return its UUID."""
    event = {}
    for field in EVENT_FIELDS:
        if field in data:
            val = data[field]
            event[field] = _jsonify(val) if field in JSONB_FIELDS else val

    if "is_published" not in event:
        event["is_published"] = True

    result = (
        _sb().table("revolt_events")
        .upsert(event, on_conflict="slug")
        .execute()
    )
    if not result.data:
        raise RuntimeError(f"Failed to upsert event: {data.get('slug')}")
    return result.data[0]["id"]


def upsert_perspectives(revolt_id: str, perspectives: list[dict]) -> int:
    _sb().table("revolt_perspectives").delete().eq("revolt_id", revolt_id).execute()
    count = 0
    for i, p in enumerate(perspectives):
        row = {
            "revolt_id": revolt_id,
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
        _sb().table("revolt_perspectives").insert(row).execute()
        count += 1
    return count


def upsert_media(revolt_id: str, media_items: list[dict]) -> int:
    _sb().table("revolt_media").delete().eq("revolt_id", revolt_id).execute()
    count = 0
    for i, m in enumerate(media_items):
        row = {
            "revolt_id": revolt_id,
            "media_type": m["media_type"],
            "title": m["title"],
            "description": m.get("description"),
            "source_url": m.get("supabase_url") or m["source_url"],
            "thumbnail_url": m.get("thumbnail_url"),
            "attribution": m["attribution"],
            "license": m.get("license", "public-domain"),
            "creator": m.get("creator"),
            "creation_date": m.get("creation_date"),
            "display_order": m.get("display_order", i),
        }
        _sb().table("revolt_media").insert(row).execute()
        count += 1
    return count


def upsert_metrics(revolt_id: str, metrics: list[dict]) -> int:
    _sb().table("revolt_metrics").delete().eq("revolt_id", revolt_id).execute()
    count = 0
    for i, mt in enumerate(metrics):
        row = {
            "revolt_id": revolt_id,
            "metric_key": mt["metric_key"],
            "label": mt["label"],
            "category": mt.get("category", "process"),
            "unit": mt.get("unit"),
            "numeric_value": mt.get("numeric_value"),
            "display_value": mt.get("display_value"),
            "framework": mt.get("framework"),
            "source": mt.get("source"),
            "source_url": mt.get("source_url"),
            "data_points": _jsonify(mt.get("data_points", [])),
            "display_order": mt.get("display_order", i),
        }
        _sb().table("revolt_metrics").insert(row).execute()
        count += 1
    return count


def upsert_connections(revolt_id: str, slug: str, connections: list[dict]) -> int:
    """Resolve target_slug -> UUID; skip (with log) when the target isn't loaded yet."""
    _sb().table("revolt_connections").delete().eq("revolt_a_id", revolt_id).execute()
    count = 0
    for conn in connections:
        target_slug = conn["target_slug"]
        result = (
            _sb().table("revolt_events").select("id").eq("slug", target_slug).execute()
        )
        if not result.data:
            print(f"    [skip] Connection target not found: {target_slug}")
            continue
        row = {
            "revolt_a_id": revolt_id,
            "revolt_b_id": result.data[0]["id"],
            "connection_type": conn["connection_type"],
            "description": conn.get("description"),
        }
        try:
            _sb().table("revolt_connections").insert(row).execute()
            count += 1
        except Exception as e:
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                print(f"    [skip] Duplicate connection: {slug} -> {target_slug}")
            else:
                raise
    return count


def _check_related_history(data: dict) -> None:
    """Warn (don't fail) if a related_history_slugs target is absent from history_events."""
    slugs = data.get("related_history_slugs") or []
    for hs in slugs:
        try:
            res = _sb().table("history_events").select("slug").eq("slug", hs).execute()
            if not res.data:
                print(f"    [warn] related_history_slug not found in history_events: {hs}")
        except Exception:
            # history table may be absent in some environments; non-fatal.
            pass


def process_file(filepath: Path, validate_only: bool = False) -> None:
    print(f"\n  Loading: {filepath.name}")
    data = load_yaml(filepath)
    slug = data["slug"]

    for w in validate(data):
        print(f"    [warn] {w}")

    if validate_only:
        print(f"    [validate-only] {slug} parsed and checked")
        return

    revolt_id = upsert_event(data)
    print(f"    Event: {slug} -> {revolt_id}")

    p_count = upsert_perspectives(revolt_id, data.get("perspectives", []))
    print(f"    Perspectives: {p_count}")

    m_count = upsert_media(revolt_id, data.get("media", []))
    print(f"    Media: {m_count}")

    mt_count = upsert_metrics(revolt_id, data.get("metrics", []))
    print(f"    Metrics: {mt_count}")

    connections = data.get("connections", [])
    c_count = upsert_connections(revolt_id, slug, connections)
    print(f"    Connections: {c_count} (of {len(connections)} defined)")

    _check_related_history(data)


def main():
    parser = argparse.ArgumentParser(description="Load revolt events into Supabase")
    parser.add_argument("--file", type=str, help="Load a single YAML file instead of all files")
    parser.add_argument("--validate-only", action="store_true", help="Parse + validate, no DB writes")
    args = parser.parse_args()

    print("void --revolt content loader")
    print("=" * 40)

    if args.file:
        filepath = Path(args.file)
        if not filepath.exists():
            print(f"  [error] File not found: {filepath}")
            sys.exit(1)
        process_file(filepath, validate_only=args.validate_only)
    else:
        yaml_files = sorted(DATA_DIR.glob("*.yaml"))
        if not yaml_files:
            print(f"  [warn] No YAML files found in {DATA_DIR}")
            sys.exit(0)
        print(f"  Found {len(yaml_files)} revolution files")
        for filepath in yaml_files:
            try:
                process_file(filepath, validate_only=args.validate_only)
            except Exception as e:
                print(f"    [error] Failed to process {filepath.name}: {e}")

    print("\n  Done.")


if __name__ == "__main__":
    main()
