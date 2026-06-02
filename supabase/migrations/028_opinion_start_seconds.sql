-- Store opinion section start time in audio for seek bar section markers
ALTER TABLE daily_briefs ADD COLUMN IF NOT EXISTS opinion_start_seconds REAL;
