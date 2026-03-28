-- Migration 023: Denormalize top-story fields onto story_clusters
-- Avoids JOINs on every frontend query — updated by memory_orchestrator.

ALTER TABLE story_clusters
    ADD COLUMN IF NOT EXISTS is_top_story BOOLEAN DEFAULT false,
    ADD COLUMN IF NOT EXISTS live_update_count INTEGER DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_live_update_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS story_memory_id UUID;

CREATE INDEX IF NOT EXISTS idx_clusters_top_story
    ON story_clusters(is_top_story) WHERE is_top_story = true;
