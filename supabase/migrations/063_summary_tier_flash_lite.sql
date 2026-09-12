-- 063_summary_tier_flash_lite.sql
--
-- Two-model Gemini hierarchy (2026-06-22). Story summaries now run on a
-- quality hierarchy instead of a single model:
--   top-5 highest-impact stories  → gemini-2.5-flash      (tier 'flash')
--   the rest of the top-50         → gemini-2.5-flash-lite (tier 'flash-lite')
--   Groq gpt-oss-20b fallback      → tier 'flash-lite' (non-premium)
--
-- summary_tier must distinguish the premium 'flash' tier from 'flash-lite'
-- so the step-8d cache can UPGRADE a story to flash when it rises into the
-- top 5 (a flash-lite cache row is no longer a hit for a flash target),
-- while a flash-lite target still treats any prior summary as a cache hit.
--
-- 062 widened the CHECK to ('sonnet','flash'); this adds 'flash-lite'.

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
      CHECK (summary_tier IN ('sonnet', 'flash', 'flash-lite'));
  END IF;
END $$;

COMMENT ON COLUMN story_clusters.summary_tier IS
  'Which LLM tier produced the cached summary: sonnet (Claude, legacy/retired), '
  'flash (gemini-2.5-flash — premium top-5 stories), or flash-lite '
  '(gemini-2.5-flash-lite or Groq fallback — the rest of the top-50). The cache '
  'upgrades flash-lite -> flash when a story enters the top 5.';
