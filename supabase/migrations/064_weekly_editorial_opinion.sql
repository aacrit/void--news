-- Weekly editorial opinion for void --weekly
-- Adds a single ARGUED editorial column to the weekly digest, mirroring the
-- daily brief's void --opinion. This is DISTINCT from the existing three-lens
-- "Perspectives" feature (opinion_left/center/right from migration 034): the
-- weekly editorial is one synthesized week-in-review argument, rendered as text
-- on /weekly and appended to the weekly MP3 as a single-voice monologue.
--
-- All columns nullable, no backfill — historical issues simply have no editorial.

ALTER TABLE weekly_digests
  ADD COLUMN IF NOT EXISTS opinion_text TEXT,
  ADD COLUMN IF NOT EXISTS opinion_headline TEXT,
  ADD COLUMN IF NOT EXISTS opinion_lean TEXT,
  ADD COLUMN IF NOT EXISTS opinion_audio_script TEXT,
  ADD COLUMN IF NOT EXISTS opinion_start_seconds REAL,
  ADD COLUMN IF NOT EXISTS audio_voice TEXT,
  ADD COLUMN IF NOT EXISTS audio_voice_label TEXT;

-- Constrain the editorial lean to the three rotating lenses (left/center/right),
-- matching the daily opinion rotation. Guarded so re-running the migration is safe.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname = 'weekly_digests_opinion_lean_check'
  ) THEN
    ALTER TABLE weekly_digests
      ADD CONSTRAINT weekly_digests_opinion_lean_check
      CHECK (opinion_lean IS NULL OR opinion_lean IN ('left', 'center', 'right'));
  END IF;
END $$;

COMMENT ON COLUMN weekly_digests.opinion_text IS 'Weekly editorial body (450-650 words, void --opinion week-in-review). Distinct from opinion_left/center/right three-lens perspectives.';
COMMENT ON COLUMN weekly_digests.opinion_audio_script IS 'Single-voice editorial monologue appended to the weekly MP3 after the news broadcast.';
COMMENT ON COLUMN weekly_digests.opinion_start_seconds IS 'Offset (seconds) into audio_url where the opinion monologue begins; drives the player News/Opinion seek tab.';
