-- ============================================================================
-- Migration 054: Persist mega_cluster_capped flag on story_clusters
-- Date: 2026-05-17
-- Trigger: 217-source mega-cluster regression — clustering already stamps
-- `mega_cluster_capped=True` on clusters that Phase 5 caught as over-merges
-- but couldn't cleanly re-split. The ranker had no way to read this flag
-- post-write, so over-merged clusters kept their inflated coverage scores
-- and locked into the top of the homepage.
--
-- This column lets:
--   1. main.py write the flag at the initial cluster insert
--   2. rerank.py read the flag at re-rank time
--   3. rank_importance() apply a 0.65x multiplier to demote the cluster
--      without permanently hiding it (still appears, just not at #1)
--
-- Non-breaking: DEFAULT false means existing rows are treated as
-- "not capped" (the previous behavior).
-- ============================================================================

ALTER TABLE story_clusters
  ADD COLUMN IF NOT EXISTS mega_cluster_capped BOOLEAN NOT NULL DEFAULT FALSE;

-- Optional partial index for the small subset of capped clusters.
-- Useful for diagnostic queries like "show me the over-merges from
-- yesterday" without scanning all clusters.
CREATE INDEX IF NOT EXISTS idx_story_clusters_mega_capped
  ON story_clusters (mega_cluster_capped)
  WHERE mega_cluster_capped = TRUE;
