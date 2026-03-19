-- Track how each source's political lean varies by topic
-- This enables Axis 6: Per-Topic Per-Outlet Tracking
CREATE TABLE IF NOT EXISTS source_topic_lean (
  id BIGSERIAL PRIMARY KEY,
  source_id BIGINT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  category TEXT NOT NULL,
  avg_lean NUMERIC(5,2) NOT NULL DEFAULT 50.0,
  avg_sensationalism NUMERIC(5,2) NOT NULL DEFAULT 50.0,
  avg_opinion NUMERIC(5,2) NOT NULL DEFAULT 50.0,
  article_count INT NOT NULL DEFAULT 0,
  last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE(source_id, category)
);

-- Index for quick lookups
CREATE INDEX idx_source_topic_lean_source ON source_topic_lean(source_id);
CREATE INDEX idx_source_topic_lean_category ON source_topic_lean(category);

-- RLS
ALTER TABLE source_topic_lean ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access" ON source_topic_lean FOR SELECT USING (true);
