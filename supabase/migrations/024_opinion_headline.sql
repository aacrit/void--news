-- Add opinion_headline column to daily_briefs
-- Stores a Gemini-generated content-based headline for the opinion piece
-- (replaces hardcoded "The Board" label in the frontend)
ALTER TABLE daily_briefs ADD COLUMN IF NOT EXISTS opinion_headline TEXT;
