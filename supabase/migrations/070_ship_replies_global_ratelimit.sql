-- 2026-08-03 — Add a global hourly backstop to the ship_replies rate limiter.
--
-- Migration 068 gave ship_replies a per-fingerprint cap (15/hr), but the
-- fingerprint is a client-supplied value, so a rotating/distributed anonymous
-- caller could still insert unbounded replies and inflate the single free-tier
-- DB. ship_requests already has a global backstop (068); this mirrors it for
-- ship_replies. CREATE OR REPLACE updates the function the existing
-- ship_replies_rate_limit_trg trigger (068) already calls; no trigger change.
CREATE OR REPLACE FUNCTION ship_replies_rate_limit()
RETURNS trigger AS $$
DECLARE
  per_fp        integer;
  global_recent integer;
BEGIN
  SELECT count(*) INTO per_fp
    FROM ship_replies
    WHERE fingerprint = NEW.fingerprint
      AND created_at > now() - interval '1 hour';
  IF per_fp >= 15 THEN
    RAISE EXCEPTION 'Too many replies from this client. Please try again later.';
  END IF;

  -- Coarse anti-DoS backstop: total replies per hour across everyone.
  SELECT count(*) INTO global_recent
    FROM ship_replies
    WHERE created_at > now() - interval '1 hour';
  IF global_recent >= 200 THEN
    RAISE EXCEPTION 'Replies are getting a lot of traffic right now. Please try again shortly.';
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER SET search_path = public;
