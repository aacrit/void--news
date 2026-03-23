-- Migration 019: Add opinion_text to daily_briefs
-- Date: 2026-03-23
-- Purpose: Separate editorial opinion section in daily brief.
-- TL;DR covers what happened + why it matters; opinion_text is the board's take.

ALTER TABLE daily_briefs ADD COLUMN IF NOT EXISTS opinion_text TEXT;
