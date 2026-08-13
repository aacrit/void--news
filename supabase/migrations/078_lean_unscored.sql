-- 078: per-article "we have no lean measurement here" flag.
--
-- The political-lean analyzer already decides, per article, whether it has any
-- signal at all: an outlet with no placement on the left/right axis, writing
-- calm copy with no partisan vocabulary, yields a 50 that is the ABSENCE of a
-- measurement rather than a finding of centrism. That judgment was computed on
-- every article and then discarded -- it lived only in the rationale blob and
-- was never persisted -- so cluster aggregation averaged those 50s into
-- avg_political_lean as though they were measured centrism.
--
-- Measured 2026-08-13 on live traffic: 52% of article volume comes from
-- outlets not placed on this axis, and 98% of a real sample from them scored
-- text_score exactly 50. That unmeasured majority pinned every cluster mean to
-- ~50 (86.2% of feed articles landed in the 46-55 bucket) and made every card
-- render "Flat".
--
-- Storing the flag lets the aggregate be computed over articles we actually
-- have signal for, while those articles still count toward source_count and
-- coverage -- they are real coverage, just not a lean measurement.
ALTER TABLE bias_scores
    ADD COLUMN IF NOT EXISTS lean_unscored BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN bias_scores.lean_unscored IS
    'TRUE when political_lean carries no measurement: the outlet is not placed '
    'on the left/right axis AND the article text showed no partisan signal. '
    'Excluded from cluster avg_political_lean / lean_spread / lean histogram; '
    'still counted in source_count and coverage.';

-- Partial index: the aggregation path filters to the measured subset.
CREATE INDEX IF NOT EXISTS idx_bias_scores_measured_lean
    ON bias_scores (article_id)
    WHERE lean_unscored = FALSE;

-- ============================================================================
-- Redefine cluster_bias_summary so every LEAN aggregate is computed over the
-- MEASURED subset only.
--
-- This view (not the Python fallback in main.py) is the primary aggregation
-- path via refresh_cluster_enrichment(), so the flag has to be applied here or
-- the fix never reaches production.
--
-- Only lean columns are filtered. sensationalism / opinion_fact / factual_rigor
-- / framing are read from the article's own words and are valid regardless of
-- whether the outlet is placed on the left/right axis, so they keep averaging
-- over all coverage. analyzed_article_count likewise stays the FULL count --
-- these articles are real coverage, they just carry no lean measurement.
--
-- Every filtered aggregate falls back to the unfiltered value when a cluster
-- has no measured articles at all, so a story covered entirely by unrated
-- outlets still reports a lean rather than NULL; lean_measured_count tells the
-- UI how far to trust it.
-- ============================================================================

DROP VIEW IF EXISTS cluster_bias_summary;

CREATE VIEW cluster_bias_summary AS
SELECT
  ca.cluster_id,

  -- Rigor-weighted mean lean over measured articles.
  COALESCE(
    CASE
      WHEN SUM(bs.factual_rigor) FILTER (WHERE NOT bs.lean_unscored) > 0
      THEN ROUND(
        SUM(bs.political_lean * bs.factual_rigor) FILTER (WHERE NOT bs.lean_unscored)::numeric
        / SUM(bs.factual_rigor) FILTER (WHERE NOT bs.lean_unscored)::numeric)
      ELSE ROUND(AVG(bs.political_lean) FILTER (WHERE NOT bs.lean_unscored))
    END,
    CASE
      WHEN SUM(bs.factual_rigor) > 0
      THEN ROUND(SUM(bs.political_lean * bs.factual_rigor)::numeric / SUM(bs.factual_rigor)::numeric)
      ELSE ROUND(AVG(bs.political_lean))
    END
  ) AS avg_political_lean,

  ROUND(AVG(bs.sensationalism))::int AS avg_sensationalism,
  ROUND(AVG(bs.opinion_fact))::int AS avg_opinion_fact,
  ROUND(AVG(bs.factual_rigor))::int AS avg_factual_rigor,
  ROUND(AVG(bs.framing))::int AS avg_framing,

  ROUND(COALESCE(
    STDDEV(bs.political_lean) FILTER (WHERE NOT bs.lean_unscored),
    STDDEV(bs.political_lean), 0)::numeric, 1)::real AS lean_spread,
  ROUND(COALESCE(STDDEV(bs.framing), 0)::numeric, 1)::real AS framing_spread,
  COALESCE(
    (MAX(bs.political_lean) FILTER (WHERE NOT bs.lean_unscored)
     - MIN(bs.political_lean) FILTER (WHERE NOT bs.lean_unscored))::int,
    (MAX(bs.political_lean) - MIN(bs.political_lean))::int
  ) AS lean_range,
  ROUND(COALESCE(STDDEV(bs.sensationalism), 0)::numeric, 1)::real AS sensationalism_spread,
  ROUND(COALESCE(STDDEV(bs.opinion_fact), 0)::numeric, 1)::real AS opinion_spread,

  -- Branch G1 confidence. The disagreement damp now reads the measured spread
  -- so a cluster is not credited with false agreement by unmeasured articles.
  GREATEST(0.0, LEAST(1.0,
    (
      0.7 * (
        CASE
          WHEN SUM(bs.factual_rigor) > 0
          THEN SUM(COALESCE(bs.confidence, 0.5) * bs.factual_rigor)::numeric
               / SUM(bs.factual_rigor)::numeric
          ELSE AVG(COALESCE(bs.confidence, 0.5))::numeric
        END
      )
      + 0.3 * LEAST(1.0, COUNT(bs.id)::numeric / 12.0)
    )
    * (1.0 - LEAST(0.20, GREATEST(0.0, COALESCE(
        STDDEV(bs.political_lean) FILTER (WHERE NOT bs.lean_unscored),
        STDDEV(bs.political_lean), 0))::numeric / 100.0))
  ))::real AS aggregate_confidence,

  COUNT(bs.id)::int AS analyzed_article_count,

  -- How much of the coverage the lean is actually measured from.
  COUNT(bs.id) FILTER (WHERE NOT bs.lean_unscored)::int AS lean_measured_count,
  COUNT(bs.id)::int AS lean_total_count,

  -- L/C/R and the 7-bucket histogram, measured articles only. An unmeasured
  -- article must not be counted as centrist coverage -- that miscount is what
  -- made the coverage bar read ~86% center.
  COUNT(*) FILTER (WHERE NOT bs.lean_unscored AND bs.political_lean <= 45)::int AS lean_left_count,
  COUNT(*) FILTER (WHERE NOT bs.lean_unscored AND bs.political_lean > 45 AND bs.political_lean <= 55)::int AS lean_center_count,
  COUNT(*) FILTER (WHERE NOT bs.lean_unscored AND bs.political_lean > 55)::int AS lean_right_count,

  COUNT(*) FILTER (WHERE NOT bs.lean_unscored AND bs.political_lean <= 20)::int AS far_left_count,
  COUNT(*) FILTER (WHERE NOT bs.lean_unscored AND bs.political_lean > 20 AND bs.political_lean <= 35)::int AS left_count,
  COUNT(*) FILTER (WHERE NOT bs.lean_unscored AND bs.political_lean > 35 AND bs.political_lean <= 45)::int AS center_left_count,
  COUNT(*) FILTER (WHERE NOT bs.lean_unscored AND bs.political_lean > 45 AND bs.political_lean <= 55)::int AS center_count,
  COUNT(*) FILTER (WHERE NOT bs.lean_unscored AND bs.political_lean > 55 AND bs.political_lean <= 65)::int AS center_right_count,
  COUNT(*) FILTER (WHERE NOT bs.lean_unscored AND bs.political_lean > 65 AND bs.political_lean <= 80)::int AS right_count,
  COUNT(*) FILTER (WHERE NOT bs.lean_unscored AND bs.political_lean > 80)::int AS far_right_count

FROM cluster_articles ca
JOIN bias_scores bs ON bs.article_id = ca.article_id
GROUP BY ca.cluster_id;

-- ============================================================================
-- refresh_cluster_enrichment(): same signature and behaviour, with two changes
-- forced by the view above.
--
--   1. polarization now divides by lean_measured_count, not
--      analyzed_article_count. lean_left_count / lean_right_count are now
--      MEASURED counts, so dividing them by the full coverage count would
--      systematically understate contestedness -- a story split 6 left / 6
--      right among 12 measured outlets inside 40 total would have read 30
--      instead of 100.
--   2. lean_measured_count / lean_total_count are emitted so the UI can say
--      how much of the coverage the lean is measured from.
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
  v_polarization INTEGER;
BEGIN
  SELECT * INTO v_summary
  FROM cluster_bias_summary
  WHERE cluster_id = p_cluster_id;

  IF NOT FOUND THEN
    RETURN;
  END IF;

  SELECT source_count INTO v_source_count
  FROM story_clusters
  WHERE id = p_cluster_id;

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

  v_coverage_score := LEAST(100.0,
    (LEAST(1.0, COALESCE(v_source_count, 1)::real / 10.0) * 35.0) +
    (COALESCE(v_tier_count, 1)::real / 3.0 * 20.0) +
    (v_summary.aggregate_confidence * 20.0) +
    (COALESCE(v_summary.avg_factual_rigor, 50)::real / 100.0 * 25.0)
  );

  v_opinion_label := CASE
    WHEN v_summary.avg_opinion_fact <= 25 THEN 'Reporting'
    WHEN v_summary.avg_opinion_fact <= 50 THEN 'Analysis'
    WHEN v_summary.avg_opinion_fact <= 75 THEN 'Opinion'
    ELSE 'Editorial'
  END;

  v_divergence := LEAST(100.0,
    (LEAST(v_summary.lean_range::real / 60.0, 1.0) * 40.0) +
    (LEAST(v_summary.lean_spread / 20.0, 1.0) * 30.0) +
    (LEAST(v_summary.framing_spread / 25.0, 1.0) * 30.0)
  );

  -- Denominator is the MEASURED count: L and R above are measured-only.
  v_polarization := CASE
    WHEN COALESCE(v_summary.lean_measured_count, 0) > 0
    THEN ROUND(
      100.0 * 2.0
      * LEAST(v_summary.lean_left_count, v_summary.lean_right_count)::numeric
      / v_summary.lean_measured_count::numeric
    )::int
    ELSE 0
  END;

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
    'avg_opinion_label', v_opinion_label,
    'lean_buckets', jsonb_build_object(
      'far_left', v_summary.far_left_count,
      'left', v_summary.left_count,
      'center_left', v_summary.center_left_count,
      'center', v_summary.center_count,
      'center_right', v_summary.center_right_count,
      'right', v_summary.right_count,
      'far_right', v_summary.far_right_count
    ),
    'lean_left_count', v_summary.lean_left_count,
    'lean_center_count', v_summary.lean_center_count,
    'lean_right_count', v_summary.lean_right_count,
    'polarization', v_polarization,
    'lean_measured_count', v_summary.lean_measured_count,
    'lean_total_count', v_summary.lean_total_count
  );

  UPDATE story_clusters
  SET
    divergence_score = v_divergence,
    bias_diversity = v_bias_diversity
  WHERE id = p_cluster_id;
END;
$$ LANGUAGE plpgsql;
