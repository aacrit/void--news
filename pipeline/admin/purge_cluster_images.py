"""
One-off purge of re-hosted cluster images (2026-08-05, copyright compliance).

The old cluster_image_cacher downloaded scraped news-publisher og:images,
re-encoded them to WebP (stripping EXIF/IPTC copyright-management info), and
stored the copies in the Supabase `cluster-images` bucket, with the public URL
in story_clusters.cached_image_url. Those stored copies are the reproduction
(and DMCA 1202(b)) exposure. The cacher stage is now disabled (main.py step 8e);
this removes the copies it already made.

Actions:
  1. Delete every object in the `cluster-images` Storage bucket.
  2. NULL story_clusters.cached_image_url + cached_image_attribution.

Idempotent (safe to re-run). Runs in CI with the service-role key
(.github/workflows/purge-cluster-images.yml).

Usage:
    python -m pipeline.admin.purge_cluster_images
"""

from pipeline.utils.supabase_client import supabase

_BUCKET = "cluster-images"


def _purge_bucket() -> int:
    removed = 0
    store = supabase.storage.from_(_BUCKET)
    while True:
        try:
            # storage3 list() returns up to 100 objects by default; loop until empty.
            objs = store.list() or []
        except Exception as e:
            print(f"[purge] bucket list failed (bucket may not exist): {e}")
            break
        names = [o["name"] for o in objs if o.get("name")]
        if not names:
            break
        try:
            store.remove(names)
            removed += len(names)
            print(f"[purge] removed {len(names)} object(s) from {_BUCKET} (running total {removed})")
        except Exception as e:
            print(f"[purge] remove batch failed: {e}")
            break
        if len(names) < 100:
            break
    return removed


def _null_columns() -> int:
    """NULL cached_image_url / cached_image_attribution on any rows that have them."""
    total = 0
    while True:
        try:
            rows = (
                supabase.table("story_clusters")
                .select("id")
                .not_.is_("cached_image_url", "null")
                .limit(500)
                .execute()
            )
        except Exception as e:
            print(f"[purge] select non-null rows failed: {e}")
            break
        ids = [r["id"] for r in (rows.data or [])]
        if not ids:
            break
        try:
            supabase.table("story_clusters").update(
                {"cached_image_url": None, "cached_image_attribution": None}
            ).in_("id", ids).execute()
            total += len(ids)
            print(f"[purge] nulled cached_image_url on {len(ids)} row(s) (running total {total})")
        except Exception as e:
            print(f"[purge] update failed: {e}")
            break
        if len(ids) < 500:
            break
    return total


def run() -> int:
    print("[purge] removing re-hosted cluster images (copyright cleanup)...")
    obj = _purge_bucket()
    rows = _null_columns()
    print(f"\n[purge] done. {obj} storage object(s) removed, {rows} row(s) cleared.")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
