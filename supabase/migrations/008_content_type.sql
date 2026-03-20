-- Add content_type column to story_clusters for facts vs opinion separation.
-- Populated during pipeline enrichment based on avg_opinion_fact score.
-- Frontend uses this for the universal Facts/Opinion toggle filter.

ALTER TABLE story_clusters
  ADD COLUMN IF NOT EXISTS content_type TEXT
  DEFAULT 'reporting'
  CHECK (content_type IN ('reporting', 'opinion'));

-- Index for efficient filtering
CREATE INDEX IF NOT EXISTS idx_clusters_content_type
  ON story_clusters (content_type);

-- Backfill: classify existing clusters based on bias_diversity->avg_opinion_fact
UPDATE story_clusters
SET content_type = CASE
  WHEN (bias_diversity->>'avg_opinion_fact')::float > 50 THEN 'opinion'
  ELSE 'reporting'
END
WHERE bias_diversity IS NOT NULL;
