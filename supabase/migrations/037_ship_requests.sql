-- void --ship: Feature/Bug request tracker
-- Public read/insert, service_role update/delete
-- Realtime enabled for live Kanban updates

CREATE TABLE ship_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  title VARCHAR(120) NOT NULL,
  description TEXT NOT NULL CHECK (char_length(description) <= 2000),
  category TEXT NOT NULL DEFAULT 'feature' CHECK (category IN ('bug', 'feature', 'enhancement')),
  area TEXT NOT NULL DEFAULT 'other' CHECK (area IN ('frontend', 'pipeline', 'bias', 'audio', 'design', 'other')),
  edition_context TEXT CHECK (edition_context IS NULL OR edition_context IN ('world', 'us', 'europe', 'south-asia')),
  status TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN ('submitted', 'triaged', 'building', 'shipped', 'wontship')),
  priority TEXT CHECK (priority IS NULL OR priority IN ('p0', 'p1', 'p2', 'p3')),
  votes INTEGER NOT NULL DEFAULT 0,
  ceo_response TEXT,
  claude_branch VARCHAR(100),
  shipped_commit VARCHAR(40),
  device_info VARCHAR(200),
  ip_hash VARCHAR(64),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  triaged_at TIMESTAMPTZ,
  shipped_at TIMESTAMPTZ,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes
CREATE INDEX idx_ship_requests_status ON ship_requests(status);
CREATE INDEX idx_ship_requests_votes ON ship_requests(votes DESC);
CREATE INDEX idx_ship_requests_created ON ship_requests(created_at DESC);

-- Updated-at trigger (reuse existing function from migration 005)
CREATE TRIGGER set_ship_requests_updated_at
  BEFORE UPDATE ON ship_requests
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- RLS
ALTER TABLE ship_requests ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ship_requests_public_read" ON ship_requests FOR SELECT USING (true);
CREATE POLICY "ship_requests_public_insert" ON ship_requests FOR INSERT WITH CHECK (true);
CREATE POLICY "ship_requests_service_update" ON ship_requests FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "ship_requests_service_delete" ON ship_requests FOR DELETE USING (auth.role() = 'service_role');

-- Vote dedup table
CREATE TABLE ship_votes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  request_id UUID NOT NULL REFERENCES ship_requests(id) ON DELETE CASCADE,
  fingerprint VARCHAR(64) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(request_id, fingerprint)
);

CREATE INDEX idx_ship_votes_request ON ship_votes(request_id);

ALTER TABLE ship_votes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ship_votes_public_read" ON ship_votes FOR SELECT USING (true);
CREATE POLICY "ship_votes_public_insert" ON ship_votes FOR INSERT WITH CHECK (true);

-- Enable realtime for live Kanban updates
ALTER PUBLICATION supabase_realtime ADD TABLE ship_requests;
