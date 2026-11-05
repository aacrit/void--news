-- 059_headline_signal.sql — first-class is_headline + headline_confidence
--
-- Replaces the band-aid article-count cap (commit 2ea12aa, 2026-05-24)
-- with a cohesion-gated signal that distinguishes true big stories from
-- false-merges. See docs/DIAGNOSTIC-LAB.md + the plan at
-- /root/.claude/plans/review-recent-commits-*.md for the full design.
--
-- Two new columns:
--   is_headline:           BOOL — passes coverage + authority/spectrum + cohesion gates
--   headline_confidence:   INT  — weighted blend 0..100 (40% coverage + 30% authority/spectrum + 30% cohesion)
--
-- Existing "Public read story_clusters" policy (migration 001) covers
-- both new columns. No new RLS needed.

ALTER TABLE story_clusters
  ADD COLUMN IF NOT EXISTS is_headline BOOLEAN NOT NULL DEFAULT false,
  ADD COLUMN IF NOT EXISTS headline_confidence INT;

-- Partial index — only ~3-10% of clusters will be is_headline=true on any
-- given day, so the partial index stays tiny and serves /world fast.
CREATE INDEX IF NOT EXISTS story_clusters_is_headline_idx
  ON story_clusters (is_headline, rank_world DESC NULLS LAST)
  WHERE is_headline = true;

COMMENT ON COLUMN story_clusters.is_headline IS
  'Computed by ranker after rank_importance(). True when cluster passes: '
  'wire-collapsed source_count >= 5 AND >= 2 tiers represented '
  'AND (institutional_authority >= 60 OR cross_spectrum_bonus fired) '
  'AND cohesion_score >= 50. Drives the HEADLINE badge on the frontend.';

COMMENT ON COLUMN story_clusters.headline_confidence IS
  'Weighted blend 0..100 of headline criteria: 40% coverage (sources + tiers) '
  '+ 30% authority/spectrum + 30% cohesion. is_headline = true iff '
  'headline_confidence >= 65.';

-- One-shot backfill on today's clusters using existing fields as a proxy.
-- Full recompute happens on next pipeline run with the engine code change.
-- Backfill criteria (loose, mirrors the engine logic that will replace it):
--   - source_count >= 5             (wire-collapsed coverage)
--   - >= 2 non-zero tier_breakdown buckets
--   - headline_rank >= 20           (already above the cluster median)
--   - not mega_cluster_capped
UPDATE story_clusters
SET is_headline = true,
    headline_confidence = LEAST(100, GREATEST(0, (headline_rank::int * 2)))
WHERE source_count >= 5
  AND COALESCE(headline_rank, 0) >= 20
  AND COALESCE(mega_cluster_capped, false) = false
  AND jsonb_typeof(COALESCE(bias_diversity->'tier_breakdown', '{}'::jsonb)) = 'object'
  AND (
    SELECT count(*)
    FROM jsonb_each(bias_diversity->'tier_breakdown')
    WHERE (value::text)::int > 0
  ) >= 2;
