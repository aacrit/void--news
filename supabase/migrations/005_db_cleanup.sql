-- Add updated_at triggers for articles and story_clusters

-- Generic trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add updated_at column to articles if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'articles' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE articles ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Add updated_at column to story_clusters if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'story_clusters' AND column_name = 'updated_at'
    ) THEN
        ALTER TABLE story_clusters ADD COLUMN updated_at TIMESTAMPTZ DEFAULT NOW();
    END IF;
END $$;

-- Create triggers
DROP TRIGGER IF EXISTS set_articles_updated_at ON articles;
CREATE TRIGGER set_articles_updated_at
    BEFORE UPDATE ON articles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS set_story_clusters_updated_at ON story_clusters;
CREATE TRIGGER set_story_clusters_updated_at
    BEFORE UPDATE ON story_clusters
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Drop redundant indexes (superseded by composite indexes)
DROP INDEX IF EXISTS idx_clusters_section;       -- superseded by idx_clusters_section_headline_rank
DROP INDEX IF EXISTS idx_clusters_importance;     -- superseded by headline_rank ordering
