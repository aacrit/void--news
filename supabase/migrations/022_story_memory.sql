-- Migration 022: News Memory Engine
-- Adds story_memory and live_updates tables for tracking the top developing
-- story between pipeline runs and polling only its sources for live updates.

-- story_memory: tracks which cluster is the current top story, its sources,
-- and continuity metadata across pipeline runs.
CREATE TABLE IF NOT EXISTS story_memory (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_id UUID NOT NULL REFERENCES story_clusters(id) ON DELETE CASCADE,
    headline TEXT NOT NULL,
    category TEXT,
    source_slugs TEXT[] NOT NULL DEFAULT '{}',
    source_count INTEGER NOT NULL DEFAULT 0,
    is_top_story BOOLEAN NOT NULL DEFAULT false,
    is_active BOOLEAN NOT NULL DEFAULT true,
    last_polled_at TIMESTAMPTZ,
    last_live_update_at TIMESTAMPTZ,
    live_update_count INTEGER NOT NULL DEFAULT 0,
    activated_at TIMESTAMPTZ DEFAULT now(),
    deactivated_at TIMESTAMPTZ,
    pipeline_run_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Only one active top story at a time
CREATE UNIQUE INDEX IF NOT EXISTS idx_story_memory_active_top
    ON story_memory (is_top_story) WHERE is_top_story = true AND is_active = true;

CREATE INDEX IF NOT EXISTS idx_story_memory_cluster ON story_memory(cluster_id);
CREATE INDEX IF NOT EXISTS idx_story_memory_active ON story_memory(is_active) WHERE is_active = true;

-- live_updates: articles discovered by the live poller between pipeline runs.
-- Each row is a new article from a tracked source about the top story.
CREATE TABLE IF NOT EXISTS live_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_memory_id UUID NOT NULL REFERENCES story_memory(id) ON DELETE CASCADE,
    article_url TEXT NOT NULL,
    title TEXT NOT NULL,
    summary TEXT,
    source_slug TEXT NOT NULL,
    source_name TEXT NOT NULL,
    published_at TIMESTAMPTZ,
    update_summary TEXT,
    summarized_at TIMESTAMPTZ,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    merged_into_cluster_id UUID REFERENCES story_clusters(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Prevent duplicate URLs within the same story
CREATE UNIQUE INDEX IF NOT EXISTS idx_live_updates_url_story
    ON live_updates (story_memory_id, article_url);

CREATE INDEX IF NOT EXISTS idx_live_updates_memory ON live_updates(story_memory_id);
CREATE INDEX IF NOT EXISTS idx_live_updates_discovered ON live_updates(discovered_at DESC);

-- RLS: public read for frontend, service-role write for pipeline
ALTER TABLE story_memory ENABLE ROW LEVEL SECURITY;
ALTER TABLE live_updates ENABLE ROW LEVEL SECURITY;

CREATE POLICY "story_memory_public_read" ON story_memory
    FOR SELECT USING (true);

CREATE POLICY "story_memory_service_write" ON story_memory
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "live_updates_public_read" ON live_updates
    FOR SELECT USING (true);

CREATE POLICY "live_updates_service_write" ON live_updates
    FOR ALL USING (auth.role() = 'service_role');

-- Auto-update updated_at on story_memory
CREATE TRIGGER update_story_memory_updated_at
    BEFORE UPDATE ON story_memory
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
