-- Migration 011: Multi-section support for cross-listed clusters
-- Adds a `sections` text[] column so clusters can appear in multiple editions.
-- A cluster about the Iran war with articles from US, world, AND India sources
-- will have sections = ARRAY['us', 'world', 'india'], making it visible in all
-- three edition feeds. The existing `section` column remains as the primary
-- (majority-vote) section for backward compatibility and ranking.

-- Step 1: Add sections array column
ALTER TABLE story_clusters
  ADD COLUMN IF NOT EXISTS sections text[] DEFAULT ARRAY['world'];

-- Step 2: Backfill from existing section column
UPDATE story_clusters SET sections = ARRAY[section]
  WHERE sections = ARRAY['world'] AND section != 'world';

-- Step 3: GIN index for array containment queries (sections @> ARRAY['india'])
CREATE INDEX IF NOT EXISTS idx_clusters_sections_gin
  ON story_clusters USING GIN(sections);

-- Step 4: Composite index for section array + headline_rank ordering
-- PostgREST will use the GIN index for filtering, then sort by headline_rank.
-- No composite GIN + btree needed; the GIN filter is selective enough.
