-- Migration 077: Persist disaster_severity on story_clusters (P0-4)
-- (2026-08-11 mass-casualty ordering floor)
--
-- The importance ranker already computes a mass-casualty disaster severity
-- (component_scores['disaster_severity'], 0-100) per cluster, but it lived
-- only in memory. The FINAL displayed feed order is written by main.py step
-- 8d.5, which RE-READS clusters from the DB and re-runs
-- feed_ranker.apply_feed_ordering over them. For the new deterministic
-- mass-casualty ordering floor (a well-sourced disaster may not sort below a
-- lower-base non-disaster) to affect the displayed feed, the severity must be
-- selectable from the DB in that pass.
--
-- Additive + nullable, DEFAULT 0 so existing rows and non-disaster clusters
-- read as "no disaster". No weight change: this only surfaces an
-- already-computed signal to the ordering layer.

ALTER TABLE story_clusters
  ADD COLUMN IF NOT EXISTS disaster_severity REAL DEFAULT 0;

COMMENT ON COLUMN story_clusters.disaster_severity IS
  'Mass-casualty disaster severity 0-100 from importance_ranker '
  'component_scores. Consumed by feed_ranker mass-casualty ordering floor. '
  '0 = not a disaster. Migration 077 (P0-4, 2026-08-11).';
