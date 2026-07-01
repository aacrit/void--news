-- 062_security_hardening.sql
-- Security hardening from the 2026-06-11 independent review
-- (docs/INDEPENDENT-REVIEW-2026-06-11.md). Six fixes, all idempotent:
--
--   1. article_claims / source_claim_accuracy: migration 041 created these
--      with NO row-level security. On Supabase, a public-schema table
--      without RLS is fully readable AND writable via the shipped anon key
--      (void --verify data poisoning). Enable RLS + read-only policies;
--      the pipeline writes via the service role, which bypasses RLS.
--   2. weekly_digests: the 034 "Service role write" policy was
--      `FOR ALL USING (true)` with no role check — despite its name it
--      granted INSERT/UPDATE/DELETE to anon. Recreate with a real check.
--   3. sandbox_runs: 058 granted anon INSERT + UPDATE for a diag.html
--      consumer that never shipped. Unbounded anon JSONB inserts are a
--      DB-fill DoS on the 0.5 GB free tier. Drop the write policies
--      (reads stay; the service role still bypasses RLS for any future
--      server-side writer).
--   4. _migrations: created by migrate.yml without RLS — anon could
--      pre-insert future migration filenames and silently block their
--      application. Enable RLS with no anon policies (the migration
--      runner connects as the table owner and is unaffected).
--   5. story_clusters.summary_tier: the 049 CHECK allowed only 'sonnet',
--      but the pipeline stamps 'flash' when Claude is unavailable —
--      every cluster insert would have failed the constraint during a
--      Gemini-fallback run. Widen to ('sonnet','flash').
--   6. sync_ship_votes(): ship_requests.votes is RLS-protected
--      (service-role UPDATE only), so the frontend's direct anon update
--      silently matched 0 rows and the counter never moved. Provide an
--      anon-callable SECURITY DEFINER recount: votes = COUNT(ship_votes),
--      idempotent, so spamming the RPC cannot inflate the counter.

-- ── 1. RLS on void --verify tables ──────────────────────────────────────

ALTER TABLE article_claims ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read access for article_claims" ON article_claims;
CREATE POLICY "Public read access for article_claims"
  ON article_claims FOR SELECT USING (true);

ALTER TABLE source_claim_accuracy ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Public read access for source_claim_accuracy" ON source_claim_accuracy;
CREATE POLICY "Public read access for source_claim_accuracy"
  ON source_claim_accuracy FOR SELECT USING (true);

-- ── 2. weekly_digests write policy ──────────────────────────────────────

DROP POLICY IF EXISTS "Service role write for weekly_digests" ON weekly_digests;
CREATE POLICY "Service role write for weekly_digests"
  ON weekly_digests FOR ALL
  USING (auth.role() = 'service_role')
  WITH CHECK (auth.role() = 'service_role');

-- ── 3. Drop dead sandbox_runs anon write policies ───────────────────────

DROP POLICY IF EXISTS sandbox_runs_anon_insert ON sandbox_runs;
DROP POLICY IF EXISTS sandbox_runs_anon_update_recent ON sandbox_runs;

-- ── 4. _migrations tracker ──────────────────────────────────────────────
-- Owner (the migration runner's postgres role) bypasses RLS; PostgREST
-- anon gets denied with no policies defined.

ALTER TABLE IF EXISTS _migrations ENABLE ROW LEVEL SECURITY;

-- ── 5. Widen summary_tier CHECK ─────────────────────────────────────────

ALTER TABLE story_clusters
  DROP CONSTRAINT IF EXISTS story_clusters_summary_tier_check;
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'story_clusters_summary_tier_check'
      AND conrelid = 'story_clusters'::regclass
  ) THEN
    ALTER TABLE story_clusters
      ADD CONSTRAINT story_clusters_summary_tier_check
      CHECK (summary_tier IN ('sonnet', 'flash'));
  END IF;
END $$;

COMMENT ON COLUMN story_clusters.summary_tier IS
  'Which LLM produced the cached summary: sonnet (Claude, cache-freezable) '
  'or flash (Gemini fallback, re-summarized by the next Sonnet pass).';

-- ── 6. Anon-callable vote recount ───────────────────────────────────────

CREATE OR REPLACE FUNCTION sync_ship_votes(p_request_id UUID)
RETURNS INTEGER
LANGUAGE sql
SECURITY DEFINER
SET search_path = public
AS $$
  UPDATE ship_requests
     SET votes = (
       SELECT COUNT(*)::int FROM ship_votes v
        WHERE v.request_id = p_request_id
     )
   WHERE id = p_request_id
   RETURNING votes;
$$;

REVOKE ALL ON FUNCTION sync_ship_votes(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION sync_ship_votes(UUID) TO anon, authenticated, service_role;

COMMENT ON FUNCTION sync_ship_votes(UUID) IS
  'Recounts ship_votes for one request and writes the count to '
  'ship_requests.votes (RLS blocks direct anon updates). Idempotent: '
  'repeated calls cannot inflate the counter. Returns the new count.';
