-- void --history: Multi-perspective historical event explorer
-- Public read, service_role write for all tables

-- ============================================================
-- 1. history_events — core event records
-- ============================================================
CREATE TABLE history_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  subtitle TEXT,
  date_display TEXT NOT NULL,
  date_sort INTEGER NOT NULL,
  date_precision TEXT NOT NULL DEFAULT 'year'
    CHECK (date_precision IN ('day', 'month', 'year', 'decade', 'century')),
  era TEXT NOT NULL
    CHECK (era IN ('ancient', 'classical', 'medieval', 'early-modern', 'modern', 'contemporary')),
  region TEXT NOT NULL
    CHECK (region IN (
      'africa', 'americas', 'east-asia', 'south-asia', 'southeast-asia',
      'middle-east', 'europe', 'oceania', 'central-asia', 'global'
    )),
  country TEXT,
  category TEXT NOT NULL
    CHECK (category IN (
      'war', 'revolution', 'empire', 'independence', 'genocide',
      'disaster', 'cultural', 'scientific', 'economic', 'political'
    )),
  severity TEXT NOT NULL DEFAULT 'critical'
    CHECK (severity IN ('catastrophic', 'critical', 'major')),
  summary TEXT NOT NULL,
  significance TEXT NOT NULL,
  death_toll TEXT,
  affected_population TEXT,
  duration TEXT,
  key_figures JSONB DEFAULT '[]'::jsonb,
  legacy_points JSONB DEFAULT '[]'::jsonb,
  primary_source_excerpts JSONB DEFAULT '[]'::jsonb,
  coordinates JSONB,
  hero_image_url TEXT,
  hero_image_attribution TEXT,
  map_image_url TEXT,
  related_event_slugs TEXT[] DEFAULT '{}',
  display_order INTEGER DEFAULT 0,
  is_published BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_history_events_slug ON history_events(slug);
CREATE INDEX idx_history_events_era ON history_events(era);
CREATE INDEX idx_history_events_region ON history_events(region);
CREATE INDEX idx_history_events_category ON history_events(category);
CREATE INDEX idx_history_events_date_sort ON history_events(date_sort);
CREATE INDEX idx_history_events_published ON history_events(is_published);

-- Reuse existing updated_at trigger function from migration 005
CREATE TRIGGER set_history_events_updated_at
  BEFORE UPDATE ON history_events
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE history_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "history_events_public_read" ON history_events FOR SELECT USING (true);
CREATE POLICY "history_events_service_insert" ON history_events FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "history_events_service_update" ON history_events FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "history_events_service_delete" ON history_events FOR DELETE USING (auth.role() = 'service_role');

-- ============================================================
-- 2. history_perspectives — multiple viewpoints per event
-- ============================================================
CREATE TABLE history_perspectives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID NOT NULL REFERENCES history_events(id) ON DELETE CASCADE,
  viewpoint TEXT NOT NULL,
  viewpoint_type TEXT NOT NULL
    CHECK (viewpoint_type IN ('victor', 'vanquished', 'bystander', 'academic', 'revisionist', 'indigenous')),
  region_origin TEXT NOT NULL,
  narrative TEXT NOT NULL,
  key_arguments JSONB DEFAULT '[]'::jsonb,
  sources JSONB DEFAULT '[]'::jsonb,
  notable_quotes JSONB DEFAULT '[]'::jsonb,
  emphasized JSONB DEFAULT '[]'::jsonb,
  omitted JSONB DEFAULT '[]'::jsonb,
  display_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_history_perspectives_event ON history_perspectives(event_id);
CREATE INDEX idx_history_perspectives_type ON history_perspectives(viewpoint_type);

ALTER TABLE history_perspectives ENABLE ROW LEVEL SECURITY;
CREATE POLICY "history_perspectives_public_read" ON history_perspectives FOR SELECT USING (true);
CREATE POLICY "history_perspectives_service_insert" ON history_perspectives FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "history_perspectives_service_update" ON history_perspectives FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "history_perspectives_service_delete" ON history_perspectives FOR DELETE USING (auth.role() = 'service_role');

-- ============================================================
-- 3. history_media — images, maps, documents per event
-- ============================================================
CREATE TABLE history_media (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_id UUID NOT NULL REFERENCES history_events(id) ON DELETE CASCADE,
  media_type TEXT NOT NULL
    CHECK (media_type IN ('image', 'map', 'video', 'document', 'painting', 'photograph')),
  title TEXT NOT NULL,
  description TEXT,
  source_url TEXT NOT NULL,
  thumbnail_url TEXT,
  attribution TEXT NOT NULL,
  license TEXT DEFAULT 'public-domain'
    CHECK (license IN ('public-domain', 'cc0', 'cc-by', 'cc-by-sa', 'fair-use')),
  creator TEXT,
  creation_date TEXT,
  display_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_history_media_event ON history_media(event_id);
CREATE INDEX idx_history_media_type ON history_media(media_type);

ALTER TABLE history_media ENABLE ROW LEVEL SECURITY;
CREATE POLICY "history_media_public_read" ON history_media FOR SELECT USING (true);
CREATE POLICY "history_media_service_insert" ON history_media FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "history_media_service_update" ON history_media FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "history_media_service_delete" ON history_media FOR DELETE USING (auth.role() = 'service_role');

-- ============================================================
-- 4. history_connections — causal/parallel links between events
-- ============================================================
CREATE TABLE history_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  event_a_id UUID NOT NULL REFERENCES history_events(id) ON DELETE CASCADE,
  event_b_id UUID NOT NULL REFERENCES history_events(id) ON DELETE CASCADE,
  connection_type TEXT NOT NULL
    CHECK (connection_type IN ('caused', 'influenced', 'response-to', 'parallel', 'consequence')),
  description TEXT,
  UNIQUE(event_a_id, event_b_id)
);

CREATE INDEX idx_history_connections_a ON history_connections(event_a_id);
CREATE INDEX idx_history_connections_b ON history_connections(event_b_id);

ALTER TABLE history_connections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "history_connections_public_read" ON history_connections FOR SELECT USING (true);
CREATE POLICY "history_connections_service_insert" ON history_connections FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "history_connections_service_update" ON history_connections FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "history_connections_service_delete" ON history_connections FOR DELETE USING (auth.role() = 'service_role');
