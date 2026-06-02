-- ============================================================================
-- Migration 055: Persist wire-syndication fields on articles
-- Date: 2026-05-17
-- Trigger: 217-source mega-cluster regression analysis revealed that
-- `is_wire_copy` and `wire_origin_publisher_id` (set by
-- pipeline/clustering/deduplicator.py Phase 0) live only in memory during
-- the initial pipeline run and are discarded on insert. Any post-hoc
-- consumer (rerank.py, weekly digest, audit scripts, future analyzers)
-- that loads articles from the DB cannot perform wire-collapse, leading
-- to inflated source_count math.
--
-- Persisting these columns:
--   1. Unblocks rerank.py to do wire-aware voice collapse if ever needed
--   2. Lets db-reviewer audit scripts detect wire amplification ratios
--   3. Lets the weekly digest compute "X stories from Y voices" accurately
--   4. Costs ~2 bytes (bool) + ~36 bytes (UUID) per article — negligible
--
-- Non-breaking: NULL defaults preserve existing rows. Pipeline writes
-- start populating on the next run.
-- ============================================================================

ALTER TABLE articles
  ADD COLUMN IF NOT EXISTS is_wire_copy BOOLEAN NOT NULL DEFAULT FALSE,
  ADD COLUMN IF NOT EXISTS wire_origin_publisher_id TEXT;

-- Index for "find me all carriers of a given AP/Reuters story"
-- diagnostic queries. Sparse — most articles are originals.
CREATE INDEX IF NOT EXISTS idx_articles_wire_origin
  ON articles (wire_origin_publisher_id)
  WHERE wire_origin_publisher_id IS NOT NULL;
