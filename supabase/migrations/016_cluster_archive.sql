-- Migration 016: Cluster archive table for retention + historical summaries
-- Date: 2026-03-21
-- Purpose: Preserve Gemini-generated summaries, consensus/divergence points,
-- and bias diversity data after clusters are pruned by 3-day retention.
-- Enables weekly/monthly trend reports without keeping stale clusters in the
-- active story_clusters table.

CREATE TABLE IF NOT EXISTS cluster_archive (
  id UUID PRIMARY KEY,
  title TEXT,
  summary TEXT,
  section TEXT DEFAULT 'world',
  sections TEXT[],
  category TEXT,
  source_count INTEGER DEFAULT 1,
  first_published TIMESTAMPTZ,
  headline_rank REAL DEFAULT 0,
  divergence_score REAL DEFAULT 0,
  bias_diversity JSONB,
  consensus_points JSONB,
  divergence_points JSONB,
  archived_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for time-range queries (weekly/monthly summaries)
CREATE INDEX IF NOT EXISTS idx_cluster_archive_published
  ON cluster_archive (first_published DESC);

-- Index for section-based historical queries
CREATE INDEX IF NOT EXISTS idx_cluster_archive_section
  ON cluster_archive USING GIN (sections);

-- RLS: public read access (same as story_clusters)
ALTER TABLE cluster_archive ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read access for cluster_archive"
  ON cluster_archive FOR SELECT
  USING (true);
