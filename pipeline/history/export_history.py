"""Emit the static History snapshot the frontend reads.

History content lives in data/history/events/*.yaml, not in the pipeline state
DB. Before the Cloudflare migration the loader pushed those files into the
Supabase history_* tables and the browser queried them directly; with Supabase
decommissioned that read path resolves to null and every /history route falls
back to MOCK_EVENTS. This emitter is the replacement: it reads the YAML and
writes frontend/public/data/history.json in the SAME row shape PostgREST
returned, with the relations nested, so the frontend mapper is unchanged.

  frontend/public/data/history.json
      [{...history_events row, perspectives:[...], media:[...],
        connections:[...]}]  sorted by date_sort

Ids are derived from the slug (deterministic, stable across runs) because the
frontend uses them only as React keys and for connection lookups. Connections
are emitted on BOTH endpoints, matching the forward+reverse pair of queries the
Supabase path issued, and dropped when the target slug has no event file.

Media URLs come from `source_url`, never `supabase_url`: the latter points into
the decommissioned storage bucket and every one of those objects is gone.

Usage:
    python -m pipeline.history.export_history
"""
import json
import os
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = REPO / "data" / "history" / "events"
PUBLIC_DIR = Path(
    os.environ.get("VOID_EXPORT_PUBLIC_DIR") or REPO / "frontend" / "public" / "data"
)

# history_events columns the frontend mapper reads, in YAML spelling.
EVENT_FIELDS = [
    "slug", "title", "subtitle", "date_display", "date_sort", "date_precision",
    "era", "region", "country", "category", "severity", "summary", "significance",
    "death_toll", "affected_population", "duration", "key_figures", "legacy_points",
    "primary_source_excerpts", "coordinates", "hero_image_url",
    "hero_image_attribution", "map_image_url", "related_event_slugs",
]


def event_id(slug: str) -> str:
    """Stable synthetic id for a slug (no DB to assign UUIDs)."""
    return f"ev-{slug}"


def load_events() -> list[dict]:
    """Read every event YAML, newest-last by date_sort."""
    docs = []
    for path in sorted(DATA_DIR.glob("*.yaml")):
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not data or not data.get("slug"):
            print(f"  [skip] {path.name}: no slug")
            continue
        docs.append(data)
    docs.sort(key=lambda d: (d.get("date_sort") or 0, d.get("slug") or ""))
    return docs


def is_renderable(url) -> bool:
    """True when the url resolves to an actual image the browser can load.

    A commons File: page is rewritten to Special:Redirect/file/ by the frontend
    and served by Wikimedia; an upload.wikimedia.org path is already direct.
    Everything else here is a landing page (unsplash.com/photos/..., a pexels
    gallery, an en.wikipedia article anchor, a doi.org record) or a dead
    Supabase Storage object.
    """
    u = str(url or "")
    return (
        u.startswith("https://commons.wikimedia.org/wiki/File:")
        or u.startswith("https://upload.wikimedia.org/")
    )


def build_rows(docs: list[dict]) -> list[dict]:
    known = {d["slug"] for d in docs}
    rows: dict[str, dict] = {}
    dropped_media: dict[str, int] = {}
    heroes_substituted: list[str] = []
    heroes_missing: list[str] = []

    for doc in docs:
        slug = doc["slug"]
        row = {f: doc.get(f) for f in EVENT_FIELDS if f in doc}
        row["id"] = event_id(slug)
        row["is_published"] = True
        # No history audio has been generated since the migration; the frontend
        # treats null as "not yet generated" and hides the player.
        row["audio_url"] = doc.get("audio_url")
        row["audio_duration_seconds"] = doc.get("audio_duration_seconds")

        row["perspectives"] = [
            {
                "id": f"{event_id(slug)}-p{i}",
                "event_id": event_id(slug),
                "viewpoint": p.get("viewpoint", ""),
                "viewpoint_type": p.get("viewpoint_type", ""),
                "region_origin": p.get("region_origin", ""),
                "narrative": p.get("narrative", ""),
                "key_arguments": p.get("key_arguments") or [],
                "sources": p.get("sources") or [],
                "notable_quotes": p.get("notable_quotes") or [],
                "emphasized": p.get("emphasized") or [],
                "omitted": p.get("omitted") or [],
                "display_order": p.get("display_order", i),
            }
            for i, p in enumerate(doc.get("perspectives") or [])
        ]

        kept = [m for m in (doc.get("media") or []) if is_renderable(m.get("source_url"))]
        dropped_media[slug] = len(doc.get("media") or []) - len(kept)
        row["media"] = [
            {
                "id": f"{event_id(slug)}-m{i}",
                "event_id": event_id(slug),
                "media_type": m.get("media_type", "image"),
                "title": m.get("title", ""),
                "description": m.get("description"),
                # source_url ONLY. supabase_url points into the deleted bucket.
                "source_url": m.get("source_url"),
                "thumbnail_url": m.get("thumbnail_url"),
                "attribution": m.get("attribution", ""),
                "license": m.get("license", "public-domain"),
                "creator": m.get("creator"),
                "creation_date": m.get("creation_date"),
                "display_order": m.get("display_order", i),
                "width": m.get("width"),
                "height": m.get("height"),
                "location": m.get("location"),
                "embed_url": m.get("embed_url"),
            }
            for i, m in enumerate(kept)
        ]

        # Hero: keep a live one, else adopt the first surviving media item and
        # its credit. Events with no Wikimedia media at all keep no hero; the
        # page already renders without one.
        if not is_renderable(row.get("hero_image_url")):
            if kept:
                row["hero_image_url"] = kept[0].get("source_url")
                row["hero_image_attribution"] = kept[0].get("attribution", "")
                heroes_substituted.append(slug)
            else:
                row["hero_image_url"] = None
                row["hero_image_attribution"] = None
                heroes_missing.append(slug)

        row["connections"] = []
        rows[slug] = row

    # Connections are directional in the YAML but the Supabase path queried both
    # endpoints and concatenated, so each event saw its inbound edges too.
    dropped = 0
    for doc in docs:
        slug = doc["slug"]
        for conn in doc.get("connections") or []:
            target = conn.get("target_slug")
            if target not in known:
                dropped += 1
                continue
            edge = {
                "connection_type": conn.get("connection_type", "influenced"),
                "description": conn.get("description") or "",
            }
            rows[slug]["connections"].append({
                **edge,
                "event_a_id": event_id(slug),
                "event_b_id": event_id(target),
                "target": {"slug": target, "title": rows[target]["title"]},
            })
            rows[target]["connections"].append({
                **edge,
                "event_a_id": event_id(slug),
                "event_b_id": event_id(target),
                "source": {"slug": slug, "title": rows[slug]["title"]},
            })
    if dropped:
        print(f"  {dropped} connection(s) dropped: target has no event file")
    total_dropped = sum(dropped_media.values())
    if total_dropped:
        print(f"  {total_dropped} media item(s) dropped: no directly renderable image url")
    if heroes_substituted:
        print(f"  {len(heroes_substituted)} hero(es) adopted from the event's own gallery")
    if heroes_missing:
        print(f"  {len(heroes_missing)} event(s) have NO hero: {heroes_missing}")

    return [rows[d["slug"]] for d in docs]


def main() -> int:
    docs = load_events()
    if not docs:
        print("history.json: MISSING (no event YAML found)")
        return 1

    rows = build_rows(docs)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    out = PUBLIC_DIR / "history.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, separators=(",", ":"), sort_keys=True)

    p = sum(len(r["perspectives"]) for r in rows)
    m = sum(len(r["media"]) for r in rows)
    cx = sum(len(r["connections"]) for r in rows)
    size_kb = out.stat().st_size / 1024
    print(
        f"history.json: ok — {len(rows)} events, {p} perspectives, "
        f"{m} media, {cx} connection edges ({size_kb:.0f} KB)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
