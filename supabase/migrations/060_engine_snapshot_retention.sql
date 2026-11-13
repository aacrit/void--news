-- ============================================================================
-- Migration 060: engine_snapshots / sandbox_runs retention RPCs
-- Date: 2026-06-01
-- Trigger: Supabase Free Plan database hit 0.55 GB / 0.5 GB cap on 2026-06-01.
-- The project was restricted ("exceed_egress_quota" — same restriction code
-- used for storage cap on Free Plan). Investigation traced ~50-150 MB of
-- bloat to the engine_snapshots table (5-7 MB JSONB per pipeline run since
-- migration 057 shipped 2026-05-22 — 10 days × multiple runs/day).
--
-- The engine_snapshot writer call in pipeline/main.py step 8c.6 is disabled
-- as of the 2026-05-31 simplification commit. This migration adds the
-- retention RPCs so that any future / opt-in writes are auto-pruned.
--
-- Three new RPCs:
--   cleanup_stale_engine_snapshots(days INT DEFAULT 3)
--   cleanup_stale_engine_runs(days INT DEFAULT 14)
--   cleanup_stale_sandbox_runs(days INT DEFAULT 7)
--
-- Default windows are aggressive (3-14 days vs articles at 8) because these
-- tables are pure diagnostic state — losing yesterday's snapshot doesn't
-- affect anything except sandbox-replay capability.
--
-- ON DELETE CASCADE in migration 057 means engine_runs deletion automatically
-- removes its engine_snapshots payload (so cleanup_stale_engine_runs alone
-- would prune both, but having separate RPCs lets us prune snapshots more
-- aggressively than the run metadata).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- engine_snapshots: 3-day default. JSONB payload is the bulk of the bloat.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cleanup_stale_engine_snapshots(days INT DEFAULT 3)
RETURNS INT AS $$
DECLARE
  deleted_count INT;
BEGIN
  DELETE FROM engine_snapshots
  WHERE created_at < NOW() - (days || ' days')::INTERVAL;
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION cleanup_stale_engine_snapshots(INT) FROM anon, authenticated;

-- ----------------------------------------------------------------------------
-- engine_runs: 14-day default. Tiny rows (just metadata + step_timings).
-- Kept longer for run-picker history in the diag.html lab.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cleanup_stale_engine_runs(days INT DEFAULT 14)
RETURNS INT AS $$
DECLARE
  deleted_count INT;
BEGIN
  DELETE FROM engine_runs
  WHERE created_at < NOW() - (days || ' days')::INTERVAL;
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION cleanup_stale_engine_runs(INT) FROM anon, authenticated;

-- ----------------------------------------------------------------------------
-- sandbox_runs: 7-day default. result_payload can be large but most runs
-- are diagnostic one-shots and never re-visited after a week.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cleanup_stale_sandbox_runs(days INT DEFAULT 7)
RETURNS INT AS $$
DECLARE
  deleted_count INT;
BEGIN
  DELETE FROM sandbox_runs
  WHERE created_at < NOW() - (days || ' days')::INTERVAL;
  GET DIAGNOSTICS deleted_count = ROW_COUNT;
  RETURN deleted_count;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION cleanup_stale_sandbox_runs(INT) FROM anon, authenticated;

-- ----------------------------------------------------------------------------
-- Master cleanup: prunes everything stale in one call. Returns a JSONB
-- breakdown so pipeline logs can show exactly how much was removed from
-- each table. Use this from pipeline/main.py [cleanup] phase.
-- ----------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION cleanup_diagnostic_tables(
  snapshot_days INT DEFAULT 3,
  run_days      INT DEFAULT 14,
  sandbox_days  INT DEFAULT 7
)
RETURNS JSONB AS $$
DECLARE
  snap_n     INT;
  run_n      INT;
  sandbox_n  INT;
  db_size_mb NUMERIC;
BEGIN
  snap_n    := cleanup_stale_engine_snapshots(snapshot_days);
  sandbox_n := cleanup_stale_sandbox_runs(sandbox_days);
  run_n     := cleanup_stale_engine_runs(run_days);

  -- Capture post-cleanup DB size so the pipeline can log warning if we
  -- are still close to a known cap.
  db_size_mb := pg_database_size(current_database())::NUMERIC / (1024 * 1024);

  RETURN jsonb_build_object(
    'engine_snapshots_pruned', snap_n,
    'engine_runs_pruned',      run_n,
    'sandbox_runs_pruned',     sandbox_n,
    'db_size_mb',              round(db_size_mb, 1)
  );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

REVOKE EXECUTE ON FUNCTION cleanup_diagnostic_tables(INT, INT, INT) FROM anon, authenticated;

-- ----------------------------------------------------------------------------
-- One-shot purge: clear ALL existing engine_snapshots immediately to
-- recover from the 2026-06-01 Free-Plan cap violation. The writer call
-- in pipeline/main.py is disabled as of the 2026-05-31 simplification,
-- so the table will not refill until someone re-enables it.
-- ----------------------------------------------------------------------------
DELETE FROM engine_snapshots;
DELETE FROM sandbox_runs WHERE created_at < NOW() - INTERVAL '7 days';
DELETE FROM engine_runs   WHERE created_at < NOW() - INTERVAL '14 days';

-- VACUUM cannot run inside a transaction block, so we can't include it
-- here. Run manually after this migration applies:
--   VACUUM FULL engine_snapshots;
--   VACUUM FULL engine_runs;
--   VACUUM FULL sandbox_runs;
