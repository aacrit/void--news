-- Add rank_europe column for Europe edition support
-- Mirrors rank_world, rank_us, rank_india pattern

ALTER TABLE story_clusters
    ADD COLUMN IF NOT EXISTS rank_europe REAL DEFAULT 0;

-- Index for frontend ordering by Europe edition rank
CREATE INDEX IF NOT EXISTS idx_clusters_rank_europe
    ON story_clusters (rank_europe DESC);
