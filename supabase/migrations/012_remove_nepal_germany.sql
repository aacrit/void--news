-- Migration 012: Remove Nepal and Germany editions
-- These editions have been deprecated due to thin English-language source coverage.
-- Re-routes any existing nepal/germany data to the "world" edition.

-- Step 1: Re-route story_clusters with section = nepal/germany to world
UPDATE story_clusters SET section = 'world' WHERE section IN ('nepal', 'germany');

-- Step 2: Remove nepal/germany from the sections array on story_clusters
UPDATE story_clusters
  SET sections = array_remove(sections, 'nepal')
  WHERE 'nepal' = ANY(sections);

UPDATE story_clusters
  SET sections = array_remove(sections, 'germany')
  WHERE 'germany' = ANY(sections);

-- Step 3: Re-route articles with section = nepal/germany to world
UPDATE articles SET section = 'world' WHERE section IN ('nepal', 'germany');

-- Step 4: Drop partial indexes for the removed editions
DROP INDEX IF EXISTS idx_clusters_section_nepal;
DROP INDEX IF EXISTS idx_clusters_section_germany;

-- Step 5: Tighten CHECK constraints to exclude nepal/germany
-- (Drop and re-create since ALTER CONSTRAINT is not supported for CHECK)
ALTER TABLE articles DROP CONSTRAINT IF EXISTS articles_section_check;
ALTER TABLE story_clusters DROP CONSTRAINT IF EXISTS story_clusters_section_check;

ALTER TABLE articles ADD CONSTRAINT articles_section_check
  CHECK (section IN ('world', 'us', 'india', 'other'));

ALTER TABLE story_clusters ADD CONSTRAINT story_clusters_section_check
  CHECK (section IN ('world', 'us', 'india'));
