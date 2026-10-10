"""
Backfill cluster cover images for clusters where cached_image_url is NULL.

Background
----------
UAT 2026-05-13: db-reviewer found cached_image_url is 0% populated (0/3,998)
despite migration 044 adding the column. The pipeline's in-run cacher logs
upload success, so the column must be getting set on freshly-created clusters
that are later wiped by retention — OR the update SQL is silently matching
zero rows. This script is a one-off remediation that walks the top-100 most
recent clusters with NULL cached_image_url and re-runs the cacher logic.

Invoke
------
    cd /home/aacrit/projects/void-news
    PYTHONUNBUFFERED=1 python3 scripts/backfill_cluster_images.py

Safety
------
- Read-only on `articles` (just pulls image_url + source tier)
- Writes to Supabase Storage bucket `cluster-images` (idempotent — overwrites
  prior file at `{cluster_id}.{ext}` if any)
- Writes to `story_clusters.cached_image_url` ONLY for clusters whose id was
  matched in the SELECT, so we never touch unrelated rows.
- Does NOT auto-run in CI. Manual invocation only.

Exit codes
----------
0  — backfill completed (some clusters may have failed individually; see log)
1  — fatal setup error (Supabase unreachable, etc.)
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Make pipeline/ importable
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))

try:
    from utils.supabase_client import supabase
    from media.cluster_image_cacher import cache_cluster_images
except Exception as e:
    print(f"[fatal] setup failed: {e}")
    sys.exit(1)


def main() -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    # Top-100 most recent clusters where cached_image_url IS NULL
    res = (
        supabase.table("story_clusters")
        .select("id,title,first_published,source_count,headline_rank")
        .is_("cached_image_url", "null")
        .gte("first_published", cutoff)
        .order("headline_rank", desc=True)
        .limit(100)
        .execute()
    )
    candidates = res.data or []
    print(f"[backfill] Found {len(candidates)} clusters with NULL cached_image_url (last 7 days)")
    if not candidates:
        return 0

    # Hydrate each with its articles (the cacher expects in-memory cluster dicts
    # carrying an `articles` list with image_url + source tier).
    hydrated: list[dict] = []
    for c in candidates:
        cid = c["id"]
        ca_res = supabase.table("cluster_articles").select("article_id").eq(
            "cluster_id", cid
        ).execute()
        article_ids = [r["article_id"] for r in (ca_res.data or [])]
        if not article_ids:
            continue
        art_res = supabase.table("articles").select(
            "id,source_id,image_url,title"
        ).in_("id", article_ids).execute()
        articles = art_res.data or []
        # Attach source tier + name from sources table (the cacher reads it)
        source_ids = list({a["source_id"] for a in articles if a.get("source_id")})
        if source_ids:
            src_res = supabase.table("sources").select("id,tier,name").in_(
                "id", source_ids
            ).execute()
            smap = {s["id"]: s for s in (src_res.data or [])}
            for a in articles:
                src = smap.get(a.get("source_id", ""), {})
                a["source"] = {"tier": src.get("tier", "independent"), "name": src.get("name", "")}
        c_hydrated = dict(c)
        c_hydrated["articles"] = articles
        c_hydrated["rank_world"] = c.get("headline_rank") or 0
        hydrated.append(c_hydrated)

    print(f"[backfill] Hydrated {len(hydrated)} clusters with article + source data")
    cached = cache_cluster_images(hydrated, supabase, top_n=len(hydrated))
    print(f"[backfill] Result: {len(cached)}/{len(hydrated)} clusters now have cached_image_url")
    return 0


if __name__ == "__main__":
    sys.exit(main())
