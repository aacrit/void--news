-- Fix story_clusters section check constraint to allow europe and south-asia.
-- Migration 033 fixed articles but missed story_clusters.
-- Also clean up legacy section values: uk→europe, india→south-asia, canada→world.
-- And update daily_briefs.edition to allow europe and south-asia.

-- 1. Update story_clusters.section CHECK constraint
ALTER TABLE story_clusters
    DROP CONSTRAINT IF EXISTS story_clusters_section_check;

ALTER TABLE story_clusters
    ADD CONSTRAINT story_clusters_section_check
    CHECK (section IN ('world', 'us', 'europe', 'south-asia'));

-- 2. Update daily_briefs.edition CHECK constraint
ALTER TABLE daily_briefs
    DROP CONSTRAINT IF EXISTS daily_briefs_edition_check;

ALTER TABLE daily_briefs
    ADD CONSTRAINT daily_briefs_edition_check
    CHECK (edition IN ('world', 'us', 'europe', 'south-asia'));

-- 3. Migrate legacy section values in story_clusters
-- uk → europe
UPDATE story_clusters SET section = 'europe' WHERE section = 'uk';
UPDATE story_clusters SET sections = array_replace(sections, 'uk', 'europe');

-- india → south-asia
UPDATE story_clusters SET section = 'south-asia' WHERE section = 'india';
UPDATE story_clusters SET sections = array_replace(sections, 'india', 'south-asia');

-- canada → world (no dedicated Canada edition)
UPDATE story_clusters SET section = 'world' WHERE section = 'canada';
UPDATE story_clusters SET sections = array_replace(sections, 'canada', 'world');

-- 4. Migrate legacy section values in articles
UPDATE articles SET section = 'europe' WHERE section = 'uk';
UPDATE articles SET section = 'south-asia' WHERE section = 'india';
UPDATE articles SET section = 'world' WHERE section = 'canada';

-- 5. Tighten articles constraint (remove legacy values)
ALTER TABLE articles
    DROP CONSTRAINT IF EXISTS articles_section_check;

ALTER TABLE articles
    ADD CONSTRAINT articles_section_check
    CHECK (section IN ('world', 'us', 'europe', 'south-asia'));

-- 6. Create partial indexes for new editions
CREATE INDEX IF NOT EXISTS idx_clusters_section_europe
    ON story_clusters (section) WHERE section = 'europe';

CREATE INDEX IF NOT EXISTS idx_clusters_section_south_asia
    ON story_clusters (section) WHERE section = 'south-asia';

-- 7. Drop legacy indexes
DROP INDEX IF EXISTS idx_clusters_section_uk;
DROP INDEX IF EXISTS idx_clusters_section_canada;
