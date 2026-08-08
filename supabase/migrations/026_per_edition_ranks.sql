-- Per-edition rank columns for cross-edition differentiation.
-- headline_rank is a single column that can't support per-edition ordering.
-- Each edition gets its own rank, computed with cross-edition demotion.

ALTER TABLE story_clusters
  ADD COLUMN IF NOT EXISTS rank_world REAL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS rank_us    REAL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS rank_india REAL DEFAULT 0;

-- Backfill from existing headline_rank
UPDATE story_clusters
SET rank_world = headline_rank,
    rank_us    = headline_rank,
    rank_india = headline_rank
WHERE headline_rank > 0;

-- Partial indexes for the primary query pattern:
-- filter by sections @> ARRAY[edition], order by rank_{edition} DESC
CREATE INDEX IF NOT EXISTS idx_clusters_rank_world
  ON story_clusters (rank_world DESC)
  WHERE 'world' = ANY(sections);

CREATE INDEX IF NOT EXISTS idx_clusters_rank_us
  ON story_clusters (rank_us DESC)
  WHERE 'us' = ANY(sections);

CREATE INDEX IF NOT EXISTS idx_clusters_rank_india
  ON story_clusters (rank_india DESC)
  WHERE 'india' = ANY(sections);

-- Also add to cluster_archive for consistency
ALTER TABLE cluster_archive
  ADD COLUMN IF NOT EXISTS rank_world REAL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS rank_us    REAL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS rank_india REAL DEFAULT 0;
