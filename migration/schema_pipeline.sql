-- ============================================================================
-- schema_pipeline.sql — Void News SQLite working DB (pipeline + frontend reads)
-- ============================================================================
-- Consolidated from Supabase Postgres migrations 001-079 (the full set present
-- in supabase/migrations/, including both files numbered 053: 053_ig_engagement
-- and 053_is_international). Each ALTER / DROP / RENAME was applied in order so
-- the definitions below are the CURRENT effective schema, not per-migration
-- deltas.
--
-- This file holds every table the Python pipeline reads/writes AND every table
-- the static frontend reads (the content / read side). The live user-WRITE
-- tables (ship_requests, ship_votes, ship_replies) live in schema_d1.sql and
-- are intentionally NOT duplicated here.
--
-- Postgres -> SQLite translation applied throughout:
--   uuid                -> TEXT                (app-generated string UUIDs)
--   timestamptz / date  -> TEXT (ISO-8601);  DEFAULT now() -> CURRENT_TIMESTAMP
--   jsonb / json        -> TEXT               (parse app-side; JSON1 can query)
--   boolean             -> INTEGER (0/1);     DEFAULT true/false -> 1/0
--   text[] / arrays     -> TEXT               (stored as JSON array string)
--   smallint/int/bigint -> INTEGER
--   numeric/real/double -> REAL
--   varchar(n)          -> TEXT (length CHECKs rewritten char_length -> length)
--   tsvector (generated)-> DROPPED (see printed_stories; use SQLite FTS5 instead)
--   GIN/GiST indexes    -> DROPPED (no SQLite equivalent)
--
-- Dropped, RLS policies, RPC/functions, triggers, views, extensions, GRANTs are
-- catalogued in PORT_NOTES.md. Foreign keys are preserved; enable them at
-- connection time with:  PRAGMA foreign_keys = ON;
-- ============================================================================

-- ─────────────────────────────────────────────────────────────────────────
-- sources        (001; lean CHECK 007/015/078/079; health cols 051)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS sources (
  id                          TEXT PRIMARY KEY,
  slug                        TEXT UNIQUE NOT NULL,
  name                        TEXT NOT NULL,
  url                         TEXT NOT NULL,
  rss_url                     TEXT,
  scrape_config               TEXT DEFAULT '{}',
  tier                        TEXT NOT NULL CHECK (tier IN ('us_major', 'international', 'independent')),
  country                     TEXT NOT NULL,
  type                        TEXT NOT NULL,
  political_lean_baseline     TEXT CHECK (political_lean_baseline IN (
                                'far-left', 'left', 'center-left', 'center',
                                'center-right', 'right', 'far-right', 'varies', 'unrated')),
  credibility_notes           TEXT,
  is_active                   INTEGER DEFAULT 1,
  created_at                  TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at                  TEXT DEFAULT CURRENT_TIMESTAMP,
  consecutive_fetch_failures  INTEGER NOT NULL DEFAULT 0,   -- 051
  last_fetch_at               TEXT,                          -- 051
  last_fetch_status           TEXT                           -- 051: ok|timeout|http_4xx|http_5xx|parse_error|other
);
CREATE INDEX IF NOT EXISTS idx_sources_consecutive_fetch_failures
  ON sources (consecutive_fetch_failures DESC) WHERE consecutive_fetch_failures > 0;

-- ─────────────────────────────────────────────────────────────────────────
-- articles       (001; section NOT NULL/default 003; updated_at 005;
--                 section CHECK 036; wire fields 055)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS articles (
  id                        TEXT PRIMARY KEY,
  source_id                 TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  url                       TEXT UNIQUE NOT NULL,
  title                     TEXT NOT NULL,
  summary                   TEXT,
  full_text                 TEXT,
  author                    TEXT,
  published_at              TEXT,
  fetched_at                TEXT DEFAULT CURRENT_TIMESTAMP,
  section                   TEXT NOT NULL DEFAULT 'world'
                              CHECK (section IN ('world', 'us', 'europe', 'south-asia')),
  image_url                 TEXT,
  word_count                INTEGER,
  created_at                TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at                TEXT DEFAULT CURRENT_TIMESTAMP,   -- 005
  is_wire_copy              INTEGER NOT NULL DEFAULT 0,        -- 055
  wire_origin_publisher_id  TEXT                               -- 055
);
CREATE INDEX IF NOT EXISTS idx_articles_source     ON articles(source_id);
CREATE INDEX IF NOT EXISTS idx_articles_published  ON articles(published_at DESC);
CREATE INDEX IF NOT EXISTS idx_articles_wire_origin
  ON articles (wire_origin_publisher_id) WHERE wire_origin_publisher_id IS NOT NULL;
-- NOTE idx_articles_section dropped in migration 004.

-- ─────────────────────────────────────────────────────────────────────────
-- bias_scores    (001; confidence CHECK 003; rationale 004; lean_unscored 078)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS bias_scores (
  id             TEXT PRIMARY KEY,
  article_id     TEXT UNIQUE NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  political_lean INTEGER CHECK (political_lean BETWEEN 0 AND 100),
  sensationalism INTEGER CHECK (sensationalism BETWEEN 0 AND 100),
  opinion_fact   INTEGER CHECK (opinion_fact BETWEEN 0 AND 100),
  factual_rigor  INTEGER CHECK (factual_rigor BETWEEN 0 AND 100),
  framing        INTEGER CHECK (framing BETWEEN 0 AND 100),
  confidence     REAL DEFAULT 0.5 CHECK (confidence BETWEEN 0.0 AND 1.0),
  analyzed_at    TEXT DEFAULT CURRENT_TIMESTAMP,
  rationale      TEXT DEFAULT '{}',                 -- 004 (JSON)
  lean_unscored  INTEGER NOT NULL DEFAULT 0         -- 078
);
CREATE INDEX IF NOT EXISTS idx_bias_scores_article ON bias_scores(article_id);
CREATE INDEX IF NOT EXISTS idx_bias_scores_measured_lean
  ON bias_scores (article_id) WHERE lean_unscored = 0;  -- 078

-- ─────────────────────────────────────────────────────────────────────────
-- story_clusters (001; +002 004 008 011 013 023 026 041 044 049 053 054 056
--                 059 077; per-edition rank cols dropped by 061; section
--                 CHECK 036; summary_tier CHECK 049/062/063/071)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS story_clusters (
  id                           TEXT PRIMARY KEY,
  title                        TEXT NOT NULL,
  summary                      TEXT,
  consensus_points             TEXT DEFAULT '[]',
  divergence_points            TEXT DEFAULT '[]',
  category                     TEXT,
  section                      TEXT CHECK (section IN ('world', 'us', 'europe', 'south-asia')),
  importance_score             REAL DEFAULT 0,
  source_count                 INTEGER DEFAULT 0,
  first_published              TEXT,
  last_updated                 TEXT DEFAULT CURRENT_TIMESTAMP,
  created_at                   TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at                   TEXT DEFAULT CURRENT_TIMESTAMP,   -- 005
  -- 002 bias enrichment / ranking
  divergence_score             REAL DEFAULT 0,
  bias_diversity               TEXT DEFAULT '{}',                -- JSON
  headline_rank                REAL DEFAULT 0,
  coverage_velocity            INTEGER DEFAULT 0,
  -- 008 facts vs opinion
  content_type                 TEXT DEFAULT 'reporting' CHECK (content_type IN ('reporting', 'opinion')),
  -- 011 multi-section (JSON array string; default ["world"])
  sections                     TEXT DEFAULT '["world"]',
  -- 013 editorial intelligence
  editorial_importance         INTEGER,
  story_type                   TEXT,
  has_binding_consequences     INTEGER,                          -- boolean, nullable
  -- 023 top-story denormalization
  is_top_story                 INTEGER DEFAULT 0,
  live_update_count            INTEGER DEFAULT 0,
  last_live_update_at          TEXT,
  story_memory_id              TEXT REFERENCES story_memory(id) ON DELETE SET NULL,   -- 023 + FK 029
  -- 026 per-feed rank (rank_us/rank_europe/rank_south_asia DROPPED by 061)
  rank_world                   REAL DEFAULT 0,
  -- 041 claim consensus
  claim_consensus              TEXT,                             -- JSON
  -- 044 cached cover image (cacher retired 2026-08-05; column kept)
  cached_image_url             TEXT,
  cached_image_attribution     TEXT,
  -- 049 summary cache
  summary_article_hash         TEXT,
  summary_tier                 TEXT CHECK (summary_tier IN ('sonnet', 'flash', 'flash-lite', 'rule_based')),
  -- 053 world-overflow flag
  is_international             INTEGER NOT NULL DEFAULT 0,
  -- 054 / 056 mega-cluster cap
  mega_cluster_capped          INTEGER NOT NULL DEFAULT 0,
  mega_cluster_original_count  INTEGER,
  -- 059 headline signal
  is_headline                  INTEGER NOT NULL DEFAULT 0,
  headline_confidence          INTEGER,
  -- 077 disaster severity
  disaster_severity            REAL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_clusters_headline_rank        ON story_clusters(headline_rank DESC);
CREATE INDEX IF NOT EXISTS idx_clusters_section_headline_rank ON story_clusters(section, headline_rank DESC);
CREATE INDEX IF NOT EXISTS idx_clusters_divergence_score     ON story_clusters(divergence_score DESC);
CREATE INDEX IF NOT EXISTS idx_clusters_content_type         ON story_clusters(content_type);
CREATE INDEX IF NOT EXISTS idx_clusters_section_content_type ON story_clusters(section, content_type, headline_rank DESC);
CREATE INDEX IF NOT EXISTS idx_story_clusters_editorial_importance ON story_clusters(editorial_importance DESC);
CREATE INDEX IF NOT EXISTS idx_story_clusters_story_type     ON story_clusters(story_type);
CREATE INDEX IF NOT EXISTS idx_clusters_top_story            ON story_clusters(is_top_story) WHERE is_top_story = 1;
CREATE INDEX IF NOT EXISTS idx_clusters_rank_world           ON story_clusters(rank_world DESC);
CREATE INDEX IF NOT EXISTS idx_clusters_summary_hash         ON story_clusters(summary_article_hash);
CREATE INDEX IF NOT EXISTS idx_clusters_is_international      ON story_clusters(headline_rank DESC) WHERE is_international = 1;
CREATE INDEX IF NOT EXISTS idx_story_clusters_mega_capped    ON story_clusters(mega_cluster_capped) WHERE mega_cluster_capped = 1;
CREATE INDEX IF NOT EXISTS idx_story_clusters_mega_original_count
  ON story_clusters(mega_cluster_original_count DESC) WHERE mega_cluster_original_count IS NOT NULL;
CREATE INDEX IF NOT EXISTS story_clusters_is_headline_idx
  ON story_clusters(is_headline, rank_world DESC) WHERE is_headline = 1;
-- DROPPED (GIN): idx_clusters_sections_gin (011). See PORT_NOTES.md.

-- ─────────────────────────────────────────────────────────────────────────
-- cluster_articles  (001; article_id + cluster_id CASCADE 046/047)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cluster_articles (
  cluster_id TEXT NOT NULL REFERENCES story_clusters(id) ON DELETE CASCADE,
  article_id TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  PRIMARY KEY (cluster_id, article_id)
);
CREATE INDEX IF NOT EXISTS idx_cluster_articles_cluster ON cluster_articles(cluster_id);
CREATE INDEX IF NOT EXISTS idx_cluster_articles_article ON cluster_articles(article_id);

-- ─────────────────────────────────────────────────────────────────────────
-- categories / article_categories  (001)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS categories (
  id   TEXT PRIMARY KEY,
  name TEXT UNIQUE NOT NULL,
  slug TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS article_categories (
  article_id  TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  category_id TEXT NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  PRIMARY KEY (article_id, category_id)
);

-- Seed categories (001). Slugs match auto_categorize.py; names match types.ts.
-- id is app-generated; use INSERT OR IGNORE keyed on the unique slug.
INSERT OR IGNORE INTO categories (id, name, slug) VALUES
  ('cat-politics',    'Politics',    'politics'),
  ('cat-economy',     'Economy',     'economy'),
  ('cat-technology',  'Tech',        'technology'),
  ('cat-health',      'Health',      'health'),
  ('cat-environment', 'Environment', 'environment'),
  ('cat-conflict',    'Conflict',    'conflict'),
  ('cat-science',     'Science',     'science'),
  ('cat-culture',     'Culture',     'culture'),
  ('cat-sports',      'Sports',      'sports');

-- ─────────────────────────────────────────────────────────────────────────
-- pipeline_runs  (001; llm_metrics 049)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS pipeline_runs (
  id                TEXT PRIMARY KEY,
  started_at        TEXT DEFAULT CURRENT_TIMESTAMP,
  completed_at      TEXT,
  status            TEXT DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed')),
  articles_fetched  INTEGER DEFAULT 0,
  articles_analyzed INTEGER DEFAULT 0,
  clusters_created  INTEGER DEFAULT 0,
  errors            TEXT DEFAULT '[]',    -- JSON
  duration_seconds  REAL,
  llm_metrics       TEXT                  -- 049 (JSON)
);
CREATE INDEX IF NOT EXISTS idx_pipeline_runs_completed
  ON pipeline_runs(status, completed_at DESC) WHERE status = 'completed';

-- ─────────────────────────────────────────────────────────────────────────
-- source_topic_lean  (006) — Axis 6 per-topic per-outlet tracking
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS source_topic_lean (
  id                 TEXT PRIMARY KEY,
  source_id          TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  category           TEXT NOT NULL,
  avg_lean           REAL NOT NULL DEFAULT 50.0,
  avg_sensationalism REAL NOT NULL DEFAULT 50.0,
  avg_opinion        REAL NOT NULL DEFAULT 50.0,
  article_count      INTEGER NOT NULL DEFAULT 0,
  last_updated       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(source_id, category)
);
CREATE INDEX IF NOT EXISTS idx_source_topic_lean_source   ON source_topic_lean(source_id);
CREATE INDEX IF NOT EXISTS idx_source_topic_lean_category ON source_topic_lean(category);

-- ─────────────────────────────────────────────────────────────────────────
-- cluster_archive  (016; rank cols 026 — 061 dropped these ONLY on
--                   story_clusters, not here, so they remain)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cluster_archive (
  id                TEXT PRIMARY KEY,
  title             TEXT,
  summary           TEXT,
  section           TEXT DEFAULT 'world',
  sections          TEXT,                 -- JSON array string
  category          TEXT,
  source_count      INTEGER DEFAULT 1,
  first_published   TEXT,
  headline_rank     REAL DEFAULT 0,
  divergence_score  REAL DEFAULT 0,
  bias_diversity    TEXT,                 -- JSON
  consensus_points  TEXT,                 -- JSON
  divergence_points TEXT,                 -- JSON
  archived_at       TEXT DEFAULT CURRENT_TIMESTAMP,
  rank_world        REAL DEFAULT 0,       -- 026
  rank_us           REAL DEFAULT 0,       -- 026
  rank_india        REAL DEFAULT 0        -- 026
);
CREATE INDEX IF NOT EXISTS idx_cluster_archive_published ON cluster_archive(first_published DESC);
-- DROPPED (GIN): idx_cluster_archive_section on sections (016). See PORT_NOTES.md.

-- ─────────────────────────────────────────────────────────────────────────
-- story_memory  (022; rank 025)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS story_memory (
  id                   TEXT PRIMARY KEY,
  cluster_id           TEXT NOT NULL REFERENCES story_clusters(id) ON DELETE CASCADE,
  headline             TEXT NOT NULL,
  category             TEXT,
  source_slugs         TEXT NOT NULL DEFAULT '[]',   -- JSON array string
  source_count         INTEGER NOT NULL DEFAULT 0,
  is_top_story         INTEGER NOT NULL DEFAULT 0,
  is_active            INTEGER NOT NULL DEFAULT 1,
  last_polled_at       TEXT,
  last_live_update_at  TEXT,
  live_update_count    INTEGER NOT NULL DEFAULT 0,
  activated_at         TEXT DEFAULT CURRENT_TIMESTAMP,
  deactivated_at       TEXT,
  pipeline_run_id      TEXT,
  created_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  rank                 INTEGER DEFAULT 1             -- 025
);
CREATE INDEX IF NOT EXISTS idx_story_memory_cluster ON story_memory(cluster_id);
CREATE INDEX IF NOT EXISTS idx_story_memory_active  ON story_memory(is_active) WHERE is_active = 1;
-- One active story per rank position (025). Partial UNIQUE index.
CREATE UNIQUE INDEX IF NOT EXISTS idx_story_memory_active_rank
  ON story_memory(rank) WHERE is_active = 1;

-- ─────────────────────────────────────────────────────────────────────────
-- live_updates  (022)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS live_updates (
  id                     TEXT PRIMARY KEY,
  story_memory_id        TEXT NOT NULL REFERENCES story_memory(id) ON DELETE CASCADE,
  article_url            TEXT NOT NULL,
  title                  TEXT NOT NULL,
  summary                TEXT,
  source_slug            TEXT NOT NULL,
  source_name            TEXT NOT NULL,
  published_at           TEXT,
  update_summary         TEXT,
  summarized_at          TEXT,
  discovered_at          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  merged_into_cluster_id TEXT REFERENCES story_clusters(id) ON DELETE SET NULL,
  created_at             TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_live_updates_url_story ON live_updates(story_memory_id, article_url);
CREATE INDEX IF NOT EXISTS idx_live_updates_memory     ON live_updates(story_memory_id);
CREATE INDEX IF NOT EXISTS idx_live_updates_discovered ON live_updates(discovered_at DESC);

-- ─────────────────────────────────────────────────────────────────────────
-- daily_briefs  (017; +019 020 021 023-adjacent 024 027 028 030;
--                edition CHECK 036)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS daily_briefs (
  id                     TEXT PRIMARY KEY,
  edition                TEXT NOT NULL CHECK (edition IN ('world', 'us', 'europe', 'south-asia')),
  pipeline_run_id        TEXT REFERENCES pipeline_runs(id) ON DELETE SET NULL,
  tldr_text              TEXT NOT NULL,
  audio_script           TEXT,
  audio_url              TEXT,
  audio_duration_seconds REAL,
  audio_voice            TEXT,
  audio_voice_label      TEXT,
  audio_file_size        INTEGER,
  top_cluster_ids        TEXT,                 -- 017 (JSON array of UUID strings)
  created_at             TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at             TEXT DEFAULT CURRENT_TIMESTAMP,
  opinion_text           TEXT,                 -- 019
  opinion_cluster_id     TEXT REFERENCES story_clusters(id) ON DELETE SET NULL,  -- 020 + FK 029
  opinion_lean           TEXT CHECK (opinion_lean IS NULL OR opinion_lean IN ('left', 'center', 'right')),  -- 020
  opinion_audio_script   TEXT,                 -- 021
  opinion_headline       TEXT,                 -- 024
  tldr_headline          TEXT,                 -- 027
  opinion_start_seconds  REAL,                 -- 028
  generator              TEXT                  -- 030
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_briefs_edition_run     ON daily_briefs(edition, pipeline_run_id);
CREATE INDEX IF NOT EXISTS        idx_daily_briefs_edition_created ON daily_briefs(edition, created_at DESC);

-- ─────────────────────────────────────────────────────────────────────────
-- weekly_digests  (034; +035 040 064 065)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS weekly_digests (
  id                        TEXT PRIMARY KEY,
  edition                   TEXT NOT NULL,
  week_start                TEXT NOT NULL,   -- DATE
  week_end                  TEXT NOT NULL,   -- DATE
  issue_number              INTEGER,
  cover_headline            TEXT NOT NULL,
  cover_text                TEXT NOT NULL,
  cover_cluster_ids         TEXT,            -- JSON array of UUID strings
  cover_numbers             TEXT,            -- JSON
  recap_stories             TEXT NOT NULL DEFAULT '[]',   -- JSON
  opinion_left              TEXT,
  opinion_center            TEXT,
  opinion_right             TEXT,
  opinion_headlines         TEXT,            -- JSON
  opinion_topic             TEXT,
  bias_report_text          TEXT,
  bias_report_data          TEXT,            -- JSON
  audio_script              TEXT,
  audio_url                 TEXT,
  audio_duration_seconds    REAL,
  audio_file_size           INTEGER,
  total_articles            INTEGER,
  total_clusters            INTEGER,
  total_sources_active      INTEGER,
  generator                 TEXT,
  gemini_calls_used         INTEGER,
  generation_duration_seconds REAL,
  created_at                TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at                TEXT DEFAULT CURRENT_TIMESTAMP,
  cover_timelines           TEXT DEFAULT '[]',   -- 035 (JSON)
  cover_image_url           TEXT,                -- 040
  cover_image_attribution   TEXT,                -- 040
  cover_image_source        TEXT,                -- 040
  -- 064 weekly editorial opinion (distinct from the three-lens Perspectives)
  opinion_text              TEXT,
  opinion_headline          TEXT,
  opinion_lean              TEXT CHECK (opinion_lean IS NULL OR opinion_lean IN ('left', 'center', 'right')),
  opinion_audio_script      TEXT,
  opinion_start_seconds     REAL,
  audio_voice               TEXT,
  audio_voice_label         TEXT,
  -- 065 editor's note
  editor_note               TEXT,
  UNIQUE(edition, week_start)
);
CREATE INDEX IF NOT EXISTS idx_weekly_digests_edition_created ON weekly_digests(edition, created_at DESC);

-- ─────────────────────────────────────────────────────────────────────────
-- article_claims / source_claim_accuracy  (041; RLS added 062)
-- ─────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS article_claims (
  id                     TEXT PRIMARY KEY,
  article_id             TEXT NOT NULL REFERENCES articles(id) ON DELETE CASCADE,
  cluster_id             TEXT REFERENCES story_clusters(id) ON DELETE SET NULL,
  claim_text             TEXT NOT NULL,
  source_sentence        TEXT,
  subject_entity         TEXT,
  subject_entity_type    TEXT,
  claim_type             TEXT DEFAULT 'statement'
                           CHECK (claim_type IN ('quantitative', 'attribution', 'event', 'statement')),
  has_quantitative       INTEGER DEFAULT 0,
  status                 TEXT DEFAULT 'unverified'
                           CHECK (status IN ('unverified','corroborated','single_source',
                                             'disputed','later_corroborated','later_contradicted')),
  corroboration_count    INTEGER DEFAULT 0,
  corroborating_sources  TEXT DEFAULT '[]',   -- JSON array string
  contradiction_type     TEXT CHECK (contradiction_type IN ('negation','numeric','entity_swap')
                                     OR contradiction_type IS NULL),
  contradicting_claim_id TEXT REFERENCES article_claims(id),
  created_at             TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at             TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_claims_cluster ON article_claims(cluster_id);
CREATE INDEX IF NOT EXISTS idx_claims_article ON article_claims(article_id);
CREATE INDEX IF NOT EXISTS idx_claims_status  ON article_claims(status);
CREATE INDEX IF NOT EXISTS idx_claims_entity  ON article_claims(subject_entity) WHERE subject_entity IS NOT NULL;

CREATE TABLE IF NOT EXISTS source_claim_accuracy (
  id                  TEXT PRIMARY KEY,
  source_slug         TEXT NOT NULL UNIQUE,
  source_name         TEXT,
  total_unique_claims INTEGER DEFAULT 0,
  later_corroborated  INTEGER DEFAULT 0,
  later_contradicted  INTEGER DEFAULT 0,
  still_unverified    INTEGER DEFAULT 0,
  accuracy_rate       REAL DEFAULT 0.0,
  trend               TEXT DEFAULT 'stable' CHECK (trend IN ('improving', 'stable', 'declining')),
  accuracy_30d        REAL,
  accuracy_90d        REAL,
  updated_at          TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_accuracy_slug ON source_claim_accuracy(source_slug);
CREATE INDEX IF NOT EXISTS idx_accuracy_rate ON source_claim_accuracy(accuracy_rate);

-- ═════════════════════════════════════════════════════════════════════════
-- void --history  (039; media constraints 043; audio 045; media dims 072)
-- ═════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS history_events (
  id                      TEXT PRIMARY KEY,
  slug                    TEXT UNIQUE NOT NULL,
  title                   TEXT NOT NULL,
  subtitle                TEXT,
  date_display            TEXT NOT NULL,
  date_sort               INTEGER NOT NULL,
  date_precision          TEXT NOT NULL DEFAULT 'year'
                            CHECK (date_precision IN ('day', 'month', 'year', 'decade', 'century')),
  era                     TEXT NOT NULL
                            CHECK (era IN ('ancient','classical','medieval','early-modern','modern','contemporary')),
  region                  TEXT NOT NULL
                            CHECK (region IN ('africa','americas','east-asia','south-asia','southeast-asia',
                                              'middle-east','europe','oceania','central-asia','global')),
  country                 TEXT,
  category                TEXT NOT NULL
                            CHECK (category IN ('war','revolution','empire','independence','genocide',
                                                'disaster','cultural','scientific','economic','political')),
  severity                TEXT NOT NULL DEFAULT 'critical'
                            CHECK (severity IN ('catastrophic', 'critical', 'major')),
  summary                 TEXT NOT NULL,
  significance            TEXT NOT NULL,
  death_toll              TEXT,
  affected_population     TEXT,
  duration                TEXT,
  key_figures             TEXT DEFAULT '[]',   -- JSON
  legacy_points           TEXT DEFAULT '[]',   -- JSON
  primary_source_excerpts TEXT DEFAULT '[]',   -- JSON
  coordinates             TEXT,                -- JSON
  hero_image_url          TEXT,
  hero_image_attribution  TEXT,
  map_image_url           TEXT,
  related_event_slugs     TEXT DEFAULT '[]',   -- JSON array string
  display_order           INTEGER DEFAULT 0,
  is_published            INTEGER DEFAULT 0,
  created_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at              TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  audio_url               TEXT,   -- 045
  audio_duration_seconds  REAL    -- 045
);
CREATE INDEX IF NOT EXISTS idx_history_events_slug      ON history_events(slug);
CREATE INDEX IF NOT EXISTS idx_history_events_era       ON history_events(era);
CREATE INDEX IF NOT EXISTS idx_history_events_region    ON history_events(region);
CREATE INDEX IF NOT EXISTS idx_history_events_category  ON history_events(category);
CREATE INDEX IF NOT EXISTS idx_history_events_date_sort ON history_events(date_sort);
CREATE INDEX IF NOT EXISTS idx_history_events_published ON history_events(is_published);

CREATE TABLE IF NOT EXISTS history_perspectives (
  id             TEXT PRIMARY KEY,
  event_id       TEXT NOT NULL REFERENCES history_events(id) ON DELETE CASCADE,
  viewpoint      TEXT NOT NULL,
  viewpoint_type TEXT NOT NULL
                   CHECK (viewpoint_type IN ('victor','vanquished','bystander','academic','revisionist','indigenous')),
  region_origin  TEXT NOT NULL,
  narrative      TEXT NOT NULL,
  key_arguments  TEXT DEFAULT '[]',
  sources        TEXT DEFAULT '[]',
  notable_quotes TEXT DEFAULT '[]',
  emphasized     TEXT DEFAULT '[]',
  omitted        TEXT DEFAULT '[]',
  display_order  INTEGER DEFAULT 0,
  created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_history_perspectives_event ON history_perspectives(event_id);
CREATE INDEX IF NOT EXISTS idx_history_perspectives_type  ON history_perspectives(viewpoint_type);

CREATE TABLE IF NOT EXISTS history_media (
  id            TEXT PRIMARY KEY,
  event_id      TEXT NOT NULL REFERENCES history_events(id) ON DELETE CASCADE,
  media_type    TEXT NOT NULL
                  CHECK (media_type IN ('image','map','video','document','painting','photograph','artwork')),  -- 043
  title         TEXT NOT NULL,
  description   TEXT,
  source_url    TEXT NOT NULL,
  thumbnail_url TEXT,
  attribution   TEXT NOT NULL,
  license       TEXT DEFAULT 'public-domain'
                  CHECK (license IN ('public-domain','cc0','cc-by','cc-by-sa','fair-use',
                                     'unsplash-license','pexels-license')),   -- 043
  creator       TEXT,
  creation_date TEXT,
  display_order INTEGER DEFAULT 0,
  created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  width         INTEGER,   -- 072
  height        INTEGER,   -- 072
  location      TEXT       -- 072
);
CREATE INDEX IF NOT EXISTS idx_history_media_event ON history_media(event_id);
CREATE INDEX IF NOT EXISTS idx_history_media_type  ON history_media(media_type);

CREATE TABLE IF NOT EXISTS history_connections (
  id              TEXT PRIMARY KEY,
  event_a_id      TEXT NOT NULL REFERENCES history_events(id) ON DELETE CASCADE,
  event_b_id      TEXT NOT NULL REFERENCES history_events(id) ON DELETE CASCADE,
  connection_type TEXT NOT NULL
                    CHECK (connection_type IN ('caused','influenced','response-to','parallel','consequence')),
  description     TEXT,
  UNIQUE(event_a_id, event_b_id)
);
CREATE INDEX IF NOT EXISTS idx_history_connections_a ON history_connections(event_a_id);
CREATE INDEX IF NOT EXISTS idx_history_connections_b ON history_connections(event_b_id);

-- void --history long-arc topics (042)
CREATE TABLE IF NOT EXISTS history_arcs (
  id                     TEXT PRIMARY KEY,
  slug                   TEXT UNIQUE NOT NULL,
  title                  TEXT NOT NULL,
  subtitle               TEXT,
  central_question       TEXT NOT NULL,
  date_range             TEXT NOT NULL,
  date_start             INTEGER NOT NULL,
  date_end               INTEGER NOT NULL,
  theme                  TEXT NOT NULL
                           CHECK (theme IN ('economic','political','social','technological',
                                            'cultural','military','environmental','philosophical')),
  regions                TEXT NOT NULL DEFAULT '[]',   -- JSON array string
  introduction           TEXT NOT NULL,
  hero_image_url         TEXT,
  hero_image_caption     TEXT,
  hero_image_attribution TEXT,
  display_order          INTEGER DEFAULT 0,
  is_published           INTEGER DEFAULT 0,
  created_at             TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at             TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_history_arcs_slug      ON history_arcs(slug);
CREATE INDEX IF NOT EXISTS idx_history_arcs_theme     ON history_arcs(theme);
CREATE INDEX IF NOT EXISTS idx_history_arcs_published ON history_arcs(is_published);

CREATE TABLE IF NOT EXISTS history_arc_perspectives (
  id              TEXT PRIMARY KEY,
  arc_id          TEXT NOT NULL REFERENCES history_arcs(id) ON DELETE CASCADE,
  slug            TEXT NOT NULL,
  name            TEXT NOT NULL,
  ideology        TEXT NOT NULL,
  color           TEXT NOT NULL DEFAULT 'a' CHECK (color IN ('a','b','c','d','e','f')),
  throughline     TEXT NOT NULL,
  key_thinkers    TEXT DEFAULT '[]',
  canonical_works TEXT DEFAULT '[]',
  display_order   INTEGER DEFAULT 0,
  UNIQUE(arc_id, slug)
);
CREATE INDEX IF NOT EXISTS idx_history_arc_perspectives_arc ON history_arc_perspectives(arc_id);

CREATE TABLE IF NOT EXISTS history_arc_chapters (
  id                    TEXT PRIMARY KEY,
  arc_id                TEXT NOT NULL REFERENCES history_arcs(id) ON DELETE CASCADE,
  chapter_number        INTEGER NOT NULL,
  title                 TEXT NOT NULL,
  subtitle              TEXT,
  date_range            TEXT NOT NULL,
  date_start            INTEGER NOT NULL,
  date_end              INTEGER NOT NULL,
  narrative             TEXT NOT NULL,
  key_moments           TEXT DEFAULT '[]',
  primary_sources       TEXT DEFAULT '[]',
  connected_event_slugs TEXT DEFAULT '[]',   -- JSON array string
  relevant_statistics   TEXT DEFAULT '[]',   -- JSON array string
  hero_image_url        TEXT,
  hero_image_caption    TEXT,
  hero_image_attribution TEXT,
  UNIQUE(arc_id, chapter_number)
);
CREATE INDEX IF NOT EXISTS idx_history_arc_chapters_arc   ON history_arc_chapters(arc_id);
CREATE INDEX IF NOT EXISTS idx_history_arc_chapters_order ON history_arc_chapters(arc_id, chapter_number);

CREATE TABLE IF NOT EXISTS history_arc_chapter_perspectives (
  id             TEXT PRIMARY KEY,
  chapter_id     TEXT NOT NULL REFERENCES history_arc_chapters(id) ON DELETE CASCADE,
  perspective_id TEXT NOT NULL REFERENCES history_arc_perspectives(id) ON DELETE CASCADE,
  narrative      TEXT NOT NULL,
  key_arguments  TEXT DEFAULT '[]',
  emphasized     TEXT DEFAULT '[]',
  omitted        TEXT DEFAULT '[]',
  sources        TEXT DEFAULT '[]',
  notable_quotes TEXT DEFAULT '[]',
  UNIQUE(chapter_id, perspective_id)
);
CREATE INDEX IF NOT EXISTS idx_arc_chap_persp_chapter     ON history_arc_chapter_perspectives(chapter_id);
CREATE INDEX IF NOT EXISTS idx_arc_chap_persp_perspective ON history_arc_chapter_perspectives(perspective_id);

CREATE TABLE IF NOT EXISTS history_arc_events (
  id            TEXT PRIMARY KEY,
  arc_id        TEXT NOT NULL REFERENCES history_arcs(id) ON DELETE CASCADE,
  event_id      TEXT NOT NULL REFERENCES history_events(id) ON DELETE CASCADE,
  chapter_id    TEXT REFERENCES history_arc_chapters(id) ON DELETE SET NULL,
  event_slug    TEXT NOT NULL,
  role_in_arc   TEXT,
  display_order INTEGER DEFAULT 0,
  UNIQUE(arc_id, event_id)
);
CREATE INDEX IF NOT EXISTS idx_history_arc_events_arc     ON history_arc_events(arc_id);
CREATE INDEX IF NOT EXISTS idx_history_arc_events_event   ON history_arc_events(event_id);
CREATE INDEX IF NOT EXISTS idx_history_arc_events_chapter ON history_arc_events(chapter_id);

CREATE TABLE IF NOT EXISTS history_arc_statistics (
  id                TEXT PRIMARY KEY,
  arc_id            TEXT NOT NULL REFERENCES history_arcs(id) ON DELETE CASCADE,
  label             TEXT NOT NULL,
  description       TEXT,
  unit              TEXT NOT NULL,
  source            TEXT NOT NULL,
  source_url        TEXT,
  data_points       TEXT NOT NULL DEFAULT '[]',   -- JSON
  relevant_chapters TEXT DEFAULT '[]',            -- JSON array string (int[])
  display_order     INTEGER DEFAULT 0,
  UNIQUE(arc_id, label)
);
CREATE INDEX IF NOT EXISTS idx_history_arc_statistics_arc ON history_arc_statistics(arc_id);

-- ═════════════════════════════════════════════════════════════════════════
-- void --revolt  (066; consolidating end-year 067)
-- ═════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS revolt_events (
  id                            TEXT PRIMARY KEY,
  slug                          TEXT UNIQUE NOT NULL,
  title                         TEXT NOT NULL,
  subtitle                      TEXT,
  date_display                  TEXT NOT NULL,
  date_start                    INTEGER NOT NULL,
  date_end                      INTEGER,
  date_precision                TEXT NOT NULL DEFAULT 'year'
                                  CHECK (date_precision IN ('day','month','year','decade','century')),
  era                           TEXT NOT NULL
                                  CHECK (era IN ('classical','atlantic','springtime','modern-nationalist',
                                                 'anticolonial','people-power','color-revolutions','square-revolutions')),
  region                        TEXT NOT NULL
                                  CHECK (region IN ('africa','americas','east-asia','south-asia','southeast-asia',
                                                    'middle-east','europe','oceania','central-asia','global')),
  country                       TEXT,
  revolt_type                   TEXT NOT NULL
                                  CHECK (revolt_type IN ('social','political','anticolonial','nationalist-secessionist',
                                                         'democratic-uprising','communist','religious-theocratic',
                                                         'peasant-agrarian','coup-from-above','velvet-negotiated')),
  status                        TEXT NOT NULL DEFAULT 'concluded'
                                  CHECK (status IN ('concluded','active','consolidating','dormant','watchlist')),
  summary                       TEXT NOT NULL,
  significance                  TEXT NOT NULL,
  analytical_outlook            TEXT,
  grievances                    TEXT DEFAULT '[]',   -- JSON
  structural_pressures          TEXT DEFAULT '{}',   -- JSON
  structural_indicators         TEXT DEFAULT '{}',   -- JSON
  fiscal_crisis                 INTEGER,             -- boolean nullable
  elite_fracture                INTEGER,
  youth_bulge                   INTEGER,
  repression_level              TEXT CHECK (repression_level IN ('none','low','moderate','high','severe')),
  external_shock                TEXT,
  actors                        TEXT DEFAULT '[]',   -- JSON
  tactics                       TEXT DEFAULT '[]',   -- JSON
  resistance_type               TEXT CHECK (resistance_type IN ('nonviolent','armed','hybrid')),
  phases                        TEXT DEFAULT '[]',   -- JSON
  ate_its_children              INTEGER,             -- boolean nullable
  outcome                       TEXT CHECK (outcome IN ('independence','consolidated-democracy','consolidated-autocracy',
                                                        'restored-old-regime','failed-suppressed','civil-war',
                                                        'ongoing-unresolved','intra-regime-purge','secession-partition')),
  peak_participation_pct        REAL,
  peak_participation_display    TEXT,
  crossed_participation_threshold INTEGER,           -- boolean nullable
  military_defection            TEXT CHECK (military_defection IN ('none','partial','full','unknown')),
  foreign_intervention          TEXT CHECK (foreign_intervention IN ('none','diplomatic','material','direct-military','unknown')),
  duration_days                 INTEGER,
  death_toll                    TEXT,
  death_toll_low                INTEGER,
  death_toll_high               INTEGER,
  regime_before                 TEXT CHECK (regime_before IN ('monarchy','personalist','military','one-party','colonial','theocracy','democracy','other')),
  regime_after                  TEXT CHECK (regime_after IN ('monarchy','personalist','military','one-party','colonial','theocracy','democracy','other','unresolved')),
  democratization_delta         INTEGER CHECK (democratization_delta BETWEEN -3 AND 3),
  success_factors               TEXT DEFAULT '[]',   -- JSON
  key_figures                   TEXT DEFAULT '[]',   -- JSON
  legacy_points                 TEXT DEFAULT '[]',   -- JSON
  primary_source_excerpts       TEXT DEFAULT '[]',   -- JSON
  coordinates                   TEXT,                -- JSON
  hero_image_url                TEXT,
  hero_image_attribution        TEXT,
  map_image_url                 TEXT,
  audio_url                     TEXT,
  audio_duration_seconds        REAL,
  related_revolt_slugs          TEXT DEFAULT '[]',   -- JSON array string
  related_history_slugs         TEXT DEFAULT '[]',   -- JSON array string
  live_query                    TEXT,                -- JSON
  analysis_reviewed_at          TEXT,                -- DATE
  prediction_confidence         TEXT CHECK (prediction_confidence IN ('high','medium','low','n/a')),
  display_order                 INTEGER DEFAULT 0,
  is_published                  INTEGER DEFAULT 0,
  created_at                    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at                    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  -- 067: concluded/consolidating must carry an end year
  CONSTRAINT revolt_end_year_required
    CHECK (status IN ('active','watchlist','dormant','consolidating') OR date_end IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_revolt_events_slug       ON revolt_events(slug);
CREATE INDEX IF NOT EXISTS idx_revolt_events_era        ON revolt_events(era);
CREATE INDEX IF NOT EXISTS idx_revolt_events_region     ON revolt_events(region);
CREATE INDEX IF NOT EXISTS idx_revolt_events_type       ON revolt_events(revolt_type);
CREATE INDEX IF NOT EXISTS idx_revolt_events_status     ON revolt_events(status);
CREATE INDEX IF NOT EXISTS idx_revolt_events_outcome    ON revolt_events(outcome);
CREATE INDEX IF NOT EXISTS idx_revolt_events_date_start ON revolt_events(date_start);
CREATE INDEX IF NOT EXISTS idx_revolt_events_published  ON revolt_events(is_published);
CREATE INDEX IF NOT EXISTS idx_revolt_events_active     ON revolt_events(status) WHERE status = 'active';

CREATE TABLE IF NOT EXISTS revolt_perspectives (
  id             TEXT PRIMARY KEY,
  revolt_id      TEXT NOT NULL REFERENCES revolt_events(id) ON DELETE CASCADE,
  viewpoint      TEXT NOT NULL,
  viewpoint_type TEXT NOT NULL
                   CHECK (viewpoint_type IN ('revolutionary','movement','regime','counter-revolutionary',
                                             'moderate','radical','military','academic','diaspora','indigenous')),
  region_origin  TEXT NOT NULL,
  narrative      TEXT NOT NULL,
  key_arguments  TEXT DEFAULT '[]',
  sources        TEXT DEFAULT '[]',
  notable_quotes TEXT DEFAULT '[]',
  emphasized     TEXT DEFAULT '[]',
  omitted        TEXT DEFAULT '[]',
  display_order  INTEGER DEFAULT 0,
  created_at     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_revolt_perspectives_revolt ON revolt_perspectives(revolt_id);
CREATE INDEX IF NOT EXISTS idx_revolt_perspectives_type   ON revolt_perspectives(viewpoint_type);

CREATE TABLE IF NOT EXISTS revolt_media (
  id            TEXT PRIMARY KEY,
  revolt_id     TEXT NOT NULL REFERENCES revolt_events(id) ON DELETE CASCADE,
  media_type    TEXT NOT NULL
                  CHECK (media_type IN ('image','photograph','painting','artwork','map','document',
                                        'video','poster','infographic','chart','footage')),
  title         TEXT NOT NULL,
  description   TEXT,
  source_url    TEXT NOT NULL,
  thumbnail_url TEXT,
  attribution   TEXT NOT NULL,
  license       TEXT DEFAULT 'public-domain'
                  CHECK (license IN ('public-domain','cc0','cc-by','cc-by-sa','fair-use',
                                     'unsplash-license','pexels-license')),
  creator       TEXT,
  creation_date TEXT,
  display_order INTEGER DEFAULT 0,
  created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_revolt_media_revolt ON revolt_media(revolt_id);
CREATE INDEX IF NOT EXISTS idx_revolt_media_type   ON revolt_media(media_type);

CREATE TABLE IF NOT EXISTS revolt_connections (
  id              TEXT PRIMARY KEY,
  revolt_a_id     TEXT NOT NULL REFERENCES revolt_events(id) ON DELETE CASCADE,
  revolt_b_id     TEXT NOT NULL REFERENCES revolt_events(id) ON DELETE CASCADE,
  connection_type TEXT NOT NULL
                    CHECK (connection_type IN ('inspired','provided-model','triggered-contagion','provoked-backlash',
                                               'shared-repertoire','parallel','counter-example')),
  description     TEXT,
  UNIQUE(revolt_a_id, revolt_b_id)
);
CREATE INDEX IF NOT EXISTS idx_revolt_connections_a ON revolt_connections(revolt_a_id);
CREATE INDEX IF NOT EXISTS idx_revolt_connections_b ON revolt_connections(revolt_b_id);

CREATE TABLE IF NOT EXISTS revolt_metrics (
  id            TEXT PRIMARY KEY,
  revolt_id     TEXT NOT NULL REFERENCES revolt_events(id) ON DELETE CASCADE,
  metric_key    TEXT NOT NULL,
  label         TEXT NOT NULL,
  category      TEXT NOT NULL DEFAULT 'process' CHECK (category IN ('precondition','process','outcome')),
  unit          TEXT,
  numeric_value REAL,
  display_value TEXT,
  framework     TEXT,
  source        TEXT,
  source_url    TEXT,
  data_points   TEXT DEFAULT '[]',   -- JSON
  display_order INTEGER DEFAULT 0,
  created_at    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(revolt_id, metric_key)
);
CREATE INDEX IF NOT EXISTS idx_revolt_metrics_revolt ON revolt_metrics(revolt_id);

-- ═════════════════════════════════════════════════════════════════════════
-- Instagram automation  (052 ig_posts; 053 engagement; 073/074 ig_posts cols)
--   Server/service-role only in production. Included here because the pipeline
--   generator writes them; no browser writes.
-- ═════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS ig_posts (
  id                 TEXT PRIMARY KEY,
  created_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  state              TEXT NOT NULL DEFAULT 'draft'
                       CHECK (state IN ('draft','rendering','render_failed','captioning','caption_review',
                                        'approved','posting','posted','failed','rejected')),
  scheduled_for      TEXT NOT NULL,
  pillar             TEXT NOT NULL
                       CHECK (pillar IN ('vision','method','example','history','weekly',   -- 073 current
                                         'receipt','brief','bts','heatmap')),               -- 073 retired-but-valid
  surface            TEXT NOT NULL DEFAULT 'feed' CHECK (surface IN ('feed','story','reel')),
  launch_slot        INTEGER,
  slide_specs        TEXT NOT NULL,   -- JSON
  caption            TEXT,
  hashtags           TEXT,            -- JSON array string
  image_urls         TEXT,            -- JSON array string
  ig_media_id        TEXT,
  ig_permalink       TEXT,
  posted_at          TEXT,
  bluesky_uri        TEXT,
  metrics            TEXT,            -- JSON
  metrics_updated_at TEXT,
  error              TEXT,
  retry_count        INTEGER NOT NULL DEFAULT 0,
  caption_x          TEXT,   -- 074
  caption_bluesky    TEXT,   -- 074
  intent             TEXT    -- 074
);
CREATE INDEX IF NOT EXISTS idx_ig_posts_state_scheduled ON ig_posts(state, scheduled_for);
CREATE INDEX IF NOT EXISTS idx_ig_posts_pillar_posted   ON ig_posts(pillar, posted_at DESC) WHERE posted_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ig_posts_approved_due     ON ig_posts(scheduled_for) WHERE state = 'approved';

CREATE TABLE IF NOT EXISTS ig_comments (
  id                TEXT PRIMARY KEY,
  created_at        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ig_comment_id     TEXT NOT NULL UNIQUE,
  ig_media_id       TEXT NOT NULL,
  parent_id         TEXT,
  ig_user_id        TEXT NOT NULL,
  ig_username       TEXT,
  text              TEXT NOT NULL,
  is_reply          INTEGER NOT NULL DEFAULT 0,
  score             REAL DEFAULT 0,
  auto_replied      INTEGER NOT NULL DEFAULT 0,
  reply_drafted     TEXT,
  reply_sent_at     TEXT,
  reply_ig_id       TEXT,
  hidden_or_deleted INTEGER NOT NULL DEFAULT 0,
  signature_ok      INTEGER NOT NULL DEFAULT 1,
  raw               TEXT   -- JSON
);
CREATE INDEX IF NOT EXISTS idx_ig_comments_media ON ig_comments(ig_media_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ig_comments_pending_reply
  ON ig_comments(score DESC, created_at DESC)
  WHERE auto_replied = 0 AND reply_sent_at IS NULL AND hidden_or_deleted = 0;

CREATE TABLE IF NOT EXISTS ig_dms (
  id               TEXT PRIMARY KEY,
  created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ig_thread_id     TEXT NOT NULL,
  ig_message_id    TEXT NOT NULL UNIQUE,
  ig_user_id       TEXT NOT NULL,
  ig_username      TEXT,
  text             TEXT,
  inbound          INTEGER NOT NULL DEFAULT 1,
  priority         TEXT NOT NULL DEFAULT 'inbox' CHECK (priority IN ('press','inbox','noise')),
  matched_keywords TEXT,   -- JSON array string
  first_touch_sent INTEGER NOT NULL DEFAULT 0,
  read_by_admin    INTEGER NOT NULL DEFAULT 0,
  raw              TEXT
);
CREATE INDEX IF NOT EXISTS idx_ig_dms_priority_unread ON ig_dms(priority, created_at DESC) WHERE read_by_admin = 0;
CREATE INDEX IF NOT EXISTS idx_ig_dms_thread          ON ig_dms(ig_thread_id, created_at DESC);

CREATE TABLE IF NOT EXISTS ig_mentions (
  id           TEXT PRIMARY KEY,
  created_at   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ig_media_id  TEXT NOT NULL UNIQUE,
  ig_user_id   TEXT,
  ig_username  TEXT,
  caption      TEXT,
  permalink    TEXT,
  is_seed_list INTEGER NOT NULL DEFAULT 0,
  archived     INTEGER NOT NULL DEFAULT 0,
  raw          TEXT
);
CREATE INDEX IF NOT EXISTS idx_ig_mentions_fresh ON ig_mentions(created_at DESC) WHERE archived = 0;

CREATE TABLE IF NOT EXISTS ig_hashtag_candidates (
  id               TEXT PRIMARY KEY,
  created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  hashtag          TEXT NOT NULL,
  ig_media_id      TEXT NOT NULL UNIQUE,
  ig_user_id       TEXT,
  ig_username      TEXT,
  caption          TEXT,
  permalink        TEXT,
  engagement_score REAL DEFAULT 0,
  dismissed        INTEGER NOT NULL DEFAULT 0,
  acted_on         INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_ig_hashtag_candidates_fresh
  ON ig_hashtag_candidates(hashtag, engagement_score DESC, created_at DESC)
  WHERE dismissed = 0 AND acted_on = 0;

-- ═════════════════════════════════════════════════════════════════════════
-- Diagnostic-lab engine tables  (057; retention RPCs 060 — writer disabled)
-- ═════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS engine_runs (
  id              TEXT PRIMARY KEY,
  pipeline_run_id TEXT REFERENCES pipeline_runs(id) ON DELETE SET NULL,
  source          TEXT NOT NULL DEFAULT 'production',
  params          TEXT NOT NULL DEFAULT '{}',
  step_timings    TEXT NOT NULL DEFAULT '{}',
  step_errors     TEXT NOT NULL DEFAULT '{}',
  cluster_count   INTEGER,
  article_count   INTEGER,
  sonnet_calls    INTEGER DEFAULT 0,
  gemini_calls    INTEGER DEFAULT 0,
  created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS engine_runs_created_at_idx ON engine_runs(created_at DESC);
CREATE INDEX IF NOT EXISTS engine_runs_source_idx     ON engine_runs(source, created_at DESC);

CREATE TABLE IF NOT EXISTS engine_snapshots (
  id                 TEXT PRIMARY KEY,
  engine_run_id      TEXT NOT NULL REFERENCES engine_runs(id) ON DELETE CASCADE,
  payload            TEXT NOT NULL,   -- JSON
  payload_size_bytes INTEGER,
  created_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS engine_snapshots_run_idx ON engine_snapshots(engine_run_id);

CREATE TABLE IF NOT EXISTS sandbox_runs (
  id               TEXT PRIMARY KEY,
  base_snapshot_id TEXT REFERENCES engine_snapshots(id) ON DELETE SET NULL,
  param_overrides  TEXT NOT NULL DEFAULT '{}',
  result_payload   TEXT,
  status           TEXT NOT NULL DEFAULT 'pending',
  triggered_via    TEXT,
  error_message    TEXT,
  duration_ms      INTEGER,
  created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at     TEXT
);
CREATE INDEX IF NOT EXISTS sandbox_runs_status_idx ON sandbox_runs(status, created_at DESC);
CREATE INDEX IF NOT EXISTS sandbox_runs_base_idx   ON sandbox_runs(base_snapshot_id);

-- ═════════════════════════════════════════════════════════════════════════
-- Printed archive (Newspaper of Record)  (075)
--   printed_stories.id is the permanent /story/[id] permalink.
-- ═════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS printed_days (
  printed_on      TEXT PRIMARY KEY,   -- DATE
  pipeline_run_id TEXT,
  story_count     INTEGER NOT NULL DEFAULT 0,
  daily_brief_id  TEXT,
  created_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS printed_stories (
  id                   TEXT PRIMARY KEY,
  printed_on           TEXT NOT NULL REFERENCES printed_days(printed_on),   -- DATE
  edition_position     INTEGER NOT NULL CHECK (edition_position BETWEEN 1 AND 50),
  source_cluster_id    TEXT NOT NULL,
  title                TEXT NOT NULL,
  summary              TEXT,
  category             TEXT,
  content_type         TEXT,
  story_type           TEXT,
  editorial_importance INTEGER,
  summary_tier         TEXT,
  rank_world           REAL NOT NULL,
  headline_rank        REAL,
  source_count         INTEGER NOT NULL DEFAULT 0,
  divergence_score     REAL,
  first_published      TEXT,
  consensus_points     TEXT,   -- JSON
  divergence_points    TEXT,   -- JSON
  claim_consensus      TEXT,   -- JSON
  bias_diversity       TEXT,   -- JSON
  mean_lean            REAL,
  polarization         INTEGER,
  lean_spread          REAL,
  aggregate_confidence REAL,
  members              TEXT NOT NULL DEFAULT '[]',   -- JSON
  member_count         INTEGER NOT NULL DEFAULT 0,
  title_keywords       TEXT NOT NULL DEFAULT '[]',   -- JSON array string (was text[])
  story_thread_id      TEXT NOT NULL,
  continues_printed_id TEXT REFERENCES printed_stories(id),
  search_terms         TEXT,
  -- DROPPED (generated tsvector search_tsv): SQLite has no tsvector. Use an
  -- FTS5 virtual table over (title, summary, search_terms) instead. See PORT_NOTES.md.
  created_at           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT uq_printed_day_cluster UNIQUE (printed_on, source_cluster_id)
);
CREATE INDEX IF NOT EXISTS idx_printed_day_pos        ON printed_stories(printed_on DESC, edition_position ASC);
CREATE INDEX IF NOT EXISTS idx_printed_source_cluster ON printed_stories(source_cluster_id, printed_on DESC);
CREATE INDEX IF NOT EXISTS idx_printed_thread         ON printed_stories(story_thread_id, printed_on ASC);
CREATE INDEX IF NOT EXISTS idx_printed_category_day   ON printed_stories(category, printed_on DESC);
-- DROPPED (GIN): idx_printed_search on search_tsv (075). Use FTS5. See PORT_NOTES.md.
