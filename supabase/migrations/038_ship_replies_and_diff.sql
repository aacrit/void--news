-- void --ship v2: thread replies + ship diff summary

-- Ship diff: plain-text summary of what changed (written by agent at ship time)
ALTER TABLE ship_requests ADD COLUMN IF NOT EXISTS shipped_diff_summary TEXT;

-- Thread replies: lightweight conversation on any request (no accounts, fingerprint dedup)
CREATE TABLE ship_replies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id UUID NOT NULL REFERENCES ship_requests(id) ON DELETE CASCADE,
  body VARCHAR(280) NOT NULL,
  fingerprint VARCHAR(64) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_ship_replies_request ON ship_replies(request_id);
CREATE INDEX idx_ship_replies_created ON ship_replies(created_at DESC);

ALTER TABLE ship_replies ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ship_replies_public_read" ON ship_replies FOR SELECT USING (true);
CREATE POLICY "ship_replies_public_insert" ON ship_replies FOR INSERT WITH CHECK (true);
CREATE POLICY "ship_replies_service_delete" ON ship_replies FOR DELETE USING (auth.role() = 'service_role');

-- Enable realtime for live thread updates
ALTER PUBLICATION supabase_realtime ADD TABLE ship_replies;
