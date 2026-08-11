-- Migration 076: Real aggregate_confidence + rev-49 lean histogram from the RPC
-- (Branch G, 2026-08-10)
--
-- Two root causes fixed here (docs/PHASE2-CHANGES-2026-08-10.md callouts 3 & 4):
--
--   G1. aggregate_confidence was LEAST(1.0, COUNT/5.0) in BOTH migration 002's
--       cluster_bias_summary view and pipeline/main.py. That is a saturating
--       article-count proxy: it pins to 1.0 at 5+ articles and ignores the
--       per-article bias_scores.confidence that already exists, so it never
--       varied across top stories and deadened the frontend display-position
--       confidence damping (biasColors.ts leanToDisplayPos) and the isUnscored
--       gate. Recomputed here from the rigor-weighted MEAN of the per-article
--       confidence, lifted a little by coverage breadth and damped a little by
--       cross-source lean disagreement. It now genuinely varies: a 3-source
--       low-confidence cluster scores clearly below a 30-source high-confidence
--       one, and never pins to 1.0 on count alone. Still clamped to [0, 1].
--
--   G2. The rev-49 wing/polarization fields (7-bucket lean histogram, L/C/R
--       segment counts, polarization index) were emitted ONLY by main.py's
--       Python fallback, never by this primary SQL RPC. On live data the RPC
--       succeeds, so those fields were absent from bias_diversity, leaving the
--       "Contested" marker (LeanCoverageBar) and the rev-49 UI dormant. The RPC
--       now emits them into bias_diversity in the exact shape the frontend reads
--       (feedMapping.ts: lean_left_count / lean_center_count / lean_right_count /
--       polarization / lean_buckets), matching main.py's fallback byte-for-byte.
--
-- Idempotent / re-runnable: DROP VIEW IF EXISTS + CREATE, CREATE OR REPLACE
-- FUNCTION. Supersedes the aggregate_confidence expression in migration 002 and
-- the refresh_cluster_enrichment body in migration 004 (both left as historical
-- record). The function keeps the same signature refresh_cluster_enrichment(UUID)
-- so pipeline/main.py's caller is unchanged. The formulas mirror
-- pipeline/utils/bias_aggregation.py exactly so the RPC and the Python fallback
-- always agree.

-- ============================================================================
-- 1. cluster_bias_summary view: new aggregate_confidence + histogram counts.
--    Only additive columns are appended; the pre-existing columns keep their
--    name/type/order. aggregate_confidence keeps its name and REAL type but its
--    expression is replaced.
-- ============================================================================

DROP VIEW IF EXISTS cluster_bias_summary;

CREATE VIEW cluster_bias_summary AS
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

  -- Branch G1: REAL aggregate_confidence in [0, 1].
  --   conf_mean = rigor-weighted mean of per-article confidence
  --   breadth   = LEAST(1, count / 12)                  (secondary lift)
  --   raw       = 0.7 * conf_mean + 0.3 * breadth
  --   damp      = 1 - LEAST(0.20, lean_spread / 100)    (disagreement damp)
  --   confidence = clamp(raw * damp, 0, 1)
  -- Mirrors bias_aggregation.compute_aggregate_confidence exactly.
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
    * (1.0 - LEAST(0.20, GREATEST(0.0, COALESCE(STDDEV(bs.political_lean), 0))::numeric / 100.0))
  ))::real AS aggregate_confidence,

  COUNT(bs.id)::int AS analyzed_article_count,

  -- Branch G2: 3-segment L/C/R counts (boundaries match biasColors.ts
  -- leanToBucket: left = lean<=45, center = 46..55, right = lean>55).
  SUM(CASE WHEN bs.political_lean <= 45 THEN 1 ELSE 0 END)::int AS lean_left_count,
  SUM(CASE WHEN bs.political_lean > 45 AND bs.political_lean <= 55 THEN 1 ELSE 0 END)::int AS lean_center_count,
  SUM(CASE WHEN bs.political_lean > 55 THEN 1 ELSE 0 END)::int AS lean_right_count,

  -- Branch G2: 7-bucket histogram.
  SUM(CASE WHEN bs.political_lean <= 20 THEN 1 ELSE 0 END)::int AS far_left_count,
  SUM(CASE WHEN bs.political_lean > 20 AND bs.political_lean <= 35 THEN 1 ELSE 0 END)::int AS left_count,
  SUM(CASE WHEN bs.political_lean > 35 AND bs.political_lean <= 45 THEN 1 ELSE 0 END)::int AS center_left_count,
  SUM(CASE WHEN bs.political_lean > 45 AND bs.political_lean <= 55 THEN 1 ELSE 0 END)::int AS center_count,
  SUM(CASE WHEN bs.political_lean > 55 AND bs.political_lean <= 65 THEN 1 ELSE 0 END)::int AS center_right_count,
  SUM(CASE WHEN bs.political_lean > 65 AND bs.political_lean <= 80 THEN 1 ELSE 0 END)::int AS right_count,
  SUM(CASE WHEN bs.political_lean > 80 THEN 1 ELSE 0 END)::int AS far_right_count

FROM cluster_articles ca
JOIN bias_scores bs ON bs.article_id = ca.article_id
GROUP BY ca.cluster_id;

-- ============================================================================
-- 2. refresh_cluster_enrichment(): same signature/return, now ALSO emits the
--    rev-49 histogram + polarization into bias_diversity. Body reproduces
--    migration 004 (coverage_score, tier_breakdown, opinion_label, divergence)
--    and appends the new fields.
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

  -- Compute coverage score (0-100 composite). Uses the new aggregate_confidence.
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

  -- Branch G2: polarization index. 0 = one-sided / all-center, 100 = a perfect
  -- L/R split. Mirrors bias_aggregation.compute_lean_histogram:
  --   round(100 * 2 * min(L, R) / n).
  v_polarization := CASE
    WHEN v_summary.analyzed_article_count > 0
    THEN ROUND(
      100.0 * 2.0
      * LEAST(v_summary.lean_left_count, v_summary.lean_right_count)::numeric
      / v_summary.analyzed_article_count::numeric
    )::int
    ELSE 0
  END;

  -- Build bias diversity JSON (existing fields + rev-49 wing/polarization).
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
    -- rev-49 wing / polarization (frontend: LeanCoverageBar + Contested marker)
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
    'polarization', v_polarization
  );

  -- Update the cluster
  UPDATE story_clusters
  SET
    divergence_score = v_divergence,
    bias_diversity = v_bias_diversity
  WHERE id = p_cluster_id;
END;
$$ LANGUAGE plpgsql;

-- Migration 029 revoked EXECUTE on this function from anon/authenticated; the
-- CREATE OR REPLACE above preserves the function's ACL, so no re-grant needed.
