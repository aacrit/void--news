"""
Cluster image cacher — solves hotlink protection on news CDN images.

News outlets block <img src> cross-domain requests (hotlinking). The pipeline
runs on GitHub Actions (neutral server, no Referer header), so downloads succeed.
We re-upload to Supabase Storage and serve the cached URL — no hotlinking issue.

Flow per top-N cluster:
  1. Download best og:image from cluster articles (tier-prioritised: us_major first)
  2. If download fails → try Wikimedia Commons by cluster title
  3. Upload to Supabase Storage bucket "cluster-images/{cluster_id}.jpg"
  4. UPDATE story_clusters SET cached_image_url = public_url WHERE id = cluster_id

Storage budget: 10 clusters × ~150KB × 2 runs/day ≈ 3MB/day → ~90MB/month
(well within Supabase 1GB free tier; old images are overwritten each run).
"""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING

import requests

if TYPE_CHECKING:
    pass  # supabase client type hint only

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (compatible; voidnews-pipeline/1.0; "
        "+https://github.com/void-news)"
    )
})

_BUCKET = "cluster-images"
_SKIP_PATTERNS = [
    "logo", "icon", "favicon", "pixel", "spacer", "tracker",
    "1x1", "blank", "placeholder", "default-og", "brand", "avatar",
    "share-", "social-share", "twitter-card",
]
_TIER_RANK = {"us_major": 3, "international": 2, "independent": 1}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _init_bucket(client) -> None:
    """Ensure the cluster-images bucket exists and is public."""
    try:
        from storage3.types import CreateOrUpdateBucketOptions
        opts = CreateOrUpdateBucketOptions(public=True)
        client.storage.create_bucket(_BUCKET, options=opts)
    except Exception as e:
        msg = str(e).lower()
        if not any(k in msg for k in ("already exists", "duplicate", "409")):
            print(f"  [img-cache] bucket note: {e}")


def _is_valid_url(url: str) -> bool:
    url_l = url.lower()
    return (
        bool(url)
        and len(url) >= 20
        and not url.startswith("data:")
        and not any(p in url_l for p in _SKIP_PATTERNS)
    )


def _download(url: str) -> tuple[bytes, str] | None:
    """Download image. Returns (bytes, content_type) or None."""
    try:
        resp = _SESSION.get(url, timeout=20, stream=False)
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "")
        if "image" not in ct:
            return None
        data = resp.content
        if len(data) < 1000:           # <1KB = likely a redirect or placeholder
            return None
        return data, ct.split(";")[0].strip()
    except Exception:
        return None


def _upload(client, cluster_id: str, data: bytes, content_type: str) -> str | None:
    """Upload to Supabase Storage, return public URL or None."""
    supabase_url = os.getenv("SUPABASE_URL", "").rstrip("/")
    if not supabase_url:
        return None
    ext = "jpg" if "jpeg" in content_type or "jpg" in content_type else "jpg"
    path = f"{cluster_id}.{ext}"
    try:
        # Overwrite previous run's image (idempotent)
        try:
            client.storage.from_(_BUCKET).remove([path])
        except Exception:
            pass
        client.storage.from_(_BUCKET).upload(path, data, {"content-type": content_type})
        return f"{supabase_url}/storage/v1/object/public/{_BUCKET}/{path}"
    except Exception as e:
        print(f"  [img-cache] upload failed {cluster_id[:8]}: {e}")
        return None


def _best_article_image(cluster: dict) -> tuple[str, str]:
    """
    Return (image_url, source_name) from the cluster's in-memory articles,
    preferring higher-tier sources (us_major > international > independent).
    """
    best_url = ""
    best_name = ""
    best_rank = -1

    for art in cluster.get("articles", []):
        url = art.get("image_url") or ""
        if not _is_valid_url(url):
            continue

        # Source tier: the article dict may store source as dict or string
        source = art.get("source") or {}
        if isinstance(source, str):
            tier = "independent"
            name = source
        else:
            tier = source.get("tier", "independent")
            name = source.get("name", "")

        rank = _TIER_RANK.get(tier, 0)
        if rank > best_rank:
            best_rank = rank
            best_url = url
            best_name = name

    return best_url, best_name


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def cache_cluster_images(
    clusters: list[dict],
    supabase_client,
    top_n: int = 10,
) -> dict[str, str]:
    """
    Download og:images for the top-N clusters and re-serve from Supabase Storage.

    Args:
        clusters: Full in-memory cluster list (with articles).
        supabase_client: Authenticated Supabase client.
        top_n: Number of clusters to cache (default 10).

    Returns:
        Dict mapping cluster_id → cached public URL for successfully cached clusters.
    """
    if not supabase_client:
        return {}

    _init_bucket(supabase_client)

    # Select top-N by rank_world (post-holistic-rerank), then headline_rank fallback
    # Only include clusters with proper DB UUIDs — in-memory clusters created this run
    # may have Python object id() as their id before being written to Supabase (step 9).
    import re as _re
    _UUID_RE = _re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        _re.IGNORECASE,
    )
    eligible = [
        c for c in clusters
        if c.get("id")
        and _UUID_RE.match(str(c["id"]))  # skip Python memory-address IDs
        and not c.get("_is_opinion")
        and c.get("articles")
    ]
    no_uuid = sum(
        1 for c in clusters
        if c.get("id") and not _UUID_RE.match(str(c["id"]))
    )
    if no_uuid > 0:
        print(f"  [img-cache] Skipped {no_uuid} cluster(s) without a DB UUID (in-memory only, not yet persisted)")

    ranked = sorted(
        eligible,
        key=lambda c: c.get("rank_world") or c.get("headline_rank") or 0,
        reverse=True,
    )[:top_n]

    cached: dict[str, str] = {}

    for cluster in ranked:
        cluster_id: str = cluster["id"]

        # --- Strategy 1: og:image from cluster articles ---
        img_url, source_name = _best_article_image(cluster)
        result = None
        attribution = ""

        if img_url:
            result = _download(img_url)
            if result:
                attribution = f"Image via {source_name}" if source_name else "Publisher image"

        # --- Strategy 2: Wikimedia Commons fallback ---
        if not result:
            try:
                from media.image_search import search_wikimedia
                title = cluster.get("title", "")
                wiki_results = search_wikimedia(title, max_results=2)
                for wr in wiki_results:
                    result = _download(wr.url)
                    if result:
                        attribution = wr.attribution
                        break
            except Exception:
                pass

        if not result:
            continue

        data, content_type = result
        public_url = _upload(supabase_client, cluster_id, data, content_type)
        if not public_url:
            continue

        # Persist to DB
        try:
            supabase_client.table("story_clusters").update({
                "cached_image_url": public_url,
                "cached_image_attribution": attribution,
            }).eq("id", cluster_id).execute()
        except Exception as e:
            print(f"  [img-cache] DB update failed {cluster_id[:8]}: {e}")
            continue

        # Update in-memory cluster so downstream steps see it
        cluster["cached_image_url"] = public_url
        cluster["cached_image_attribution"] = attribution
        cached[cluster_id] = public_url

        # Polite delay — avoid hammering news CDNs
        time.sleep(0.3)

    ok = len(cached)
    total = len(ranked)
    print(f"  Image cache: {ok}/{total} clusters → Supabase Storage")
    return cached
