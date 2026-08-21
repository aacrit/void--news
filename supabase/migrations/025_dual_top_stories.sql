-- Migration 025: Support dual top stories in memory engine
-- Allows tracking top 2 stories simultaneously instead of just 1.
-- Each story gets its own rank (1 = primary, 2 = secondary).

-- Drop the single-active-top-story constraint
DROP INDEX IF EXISTS idx_story_memory_active_top;

-- Add rank column (1 = primary lead, 2 = secondary lead)
ALTER TABLE story_memory ADD COLUMN IF NOT EXISTS rank INTEGER DEFAULT 1;

-- One active story per rank position
CREATE UNIQUE INDEX IF NOT EXISTS idx_story_memory_active_rank
    ON story_memory (rank) WHERE is_active = true;
