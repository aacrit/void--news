-- ============================================================================
-- Migration 047: Cascade cluster_articles.cluster_id + recompute source_count
-- Date: 2026-04-29
-- Audit: db-reviewer (2026-04-29) found cluster-side junction corruption:
--   - 8,694 cluster_articles rows pointing at deleted story_clusters
--   - 3,927 story_clusters rows with cached source_count out of sync with
--     the actual COUNT(DISTINCT articles.source_id) over cluster_articles
--
-- ROOT CAUSE
-- 001_initial_schema.sql declared ON DELETE CASCADE on
-- cluster_articles.cluster_id, but the audit shows thousands of dangling
-- rows survived cluster deletes. The same pattern as migration 046:
-- either the constraint was silently dropped on a downstream environment,
-- or rows were inserted via a path that bypassed FK enforcement
-- (service-role bulk loads against a temporarily detached constraint).
-- Migration 046 cleaned up the article_id side; this migration mirrors
-- that defense for the cluster_id side.
--
-- WHAT THIS MIGRATION DOES
-- 1. Drops and recreates the cluster_id foreign key on cluster_articles
--    with ON DELETE CASCADE so future deletes from `story_clusters`
--    propagate cleanly to the junction table.
-- 2. One-shot cleanup of cluster_articles rows pointing at non-existent
--    story_clusters (NOT EXISTS anti-join, index-friendly).
-- 3. Recomputes the cached source_count on every story_clusters row where
--    the cached value disagrees with the live count over cluster_articles
--    joined to articles. Live count uses COUNT(DISTINCT articles.source_id)
--    so duplicate sources within a cluster collapse correctly.
-- 4. Idempotent — safe to re-run. The constraint drop uses IF EXISTS, the
--    re-add uses the canonical Postgres-default name
--    (cluster_articles_cluster_id_fkey), and the DELETE / UPDATE statements
--    are no-ops on a clean database.
--
-- TARGETED ROW COUNTS (from 2026-04-29 audit)
--   DELETE FROM cluster_articles ... -> 8,694 rows
--   UPDATE story_clusters ...        -> 3,927 rows
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- STEP 1: Re-establish ON DELETE CASCADE on cluster_articles.cluster_id
-- ----------------------------------------------------------------------------
ALTER TABLE cluster_articles
    DROP CONSTRAINT IF EXISTS cluster_articles_cluster_id_fkey;

ALTER TABLE cluster_articles
    ADD CONSTRAINT cluster_articles_cluster_id_fkey
    FOREIGN KEY (cluster_id)
    REFERENCES story_clusters(id)
    ON DELETE CASCADE;

-- ----------------------------------------------------------------------------
-- STEP 2: One-shot cleanup of cluster_articles rows pointing at deleted
--         story_clusters (audit: 8,694 rows).
-- ----------------------------------------------------------------------------
DELETE FROM cluster_articles ca
WHERE NOT EXISTS (
    SELECT 1 FROM story_clusters sc WHERE sc.id = ca.cluster_id
);

-- ----------------------------------------------------------------------------
-- STEP 3: Recompute cached source_count where it disagrees with reality
--         (audit: 3,927 rows). Live count over cluster_articles joined to
--         articles, COUNT(DISTINCT a.source_id) so duplicate sources within
--         a cluster collapse to one.
-- ----------------------------------------------------------------------------
UPDATE story_clusters sc
SET source_count = (
    SELECT COUNT(DISTINCT a.source_id)
    FROM cluster_articles ca
    JOIN articles a ON a.id = ca.article_id
    WHERE ca.cluster_id = sc.id
)
WHERE source_count IS DISTINCT FROM (
    SELECT COUNT(DISTINCT a.source_id)
    FROM cluster_articles ca
    JOIN articles a ON a.id = ca.article_id
    WHERE ca.cluster_id = sc.id
);

COMMIT;

-- ============================================================================
-- VERIFICATION (run manually after migration; both should return 0)
-- ============================================================================
-- SELECT COUNT(*) FROM cluster_articles ca
--   WHERE NOT EXISTS (SELECT 1 FROM story_clusters sc WHERE sc.id = ca.cluster_id);
-- SELECT COUNT(*) FROM story_clusters sc
--   WHERE source_count IS DISTINCT FROM (
--       SELECT COUNT(DISTINCT a.source_id)
--       FROM cluster_articles ca
--       JOIN articles a ON a.id = ca.article_id
--       WHERE ca.cluster_id = sc.id
--   );
