-- ============================================================================
-- Migration 046: Cascade junction tables + clean up dangling rows
-- Date: 2026-04-29
-- Audit: db-reviewer (2026-04-29) found junction-table corruption:
--   - cluster_articles: 614 rows pointing at non-existent articles
--   - bias_scores: 326 rows pointing at non-existent articles
--   - story_clusters: 44 orphaned rows (zero linked articles)
--
-- ROOT CAUSE
-- Cleanup paths in the pipeline delete from `articles` without cascading.
-- Although 001_initial_schema.sql declared ON DELETE CASCADE on the
-- bias_scores.article_id and cluster_articles.article_id foreign keys, the
-- corruption count matches what migration 014 already cleaned in 2026-03-21.
-- Either the constraints were silently dropped on a downstream environment,
-- or rows were inserted via a path that bypassed FK enforcement
-- (e.g. service-role bulk loads against a temporarily detached constraint).
-- This migration is defensive: it drops-if-exists and re-adds with cascade,
-- guaranteeing the on-disk state matches the declared schema.
--
-- WHAT THIS MIGRATION DOES
-- 1. Drops and recreates the article_id foreign keys on cluster_articles and
--    bias_scores with ON DELETE CASCADE so future deletes from `articles`
--    propagate cleanly to the junction tables.
-- 2. One-shot cleanup of existing dangling rows in cluster_articles,
--    bias_scores, and story_clusters. Uses NOT EXISTS for index-friendly
--    anti-joins on tables with thousands of rows.
-- 3. Idempotent — safe to re-run. The constraint drops use IF EXISTS, the
--    re-adds use the same canonical Postgres-default constraint names
--    (<table>_<column>_fkey), and the DELETE statements are no-ops on a
--    clean database.
--
-- TARGETED ROW COUNTS (from 2026-04-29 audit)
--   DELETE FROM cluster_articles ...   -> 614 rows
--   DELETE FROM bias_scores ...        -> 326 rows
--   DELETE FROM story_clusters ...     ->  44 rows
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- STEP 1: Re-establish ON DELETE CASCADE on cluster_articles.article_id
-- ----------------------------------------------------------------------------
ALTER TABLE cluster_articles
    DROP CONSTRAINT IF EXISTS cluster_articles_article_id_fkey;

ALTER TABLE cluster_articles
    ADD CONSTRAINT cluster_articles_article_id_fkey
    FOREIGN KEY (article_id)
    REFERENCES articles(id)
    ON DELETE CASCADE;

-- ----------------------------------------------------------------------------
-- STEP 2: Re-establish ON DELETE CASCADE on bias_scores.article_id
-- ----------------------------------------------------------------------------
ALTER TABLE bias_scores
    DROP CONSTRAINT IF EXISTS bias_scores_article_id_fkey;

ALTER TABLE bias_scores
    ADD CONSTRAINT bias_scores_article_id_fkey
    FOREIGN KEY (article_id)
    REFERENCES articles(id)
    ON DELETE CASCADE;

-- ----------------------------------------------------------------------------
-- STEP 3: One-shot cleanup of dangling junction rows
-- ----------------------------------------------------------------------------
-- 3a. cluster_articles rows pointing at non-existent articles (audit: 614).
DELETE FROM cluster_articles ca
WHERE NOT EXISTS (
    SELECT 1 FROM articles a WHERE a.id = ca.article_id
);

-- 3b. bias_scores rows pointing at non-existent articles (audit: 326).
DELETE FROM bias_scores bs
WHERE NOT EXISTS (
    SELECT 1 FROM articles a WHERE a.id = bs.article_id
);

-- 3c. story_clusters rows with zero linked articles (audit: 44).
--     Run AFTER step 3a so that clusters orphaned by the cleanup above
--     are also swept in this same migration.
DELETE FROM story_clusters sc
WHERE NOT EXISTS (
    SELECT 1 FROM cluster_articles ca WHERE ca.cluster_id = sc.id
);

COMMIT;

-- ============================================================================
-- VERIFICATION (run manually after migration; all three should return 0)
-- ============================================================================
-- SELECT COUNT(*) FROM cluster_articles ca
--   WHERE NOT EXISTS (SELECT 1 FROM articles a WHERE a.id = ca.article_id);
-- SELECT COUNT(*) FROM bias_scores bs
--   WHERE NOT EXISTS (SELECT 1 FROM articles a WHERE a.id = bs.article_id);
-- SELECT COUNT(*) FROM story_clusters sc
--   WHERE NOT EXISTS (SELECT 1 FROM cluster_articles ca WHERE ca.cluster_id = sc.id);
