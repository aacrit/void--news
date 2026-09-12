-- 071_summary_tier_rule_based.sql
--
-- Top-50 summary floor (2026-08-04). New pipeline step 8d.1
-- (ensure_top50_summary_floor) guarantees no displayed top-50 card renders a
-- raw scraped excerpt: it re-summarizes any still-null card with the LLM, and
-- failing that rebuilds a clean, sentence-bounded summary from member articles
-- via the rule-based path. That deterministic fallback stamps tier 'rule_based'.
--
-- Widen the CHECK so the honest 'rule_based' tier can be stored instead of
-- leaving the row NULL. The upgrade-aware step-8d cache treats 'rule_based' as
-- a MISS (re-attempts the LLM next run), same as NULL, so a temporarily
-- degraded card recovers automatically; the difference is an honest label
-- rather than an ambiguous NULL.
--
-- 063 widened the CHECK to ('sonnet','flash','flash-lite'); this adds
-- 'rule_based'.

ALTER TABLE story_clusters
  DROP CONSTRAINT IF EXISTS story_clusters_summary_tier_check;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'story_clusters_summary_tier_check'
      AND conrelid = 'story_clusters'::regclass
  ) THEN
    ALTER TABLE story_clusters
      ADD CONSTRAINT story_clusters_summary_tier_check
      CHECK (summary_tier IN ('sonnet', 'flash', 'flash-lite', 'rule_based'));
  END IF;
END $$;

COMMENT ON COLUMN story_clusters.summary_tier IS
  'Which tier produced the cached summary: sonnet (Claude, legacy/retired), '
  'flash (gemini-2.5-flash - premium top-10 stories), flash-lite '
  '(gemini-2.5-flash-lite - the rest of the top-50), or rule_based (the '
  'deterministic top-50 summary floor, step 8d.1, when the LLM was unreachable). '
  'The cache upgrades flash-lite -> flash for top stories and re-attempts the '
  'LLM on any rule_based/NULL row next run.';
