-- 057_engine_snapshots.sql — Engine/editorial separation foundation
--
-- Three tables that turn the rule-based core of the void --news pipeline
-- into a re-runnable, diagnosable engine separate from the LLM editorial
-- layer. The sandbox at frontend/public/diag.html reads these.
--
--   engine_runs       — one row per pipeline run (production or sandbox),
--                       tracks per-step timings, errors, counts, cost
--   engine_snapshots  — full frozen JSON payload of articles + clusters +
--                       bias scores + rankings; the contract that the
--                       editorial layer consumes
--   sandbox_runs      — sandbox replays of an engine_snapshots row with
--                       param overrides; lets the diagnostic UI re-run
--                       clustering/ranking/bias at $0 to test "what if"
--
-- RLS in 058_sandbox_rls.sql: anon-read on all three; anon-write on
-- sandbox_runs only. Production tables (story_clusters, articles,
-- article_bias_scores) remain anon-read-only via existing policies.

CREATE TABLE IF NOT EXISTS engine_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pipeline_run_id UUID REFERENCES pipeline_runs(id) ON DELETE SET NULL,
  source TEXT NOT NULL DEFAULT 'production',  -- 'production' | 'sandbox'
  params JSONB NOT NULL DEFAULT '{}'::jsonb,
  step_timings JSONB NOT NULL DEFAULT '{}'::jsonb,
  step_errors JSONB NOT NULL DEFAULT '{}'::jsonb,
  cluster_count INT,
  article_count INT,
  sonnet_calls INT DEFAULT 0,
  gemini_calls INT DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS engine_snapshots (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  engine_run_id UUID NOT NULL REFERENCES engine_runs(id) ON DELETE CASCADE,
  payload JSONB NOT NULL,
  payload_size_bytes INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sandbox_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  base_snapshot_id UUID REFERENCES engine_snapshots(id) ON DELETE SET NULL,
  param_overrides JSONB NOT NULL DEFAULT '{}'::jsonb,
  result_payload JSONB,
  status TEXT NOT NULL DEFAULT 'pending',  -- pending | running | complete | error
  triggered_via TEXT,                       -- sidecar | cli | actions
  error_message TEXT,
  duration_ms INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS engine_runs_created_at_idx
  ON engine_runs (created_at DESC);
CREATE INDEX IF NOT EXISTS engine_runs_source_idx
  ON engine_runs (source, created_at DESC);
CREATE INDEX IF NOT EXISTS engine_snapshots_run_idx
  ON engine_snapshots (engine_run_id);
CREATE INDEX IF NOT EXISTS sandbox_runs_status_idx
  ON sandbox_runs (status, created_at DESC);
CREATE INDEX IF NOT EXISTS sandbox_runs_base_idx
  ON sandbox_runs (base_snapshot_id);

COMMENT ON TABLE engine_runs IS
  'Per-run metadata for the rule-based engine stage. Captures timings, errors, counts. Source = production for daily runs; sandbox for diagnostic replays.';
COMMENT ON TABLE engine_snapshots IS
  'Frozen engine output (articles + clusters + bias scores + rankings). The contract consumed by the editorial layer and replayed by the sandbox.';
COMMENT ON TABLE sandbox_runs IS
  'Sandbox replays of an engine_snapshot with parameter overrides. Lets the diagnostic UI test clustering/ranking/bias tunings at zero cost.';
