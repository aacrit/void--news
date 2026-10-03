-- void --revolt: Comparative anatomy of revolutions (past + active)
-- Sibling of void --history (039). Public read, service_role write for all tables.
-- Design law: every axis the Comparison Lab or success scorecard sorts/filters on
-- is a typed scalar column; rich/repeating narrative is JSONB, so one `select *`
-- streams the whole comparison plane to the static client.

-- ============================================================
-- 1. revolt_events — the comparative revolution record
-- ============================================================
CREATE TABLE revolt_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  subtitle TEXT,

  -- ── Time / classification (scalars) ──
  date_display TEXT NOT NULL,
  date_start INTEGER NOT NULL,          -- start year (negative for BCE)
  date_end INTEGER,                     -- end year; NULL while active/watchlist/dormant
  date_precision TEXT NOT NULL DEFAULT 'year'
    CHECK (date_precision IN ('day', 'month', 'year', 'decade', 'century')),
  era TEXT NOT NULL
    CHECK (era IN (
      'classical', 'atlantic', 'springtime', 'modern-nationalist',
      'anticolonial', 'people-power', 'color-revolutions', 'square-revolutions'
    )),
  -- Region reuses void --history's 10-value taxonomy verbatim
  region TEXT NOT NULL
    CHECK (region IN (
      'africa', 'americas', 'east-asia', 'south-asia', 'southeast-asia',
      'middle-east', 'europe', 'oceania', 'central-asia', 'global'
    )),
  country TEXT,
  revolt_type TEXT NOT NULL
    CHECK (revolt_type IN (
      'social', 'political', 'anticolonial', 'nationalist-secessionist',
      'democratic-uprising', 'communist', 'religious-theocratic',
      'peasant-agrarian', 'coup-from-above', 'velvet-negotiated'
    )),
  status TEXT NOT NULL DEFAULT 'concluded'
    CHECK (status IN ('concluded', 'active', 'consolidating', 'dormant', 'watchlist')),

  -- ── Narrative ──
  summary TEXT NOT NULL,
  significance TEXT NOT NULL,
  analytical_outlook TEXT,              -- active/watchlist only; neutral read of the record

  -- ── Preconditions (three distinct roles) ──
  grievances JSONB DEFAULT '[]'::jsonb,          -- [{kind, intensity 0-100, evidence}]
  structural_pressures JSONB DEFAULT '{}'::jsonb, -- 6-axis {axis:{score 0-3, note}}
  structural_indicators JSONB DEFAULT '{}'::jsonb,-- World Bank numbers (enrichment-filled)
  fiscal_crisis BOOLEAN,               -- denorm filter flags
  elite_fracture BOOLEAN,
  youth_bulge BOOLEAN,
  repression_level TEXT
    CHECK (repression_level IN ('none', 'low', 'moderate', 'high', 'severe')),
  external_shock TEXT,

  -- ── Actors + repertoire ──
  actors JSONB DEFAULT '[]'::jsonb,    -- [{actor_type, name, description, role_in_arc, defected}]
  tactics JSONB DEFAULT '[]'::jsonb,   -- [{tactic_type, description, prominence}]
  resistance_type TEXT
    CHECK (resistance_type IN ('nonviolent', 'armed', 'hybrid')),

  -- ── Arc ──
  phases JSONB DEFAULT '[]'::jsonb,    -- [{phase, label, date_start, t_start, t_end, intensity, reached, summary, key_events}]
  ate_its_children BOOLEAN,

  -- ── Outcome / scorecard (all denormalized for the Lab) ──
  outcome TEXT
    CHECK (outcome IN (
      'independence', 'consolidated-democracy', 'consolidated-autocracy',
      'restored-old-regime', 'failed-suppressed', 'civil-war',
      'ongoing-unresolved', 'intra-regime-purge', 'secession-partition'
    )),
  peak_participation_pct NUMERIC(5, 2),
  peak_participation_display TEXT,
  crossed_participation_threshold BOOLEAN,   -- Chenoweth ~3.5%
  military_defection TEXT
    CHECK (military_defection IN ('none', 'partial', 'full', 'unknown')),
  foreign_intervention TEXT
    CHECK (foreign_intervention IN ('none', 'diplomatic', 'material', 'direct-military', 'unknown')),
  duration_days INTEGER,               -- NULL if ongoing
  death_toll TEXT,
  death_toll_low BIGINT,
  death_toll_high BIGINT,
  regime_before TEXT
    CHECK (regime_before IN ('monarchy', 'personalist', 'military', 'one-party', 'colonial', 'theocracy', 'democracy', 'other')),
  regime_after TEXT
    CHECK (regime_after IN ('monarchy', 'personalist', 'military', 'one-party', 'colonial', 'theocracy', 'democracy', 'other', 'unresolved')),
  democratization_delta INTEGER
    CHECK (democratization_delta BETWEEN -3 AND 3),  -- curated; NULL for active
  success_factors JSONB DEFAULT '[]'::jsonb, -- [{factor_key,label,framework,status,direction,base_rate,rationale,sources,as_of,confidence}]

  -- ── Supporting / geo / media (mirror history) ──
  key_figures JSONB DEFAULT '[]'::jsonb,
  legacy_points JSONB DEFAULT '[]'::jsonb,
  primary_source_excerpts JSONB DEFAULT '[]'::jsonb,
  coordinates JSONB,
  hero_image_url TEXT,
  hero_image_attribution TEXT,
  map_image_url TEXT,
  audio_url TEXT,
  audio_duration_seconds NUMERIC,

  -- ── Cross-links / live ──
  related_revolt_slugs TEXT[] DEFAULT '{}',
  related_history_slugs TEXT[] DEFAULT '{}',  -- cross-link into void --history
  live_query JSONB,                    -- {keywords,entities,exclude,require_all,category_hint,min_importance}

  -- ── Freshness / confidence (active portal integrity) ──
  analysis_reviewed_at DATE,
  prediction_confidence TEXT
    CHECK (prediction_confidence IN ('high', 'medium', 'low', 'n/a')),

  -- ── Housekeeping ──
  display_order INTEGER DEFAULT 0,
  is_published BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  -- A concluded/consolidating revolution must carry an end year.
  CONSTRAINT revolt_end_year_required
    CHECK (status IN ('active', 'watchlist', 'dormant') OR date_end IS NOT NULL)
);

CREATE INDEX idx_revolt_events_slug ON revolt_events(slug);
CREATE INDEX idx_revolt_events_era ON revolt_events(era);
CREATE INDEX idx_revolt_events_region ON revolt_events(region);
CREATE INDEX idx_revolt_events_type ON revolt_events(revolt_type);
CREATE INDEX idx_revolt_events_status ON revolt_events(status);
CREATE INDEX idx_revolt_events_outcome ON revolt_events(outcome);
CREATE INDEX idx_revolt_events_date_start ON revolt_events(date_start);
CREATE INDEX idx_revolt_events_published ON revolt_events(is_published);
CREATE INDEX idx_revolt_events_active ON revolt_events(status) WHERE status = 'active';

CREATE TRIGGER set_revolt_events_updated_at
  BEFORE UPDATE ON revolt_events
  FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

ALTER TABLE revolt_events ENABLE ROW LEVEL SECURITY;
CREATE POLICY "revolt_events_public_read" ON revolt_events FOR SELECT USING (true);
CREATE POLICY "revolt_events_service_insert" ON revolt_events FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "revolt_events_service_update" ON revolt_events FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "revolt_events_service_delete" ON revolt_events FOR DELETE USING (auth.role() = 'service_role');

-- ============================================================
-- 2. revolt_perspectives — short analytical viewpoints per revolution
-- ============================================================
CREATE TABLE revolt_perspectives (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  revolt_id UUID NOT NULL REFERENCES revolt_events(id) ON DELETE CASCADE,
  viewpoint TEXT NOT NULL,
  viewpoint_type TEXT NOT NULL
    CHECK (viewpoint_type IN (
      'revolutionary', 'movement', 'regime', 'counter-revolutionary',
      'moderate', 'radical', 'military', 'academic', 'diaspora', 'indigenous'
    )),
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

CREATE INDEX idx_revolt_perspectives_revolt ON revolt_perspectives(revolt_id);
CREATE INDEX idx_revolt_perspectives_type ON revolt_perspectives(viewpoint_type);

ALTER TABLE revolt_perspectives ENABLE ROW LEVEL SECURITY;
CREATE POLICY "revolt_perspectives_public_read" ON revolt_perspectives FOR SELECT USING (true);
CREATE POLICY "revolt_perspectives_service_insert" ON revolt_perspectives FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "revolt_perspectives_service_update" ON revolt_perspectives FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "revolt_perspectives_service_delete" ON revolt_perspectives FOR DELETE USING (auth.role() = 'service_role');

-- ============================================================
-- 3. revolt_media — images, maps, posters per revolution
--    (media_type / license CHECKs widened vs history 039, grounded in real YAML)
-- ============================================================
CREATE TABLE revolt_media (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  revolt_id UUID NOT NULL REFERENCES revolt_events(id) ON DELETE CASCADE,
  media_type TEXT NOT NULL
    CHECK (media_type IN (
      'image', 'photograph', 'painting', 'artwork', 'map', 'document',
      'video', 'poster', 'infographic', 'chart', 'footage'
    )),
  title TEXT NOT NULL,
  description TEXT,
  source_url TEXT NOT NULL,
  thumbnail_url TEXT,
  attribution TEXT NOT NULL,
  license TEXT DEFAULT 'public-domain'
    CHECK (license IN (
      'public-domain', 'cc0', 'cc-by', 'cc-by-sa', 'fair-use',
      'unsplash-license', 'pexels-license'
    )),
  creator TEXT,
  creation_date TEXT,
  display_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_revolt_media_revolt ON revolt_media(revolt_id);
CREATE INDEX idx_revolt_media_type ON revolt_media(media_type);

ALTER TABLE revolt_media ENABLE ROW LEVEL SECURITY;
CREATE POLICY "revolt_media_public_read" ON revolt_media FOR SELECT USING (true);
CREATE POLICY "revolt_media_service_insert" ON revolt_media FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "revolt_media_service_update" ON revolt_media FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "revolt_media_service_delete" ON revolt_media FOR DELETE USING (auth.role() = 'service_role');

-- ============================================================
-- 4. revolt_connections — how revolutions influenced one another
-- ============================================================
CREATE TABLE revolt_connections (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  revolt_a_id UUID NOT NULL REFERENCES revolt_events(id) ON DELETE CASCADE,
  revolt_b_id UUID NOT NULL REFERENCES revolt_events(id) ON DELETE CASCADE,
  connection_type TEXT NOT NULL
    CHECK (connection_type IN (
      'inspired', 'provided-model', 'triggered-contagion', 'provoked-backlash',
      'shared-repertoire', 'parallel', 'counter-example'
    )),
  description TEXT,
  UNIQUE(revolt_a_id, revolt_b_id)
);

CREATE INDEX idx_revolt_connections_a ON revolt_connections(revolt_a_id);
CREATE INDEX idx_revolt_connections_b ON revolt_connections(revolt_b_id);

ALTER TABLE revolt_connections ENABLE ROW LEVEL SECURITY;
CREATE POLICY "revolt_connections_public_read" ON revolt_connections FOR SELECT USING (true);
CREATE POLICY "revolt_connections_service_insert" ON revolt_connections FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "revolt_connections_service_update" ON revolt_connections FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "revolt_connections_service_delete" ON revolt_connections FOR DELETE USING (auth.role() = 'service_role');

-- ============================================================
-- 5. revolt_metrics — tall/extensible cross-revolution axes
--    (analog of history_arc_statistics.data_points; lets the Comparison Lab
--     add a new comparison axis with zero schema change)
-- ============================================================
CREATE TABLE revolt_metrics (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  revolt_id UUID NOT NULL REFERENCES revolt_events(id) ON DELETE CASCADE,
  metric_key TEXT NOT NULL,
  label TEXT NOT NULL,
  category TEXT NOT NULL DEFAULT 'process'
    CHECK (category IN ('precondition', 'process', 'outcome')),
  unit TEXT,
  numeric_value NUMERIC,
  display_value TEXT,
  framework TEXT,
  source TEXT,
  source_url TEXT,
  data_points JSONB DEFAULT '[]'::jsonb,   -- [{t/year, value, label?}]
  display_order INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  UNIQUE(revolt_id, metric_key)
);

CREATE INDEX idx_revolt_metrics_revolt ON revolt_metrics(revolt_id);

ALTER TABLE revolt_metrics ENABLE ROW LEVEL SECURITY;
CREATE POLICY "revolt_metrics_public_read" ON revolt_metrics FOR SELECT USING (true);
CREATE POLICY "revolt_metrics_service_insert" ON revolt_metrics FOR INSERT WITH CHECK (auth.role() = 'service_role');
CREATE POLICY "revolt_metrics_service_update" ON revolt_metrics FOR UPDATE USING (auth.role() = 'service_role');
CREATE POLICY "revolt_metrics_service_delete" ON revolt_metrics FOR DELETE USING (auth.role() = 'service_role');
