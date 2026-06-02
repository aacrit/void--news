-- Add cover image support to weekly_digests
-- Primary source: og:image from top cover story article (publisher-curated)
-- Fallback: free API search (Wikimedia Commons, Unsplash, Pexels)

ALTER TABLE weekly_digests
  ADD COLUMN IF NOT EXISTS cover_image_url TEXT,
  ADD COLUMN IF NOT EXISTS cover_image_attribution TEXT,
  ADD COLUMN IF NOT EXISTS cover_image_source TEXT;  -- 'og_image' | 'wikimedia' | 'unsplash' | 'pexels' | 'pixabay'

COMMENT ON COLUMN weekly_digests.cover_image_url IS 'Hero image URL for weekly cover (og:image primary, free API fallback)';
COMMENT ON COLUMN weekly_digests.cover_image_attribution IS 'Image attribution string (photographer, license, source)';
COMMENT ON COLUMN weekly_digests.cover_image_source IS 'How the image was sourced: og_image, wikimedia, unsplash, pexels, pixabay';
