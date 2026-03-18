-- Migration 003: Schema fixes from db-reviewer audit (score: 62/100 → target 85+)
--
-- Critical: Missing indexes, cascades, constraints
-- Must Have: Stale cleanup, dead table fix, query optimization

-- ============================================================================
-- 1. CRITICAL: Composite index for homepage query
--    Frontend queries WHERE section=X ORDER BY headline_rank DESC
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_clusters_section_headline_rank
  ON story_clusters(section, headline_rank DESC);

-- ============================================================================
-- 2. CRITICAL: Index on pipeline_runs for frontend "last updated" query
--    Frontend queries WHERE status='completed' ORDER BY completed_at DESC
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_pipeline_runs_status_completed
  ON pipeline_runs(status, completed_at DESC);

-- ============================================================================
-- 3. CRITICAL: Add ON DELETE CASCADE to articles.source_id
--    Prevents FK violations if a source is ever removed
-- ============================================================================

ALTER TABLE articles DROP CONSTRAINT IF EXISTS articles_source_id_fkey;
ALTER TABLE articles ADD CONSTRAINT articles_source_id_fkey
  FOREIGN KEY (source_id) REFERENCES sources(id) ON DELETE CASCADE;

-- ============================================================================
-- 4. MUST HAVE: NOT NULL + DEFAULT on articles.section
--    Prevents articles from falling through section-based queries
-- ============================================================================

-- Backfill any existing NULLs
UPDATE articles SET section = 'world' WHERE section IS NULL;

ALTER TABLE articles ALTER COLUMN section SET NOT NULL;
ALTER TABLE articles ALTER COLUMN section SET DEFAULT 'world';

-- ============================================================================
-- 5. MUST HAVE: CHECK constraint on bias_scores.confidence
-- ============================================================================

ALTER TABLE bias_scores ADD CONSTRAINT IF NOT EXISTS chk_confidence_range
  CHECK (confidence BETWEEN 0.0 AND 1.0);

-- ============================================================================
-- 6. MUST HAVE: Stale cluster cleanup function
--    Call from pipeline or scheduled job to prevent unbounded table growth
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_stale_clusters(max_age_days INT DEFAULT 7)
RETURNS INT AS $$
DECLARE
  deleted_count INT;
BEGIN
  DELETE FROM story_clusters
  WHERE first_published < NOW() - (max_age_days || ' days')::INTERVAL;
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 7. MUST HAVE: Stuck pipeline run cleanup
--    Marks runs stuck in 'running' for > 30 minutes as 'failed'
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_stuck_pipeline_runs(max_minutes INT DEFAULT 30)
RETURNS INT AS $$
DECLARE
  cleaned INT;
BEGIN
  UPDATE pipeline_runs
  SET status = 'failed',
      completed_at = NOW(),
      errors = errors || jsonb_build_array(jsonb_build_object(
        'error', 'Pipeline run timed out (stuck in running state)',
        'timestamp', NOW()::text
      ))
  WHERE status = 'running'
    AND started_at < NOW() - (max_minutes || ' minutes')::INTERVAL;
  GET DIAGNOSTICS cleaned = ROW_COUNT;
  RETURN cleaned;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 8. Index on divergence_score for potential future queries
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_clusters_divergence_score
  ON story_clusters(divergence_score DESC);
