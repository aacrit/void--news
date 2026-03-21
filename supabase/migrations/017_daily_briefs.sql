-- Migration 017: Daily Brief — TL;DR text + audio broadcast
-- Date: 2026-03-21
-- Purpose: Store per-edition editorial briefs (3-line TL;DR text + Gemini-generated
-- audio script) alongside audio metadata pointing to Supabase Storage.

CREATE TABLE IF NOT EXISTS daily_briefs (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  edition TEXT NOT NULL CHECK (edition IN ('world', 'us', 'india')),
  pipeline_run_id UUID REFERENCES pipeline_runs(id) ON DELETE SET NULL,

  -- TL;DR text (3-line editorial summary, displayed on homepage)
  tldr_text TEXT NOT NULL,

  -- Audio script (full broadcast script, used to generate TTS)
  audio_script TEXT,

  -- Audio metadata
  audio_url TEXT,
  audio_duration_seconds REAL,
  audio_voice TEXT,
  audio_voice_label TEXT,
  audio_file_size INTEGER,

  -- Generation metadata
  top_cluster_ids UUID[],

  -- Timestamps
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Only one brief per edition per pipeline run
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_briefs_edition_run
  ON daily_briefs (edition, pipeline_run_id);

-- Fast lookup: latest brief per edition (frontend query pattern)
CREATE INDEX IF NOT EXISTS idx_daily_briefs_edition_created
  ON daily_briefs (edition, created_at DESC);

-- RLS: public read access (same as all other tables)
ALTER TABLE daily_briefs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Public read access for daily_briefs"
  ON daily_briefs FOR SELECT
  USING (true);

-- Auto-update updated_at trigger (reuse existing function)
CREATE TRIGGER update_daily_briefs_updated_at
  BEFORE UPDATE ON daily_briefs
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();
