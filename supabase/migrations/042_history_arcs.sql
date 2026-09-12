-- void --history: Long-arc topics — multi-century thematic narratives
-- Extends the history system with arc-level content that CONTAINS events
-- Public read, service_role write for all tables

-- ============================================================
-- 1. history_arcs — top-level arc records
-- ============================================================
CREATE TABLE history_arcs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  subtitle TEXT,
  central_question TEXT NOT NULL,
  date_range TEXT NOT NULL,
  date_start INTEGER NOT NULL,
  date_end INTEGER NOT NULL,
  theme TEXT NOT NULL
    CHECK (theme IN (
      'economic', 'political', 'social', 'technological',
      'cultural', 'military', 'environmental', 'philosophical'
    )),
  regions TEXT[] NOT NULL DEFAULT '{}',
  introduction TEXT NOT NULL,
  hero_image_url TEXT,
  hero_image_caption TEXT,
  hero_image_attribution TEXT,
  display_order INTEGER DEFAULT 0,
  is_published BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_history_arcs_slug ON history_arcs(slug);
CREATE INDEX idx_history_arcs_theme ON history_arcs(theme);
CREATE INDEX idx_history_arcs_published ON history_arcs(is_published);

CREATE TRIGGER set_history_arcs_updated_at
  BEFORE UPDATE ON history_arcs
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE history_arcs ENABLE ROW LEVEL SECURITY;
CREATE POLICY "history_arcs_public_read" ON history_arcs FOR SELECT USING (true);
CREATE POLICY "history_arcs_service_insert" ON history_arcs FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "history_arcs_service_update" ON history_arcs FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "history_arcs_service_delete" ON history_arcs FOR DELETE USING (auth.role() = 'service_role');

-- ============================================================
-- 2. history_arc_perspectives — ideological traditions spanning the arc
-- ============================================================
CREATE TABLE history_arc_perspectives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  arc_id UUID NOT NULL REFERENCES history_arcs(id) ON DELETE CASCADE,
  slug TEXT NOT NULL,
  name TEXT NOT NULL,
  ideology TEXT NOT NULL,
  color TEXT NOT NULL DEFAULT 'a'
    CHECK (color IN ('a', 'b', 'c', 'd', 'e', 'f')),
  throughline TEXT NOT NULL,
  key_thinkers JSONB DEFAULT '[]'::jsonb,
  canonical_works JSONB DEFAULT '[]'::jsonb,
  display_order INTEGER DEFAULT 0,
  UNIQUE(arc_id, slug)
);

CREATE INDEX idx_history_arc_perspectives_arc ON history_arc_perspectives(arc_id);

ALTER TABLE history_arc_perspectives ENABLE ROW LEVEL SECURITY;
CREATE POLICY "history_arc_perspectives_public_read" ON history_arc_perspectives FOR SELECT USING (true);
CREATE POLICY "history_arc_perspectives_service_insert" ON history_arc_perspectives FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "history_arc_perspectives_service_update" ON history_arc_perspectives FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "history_arc_perspectives_service_delete" ON history_arc_perspectives FOR DELETE USING (auth.role() = 'service_role');

-- ============================================================
-- 3. history_arc_chapters — sequential phases within an arc
-- ============================================================
CREATE TABLE history_arc_chapters (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  arc_id UUID NOT NULL REFERENCES history_arcs(id) ON DELETE CASCADE,
  chapter_number INTEGER NOT NULL,
  title TEXT NOT NULL,
  subtitle TEXT,
  date_range TEXT NOT NULL,
  date_start INTEGER NOT NULL,
  date_end INTEGER NOT NULL,
  narrative TEXT NOT NULL,
  key_moments JSONB DEFAULT '[]'::jsonb,
  primary_sources JSONB DEFAULT '[]'::jsonb,
  connected_event_slugs TEXT[] DEFAULT '{}',
  relevant_statistics TEXT[] DEFAULT '{}',
  hero_image_url TEXT,
  hero_image_caption TEXT,
  hero_image_attribution TEXT,
  UNIQUE(arc_id, chapter_number)
);

CREATE INDEX idx_history_arc_chapters_arc ON history_arc_chapters(arc_id);
CREATE INDEX idx_history_arc_chapters_order ON history_arc_chapters(arc_id, chapter_number);

ALTER TABLE history_arc_chapters ENABLE ROW LEVEL SECURITY;
CREATE POLICY "history_arc_chapters_public_read" ON history_arc_chapters FOR SELECT USING (true);
CREATE POLICY "history_arc_chapters_service_insert" ON history_arc_chapters FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "history_arc_chapters_service_update" ON history_arc_chapters FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "history_arc_chapters_service_delete" ON history_arc_chapters FOR DELETE USING (auth.role() = 'service_role');

-- ============================================================
-- 4. history_arc_chapter_perspectives — perspective x chapter matrix
--    The intersection: how each perspective reads each chapter
-- ============================================================
CREATE TABLE history_arc_chapter_perspectives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  chapter_id UUID NOT NULL REFERENCES history_arc_chapters(id) ON DELETE CASCADE,
  perspective_id UUID NOT NULL REFERENCES history_arc_perspectives(id) ON DELETE CASCADE,
  narrative TEXT NOT NULL,
  key_arguments JSONB DEFAULT '[]'::jsonb,
  emphasized JSONB DEFAULT '[]'::jsonb,
  omitted JSONB DEFAULT '[]'::jsonb,
  sources JSONB DEFAULT '[]'::jsonb,
  notable_quotes JSONB DEFAULT '[]'::jsonb,
  UNIQUE(chapter_id, perspective_id)
);

CREATE INDEX idx_arc_chap_persp_chapter ON history_arc_chapter_perspectives(chapter_id);
CREATE INDEX idx_arc_chap_persp_perspective ON history_arc_chapter_perspectives(perspective_id);

ALTER TABLE history_arc_chapter_perspectives ENABLE ROW LEVEL SECURITY;
CREATE POLICY "history_arc_chapter_perspectives_public_read" ON history_arc_chapter_perspectives FOR SELECT USING (true);
CREATE POLICY "history_arc_chapter_perspectives_service_insert" ON history_arc_chapter_perspectives FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "history_arc_chapter_perspectives_service_update" ON history_arc_chapter_perspectives FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "history_arc_chapter_perspectives_service_delete" ON history_arc_chapter_perspectives FOR DELETE USING (auth.role() = 'service_role');

-- ============================================================
-- 5. history_arc_events — links arcs to existing history_events
--    An event can belong to multiple arcs (Berlin Wall: Cold War arc,
--    Democracy arc, etc.). Each link specifies which chapter it falls in.
-- ============================================================
CREATE TABLE history_arc_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  arc_id UUID NOT NULL REFERENCES history_arcs(id) ON DELETE CASCADE,
  event_id UUID NOT NULL REFERENCES history_events(id) ON DELETE CASCADE,
  chapter_id UUID REFERENCES history_arc_chapters(id) ON DELETE SET NULL,
  event_slug TEXT NOT NULL,
  role_in_arc TEXT,
  display_order INTEGER DEFAULT 0,
  UNIQUE(arc_id, event_id)
);

CREATE INDEX idx_history_arc_events_arc ON history_arc_events(arc_id);
CREATE INDEX idx_history_arc_events_event ON history_arc_events(event_id);
CREATE INDEX idx_history_arc_events_chapter ON history_arc_events(chapter_id);

ALTER TABLE history_arc_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "history_arc_events_public_read" ON history_arc_events FOR SELECT USING (true);
CREATE POLICY "history_arc_events_service_insert" ON history_arc_events FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "history_arc_events_service_update" ON history_arc_events FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "history_arc_events_service_delete" ON history_arc_events FOR DELETE USING (auth.role() = 'service_role');

-- ============================================================
-- 6. history_arc_statistics — time series data for charts
-- ============================================================
CREATE TABLE history_arc_statistics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  arc_id UUID NOT NULL REFERENCES history_arcs(id) ON DELETE CASCADE,
  label TEXT NOT NULL,
  description TEXT,
  unit TEXT NOT NULL,
  source TEXT NOT NULL,
  source_url TEXT,
  data_points JSONB NOT NULL DEFAULT '[]'::jsonb,
  relevant_chapters INTEGER[] DEFAULT '{}',
  display_order INTEGER DEFAULT 0,
  UNIQUE(arc_id, label)
);

CREATE INDEX idx_history_arc_statistics_arc ON history_arc_statistics(arc_id);

ALTER TABLE history_arc_statistics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "history_arc_statistics_public_read" ON history_arc_statistics FOR SELECT USING (true);
CREATE POLICY "history_arc_statistics_service_insert" ON history_arc_statistics FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "history_arc_statistics_service_update" ON history_arc_statistics FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "history_arc_statistics_service_delete" ON history_arc_statistics FOR DELETE USING (auth.role() = 'service_role');
