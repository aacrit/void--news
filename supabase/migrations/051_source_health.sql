-- ============================================================================
-- Migration 051: Source health tracking (dead-feed quarantine)
-- Date: 2026-05-13
-- Trigger: UAT 2026-05-13 — ~50 fetch timeouts per pipeline run, same
-- sources repeatedly (Hudson Institute, Janes, Manhattan Institute,
-- news.com.au, DNA India, etc.). Each timeout costs 20-30s of wall clock.
--
-- Adds a lightweight consecutive-failure counter so the RSS fetcher can
-- quarantine sources that have failed 5 runs in a row, then skip them on
-- subsequent runs until manual review via /sources admin.
--
-- Columns:
--   consecutive_fetch_failures INT DEFAULT 0
--     incremented on timeout/error, reset to 0 on any successful fetch
--   last_fetch_at TIMESTAMPTZ
--     audit trail for the most recent fetch attempt (success or failure)
--   last_fetch_status TEXT
--     'ok' | 'timeout' | 'http_4xx' | 'http_5xx' | 'parse_error' | 'other'
--
-- Quarantine threshold (enforced in code, not SQL):
--   consecutive_fetch_failures >= 5  →  skip source for this run
--
-- No auto-resurrection. Manual unqstuck via the /sources admin (out of scope).
-- ============================================================================

ALTER TABLE sources
  ADD COLUMN IF NOT EXISTS consecutive_fetch_failures INT NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_fetch_at TIMESTAMPTZ,
  ADD COLUMN IF NOT EXISTS last_fetch_status TEXT;

COMMENT ON COLUMN sources.consecutive_fetch_failures IS
  'Running count of consecutive RSS fetch failures. Sources with >=5 are quarantined (skipped) by the fetcher until reset by a successful fetch or manual /sources review.';

COMMENT ON COLUMN sources.last_fetch_at IS
  'Timestamp of the most recent fetch attempt (success or failure).';

COMMENT ON COLUMN sources.last_fetch_status IS
  'Outcome of the last fetch: ok | timeout | http_4xx | http_5xx | parse_error | other.';

-- Helpful index for the /sources admin to surface quarantined feeds quickly.
CREATE INDEX IF NOT EXISTS idx_sources_consecutive_fetch_failures
  ON sources (consecutive_fetch_failures DESC)
  WHERE consecutive_fetch_failures > 0;
