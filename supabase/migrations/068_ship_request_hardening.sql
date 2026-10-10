-- 2026-08-01 — Harden the public feedback intake (ship_requests / ship_replies).
--
-- Context: /feedback writes ship_requests with the public ANON key, which ships
-- in the client bundle. The old INSERT policy was `WITH CHECK (true)`, so a
-- direct anon-key API call could (a) flood the near-full free-tier DB and
-- (b) set privileged columns (status='shipped', ceo_response, votes, ...).
-- Client honeypot + localStorage are not controls against a direct API caller.
--
-- This migration:
--   1. Constrains anon INSERTs to unprivileged, default-shaped rows.
--   2. Adds DB-side rate limiting (per-fingerprint + a global hourly backstop).
--   3. Revokes read access to the submitter fingerprint columns from anon.
-- Service role (pipeline + CEO triage in Supabase) is unaffected throughout.

-- ── 1. Constrain anon INSERTs on ship_requests ─────────────────────────────
-- WITH CHECK runs after column defaults are applied, and the form sets none of
-- these, so legitimate submissions (status defaults to 'submitted', votes to 0,
-- the rest NULL) still pass. A crafted insert that sets any privileged field is
-- rejected. ip_hash is required so the rate limiter below always has a key.
DROP POLICY IF EXISTS "ship_requests_public_insert" ON ship_requests;
CREATE POLICY "ship_requests_public_insert" ON ship_requests
  FOR INSERT WITH CHECK (
    status = 'submitted'
    AND votes = 0
    AND priority IS NULL
    AND ceo_response IS NULL
    AND claude_branch IS NULL
    AND shipped_commit IS NULL
    AND shipped_diff_summary IS NULL
    AND triaged_at IS NULL
    AND shipped_at IS NULL
    AND ip_hash IS NOT NULL
  );

-- ── 2a. Rate limit ship_requests (per fingerprint + global backstop) ───────
-- SECURITY DEFINER so the count queries run as the table owner and bypass RLS.
CREATE OR REPLACE FUNCTION ship_requests_rate_limit()
RETURNS trigger AS $$
DECLARE
  per_fp        integer;
  global_recent integer;
BEGIN
  SELECT count(*) INTO per_fp
    FROM ship_requests
    WHERE ip_hash = NEW.ip_hash
      AND created_at > now() - interval '1 hour';
  IF per_fp >= 5 THEN
    RAISE EXCEPTION 'Too many submissions from this client. Please try again later.';
  END IF;

  -- Coarse anti-DoS backstop: cap total inserts per hour. Generous for an
  -- experimental launch; raise if real traffic grows.
  SELECT count(*) INTO global_recent
    FROM ship_requests
    WHERE created_at > now() - interval '1 hour';
  IF global_recent >= 120 THEN
    RAISE EXCEPTION 'Feedback is receiving a lot of submissions right now. Please try again shortly.';
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

DROP TRIGGER IF EXISTS ship_requests_rate_limit_trg ON ship_requests;
CREATE TRIGGER ship_requests_rate_limit_trg
  BEFORE INSERT ON ship_requests
  FOR EACH ROW EXECUTE FUNCTION ship_requests_rate_limit();

-- ── 2b. Rate limit ship_replies (per fingerprint) ─────────────────────────
CREATE OR REPLACE FUNCTION ship_replies_rate_limit()
RETURNS trigger AS $$
DECLARE
  per_fp integer;
BEGIN
  SELECT count(*) INTO per_fp
    FROM ship_replies
    WHERE fingerprint = NEW.fingerprint
      AND created_at > now() - interval '1 hour';
  IF per_fp >= 15 THEN
    RAISE EXCEPTION 'Too many replies from this client. Please try again later.';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;

DROP TRIGGER IF EXISTS ship_replies_rate_limit_trg ON ship_replies;
CREATE TRIGGER ship_replies_rate_limit_trg
  BEFORE INSERT ON ship_replies
  FOR EACH ROW EXECUTE FUNCTION ship_replies_rate_limit();

-- ── 3. Hide submitter fingerprints from anon (privacy) ─────────────────────
-- device_info (user-agent) + ip_hash are collected for rate limiting only and
-- were world-readable. The frontend selects an explicit column list that omits
-- them (see fetchShipRequests). Service role keeps full read for triage.
REVOKE SELECT (device_info, ip_hash) ON ship_requests FROM anon;
REVOKE SELECT (device_info, ip_hash) ON ship_requests FROM authenticated;
