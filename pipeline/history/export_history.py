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

Images do not come from the YAML's urls at all. They come from
data/history/commons_media.json, which pipeline/history/resolve_commons.py
builds by asking Wikimedia for each file's canonical thumbnail url AND its
licence. The YAML's `source_url` is only the key into that record, and its
`license` field is a curator's note rather than the authority.

That indirection is what makes the pictures both legal and visible:

  * A file Wikimedia does not confirm as public domain or permissively licensed
    never reaches the page. The six `fair-use` entries (Napalm Girl, Tank Man,
    Hector Pieterson among them) drop out here without needing a special case.
  * The url is Wikimedia's own CDN thumbnail. The frontend used to point at
    `Special:Redirect/file/`, a MediaWiki special page that answers real traffic
    with HTTP 429, so History rendered with no images at all.

An unresolved file is dropped rather than guessed at, so a resolution failure
costs a picture and never ships a broken one. `supabase_url` is ignored
entirely: that bucket was decommissioned and every object in it is gone.

Usage:
    python -m pipeline.history.export_history
"""
import json
import os
import re
import sys
from pathlib import Path

import yaml

from .resolve_commons import commons_filename

REPO = Path(__file__).resolve().parents[2]
DATA_DIR = REPO / "data" / "history" / "events"
COMMONS_CACHE = REPO / "data" / "history" / "commons_media.json"
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


def load_commons() -> tuple[dict, dict]:
    """The verified Wikimedia records: (files by name, backfill by slug).

    Empty if the cache was never built, in which case no images are emitted at
    all. That is the intended failure: a missing cache means nothing has been
    licence-checked, and shipping unchecked pictures is the thing this whole
    path exists to prevent.
    """
    if not COMMONS_CACHE.exists():
        print("  [warn] no commons_media.json; run pipeline.history.resolve_commons. "
              "No images will be emitted.")
        return {}, {}
    data = json.loads(COMMONS_CACHE.read_text(encoding="utf-8"))
    return (data.get("files") or {}), (data.get("backfill") or {})


def _caption_from_filename(name: str) -> str:
    """A readable caption from a Commons file name.

    Backfilled pictures have no curator's caption, so the file name is what
    there is: "Trail_of_Tears_map.jpg" reads as "Trail of Tears map".
    """
    stem = re.sub(r"\.[A-Za-z0-9]{2,4}$", "", name or "")
    stem = stem.replace("_", " ").replace("-", " ")
    stem = re.sub(r"\s+", " ", stem).strip()
    return stem[:1].upper() + stem[1:] if stem else "Archival image"


def resolved_image(url, commons: dict) -> dict | None:
    """The verified record for a source url, or None if it is not usable.

    None covers every way an image fails to be publishable: the url is not a
    Commons reference at all (an Unsplash or Pexels landing page, a doi.org
    record, a dead Supabase object), the file is not hosted on Commons, or
    Wikimedia does not report a free licence for it.
    """
    name = commons_filename(url)
    if not name:
        return None
    return commons.get(name)


def _credit(rec: dict, fallback) -> str:
    """One credit line for an image: author, licence, and where it is hosted.

    CC BY and CC BY-SA are usable precisely BECAUSE the credit is rendered, so
    this is a licence condition rather than a nicety. Falls back to the curated
    attribution when Wikimedia reports no author (common on old public-domain
    scans, where there is genuinely no one to name)."""
    artist = (rec.get("artist") or "").strip()
    licence = (rec.get("licence") or "").strip()
    if artist and licence:
        return f"{artist}, {licence}, via Wikimedia Commons"
    if licence:
        return f"{licence}, via Wikimedia Commons"
    return str(fallback or "via Wikimedia Commons")


def build_rows(docs: list[dict]) -> list[dict]:
    commons, backfilled = load_commons()
    known = {d["slug"] for d in docs}
    rows: dict[str, dict] = {}
    dropped_media: dict[str, int] = {}
    heroes_substituted: list[str] = []
    heroes_missing: list[str] = []
    backfill_added: dict[str, int] = {}

    for doc in docs:
        slug = doc["slug"]
        row = {f: doc.get(f) for f in EVENT_FIELDS if f in doc}
        row["id"] = event_id(slug)
        row["is_published"] = True
        # The audio edition is NOT carried here. Which events have a produced
        # episode is recorded in frontend/public/data/history-audio.json by
        # pipeline/history/publish_audio.py, and the frontend attaches it in
        # history/audio.ts (withHistoryAudio), because the manifest is the
        # record of what actually reached the CDN and a YAML field is not.
        # These two stay for any event whose YAML still carries them; null
        # means "no episode", and the frontend hides the player.
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

        kept = []
        for m in doc.get("media") or []:
            rec = resolved_image(m.get("source_url"), commons)
            if rec:
                kept.append((m, rec))
        dropped_media[slug] = len(doc.get("media") or []) - len(kept)

        row["media"] = [
            {
                "id": f"{event_id(slug)}-m{i}",
                "event_id": event_id(slug),
                "media_type": m.get("media_type", "image"),
                "title": m.get("title", ""),
                "description": m.get("description"),
                # Wikimedia's own CDN thumbnail, not the YAML's source url.
                "source_url": rec["url"],
                "thumbnail_url": rec["url"],
                # Credit and licence as Wikimedia reports them. The YAML's own
                # fields are a curator's note and have drifted from the file.
                "attribution": _credit(rec, m.get("attribution")),
                "license": rec.get("licence") or m.get("license"),
                "creator": rec.get("artist") or m.get("creator"),
                "creation_date": m.get("creation_date"),
                "display_order": m.get("display_order", i),
                "width": rec.get("width") or m.get("width"),
                "height": rec.get("height") or m.get("height"),
                "location": m.get("location"),
                "embed_url": m.get("embed_url"),
            }
            for i, (m, rec) in enumerate(kept)
        ]

        # Roughly a third of the catalogue's curated image references name files
        # that are not on Commons at all, so verifying the list is not enough to
        # put pictures on a page. resolve_commons --backfill searched Commons for
        # each missing picture by the caption its curator wrote and recorded what
        # it found; those go after the curated ones, which keep their order.
        extra = backfilled.get(slug) or []
        for j, rec in enumerate(extra):
            row["media"].append({
                "id": f"{event_id(slug)}-b{j}",
                "event_id": event_id(slug),
                "media_type": "image",
                "title": _caption_from_filename(rec.get("name", "")),
                "description": None,
                "source_url": rec["url"],
                "thumbnail_url": rec["url"],
                "attribution": _credit(rec, None),
                "license": rec.get("licence"),
                "creator": rec.get("artist"),
                "creation_date": None,
                "display_order": len(row["media"]) + j,
                "width": rec.get("width"),
                "height": rec.get("height"),
                "location": None,
                "embed_url": None,
            })
        backfill_added[slug] = len(extra)

        # Hero: use the stored one when it verifies, else adopt the event's first
        # surviving image and ITS credit, so the caption always describes the
        # picture actually on screen. An event with nothing verified keeps no
        # hero; the page already renders without one.
        hero_rec = resolved_image(row.get("hero_image_url"), commons)
        if hero_rec:
            row["hero_image_url"] = hero_rec["url"]
            row["hero_image_attribution"] = _credit(hero_rec, row.get("hero_image_attribution"))
        elif row["media"]:
            first = row["media"][0]
            row["hero_image_url"] = first["source_url"]
            row["hero_image_attribution"] = first["attribution"]
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
        print(f"  {total_dropped} media item(s) dropped: not a verified free-licence "
              f"Wikimedia file")
    added = sum(backfill_added.values())
    if added:
        print(f"  {added} image(s) backfilled from Commons search across "
              f"{sum(1 for v in backfill_added.values() if v)} event(s)")
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
