-- ============================================================================
-- Migration 050: cleanup_stale_articles RPC
-- Date: 2026-05-13
-- Trigger: UAT 2026-05-13 — articles back to 2026-04-21 (22+ days old) still
-- present despite the inline retention block in pipeline/main.py. The inline
-- block paginates SELECT then DELETE — fragile under pressure (timeouts,
-- partial pagination). A single SQL DELETE is atomic, indexed on
-- published_at, and cascades through the FKs re-established in migration 046
-- (bias_scores, cluster_articles, article_categories).
--
-- Usage from pipeline:
--   supabase.rpc('cleanup_stale_articles', {'days': 8}).execute()
--
-- Default 8 days = 7 full days of data for weekly digest + 1-day buffer.
--
-- Idempotent. Safe to call from main.py [cleanup] phase. Daily briefs are
-- PERMANENT (separate retention rule lives in main.py — 8 days for digest signal).
-- ============================================================================

CREATE OR REPLACE FUNCTION cleanup_stale_articles(days INT DEFAULT 8)
RETURNS INT AS $$
DECLARE
  deleted_count INT;
BEGIN
  DELETE FROM articles
  WHERE published_at < NOW() - (days || ' days')::INTERVAL;
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Match the lockdown applied to cleanup_stale_clusters in migration 029.
REVOKE EXECUTE ON FUNCTION cleanup_stale_articles(INT) FROM anon, authenticated;
