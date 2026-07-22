-- Migration 067: allow 'consolidating' revolutions to omit an end year.
-- A recently-overthrown movement (Syria post-Assad, Bangladesh 2024) is still
-- consolidating and has no settled end year, so it belongs with active/watchlist/
-- dormant in the ongoing set. Widen the 066 CHECK to include it.

ALTER TABLE revolt_events DROP CONSTRAINT IF EXISTS revolt_end_year_required;

ALTER TABLE revolt_events ADD CONSTRAINT revolt_end_year_required
  CHECK (status IN ('active', 'watchlist', 'dormant', 'consolidating') OR date_end IS NOT NULL);
