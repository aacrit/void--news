-- Migration 044: Add cached_image_url to story_clusters
-- The pipeline downloads og:images from news sources and re-serves them
-- from Supabase Storage, bypassing hotlink protection on news CDNs.
-- Frontend reads cached_image_url first; falls back to og:image-from-articles.

ALTER TABLE story_clusters
  ADD COLUMN IF NOT EXISTS cached_image_url TEXT,
  ADD COLUMN IF NOT EXISTS cached_image_attribution TEXT;

COMMENT ON COLUMN story_clusters.cached_image_url IS
  'Supabase Storage URL for the cluster cover image. Bypasses news CDN hotlink protection.';

COMMENT ON COLUMN story_clusters.cached_image_attribution IS
  'Attribution string for the cached image (e.g. "Image via Reuters").';
