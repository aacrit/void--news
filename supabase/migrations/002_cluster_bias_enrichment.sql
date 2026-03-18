-- Migration 002: Cluster bias enrichment
-- Adds per-cluster bias aggregation view, enrichment columns, and ranking support.

-- ============================================================================
-- 1. New columns on story_clusters for enriched data
-- ============================================================================

ALTER TABLE story_clusters
  ADD COLUMN IF NOT EXISTS divergence_score REAL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS bias_diversity JSONB DEFAULT '{}',
  ADD COLUMN IF NOT EXISTS headline_rank REAL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS coverage_velocity INTEGER DEFAULT 0;

-- Index for headline_rank (primary sort for feed)
CREATE INDEX IF NOT EXISTS idx_clusters_headline_rank ON story_clusters(headline_rank DESC);

-- ============================================================================
-- 2. Cluster bias summary view
--    Aggregates per-article bias scores to the cluster level.
--    Weighted political lean: articles with higher factual rigor influence more.
--    Includes spread metrics (stddev, range) for divergence scoring.
-- ============================================================================

CREATE OR REPLACE VIEW cluster_bias_summary AS
SELECT
  ca.cluster_id,

  -- Weighted average political lean (weight by factual_rigor)
  CASE
    WHEN SUM(bs.factual_rigor) > 0
    THEN ROUND(SUM(bs.political_lean * bs.factual_rigor)::numeric / SUM(bs.factual_rigor)::numeric)
    ELSE ROUND(AVG(bs.political_lean))
  END AS avg_political_lean,

  ROUND(AVG(bs.sensationalism))::int AS avg_sensationalism,
  ROUND(AVG(bs.opinion_fact))::int AS avg_opinion_fact,
  ROUND(AVG(bs.factual_rigor))::int AS avg_factual_rigor,
  ROUND(AVG(bs.framing))::int AS avg_framing,

  -- Spread metrics for divergence scoring
  ROUND(COALESCE(STDDEV(bs.political_lean), 0)::numeric, 1)::real AS lean_spread,
  ROUND(COALESCE(STDDEV(bs.framing), 0)::numeric, 1)::real AS framing_spread,
  (MAX(bs.political_lean) - MIN(bs.political_lean))::int AS lean_range,
  ROUND(COALESCE(STDDEV(bs.sensationalism), 0)::numeric, 1)::real AS sensationalism_spread,
  ROUND(COALESCE(STDDEV(bs.opinion_fact), 0)::numeric, 1)::real AS opinion_spread,

  -- Confidence: higher when more articles analyzed (saturates at 5)
  LEAST(1.0, COUNT(bs.id)::real / 5.0) AS aggregate_confidence,

  COUNT(bs.id)::int AS analyzed_article_count

FROM cluster_articles ca
JOIN bias_scores bs ON bs.article_id = ca.article_id
GROUP BY ca.cluster_id;

-- ============================================================================
-- 3. RLS policy for the view (views inherit base table policies, but ensure
--    the view is accessible to anon reads)
-- ============================================================================
-- Views don't need separate RLS — they use the underlying table policies.
-- The cluster_articles and bias_scores tables already have public read.

-- ============================================================================
-- 4. Function to refresh cluster enrichment data after pipeline run.
--    Called from the pipeline after all clusters are stored.
-- ============================================================================

CREATE OR REPLACE FUNCTION refresh_cluster_enrichment(p_cluster_id UUID)
RETURNS void AS $$
DECLARE
  v_summary RECORD;
  v_divergence REAL;
  v_bias_diversity JSONB;
BEGIN
  -- Get the cluster's bias summary
  SELECT * INTO v_summary
  FROM cluster_bias_summary
  WHERE cluster_id = p_cluster_id;

  IF NOT FOUND THEN
    RETURN;
  END IF;

  -- Compute divergence score (0-100)
  -- Higher when sources disagree on political lean and framing
  v_divergence := LEAST(100.0,
    -- Lean range: 60+ point range = max contribution (40% weight)
    (LEAST(v_summary.lean_range::real / 60.0, 1.0) * 40.0) +
    -- Lean stddev: 20+ = max contribution (30% weight)
    (LEAST(v_summary.lean_spread / 20.0, 1.0) * 30.0) +
    -- Framing stddev: 25+ = max contribution (30% weight)
    (LEAST(v_summary.framing_spread / 25.0, 1.0) * 30.0)
  );

  -- Build bias diversity JSON
  v_bias_diversity := jsonb_build_object(
    'avg_political_lean', v_summary.avg_political_lean,
    'avg_sensationalism', v_summary.avg_sensationalism,
    'avg_opinion_fact', v_summary.avg_opinion_fact,
    'avg_factual_rigor', v_summary.avg_factual_rigor,
    'avg_framing', v_summary.avg_framing,
    'lean_spread', v_summary.lean_spread,
    'framing_spread', v_summary.framing_spread,
    'lean_range', v_summary.lean_range,
    'sensationalism_spread', v_summary.sensationalism_spread,
    'opinion_spread', v_summary.opinion_spread,
    'aggregate_confidence', v_summary.aggregate_confidence,
    'analyzed_count', v_summary.analyzed_article_count
  );

  -- Update the cluster
  UPDATE story_clusters
  SET
    divergence_score = v_divergence,
    bias_diversity = v_bias_diversity
  WHERE id = p_cluster_id;
END;
$$ LANGUAGE plpgsql;
