"""
void --revolt image enricher.

Adds license-safe atmospheric imagery (Unsplash + Pexels, attribution baked in)
to revolution YAML, uploading each file to the Supabase Storage bucket
"revolt-media" and appending a media entry. Idempotent: prior unsplash/pexels
entries are stripped and re-added, while authentic public-domain (Wikimedia)
entries curated from the source_enricher dossiers are preserved.

Authentic historical imagery comes from the source_enricher (Wikimedia,
public-domain). This adds atmospheric stock only, which matters most for the
active/modern movements whose authentic photos are copyright-locked wire images
we must not ingest.

Env: UNSPLASH_ACCESS_KEY and/or PEXELS_API_KEY; SUPABASE_URL/SUPABASE_KEY
(unless --dry-run).

Usage:
    python -m pipeline.revolt.image_enricher --event myanmar-spring-revolution
    python -m pipeline.revolt.image_enricher --dry-run
"""

import argparse
import os
import time
from pathlib import Path

import requests
import yaml

from pipeline.media.image_search import search_unsplash, search_pexels, ImageResult

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
EVENTS_DIR = _PROJECT_ROOT / "data" / "revolt" / "events"
BUCKET = "revolt-media"

UNSPLASH_PER_QUERY = 2
UNSPLASH_TARGET = 3
PEXELS_PER_QUERY = 2
PEXELS_TARGET = 2

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY_ENV = os.getenv("SUPABASE_KEY")

# Atmospheric / place-based queries per revolution (stock sites lack authentic
# historical imagery; authentic public-domain art comes from the source_enricher).
EVENT_QUERIES: dict[str, dict[str, list[str]]] = {
    "french-revolution": {"unsplash": ["paris monument", "france flag"], "pexels": ["old barricade"]},
    "russian-revolution": {"unsplash": ["moscow red square winter", "soviet monument"], "pexels": ["red flag protest"]},
    "iranian-revolution": {"unsplash": ["tehran city", "iran mosque"], "pexels": ["crowd protest"]},
    "haitian-revolution": {"unsplash": ["haiti landscape", "caribbean fortress"], "pexels": ["independence monument"]},
    "american-revolution": {"unsplash": ["colonial america", "american flag"], "pexels": ["independence hall"]},
    "fall-of-communism-1989": {"unsplash": ["berlin wall", "brandenburg gate"], "pexels": ["crowd celebration"]},
    "people-power-1986": {"unsplash": ["manila philippines", "peaceful protest"], "pexels": ["crowd street"]},
    "arab-spring": {"unsplash": ["cairo tahrir square", "middle east city"], "pexels": ["protest crowd square"]},
    "myanmar-spring-revolution": {"unsplash": ["yangon myanmar", "myanmar temple"], "pexels": ["protest crowd"]},
    "iran-woman-life-freedom": {"unsplash": ["tehran street", "women solidarity"], "pexels": ["protest women"]},
    "sudan-civil-war": {"unsplash": ["khartoum sudan", "african city"], "pexels": ["protest africa"]},
    "venezuela": {"unsplash": ["caracas venezuela", "latin america city"], "pexels": ["protest latin america"]},
}


def collect_images_for_event(slug: str) -> list[ImageResult]:
    spec = EVENT_QUERIES.get(slug, {})
    out: list[ImageResult] = []
    seen: set[str] = set()

    for q in spec.get("unsplash", []):
        for img in search_unsplash(q, per_page=UNSPLASH_PER_QUERY) or []:
            if img.url not in seen:
                seen.add(img.url)
                out.append(img)
        time.sleep(1)
    unsplash = [i for i in out if i.source == "unsplash"][:UNSPLASH_TARGET]

    pex: list[ImageResult] = []
    for q in spec.get("pexels", []):
        for img in search_pexels(q, per_page=PEXELS_PER_QUERY) or []:
            if img.url not in seen:
                seen.add(img.url)
                pex.append(img)
        time.sleep(1)
    pex = pex[:PEXELS_TARGET]

    return unsplash + pex


def init_supabase():
    from supabase import create_client
    if not SUPABASE_URL or not SUPABASE_KEY_ENV:
        raise EnvironmentError("SUPABASE_URL and SUPABASE_KEY required (or use --dry-run)")
    client = create_client(SUPABASE_URL, SUPABASE_KEY_ENV)
    try:
        from storage3.types import CreateOrUpdateBucketOptions
        client.storage.create_bucket(BUCKET, options=CreateOrUpdateBucketOptions(public=True))
    except Exception as e:
        if "exist" not in str(e).lower():
            print(f"    [warn] bucket: {e}")
    return client


def download_image(url: str) -> bytes | None:
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.content
    except Exception as e:
        print(f"    [warn] download failed: {e}")
        return None


def upload_to_supabase(client, slug: str, filename: str, data: bytes) -> str | None:
    path = f"{slug}/{filename}"
    try:
        try:
            client.storage.from_(BUCKET).remove([path])
        except Exception:
            pass
        client.storage.from_(BUCKET).upload(path, data, {"content-type": "image/jpeg"})
        return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"
    except Exception as e:
        print(f"    [warn] upload failed: {e}")
        return None


def update_yaml_media(slug: str, new_media: list[dict]) -> bool:
    path = EVENTS_DIR / f"{slug}.yaml"
    if not path.exists():
        print(f"    [error] YAML not found: {path}")
        return False
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    existing = data.get("media", []) or []
    # Strip prior stock entries; preserve authentic (public-domain, etc.).
    preserved = [m for m in existing if m.get("license") not in ("unsplash-license", "pexels-license")]
    data["media"] = preserved + new_media
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return True


def _media_entry(img: ImageResult, public_url: str | None) -> dict:
    entry = {
        "media_type": "photograph",
        "title": (img.alt_text or f"Atmospheric image for the movement")[:100],
        "description": f"Atmospheric imagery, {img.width}x{img.height}px",
        "source_url": img.source_url,
        "attribution": img.attribution,
        "license": img.license,
        "creator": img.photographer,
    }
    if public_url:
        entry["supabase_url"] = public_url
    return entry


def process_event(slug: str, client, dry_run: bool = False) -> dict:
    print(f"\n  Event: {slug}")
    images = collect_images_for_event(slug)
    print(f"    found {len(images)} candidate images")
    entries: list[dict] = []
    for i, img in enumerate(images):
        if dry_run:
            entries.append(_media_entry(img, None))
            continue
        blob = download_image(img.url)
        if not blob:
            continue
        fname = f"{img.source}_{i}.jpg"
        public_url = upload_to_supabase(client, slug, fname, blob)
        entries.append(_media_entry(img, public_url))
    if entries and not dry_run:
        update_yaml_media(slug, entries)
    return {"slug": slug, "found": len(images), "uploaded": len(entries)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Add atmospheric imagery to revolt events")
    parser.add_argument("--event", type=str, help="Single revolution slug")
    parser.add_argument("--dry-run", action="store_true", help="No Supabase upload / no YAML write")
    args = parser.parse_args()

    if not os.getenv("UNSPLASH_ACCESS_KEY") and not os.getenv("PEXELS_API_KEY"):
        print("  [warn] no UNSPLASH_ACCESS_KEY or PEXELS_API_KEY set; searches will return nothing.")

    client = None if args.dry_run else init_supabase()
    slugs = [args.event] if args.event else list(EVENT_QUERIES.keys())

    for slug in slugs:
        stats = process_event(slug, client, dry_run=args.dry_run)
        print(f"    {stats['found']} found, {stats['uploaded']} {'previewed' if args.dry_run else 'uploaded'}")

    print("\n  Done.")


if __name__ == "__main__":
    main()
