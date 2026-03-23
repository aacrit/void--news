-- Migration 018: Expand editions — add UK and Canada
-- Date: 2026-03-22
-- Purpose: Expand CHECK constraints on articles, story_clusters, and daily_briefs
-- to allow new editions (uk, canada).

-- 1. articles.section — currently restricted to (world, us, india, other)
ALTER TABLE articles DROP CONSTRAINT IF EXISTS articles_section_check;
ALTER TABLE articles ADD CONSTRAINT articles_section_check
  CHECK (section IN ('world', 'us', 'india', 'uk', 'canada', 'other'));

-- 2. story_clusters.section — currently restricted to (world, us, india)
ALTER TABLE story_clusters DROP CONSTRAINT IF EXISTS story_clusters_section_check;
ALTER TABLE story_clusters ADD CONSTRAINT story_clusters_section_check
  CHECK (section IN ('world', 'us', 'india', 'uk', 'canada'));

-- 3. daily_briefs.edition — currently restricted to (world, us, india)
ALTER TABLE daily_briefs DROP CONSTRAINT IF EXISTS daily_briefs_edition_check;
ALTER TABLE daily_briefs ADD CONSTRAINT daily_briefs_edition_check
  CHECK (edition IN ('world', 'us', 'india', 'uk', 'canada'));

-- 4. Create partial indexes for fast per-edition queries on new editions
CREATE INDEX IF NOT EXISTS idx_clusters_section_uk
  ON story_clusters (section) WHERE section = 'uk';

CREATE INDEX IF NOT EXISTS idx_clusters_section_canada
  ON story_clusters (section) WHERE section = 'canada';
