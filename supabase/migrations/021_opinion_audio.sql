-- Migration 021: Add opinion audio script to daily_briefs
-- Date: 2026-03-24
-- Purpose: Store the single-voice opinion editorial monologue script.
-- Audio assembly places this AFTER the main news dialogue, separated by
-- the glass-bell transition asset. Listeners get the full broadcast first;
-- the opinion segment is optional.

ALTER TABLE daily_briefs ADD COLUMN IF NOT EXISTS opinion_audio_script TEXT;
