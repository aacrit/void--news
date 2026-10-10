-- Migration 053: is_international flag for World section overflow slicing
--
-- (Migration number 053 because 052_ig_posts.sql was merged in from
-- the claude/ig-automation-stack branch right before this work landed.)
--
-- Context: void --news pivots from "world edition only" to "US-primary
-- newspaper with World as inline section." The frontend slices the feed:
--   /         = top 50 by headline_rank (US-primary)
--   /world    = next N where is_international AND id NOT IN top 50
-- This column drives the overflow filter.
--
-- Definition: a cluster is international iff
--   section != 'us' AND non-US-domiciled-source-count >= US-source-count
-- Both gates required to avoid mis-classifying a US-domestic story that
-- happens to have one Reuters byline.
--
-- The pipeline's main.py computes the precise value per cluster post-
-- section-assignment. The backfill below uses a coarser proxy
-- (section != 'us') so existing clusters get a usable default before the
-- next pipeline run; the next pipeline run overwrites with the precise
-- per-cluster computation.

ALTER TABLE story_clusters
    ADD COLUMN IF NOT EXISTS is_international BOOLEAN NOT NULL DEFAULT FALSE;

-- Partial index — only the TRUE rows are queried (overflow filter)
CREATE INDEX IF NOT EXISTS idx_clusters_is_international
    ON story_clusters(headline_rank DESC, is_international)
    WHERE is_international = TRUE;

-- Backfill: rough proxy by section. Pipeline next run will refine.
UPDATE story_clusters
SET is_international = TRUE
WHERE section IS NOT NULL
  AND section <> 'us'
  AND is_international = FALSE;

COMMENT ON COLUMN story_clusters.is_international IS
    'True iff cluster qualifies for the /world overflow section. '
    'Computed by pipeline/main.py compute_is_international() after '
    'section assignment. Frontend uses this + headline_rank sort + '
    'NOT-IN-main-top-50 filter to populate the inline World section.';
