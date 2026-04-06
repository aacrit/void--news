"""
Enrich history events with images from Unsplash + Pexels, mirrored to Supabase Storage.

Uses the shared `pipeline.media.image_search` module for API calls, ensuring
consistent attribution, rate limiting, and error handling across History and Weekly.

For each of 25 events:
  1. Search Unsplash (3-4 images, artistic/editorial quality)
  2. Search Pexels (2-3 images, landmarks/locations)
  3. Download and upload to Supabase Storage `history-media/{slug}/`
  4. Append to the event YAML media array with proper attribution

Legal requirements:
  - Unsplash: "Photo by {name} on Unsplash"
  - Pexels:   "Photo by {name} on Pexels"
  (Handled by image_search module's ImageResult.attribution)

Rate limiting: handled by image_search module (0.5s between sources).
  - Unsplash: 50 req/hour
  - Pexels:   200 req/hour

Usage:
    python pipeline/history/image_enricher.py
    python pipeline/history/image_enricher.py --event partition-of-india
    python pipeline/history/image_enricher.py --dry-run
"""

import os
import sys
import time
import argparse
from pathlib import Path

import requests
import yaml
from dotenv import load_dotenv
from supabase import create_client

# Ensure pipeline root is on path so we can import sibling packages
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from pipeline.media.image_search import (
    search_unsplash,
    search_pexels,
    ImageResult,
)

load_dotenv()

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY_ENV = os.getenv("SUPABASE_KEY")

BUCKET = "history-media"
EVENTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "history" / "events"

# Unsplash: 3 queries x 2 per_page = ~6 candidates, cap at 4
UNSPLASH_PER_QUERY = 2
UNSPLASH_TARGET = 4

# Pexels: 2 queries x 2 per_page = ~4 candidates, cap at 3
PEXELS_PER_QUERY = 2
PEXELS_TARGET = 3

# ---------------------------------------------------------------------------
# Search queries per event
# "unsplash": artistic/editorial queries
# "pexels":   landmark/location queries
# ---------------------------------------------------------------------------
EVENT_QUERIES = {
    "partition-of-india": {
        "unsplash": ["India partition 1947", "India Pakistan border Wagah", "Punjab heritage"],
        "pexels": ["India Pakistan border Wagah", "Punjab India heritage"],
    },
    "hiroshima-nagasaki": {
        "unsplash": ["Hiroshima peace memorial dome", "Nagasaki atomic bomb memorial", "Japan peace crane"],
        "pexels": ["Hiroshima peace memorial", "Nagasaki memorial park"],
    },
    "rwandan-genocide": {
        "unsplash": ["Rwanda genocide memorial Kigali", "Rwanda reconciliation", "East Africa memorial"],
        "pexels": ["Kigali Rwanda memorial", "Rwanda landscape"],
    },
    "creation-of-israel-nakba": {
        "unsplash": ["Jerusalem old city", "Palestine refugee camp", "Israel Palestine wall"],
        "pexels": ["Jerusalem old city walls", "Palestine landscape"],
    },
    "fall-of-berlin-wall": {
        "unsplash": ["Berlin Wall memorial", "Brandenburg Gate", "German reunification"],
        "pexels": ["Berlin Wall art graffiti", "Brandenburg Gate Berlin"],
    },
    "french-revolution": {
        "unsplash": ["Bastille Paris", "French Revolution art painting", "Versailles palace"],
        "pexels": ["Place de la Bastille Paris", "Versailles palace France"],
    },
    "opium-wars": {
        "unsplash": ["Hong Kong colonial history", "China trade port historic", "Canton Guangzhou old"],
        "pexels": ["Hong Kong harbor historic", "Guangzhou China old city"],
    },
    "scramble-for-africa": {
        "unsplash": ["Africa colonial borders", "Congo river historic", "African independence"],
        "pexels": ["Africa colonial architecture", "African independence monument"],
    },
    "trail-of-tears": {
        "unsplash": ["Cherokee heritage", "Native American memorial Oklahoma", "Trail of Tears historic route"],
        "pexels": ["Cherokee Nation Oklahoma", "Native American heritage"],
    },
    "transatlantic-slave-trade": {
        "unsplash": ["slave trade memorial", "Ghana cape coast castle", "middle passage memorial"],
        "pexels": ["Cape Coast Castle Ghana", "slavery memorial"],
    },
    "armenian-genocide": {
        "unsplash": ["Armenian genocide memorial Yerevan", "Tsitsernakaberd memorial", "Armenia historic church"],
        "pexels": ["Yerevan Armenia memorial", "Armenian church historic"],
    },
    "holodomor": {
        "unsplash": ["Ukraine wheat field historic", "Holodomor memorial Kyiv", "Ukraine famine memorial"],
        "pexels": ["Ukraine wheat field golden", "Kyiv memorial monument"],
    },
    "congo-free-state": {
        "unsplash": ["Congo River historic", "Belgium colonial Africa", "Kinshasa historic"],
        "pexels": ["Congo River Africa", "Kinshasa city"],
    },
    "tiananmen-square": {
        "unsplash": ["Tiananmen Square Beijing", "Beijing Forbidden City", "China democracy memorial"],
        "pexels": ["Tiananmen Square Beijing", "Forbidden City Beijing"],
    },
    "cambodian-genocide": {
        "unsplash": ["Tuol Sleng museum Cambodia", "Angkor Wat Cambodia", "Phnom Penh killing fields"],
        "pexels": ["Angkor Wat Cambodia temple", "Phnom Penh Cambodia"],
    },
    "meiji-restoration": {
        "unsplash": ["Japan Meiji era", "Tokyo imperial palace", "Japanese modernization historic"],
        "pexels": ["Tokyo imperial palace Japan", "Japanese traditional architecture"],
    },
    "treaty-of-waitangi": {
        "unsplash": ["New Zealand Maori heritage", "Waitangi Treaty grounds", "New Zealand indigenous"],
        "pexels": ["New Zealand Maori culture", "Waitangi New Zealand"],
    },
    "bolivarian-revolutions": {
        "unsplash": ["South America independence", "Caracas Venezuela historic", "Simon Bolivar statue"],
        "pexels": ["Simon Bolivar statue South America", "Caracas Venezuela"],
    },
    "ashoka-maurya-empire": {
        "unsplash": ["Ashoka pillar India", "Sanchi stupa Buddhist", "Maurya empire ruins"],
        "pexels": ["Sanchi stupa India", "Ashoka pillar ancient India"],
    },
    "peloponnesian-war": {
        "unsplash": ["Athens Parthenon Greece", "ancient Greek ruins Sparta", "Peloponnese Greece"],
        "pexels": ["Parthenon Athens Greece", "ancient Greek ruins"],
    },
    "fall-of-rome": {
        "unsplash": ["Rome Colosseum ruins", "Roman Forum ancient", "Roman empire ruins"],
        "pexels": ["Colosseum Rome Italy", "Roman Forum ruins"],
    },
    "mongol-conquest-baghdad": {
        "unsplash": ["Baghdad historic mosque", "Mongol Empire Central Asia", "Iraq historic ruins"],
        "pexels": ["Baghdad mosque Iraq", "Central Asia historic"],
    },
    "the-crusades": {
        "unsplash": ["Jerusalem walls historic", "Crusader castle Middle East", "Holy Land historic"],
        "pexels": ["Jerusalem old walls", "Crusader castle ruins"],
    },
    "mali-empire-mansa-musa": {
        "unsplash": ["Timbuktu mosque Mali", "Mali Africa Djenne mosque", "West Africa historic"],
        "pexels": ["Djenne mosque Mali Africa", "Timbuktu Mali"],
    },
    "haitian-revolution": {
        "unsplash": ["Haiti Citadelle fortress", "Port au Prince historic", "Caribbean colonial historic"],
        "pexels": ["Citadelle Laferriere Haiti", "Port au Prince Haiti"],
    },
}


# ---------------------------------------------------------------------------
# Collect images for an event using shared image_search module
# ---------------------------------------------------------------------------
def collect_images_for_event(slug: str) -> list[ImageResult]:
    """
    Run Unsplash + Pexels queries for an event via shared image_search module.
    Returns deduplicated list: up to 4 Unsplash + up to 3 Pexels = 5-7 total.
    """
    queries = EVENT_QUERIES.get(slug)
    if not queries:
        print(f"  No queries defined for {slug}")
        return []

    unsplash_queries = queries.get("unsplash", [])
    pexels_queries = queries.get("pexels", [])

    seen_urls = set()
    unsplash_images: list[ImageResult] = []
    pexels_images: list[ImageResult] = []

    # Unsplash searches
    for query in unsplash_queries:
        print(f"    [Unsplash] '{query}'")
        results = search_unsplash(query, per_page=UNSPLASH_PER_QUERY)
        for img in results:
            if img.url not in seen_urls:
                seen_urls.add(img.url)
                unsplash_images.append(img)
        time.sleep(1)

    # Pexels searches
    for query in pexels_queries:
        print(f"    [Pexels]   '{query}'")
        results = search_pexels(query, per_page=PEXELS_PER_QUERY)
        for img in results:
            if img.url not in seen_urls:
                seen_urls.add(img.url)
                pexels_images.append(img)
        time.sleep(1)

    # Trim to targets
    unsplash_images = unsplash_images[:UNSPLASH_TARGET]
    pexels_images = pexels_images[:PEXELS_TARGET]

    return unsplash_images + pexels_images


# ---------------------------------------------------------------------------
# Download & Upload
# ---------------------------------------------------------------------------
def init_supabase():
    """Create Supabase client and ensure bucket exists."""
    client = create_client(SUPABASE_URL, SUPABASE_KEY_ENV)
    try:
        from storage3.types import CreateOrUpdateBucketOptions
        opts = CreateOrUpdateBucketOptions(public=True)
        client.storage.create_bucket(BUCKET, options=opts)
        print(f"  Created bucket '{BUCKET}'")
    except Exception as e:
        msg = str(e)
        if any(k in msg.lower() for k in ("already exists", "duplicate", "409")):
            pass
        else:
            print(f"  Bucket note: {msg}")
    return client


def download_image(url: str) -> bytes | None:
    """Download image bytes from a URL."""
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        return r.content
    except requests.RequestException as e:
        print(f"      Download failed: {e}")
        return None


def upload_to_supabase(client, slug: str, filename: str, data: bytes) -> str | None:
    """Upload image to Supabase Storage and return public URL."""
    path = f"{slug}/{filename}"
    try:
        # Remove existing to allow idempotent re-runs
        try:
            client.storage.from_(BUCKET).remove([path])
        except Exception:
            pass
        client.storage.from_(BUCKET).upload(
            path, data, {"content-type": "image/jpeg"}
        )
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"
        return public_url
    except Exception as e:
        print(f"      Upload failed: {e}")
        return None


# ---------------------------------------------------------------------------
# YAML update
# ---------------------------------------------------------------------------
def update_yaml_media(slug: str, new_media_entries: list[dict]) -> bool:
    """
    Append new Unsplash/Pexels media entries to the event's YAML file.
    Preserves existing entries (Wikimedia archival).
    Re-runs are idempotent: previous Unsplash/Pexels entries are removed first.
    """
    yaml_path = EVENTS_DIR / f"{slug}.yaml"
    if not yaml_path.exists():
        print(f"  YAML not found: {yaml_path}")
        return False

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    existing_media = data.get("media", [])

    # Remove previous Unsplash/Pexels entries for idempotent re-runs
    existing_media = [
        m for m in existing_media
        if not any(
            provider in m.get("attribution", "").lower()
            for provider in ("unsplash", "pexels")
        )
    ]

    existing_media.extend(new_media_entries)
    data["media"] = existing_media

    with open(yaml_path, "w") as f:
        yaml.dump(
            data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            width=120,
            sort_keys=False,
        )

    return True


# ---------------------------------------------------------------------------
# Process one event
# ---------------------------------------------------------------------------
def process_event(slug: str, client, dry_run: bool = False) -> dict:
    """Search both APIs, download, upload, update YAML for one event."""
    print(f"\n{'='*60}")
    print(f"  {slug}")
    print(f"{'='*60}")

    images = collect_images_for_event(slug)
    if not images:
        print(f"  No images found for {slug}")
        return {"slug": slug, "found": 0, "uploaded": 0}

    unsplash_count = sum(1 for i in images if i.source == "unsplash")
    pexels_count = sum(1 for i in images if i.source == "pexels")
    print(f"  Found {len(images)} images (Unsplash: {unsplash_count}, Pexels: {pexels_count})")

    if dry_run:
        for i, img in enumerate(images):
            print(f"    [{i+1}] [{img.source}] {img.photographer} — {img.alt_text[:60]}")
        return {"slug": slug, "found": len(images), "uploaded": 0}

    new_media = []
    uploaded = 0
    unsplash_idx = 0
    pexels_idx = 0

    for img in images:
        if img.source == "unsplash":
            unsplash_idx += 1
            filename = f"unsplash_{unsplash_idx}.jpg"
        else:
            pexels_idx += 1
            filename = f"pexels_{pexels_idx}.jpg"

        print(f"    [{uploaded+1}/{len(images)}] [{img.source}] {img.photographer}...")

        data = download_image(img.url)
        if data is None:
            continue

        print(f"      {len(data):,} bytes -> {slug}/{filename}")
        public_url = upload_to_supabase(client, slug, filename, data)
        if public_url is None:
            continue

        uploaded += 1
        print(f"      OK")

        # Build media entry for YAML — use attribution from ImageResult
        new_media.append({
            "media_type": "photograph",
            "title": img.alt_text[:100] if img.alt_text else f"Image for {slug}",
            "description": f"Landscape orientation, {img.width}x{img.height}px",
            "source_url": img.source_url,
            "supabase_url": public_url,
            "attribution": img.attribution,
            "license": img.license,
            "creator": img.photographer,
        })

        time.sleep(0.5)

    if new_media:
        ok = update_yaml_media(slug, new_media)
        if ok:
            print(f"  Updated YAML with {len(new_media)} new entries")
        else:
            print(f"  YAML update failed")

    return {"slug": slug, "found": len(images), "uploaded": uploaded}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="Enrich history events with Unsplash + Pexels images"
    )
    parser.add_argument("--event", type=str, help="Process single event by slug")
    parser.add_argument("--dry-run", action="store_true", help="Search only, no downloads")
    args = parser.parse_args()

    # Check API keys
    unsplash_ok = bool(os.getenv("UNSPLASH_ACCESS_KEY"))
    pexels_ok = bool(os.getenv("PEXELS_API_KEY"))
    if not unsplash_ok and not pexels_ok:
        print("ERROR: At least one of UNSPLASH_ACCESS_KEY or PEXELS_API_KEY must be set")
        sys.exit(1)
    if not unsplash_ok:
        print("WARNING: UNSPLASH_ACCESS_KEY not set — Unsplash searches disabled")
    if not pexels_ok:
        print("WARNING: PEXELS_API_KEY not set — Pexels searches disabled")

    if not args.dry_run and (not SUPABASE_URL or not SUPABASE_KEY_ENV):
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env")
        sys.exit(1)

    print("=" * 60)
    print("void --history  Image Enricher (Unsplash + Pexels)")
    print("=" * 60)
    sources = []
    if unsplash_ok:
        sources.append("Unsplash")
    if pexels_ok:
        sources.append("Pexels")
    print(f"  Sources: {' + '.join(sources)}")
    print(f"  Using shared image_search module for API calls")

    client = None
    if not args.dry_run:
        client = init_supabase()

    if args.event:
        slugs = [args.event]
        if args.event not in EVENT_QUERIES:
            print(f"WARNING: No queries defined for '{args.event}'")
    else:
        slugs = list(EVENT_QUERIES.keys())

    print(f"  Processing {len(slugs)} event(s)")
    if args.dry_run:
        print("  DRY RUN — no downloads or uploads")

    results = []
    for slug in slugs:
        result = process_event(slug, client, dry_run=args.dry_run)
        results.append(result)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total_found = sum(r["found"] for r in results)
    total_uploaded = sum(r["uploaded"] for r in results)
    print(f"  Events:   {len(results)}")
    print(f"  Found:    {total_found}")
    print(f"  Uploaded: {total_uploaded}")
    print()
    for r in results:
        status = f"found={r['found']}, uploaded={r['uploaded']}"
        print(f"  {r['slug']:40s} {status}")

    if total_uploaded > 0:
        print(f"\n  Images mirrored to Supabase and YAML files updated.")


if __name__ == "__main__":
    main()
