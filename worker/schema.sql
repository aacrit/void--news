-- ============================================================================
-- schema_d1.sql — Void News live user-write tables for Cloudflare D1
-- ============================================================================
-- Consolidated from Supabase Postgres migrations:
--   037 (ship_requests + ship_votes), 038 (ship_replies + shipped_diff_summary),
--   062 (sync_ship_votes RPC — see PORT_NOTES.md), 068 (INSERT hardening +
--   rate-limit triggers + fingerprint column revoke), 069 (status domain
--   widened), 070 (ship_replies global rate-limit backstop).
--
-- These are the ONLY tables that receive WRITES from the browser at runtime.
-- Determined by reading frontend/app/lib/supabase.ts (the anon-key client that
-- ships in the browser bundle):
--   * ship_requests  <- submitShipRequest()   INSERT
--   * ship_votes     <- voteOnShipRequest()    INSERT  (+ sync_ship_votes RPC)
--   * ship_replies   <- submitShipReply()      INSERT
-- (ig_posts .update() calls live in supabase-server.ts and run server-side with
--  the service-role key on the basic-auth admin page — NOT browser writes.)
--
-- A Cloudflare Worker sits in front of D1 and must re-implement the
-- access-control / RPC / rate-limit / privacy logic that Supabase RLS + Postgres
-- triggers + SECURITY DEFINER functions previously enforced. Every dropped
-- policy/function/trigger is catalogued in PORT_NOTES.md — read it before
-- writing the Worker.
--
-- Postgres -> SQLite translation applied:
--   uuid -> TEXT; timestamptz -> TEXT/CURRENT_TIMESTAMP; boolean n/a here;
--   varchar(n) -> TEXT; char_length(...) CHECK -> length(...) CHECK.
--   Enable FKs per connection with:  PRAGMA foreign_keys = ON;
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────
-- ship_requests  (037; +038 shipped_diff_summary; status domain 069)
--   NOTE: the anon INSERT constraints from migration 068 (status='submitted',
--   votes=0, all privileged fields NULL, ip_hash NOT NULL) were an RLS WITH
--   CHECK policy, NOT a table constraint — they MUST be re-enforced in the
--   Worker on insert. See PORT_NOTES.md.
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ship_requests (
  id                   TEXT PRIMARY KEY,
  title                TEXT NOT NULL,                       -- was varchar(120)
  description          TEXT NOT NULL CHECK (length(description) <= 2000),
  category             TEXT NOT NULL DEFAULT 'feature'
                         CHECK (category IN ('bug', 'feature', 'enhancement')),
  area                 TEXT NOT NULL DEFAULT 'other'
                         CHECK (area IN ('frontend', 'pipeline', 'bias', 'audio', 'design', 'other')),
  edition_context      TEXT CHECK (edition_context IS NULL
                         OR edition_context IN ('world', 'us', 'europe', 'south-asia')),
  status               TEXT NOT NULL DEFAULT 'submitted'
                         CHECK (status IN ('submitted','triaged','building','shipped',
                                           'wontship','deferred','not_feasible')),   -- 069
  priority             TEXT CHECK (priority IS NULL OR priority IN ('p0', 'p1', 'p2', 'p3')),
  votes                INTEGER NOT NULL DEFAULT 0,
  ceo_response         TEXT,
  claude_branch        TEXT,                                -- was varchar(100)
  shipped_commit       TEXT,                                -- was varchar(40)
  device_info          TEXT,                                -- was varchar(200); anon read revoked (068)
  ip_hash              TEXT,                                -- was varchar(64);  anon read revoked (068)
  created_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  triaged_at           TEXT,
  shipped_at           TEXT,
  updated_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  shipped_diff_summary TEXT                                 -- 038
);
CREATE INDEX IF NOT EXISTS idx_ship_requests_status  ON ship_requests(status);
CREATE INDEX IF NOT EXISTS idx_ship_requests_votes   ON ship_requests(votes DESC);
CREATE INDEX IF NOT EXISTS idx_ship_requests_created ON ship_requests(created_at DESC);

-- ─────────────────────────────────────────────────────────────────────────
-- ship_votes  (037) — one vote per (request, fingerprint)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ship_votes (
  id          TEXT PRIMARY KEY,
  request_id  TEXT NOT NULL REFERENCES ship_requests(id) ON DELETE CASCADE,
  fingerprint TEXT NOT NULL,                                -- was varchar(64)
  created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(request_id, fingerprint)
);
CREATE INDEX IF NOT EXISTS idx_ship_votes_request ON ship_votes(request_id);

-- ─────────────────────────────────────────────────────────────────────────
-- ship_replies  (038) — lightweight thread, fingerprint dedup, no accounts
--   Per-fingerprint (15/hr) + global (200/hr) rate limits were Postgres
--   triggers (068/070) — re-implement in the Worker. See PORT_NOTES.md.
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ship_replies (
  id          TEXT PRIMARY KEY,
  request_id  TEXT NOT NULL REFERENCES ship_requests(id) ON DELETE CASCADE,
  body        TEXT NOT NULL CHECK (length(body) <= 280),   -- was varchar(280)
  fingerprint TEXT NOT NULL,                                -- was varchar(64)
  created_at  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_ship_replies_request ON ship_replies(request_id);
CREATE INDEX IF NOT EXISTS idx_ship_replies_created ON ship_replies(created_at DESC);
