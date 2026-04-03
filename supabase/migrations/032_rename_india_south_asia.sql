-- Rename india edition to south-asia (expanded to cover Pakistan, Bangladesh, Sri Lanka, Nepal, Afghanistan)
-- Rename rank column to match new edition slug

ALTER TABLE story_clusters
    RENAME COLUMN rank_india TO rank_south_asia;

-- Update any existing section references in the sections array
UPDATE story_clusters
    SET sections = array_replace(sections, 'india', 'south-asia')
    WHERE 'india' = ANY(sections);

-- Update daily_briefs edition references
UPDATE daily_briefs
    SET edition = 'south-asia'
    WHERE edition = 'india';
