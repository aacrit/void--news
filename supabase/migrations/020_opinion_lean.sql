-- Migration 020: Single-story opinion with lean rotation
-- Date: 2026-03-24
-- Purpose: Track which cluster the opinion focuses on and its editorial lean.
-- The opinion rotates daily: left → center → right (day-of-year mod 3).

-- Which cluster the opinion piece is about
ALTER TABLE daily_briefs ADD COLUMN IF NOT EXISTS opinion_cluster_id UUID;

-- Editorial lean for the opinion piece: 'left', 'center', 'right'
ALTER TABLE daily_briefs ADD COLUMN IF NOT EXISTS opinion_lean TEXT
  CHECK (opinion_lean IS NULL OR opinion_lean IN ('left', 'center', 'right'));

-- Allow edition constraint to include new editions
ALTER TABLE daily_briefs DROP CONSTRAINT IF EXISTS daily_briefs_edition_check;
ALTER TABLE daily_briefs ADD CONSTRAINT daily_briefs_edition_check
  CHECK (edition IN ('world', 'us', 'india', 'uk', 'canada'));
