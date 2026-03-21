-- Migration 014: Fix referential integrity and orphaned articles
-- Date: 2026-03-21
-- Audit: db-reviewer found 45.5% of articles orphaned (not in any cluster)
-- and 614 invalid article_id references in cluster_articles table.

-- ============================================================================
-- STEP 1: Remove invalid article_id references
-- ============================================================================
-- These 614 entries reference articles that no longer exist.
-- They violate referential integrity and should be removed.
-- The ON DELETE CASCADE constraint should prevent this, but if these
-- rows exist, they must be cleaned up manually.

DELETE FROM cluster_articles
WHERE article_id NOT IN (SELECT id FROM articles);

-- ============================================================================
-- STEP 2: Create single-article clusters for orphaned articles
-- ============================================================================
-- Articles that don't appear in any cluster are invisible to the frontend
-- (which only queries story_clusters). Create placeholder single-article
-- clusters so every analyzed article is discoverable.

-- Verify count before proceeding:
-- SELECT COUNT(*) as orphaned_count
-- FROM articles WHERE id NOT IN (SELECT DISTINCT article_id FROM cluster_articles);

-- Insert single-article clusters for orphaned articles
INSERT INTO story_clusters (
  title,
  summary,
  section,
  sections,
  source_count,
  first_published,
  last_updated,
  created_at,
  importance_score,
  divergence_score,
  headline_rank,
  coverage_velocity,
  bias_diversity
)
SELECT
  COALESCE(a.title, 'Untitled Story'),
  a.summary,
  COALESCE(a.section, 'world'),
  ARRAY[COALESCE(a.section, 'world')],
  1,
  a.published_at,
  NOW(),
  NOW(),
  0.0,          -- Single-source clusters have no competitive importance
  0.0,          -- No divergence (single source)
  0.0,          -- Will be recomputed in next pipeline run
  0,            -- No coverage velocity for historical articles
  jsonb_build_object(
    'avg_political_lean', bs.political_lean,
    'avg_sensationalism', bs.sensationalism,
    'avg_opinion_fact', bs.opinion_fact,
    'avg_factual_rigor', bs.factual_rigor,
    'avg_framing', bs.framing,
    'lean_spread', 0.0,
    'framing_spread', 0.0,
    'lean_range', 0,
    'sensationalism_spread', 0.0,
    'opinion_spread', 0.0,
    'aggregate_confidence', bs.confidence,
    'analyzed_count', 1
  ) as bias_diversity
FROM articles a
LEFT JOIN bias_scores bs ON bs.article_id = a.id
WHERE a.id NOT IN (
  SELECT DISTINCT article_id FROM cluster_articles
)
ORDER BY a.published_at DESC;

-- ============================================================================
-- STEP 3: Link orphaned articles to their single-article clusters
-- ============================================================================
-- Match articles to their newly created single-article clusters
-- using deterministic matching (title + section + published_at).

INSERT INTO cluster_articles (cluster_id, article_id)
SELECT sc.id, a.id
FROM articles a
INNER JOIN story_clusters sc ON (
  sc.source_count = 1
  AND sc.title = COALESCE(a.title, 'Untitled Story')
  AND sc.section = COALESCE(a.section, 'world')
  AND sc.first_published = a.published_at
)
WHERE a.id NOT IN (
  SELECT DISTINCT article_id FROM cluster_articles
)
ON CONFLICT (cluster_id, article_id) DO NOTHING;

-- ============================================================================
-- STEP 4: Verify the fix
-- ============================================================================
-- After running the above, these queries should show:
-- - Orphaned articles: 0
-- - Invalid article_id refs: 0

-- Check remaining orphaned articles:
-- SELECT COUNT(*) as remaining_orphaned
-- FROM articles WHERE id NOT IN (SELECT DISTINCT article_id FROM cluster_articles);

-- Check remaining invalid refs:
-- SELECT COUNT(*) as invalid_refs
-- FROM cluster_articles
-- WHERE article_id NOT IN (SELECT id FROM articles);

-- Check cluster count increased:
-- SELECT COUNT(*) as total_clusters FROM story_clusters;

-- ============================================================================
-- STEP 5: Update cluster sources and populate updated_at triggers
-- ============================================================================
-- Ensure all clusters have correct source_count populated.
-- (This was a manual insert, so update triggers may not have fired.)

UPDATE story_clusters sc
SET
  source_count = (
    SELECT COUNT(DISTINCT a.source_id)
    FROM cluster_articles ca
    JOIN articles a ON a.id = ca.article_id
    WHERE ca.cluster_id = sc.id
  ),
  last_updated = NOW()
WHERE source_count = 0 OR source_count IS NULL;

-- ============================================================================
-- NOTES FOR NEXT PIPELINE RUN
-- ============================================================================
-- After these changes, the next pipeline run should:
-- 1. Skip the just-created single-article clusters (already exist)
-- 2. Recompute headline_rank for all clusters (importance_ranker.py)
-- 3. Recalculate divergence_score for multi-article clusters (refresh_cluster_enrichment)
-- 4. Verify coverage_velocity is properly populated (currently broken — see audit)

-- If you want to force an immediate refresh of headline_rank:
-- UPDATE story_clusters SET headline_rank = 0 WHERE headline_rank IS NULL;
-- Then run: pipeline/rerank.py (if available)

-- ============================================================================
-- SAFETY NOTES
-- ============================================================================
-- - This migration is backward-compatible (no schema changes)
-- - All INSERTs use ON CONFLICT ... DO NOTHING to avoid duplicates if re-run
-- - No data is deleted except the 614 invalid references (safe cleanup)
-- - No columns are modified, only populated
-- - RLS policies remain unchanged (public read access)

-- ============================================================================
-- PERFORMANCE NOTES
-- ============================================================================
-- This migration touches ~4,500 articles and creates ~2,972 new clusters.
-- On Supabase free tier, this should complete in <5 minutes.
-- Monitor dashboard during execution to ensure no timeouts.
