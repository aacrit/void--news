-- =============================================================================
-- One-shot recovery script — paste into the Supabase dashboard SQL editor at
-- https://supabase.com/dashboard/project/xryzskhgfuafyotrcdvj/sql/new
--
-- Use when the Free Plan 0.5 GB database cap has been hit and the project
-- is restricted ("exceed_egress_quota" violation).
--
-- This script:
--   1. Shows current table sizes (audit before destructive work)
--   2. Wipes engine_snapshots entirely (writer disabled 2026-05-31)
--   3. Prunes old engine_runs / sandbox_runs (>14 / >7 days)
--   4. Forcibly de-bloats articles older than 7 days (was 8) for headroom
--   5. VACUUMs the trimmed tables to reclaim disk space
--   6. Reports the new database size
-- =============================================================================

-- ---- Step 1: audit before ----------------------------------------------------
SELECT
  schemaname || '.' || tablename AS table_name,
  pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS total,
  pg_size_pretty(pg_relation_size(schemaname || '.' || tablename)) AS data,
  pg_size_pretty(pg_indexes_size(schemaname || '.' || tablename)) AS indexes
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
LIMIT 15;

-- ---- Step 2: wipe engine_snapshots (writer is disabled in main.py) ----------
DELETE FROM engine_snapshots;

-- ---- Step 3: prune engine_runs + sandbox_runs ------------------------------
DELETE FROM engine_runs   WHERE created_at < NOW() - INTERVAL '14 days';
DELETE FROM sandbox_runs  WHERE created_at < NOW() - INTERVAL '7 days';

-- ---- Step 4: tighten article retention 8 → 7 days for one cycle ------------
-- The pipeline's regular retention is 8 days. One-time 7-day prune gives
-- emergency headroom. Weekly digest still gets 7 full days of data.
DELETE FROM articles
WHERE published_at < NOW() - INTERVAL '7 days';

-- ---- Step 5: VACUUM (optional, see note) ------------------------------------
-- IMPORTANT — Supabase dashboard SQL editor wraps queries in a transaction,
-- and VACUUM cannot run inside a transaction (error 25001). Three options:
--
--   A. SKIP entirely. Supabase autovacuum will reclaim space within minutes.
--      Confirmed working 2026-06-01: DELETE alone dropped 0.55 GB → 469 MB.
--
--   B. Run each VACUUM FULL statement INDIVIDUALLY in the SQL editor —
--      open a new query tab, paste ONE line, click Run, repeat:
--          VACUUM FULL engine_snapshots;
--          VACUUM FULL engine_runs;
--          VACUUM FULL sandbox_runs;
--          VACUUM FULL articles;
--          VACUUM FULL bias_scores;
--
--   C. Use psql / a direct DB connection (not the dashboard) where
--      autocommit is default. Connection string in project settings.
--
-- VACUUM FULL takes an exclusive lock on the target table. On engine_snapshots
-- (now empty) it's instant. articles can take 10-30s and briefly blocks
-- writes — fine during off-hours.

-- ---- Step 6: audit after ---------------------------------------------------
SELECT
  pg_size_pretty(pg_database_size(current_database())) AS total_db_size,
  ROUND(pg_database_size(current_database()) / (1024.0 * 1024.0), 1) AS db_size_mb,
  ROUND(pg_database_size(current_database()) / (1024.0 * 1024.0 * 1024.0), 3) AS db_size_gb;

-- Per-table after VACUUM
SELECT
  schemaname || '.' || tablename AS table_name,
  pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS total
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC
LIMIT 10;

-- Expected result: db_size_gb well under 0.5. Project should auto-restore
-- service within a few minutes of the DB dropping below the cap.
