-- Migration 004: Three-lens bias visualization enrichment
-- Adds rationale JSONB to bias_scores and updates cluster enrichment
-- to include coverage_score and tier_breakdown for the 3-lens UI.

-- ============================================================================
-- 1. Add rationale column to bias_scores
--    Stores per-analyzer evidence (keywords found, sub-scores, etc.)
--    for hover popup rationale display.
-- ============================================================================

ALTER TABLE bias_scores
  ADD COLUMN IF NOT EXISTS rationale JSONB DEFAULT '{}';

-- ============================================================================
-- 2. Update refresh_cluster_enrichment() to compute coverage_score
--    and tier_breakdown for the 3-lens visualization.
-- ============================================================================

CREATE OR REPLACE FUNCTION refresh_cluster_enrichment(p_cluster_id UUID)
RETURNS void AS $$
DECLARE
  v_summary RECORD;
  v_divergence REAL;
  v_bias_diversity JSONB;
  v_source_count INTEGER;
  v_tier_breakdown JSONB;
  v_tier_count INTEGER;
  v_coverage_score REAL;
  v_opinion_label TEXT;
BEGIN
  -- Get the cluster's bias summary
  SELECT * INTO v_summary
  FROM cluster_bias_summary
  WHERE cluster_id = p_cluster_id;

  IF NOT FOUND THEN
    RETURN;
  END IF;

  -- Get source count from cluster
  SELECT source_count INTO v_source_count
  FROM story_clusters
  WHERE id = p_cluster_id;

  -- Compute tier breakdown
  SELECT
    jsonb_build_object(
      'us_major', COUNT(*) FILTER (WHERE s.tier = 'us_major'),
      'international', COUNT(*) FILTER (WHERE s.tier = 'international'),
      'independent', COUNT(*) FILTER (WHERE s.tier = 'independent')
    ),
    COUNT(DISTINCT s.tier)
  INTO v_tier_breakdown, v_tier_count
  FROM cluster_articles ca
  JOIN articles a ON a.id = ca.article_id
  JOIN sources s ON s.id = a.source_id
  WHERE ca.cluster_id = p_cluster_id;

  -- Compute coverage score (0-100 composite)
  v_coverage_score := LEAST(100.0,
    (LEAST(1.0, COALESCE(v_source_count, 1)::real / 10.0) * 35.0) +
    (COALESCE(v_tier_count, 1)::real / 3.0 * 20.0) +
    (v_summary.aggregate_confidence * 20.0) +
    (COALESCE(v_summary.avg_factual_rigor, 50)::real / 100.0 * 25.0)
  );

  -- Derive opinion label
  v_opinion_label := CASE
    WHEN v_summary.avg_opinion_fact <= 25 THEN 'Reporting'
    WHEN v_summary.avg_opinion_fact <= 50 THEN 'Analysis'
    WHEN v_summary.avg_opinion_fact <= 75 THEN 'Opinion'
    ELSE 'Editorial'
  END;

  -- Compute divergence score (0-100)
  v_divergence := LEAST(100.0,
    (LEAST(v_summary.lean_range::real / 60.0, 1.0) * 40.0) +
    (LEAST(v_summary.lean_spread / 20.0, 1.0) * 30.0) +
    (LEAST(v_summary.framing_spread / 25.0, 1.0) * 30.0)
  );

  -- Build bias diversity JSON (includes all existing fields + new 3-lens fields)
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
    'analyzed_count', v_summary.analyzed_article_count,
    'coverage_score', ROUND(v_coverage_score::numeric, 1),
    'tier_breakdown', v_tier_breakdown,
    'avg_opinion_label', v_opinion_label
  );

  -- Update the cluster
  UPDATE story_clusters
  SET
    divergence_score = v_divergence,
    bias_diversity = v_bias_diversity
  WHERE id = p_cluster_id;
END;
$$ LANGUAGE plpgsql;
