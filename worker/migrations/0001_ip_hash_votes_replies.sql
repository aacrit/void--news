-- 0001: key ship votes and replies on the server's salted IP hash
-- (rev 85 WS-D, audit 5 H1/H2).
--
-- Votes and reply rate limits were keyed on a client-supplied `fingerprint`,
-- so one client rotating that string could vote without bound and exhaust
-- the global reply cap for everyone. The Worker now writes `ip_hash` (and,
-- for the legacy NOT NULL column, the same value into `fingerprint`).
--
-- The old `fingerprint` column and its UNIQUE(request_id, fingerprint) stay
-- readable. Rows written before this migration have ip_hash NULL; SQLite
-- treats NULLs as distinct, so they never collide with the new index.
--
-- Apply:  cd worker && npx wrangler d1 migrations apply void-live --remote

ALTER TABLE ship_votes ADD COLUMN ip_hash TEXT;
CREATE UNIQUE INDEX IF NOT EXISTS uq_ship_votes_request_ip ON ship_votes(request_id, ip_hash);
CREATE INDEX IF NOT EXISTS idx_ship_votes_ip_created ON ship_votes(ip_hash, created_at);

ALTER TABLE ship_replies ADD COLUMN ip_hash TEXT;
CREATE INDEX IF NOT EXISTS idx_ship_replies_ip_created ON ship_replies(ip_hash, created_at);

CREATE INDEX IF NOT EXISTS idx_ship_requests_ip_created ON ship_requests(ip_hash, created_at);
