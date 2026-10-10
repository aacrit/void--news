-- ============================================================================
-- Migration 056: Retroactive mega-cluster cap backfill
-- Date: 2026-05-18
-- Trigger: After migrations 054 + 055 + the 9-commit clustering fix shipped,
-- the production DB still contained the original 217-source AI-deployment
-- mega-cluster (and any other historical over-merges from 2026-05-15..17).
--
-- These clusters were created by the old engine, before Phase 5's cap and
-- before the rerank.py source_count overwrite was removed. Their articles
-- are now older than 36 hours, so the pipeline's incremental re-cluster
-- window (pipeline/main.py:1347) doesn't touch them. They sit frozen in
-- the DB with source_count > 75 and mega_cluster_capped = FALSE — which
-- means:
--   1. The frontend shows the inflated badge ("217 sources reporting")
--   2. The ranker's 0.65× mega_capped multiplier (shipped in 31d06c6)
--      cannot fire because the flag isn't set.
--
-- This one-shot backfill:
--   • Preserves the original source_count in a new column for diagnostics
--   • Caps source_count at 75 (MEGA_CLUSTER_THRESHOLD)
--   • Sets mega_cluster_capped = TRUE so the ranker demotes these rows
--
-- Reversible (full two-statement form per pipeline-tester 2026-05-20):
--   UPDATE story_clusters
--   SET source_count        = mega_cluster_original_count,
--       mega_cluster_capped = FALSE
--   WHERE mega_cluster_original_count IS NOT NULL;
--   UPDATE story_clusters
--   SET mega_cluster_original_count = NULL
--   WHERE mega_cluster_original_count IS NOT NULL;
-- Note: the single-statement form documented in the original header
-- (restore source_count only) leaves mega_cluster_capped=TRUE, which
-- means the ranker would continue to apply the 0.65-0.85x mega_capped
-- multiplier on those rows. Use the two-statement form above for
-- complete rollback.
-- ============================================================================

-- 1. Sparse diagnostic column. NULL means "never capped" (the common case);
-- non-NULL means "this row was retroactively capped on 2026-05-18".
ALTER TABLE story_clusters
  ADD COLUMN IF NOT EXISTS mega_cluster_original_count INT;

-- 2. Backfill: any cluster with source_count above the threshold gets capped,
-- with the original count preserved.
UPDATE story_clusters
SET mega_cluster_original_count = source_count,
    source_count                = 75,
    mega_cluster_capped          = TRUE
WHERE source_count > 75
  AND mega_cluster_original_count IS NULL;

-- 3. Sparse partial index for "show me the over-merges that shipped"
-- diagnostic queries (db-reviewer agent).
CREATE INDEX IF NOT EXISTS idx_story_clusters_mega_original_count
  ON story_clusters (mega_cluster_original_count DESC NULLS LAST)
  WHERE mega_cluster_original_count IS NOT NULL;
