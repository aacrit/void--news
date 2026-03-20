-- Migration 010: Multi-edition support
-- Expands the section CHECK constraint on articles and story_clusters
-- to support India, Nepal, and Germany editions alongside existing world/us.

-- Step 1: Drop existing CHECK constraints on section columns
-- (PostgreSQL auto-names CHECK constraints as {table}_{column}_check)
ALTER TABLE articles DROP CONSTRAINT IF EXISTS articles_section_check;
ALTER TABLE story_clusters DROP CONSTRAINT IF EXISTS story_clusters_section_check;

-- Step 2: Add expanded CHECK constraints
ALTER TABLE articles ADD CONSTRAINT articles_section_check
  CHECK (section IN ('world', 'us', 'india', 'nepal', 'germany', 'other'));

ALTER TABLE story_clusters ADD CONSTRAINT story_clusters_section_check
  CHECK (section IN ('world', 'us', 'india', 'nepal', 'germany'));

-- Step 3: Add index for new edition sections (partial indexes for common queries)
CREATE INDEX IF NOT EXISTS idx_clusters_section_india
  ON story_clusters(headline_rank DESC) WHERE section = 'india';
CREATE INDEX IF NOT EXISTS idx_clusters_section_nepal
  ON story_clusters(headline_rank DESC) WHERE section = 'nepal';
CREATE INDEX IF NOT EXISTS idx_clusters_section_germany
  ON story_clusters(headline_rank DESC) WHERE section = 'germany';
