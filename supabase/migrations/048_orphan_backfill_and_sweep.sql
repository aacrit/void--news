-- ============================================================================
-- Migration 048: Sweep stale orphans + wrap recent orphans as singletons
-- Date: 2026-04-29
-- Audit: db-reviewer (2026-04-29 post-fix) found:
--   - 79,341 articles in DB, 63,771 (80.4%) not in any cluster
--   - Article retention is supposed to delete articles older than 8 days
--     (pipeline/main.py:2949). Clearly that hasn't been keeping up — likely
--     because retention has been silently failing under the same 1000-row
--     pagination cap that was masking the audit numbers.
--
-- WHAT THIS MIGRATION DOES
-- 1. SWEEP: hard-delete orphan articles older than 10 days (matches the
--    archive-retention cutoff in main.py:2976). ON DELETE CASCADE removes
--    bias_scores and article_categories rows. Cluster_articles rows are
--    not affected because these articles aren't in any cluster.
-- 2. WRAP: for surviving orphans (within last 10 days), create a singleton
--    story_cluster + cluster_articles row. Mirrors the runtime contract in
--    pipeline/main.py:1343 so the existing corpus matches the post-fix
--    behaviour. Title falls back to a placeholder when articles.title
--    is empty so the NOT NULL constraint holds.
-- 3. Idempotent — safe to re-run. The sweep's NOT EXISTS anti-join
--    naturally short-circuits on a clean DB. The wrap's INSERT…SELECT
--    only inserts rows for articles that still have no cluster_articles
--    membership, so re-running adds nothing.
--
-- TARGETED ROW COUNTS (from 2026-04-29 audit)
--   DELETE FROM articles ... -> ~50–60K rows expected (80%+ of orphans
--                               are >10 days old once retention catches up)
--   INSERT INTO story_clusters ... -> ~5–15K rows (recent orphans)
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- STEP 1: Hard-delete orphan articles older than 10 days
-- ----------------------------------------------------------------------------
-- "Orphan" means no row in cluster_articles. ON DELETE CASCADE on
-- bias_scores.article_id and article_categories.article_id propagates.
DELETE FROM articles a
WHERE a.published_at < now() - interval '10 days'
  AND NOT EXISTS (
      SELECT 1 FROM cluster_articles ca WHERE ca.article_id = a.id
  );

-- ----------------------------------------------------------------------------
-- STEP 2: Wrap remaining orphans as singleton clusters
-- ----------------------------------------------------------------------------
-- Materialize cluster_id per orphan in a temp table so both inserts reference
-- the same UUID. Joining inserted clusters back to articles by (title,
-- published_at) is unsafe — duplicate titles like "Developing Story" produce
-- a cartesian explosion in cluster_articles.
CREATE TEMP TABLE orphan_clusters ON COMMIT DROP AS
SELECT
    gen_random_uuid()                                  AS cluster_id,
    a.id                                               AS article_id,
    COALESCE(NULLIF(a.title, ''), 'Developing Story')  AS title,
    a.summary,
    CASE WHEN a.section IN ('world','us','europe','south-asia')
         THEN a.section ELSE 'world' END               AS section,
    a.published_at
FROM articles a
WHERE NOT EXISTS (
    SELECT 1 FROM cluster_articles ca WHERE ca.article_id = a.id
);

-- 2a. Insert the singleton clusters.
INSERT INTO story_clusters
    (id, title, summary, section, source_count, first_published, last_updated, created_at)
SELECT
    cluster_id, title, summary, section, 1, published_at, now(), now()
FROM orphan_clusters;

-- 2b. Attach the junction rows.
INSERT INTO cluster_articles (cluster_id, article_id)
SELECT cluster_id, article_id FROM orphan_clusters;

COMMIT;

-- ============================================================================
-- VERIFICATION (run manually after migration)
-- ============================================================================
-- -- Should be 0:
-- SELECT COUNT(*) FROM articles a
--   WHERE NOT EXISTS (SELECT 1 FROM cluster_articles ca WHERE ca.article_id = a.id);
--
-- -- Articles count should drop dramatically (from ~79K to ~15–20K):
-- SELECT COUNT(*) FROM articles;
--
-- -- New singleton clusters added:
-- SELECT COUNT(*) FROM story_clusters WHERE source_count = 1
--   AND created_at > now() - interval '5 minutes';
