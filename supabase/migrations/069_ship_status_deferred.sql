-- 069_ship_status_deferred.sql
-- Transparency: honest terminal statuses for the void --ship board.
--
-- The board moves a request submitted -> triaged -> building -> shipped, and
-- some requests will not be built. Until now the only "will not build" status
-- was 'wontship'. This adds two more honest closed states so the board can tell
-- the truth about a request instead of leaving it to rot in a queue:
--   'deferred'      -- a good idea, parked for later (not now, not never).
--   'not_feasible'  -- cannot be done as asked (technical / scope / cost).
--
-- Guarded + idempotent-safe: drop the auto-named inline CHECK if present, then
-- re-add it widened. Migration 068's INSERT policy (status must be 'submitted'
-- on insert) is untouched; only the value domain of the column changes.

ALTER TABLE ship_requests DROP CONSTRAINT IF EXISTS ship_requests_status_check;

ALTER TABLE ship_requests
  ADD CONSTRAINT ship_requests_status_check
  CHECK (status IN ('submitted','triaged','building','shipped','wontship','deferred','not_feasible'));
