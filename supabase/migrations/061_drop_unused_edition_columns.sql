-- ============================================================================
-- Migration 061: drop unused per-edition rank columns
-- Date: 2026-06-02
-- Trigger: void --news collapsed to a single daily feed (collapse-editions
-- branch). rank_us, rank_europe, rank_south_asia were carried by the pipeline
-- and frontend even though only "world" was ever active. The frontend now
-- queries rank_world directly; main.py + rerank.py stopped writing the other
-- three.
--
-- This migration drops:
--   • story_clusters.rank_us, rank_europe, rank_south_asia
--   • The partial indexes that backed those columns (if present)
--
-- Defensive kept:
--   • story_clusters.section (TEXT)        — always "world" now
--   • story_clusters.sections (TEXT[])     — always ["world"]
--   • articles.section (TEXT)              — always "world"
--   • story_clusters.rank_world            — sole per-feed rank column
--   • daily_briefs.edition                 — always "world"
--
-- Reversal: ALTER TABLE story_clusters ADD COLUMN rank_us NUMERIC, etc. The
-- migrate.yml tracker prevents accidental double-apply.
-- ============================================================================

DROP INDEX IF EXISTS idx_clusters_rank_us;
DROP INDEX IF EXISTS idx_clusters_rank_europe;
DROP INDEX IF EXISTS idx_clusters_rank_south_asia;
DROP INDEX IF EXISTS idx_clusters_rank_india;       -- legacy from migration 026
DROP INDEX IF EXISTS story_clusters_rank_us_idx;
DROP INDEX IF EXISTS story_clusters_rank_europe_idx;
DROP INDEX IF EXISTS story_clusters_rank_south_asia_idx;

ALTER TABLE story_clusters DROP COLUMN IF EXISTS rank_us;
ALTER TABLE story_clusters DROP COLUMN IF EXISTS rank_europe;
ALTER TABLE story_clusters DROP COLUMN IF EXISTS rank_south_asia;
