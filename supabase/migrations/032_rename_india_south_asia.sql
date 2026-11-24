-- Rename india edition to south-asia (expanded to cover PK, BD, LK, NP, AF, MV, BT)
-- Also add europe edition support

-- 1. Add rank_europe column if not exists (from migration 031)
ALTER TABLE story_clusters
    ADD COLUMN IF NOT EXISTS rank_europe REAL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_clusters_rank_europe
    ON story_clusters (rank_europe DESC);

-- 2. Rename rank_india → rank_south_asia
ALTER TABLE story_clusters
    RENAME COLUMN rank_india TO rank_south_asia;

-- 3. Drop the existing check constraint on daily_briefs.edition
ALTER TABLE daily_briefs
    DROP CONSTRAINT IF EXISTS daily_briefs_edition_check;

-- 4. Add updated check constraint with new edition values
ALTER TABLE daily_briefs
    ADD CONSTRAINT daily_briefs_edition_check
    CHECK (edition IN ('world', 'us', 'europe', 'south-asia', 'uk', 'india', 'canada'));

-- 5. Update existing section references
UPDATE story_clusters
    SET sections = array_replace(sections, 'india', 'south-asia')
    WHERE 'india' = ANY(sections);

-- 6. Update daily_briefs edition
UPDATE daily_briefs
    SET edition = 'south-asia'
    WHERE edition = 'india';
