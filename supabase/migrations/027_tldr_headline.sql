-- Add TL;DR headline field to daily briefs
ALTER TABLE daily_briefs ADD COLUMN IF NOT EXISTS tldr_headline TEXT;
