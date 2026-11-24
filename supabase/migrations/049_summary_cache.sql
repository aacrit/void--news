-- ============================================================================
-- Migration 049: Summary cache (content-hash + tier)
-- Date: 2026-04-29
--
-- Adds the columns needed by the post-rerank single-pass summarization step
-- introduced with the all-Sonnet pipeline rewrite.
--
-- Cache logic (pipeline/summarizer/cluster_summarizer.py:summarize_top50_after_rerank):
--   1. compute content_hash = sha256(sorted(article_ids) + "|" + len)
--   2. if hash matches summary_article_hash AND summary_tier='sonnet'
--      -> reuse stored summary, skip API call
--   3. else -> call Claude Sonnet, persist new summary + hash + tier
--
-- Both columns are nullable. Existing rows have no cache record and will be
-- summarized on the next pipeline run, populating the cache on first hit.
-- ============================================================================

ALTER TABLE story_clusters
  ADD COLUMN IF NOT EXISTS summary_article_hash TEXT,
  ADD COLUMN IF NOT EXISTS summary_tier TEXT
    CHECK (summary_tier IN ('sonnet'));

CREATE INDEX IF NOT EXISTS idx_clusters_summary_hash
  ON story_clusters(summary_article_hash);

COMMENT ON COLUMN story_clusters.summary_article_hash IS
  'sha256 of sorted article_ids + "|" + count. Used by the post-rerank '
  'summarization step to skip clusters whose article membership has not '
  'changed since their last Sonnet summary.';

COMMENT ON COLUMN story_clusters.summary_tier IS
  'Which model produced the current summary. Only "sonnet" today; reserved '
  'for future tiered rollout. NULL means rule-based / no LLM summary yet.';


-- Pipeline-run telemetry: per-run LLM call counts, cache hits, cost estimate.
-- Surfaced in command-center page for daily ops visibility.
ALTER TABLE pipeline_runs
  ADD COLUMN IF NOT EXISTS llm_metrics JSONB;

COMMENT ON COLUMN pipeline_runs.llm_metrics IS
  'JSON object with per-run LLM telemetry: summaries_total, cached_skips, '
  'cache_hit_rate, llm_calls_total, llm_failures, estimated_cost_usd, '
  'top50_coverage_pct. Written at run finalize.';

