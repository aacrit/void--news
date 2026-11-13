-- Weekly digest table for void --weekly
-- Stores permanent long-form magazine-style content generated every Sunday

CREATE TABLE IF NOT EXISTS weekly_digests (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,

  -- Issue metadata
  edition TEXT NOT NULL,
  week_start DATE NOT NULL,
  week_end DATE NOT NULL,
  issue_number INTEGER,

  -- Cover story (1,000-1,500 words, top story of the week)
  cover_headline TEXT NOT NULL,
  cover_text TEXT NOT NULL,
  cover_cluster_ids UUID[],
  cover_numbers JSONB,  -- "This Week in Numbers" sidebar

  -- Week recap (10-15 stories)
  recap_stories JSONB NOT NULL DEFAULT '[]'::jsonb,

  -- Three Lenses opinion essays (left/center/right on same story)
  opinion_left TEXT,
  opinion_center TEXT,
  opinion_right TEXT,
  opinion_headlines JSONB,
  opinion_topic TEXT,  -- The story all three essays address

  -- Bias report (rule-based, aggregated from week's data)
  bias_report_text TEXT,
  bias_report_data JSONB,

  -- Audio
  audio_script TEXT,
  audio_url TEXT,
  audio_duration_seconds REAL,
  audio_file_size INTEGER,

  -- Aggregate stats
  total_articles INTEGER,
  total_clusters INTEGER,
  total_sources_active INTEGER,

  -- Generation metadata
  generator TEXT,
  gemini_calls_used INTEGER,
  generation_duration_seconds REAL,

  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),

  -- One digest per edition per week
  CONSTRAINT weekly_digests_edition_week UNIQUE (edition, week_start)
);

-- Fast lookup for latest digest per edition
CREATE INDEX IF NOT EXISTS idx_weekly_digests_edition_created
  ON weekly_digests (edition, created_at DESC);

-- RLS
ALTER TABLE weekly_digests ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Public read access for weekly_digests"
  ON weekly_digests FOR SELECT USING (true);
CREATE POLICY "Service role write for weekly_digests"
  ON weekly_digests FOR ALL USING (true) WITH CHECK (true);
