-- Migration 045: void --history companion audio
-- Adds audio_url and audio_duration_seconds to history_events.
-- Generated files stored in Supabase Storage: audio-briefs/history/{slug}.mp3

ALTER TABLE history_events
  ADD COLUMN IF NOT EXISTS audio_url TEXT,
  ADD COLUMN IF NOT EXISTS audio_duration_seconds NUMERIC;

COMMENT ON COLUMN history_events.audio_url IS
  'void --onair companion audio MP3 URL in Supabase Storage (audio-briefs/history/{slug}.mp3). NULL = no audio generated yet.';

COMMENT ON COLUMN history_events.audio_duration_seconds IS
  'Duration of the companion audio in seconds. Set at generation time.';
