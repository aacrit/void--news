-- Migration 009: Performance indexes for homepage and pipeline queries
-- Addresses the primary bottlenecks identified in perf-optimizer audit.

-- ============================================================================
-- 1. Composite index for homepage feed query
--    The frontend queries: WHERE section = ? ORDER BY headline_rank DESC LIMIT 100
--    A composite (section, headline_rank DESC) index lets Postgres satisfy both
--    the filter and the sort with a single index scan — no separate sort step.
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_clusters_section_headline_rank
  ON story_clusters (section, headline_rank DESC);

-- ============================================================================
-- 2. Composite index for content_type + section feed query
--    The frontend filters story_clusters by both section AND infers content_type
--    via bias_diversity->avg_opinion_fact. A direct content_type + section index
--    allows efficient filtering when the content_type column is used directly.
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_clusters_section_content_type
  ON story_clusters (section, content_type, headline_rank DESC);

-- ============================================================================
-- 3. Index on pipeline_runs for the "last completed run" query
--    Query pattern: WHERE status = 'completed' ORDER BY completed_at DESC LIMIT 1
--    Currently requires a full table scan on pipeline_runs.
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_completed
  ON pipeline_runs (status, completed_at DESC)
  WHERE status = 'completed';

-- ============================================================================
-- 4. Index on articles.url for the URL existence check in the pipeline
--    The pipeline runs: SELECT url FROM articles WHERE url IN (...) in chunks.
--    The UNIQUE constraint on url creates an implicit index, but making it
--    explicit with a covering index on just the url column improves the
--    paginated full-table scan in step 3b.
-- ============================================================================
-- Note: url already has a UNIQUE constraint (implicit btree index).
-- The paginated read (SELECT url ... RANGE offset, offset+999) uses the
-- implicit index on url. No additional index needed here.

-- ============================================================================
-- 5. Index on bias_scores(article_id) — already exists in migration 001.
--    Composite index for cluster enrichment fallback queries.
--    Pattern: SELECT ... FROM bias_scores WHERE article_id IN (list)
--    The existing idx_bias_scores_article covers this; no duplicate needed.
-- ============================================================================
