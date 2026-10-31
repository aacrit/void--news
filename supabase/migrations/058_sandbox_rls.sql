-- 058_sandbox_rls.sql — Row-level security for the diagnostic lab tables.
--
-- The standalone HTML at frontend/public/diag.html runs in the browser
-- with the public anon key. It needs to:
--   - READ every row of engine_runs + engine_snapshots + sandbox_runs
--   - WRITE rows of sandbox_runs (to trigger replays from the GH Actions
--     and clipboard-CLI paths; the local sidecar path writes via service
--     role and bypasses RLS)
--
-- Production tables (story_clusters, articles, article_bias_scores,
-- pipeline_runs) retain their existing anon-read-only policies. This
-- migration ONLY governs the three new tables from 057.

ALTER TABLE engine_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE engine_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE sandbox_runs ENABLE ROW LEVEL SECURITY;

-- Read-everyone on all three.
DROP POLICY IF EXISTS engine_runs_read_all ON engine_runs;
CREATE POLICY engine_runs_read_all ON engine_runs FOR SELECT USING (true);

DROP POLICY IF EXISTS engine_snapshots_read_all ON engine_snapshots;
CREATE POLICY engine_snapshots_read_all ON engine_snapshots FOR SELECT USING (true);

DROP POLICY IF EXISTS sandbox_runs_read_all ON sandbox_runs;
CREATE POLICY sandbox_runs_read_all ON sandbox_runs FOR SELECT USING (true);

-- Write only on sandbox_runs (anon may INSERT and UPDATE their own
-- recently-created rows; engine_runs + engine_snapshots are server-only).
DROP POLICY IF EXISTS sandbox_runs_anon_insert ON sandbox_runs;
CREATE POLICY sandbox_runs_anon_insert ON sandbox_runs FOR INSERT WITH CHECK (true);

-- Allow status / result updates on sandbox_runs rows created in the last
-- hour (so a triggered replay can be moved from pending → running → complete
-- or error by the worker, but old historical rows can't be tampered with).
DROP POLICY IF EXISTS sandbox_runs_anon_update_recent ON sandbox_runs;
CREATE POLICY sandbox_runs_anon_update_recent ON sandbox_runs FOR UPDATE
  USING (created_at > NOW() - INTERVAL '1 hour')
  WITH CHECK (created_at > NOW() - INTERVAL '1 hour');

COMMENT ON POLICY engine_runs_read_all ON engine_runs IS
  'Diagnostic UI reads all runs to populate the run picker.';
COMMENT ON POLICY sandbox_runs_anon_insert ON sandbox_runs IS
  'Diagnostic UI can trigger a sandbox replay by inserting a row with status=pending. Worker process picks it up, transitions status, writes result_payload.';
