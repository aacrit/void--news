-- Migration 075: Newspaper of Record — permanent archive of each day's printed
-- top-50. Metadata-only (no article bodies; copyright-clean). Distinct from
-- cluster_archive (016), the rolling 10-day weekly-digest buffer.
--
-- Two permanent public-read tables + a GIN full-text index + two SECURITY
-- DEFINER RPCs (stats + search). Idempotent, following the house style of
-- 062/071/074: guarded CREATEs, DROP POLICY IF EXISTS before CREATE POLICY,
-- REVOKE-then-GRANT on every function.

-- ── Tables ──────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS printed_days (
  printed_on       DATE PRIMARY KEY,
  pipeline_run_id  UUID,
  story_count      SMALLINT NOT NULL DEFAULT 0,
  daily_brief_id   UUID,
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS printed_stories (
  id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  printed_on            DATE NOT NULL REFERENCES printed_days(printed_on),
  edition_position              SMALLINT NOT NULL CHECK (edition_position BETWEEN 1 AND 50),
  source_cluster_id     UUID NOT NULL,
  title                 TEXT NOT NULL,
  summary               TEXT,
  category              TEXT,
  content_type          TEXT,
  story_type            TEXT,
  editorial_importance  SMALLINT,
  summary_tier          TEXT,
  rank_world            REAL NOT NULL,
  headline_rank         REAL,
  source_count          INTEGER NOT NULL DEFAULT 0,
  divergence_score      REAL,
  first_published       TIMESTAMPTZ,
  consensus_points      JSONB,
  divergence_points     JSONB,
  claim_consensus       JSONB,
  bias_diversity        JSONB,
  mean_lean             REAL,
  polarization          SMALLINT,
  lean_spread           REAL,
  aggregate_confidence  REAL,
  members               JSONB NOT NULL DEFAULT '[]',
  member_count          SMALLINT NOT NULL DEFAULT 0,
  title_keywords        TEXT[] NOT NULL DEFAULT '{}',
  story_thread_id       UUID NOT NULL,
  continues_printed_id  UUID REFERENCES printed_stories(id),
  search_terms          TEXT,
  search_tsv            tsvector GENERATED ALWAYS AS (
                          setweight(to_tsvector('english', coalesce(title, '')),        'A')
                        || setweight(to_tsvector('english', coalesce(summary, '')),      'B')
                        || setweight(to_tsvector('simple',  coalesce(search_terms, '')), 'C')
                        ) STORED,
  created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_printed_day_cluster UNIQUE (printed_on, source_cluster_id)
);

CREATE INDEX IF NOT EXISTS idx_printed_day_pos        ON printed_stories (printed_on DESC, edition_position ASC);
CREATE INDEX IF NOT EXISTS idx_printed_source_cluster ON printed_stories (source_cluster_id, printed_on DESC);
CREATE INDEX IF NOT EXISTS idx_printed_thread         ON printed_stories (story_thread_id, printed_on ASC);
CREATE INDEX IF NOT EXISTS idx_printed_category_day   ON printed_stories (category, printed_on DESC);
CREATE INDEX IF NOT EXISTS idx_printed_search         ON printed_stories USING GIN (search_tsv);

-- ── Row-level security: public read only. The pipeline writes via the
--    service role, which bypasses RLS. ────────────────────────────────────

ALTER TABLE printed_days    ENABLE ROW LEVEL SECURITY;
ALTER TABLE printed_stories ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Public read printed_days"    ON printed_days;
DROP POLICY IF EXISTS "Public read printed_stories" ON printed_stories;
CREATE POLICY "Public read printed_days"    ON printed_days    FOR SELECT USING (true);
CREATE POLICY "Public read printed_stories" ON printed_stories FOR SELECT USING (true);

-- ── RPC 1: archive size/coverage stats ──────────────────────────────────
-- Metadata-only so total footprint stays tiny; this surfaces the true
-- on-disk cost (table + indexes + TOAST) via pg_total_relation_size.

CREATE OR REPLACE FUNCTION printed_archive_stats()
RETURNS jsonb
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  WITH sz AS (
    SELECT (pg_total_relation_size('printed_stories')
          + pg_total_relation_size('printed_days'))::numeric AS bytes
  ),
  dc AS (
    SELECT count(*)::numeric AS days FROM printed_days
  )
  SELECT jsonb_build_object(
    'days',       (SELECT days::bigint FROM dc),
    'stories',    (SELECT count(*)::bigint FROM printed_stories),
    'total_mb',   round((SELECT bytes FROM sz) / 1048576.0, 2),
    'kb_per_day', CASE
                    WHEN (SELECT days FROM dc) > 0
                    THEN round((SELECT bytes FROM sz) / 1024.0
                               / (SELECT days FROM dc), 1)
                    ELSE 0
                  END
  );
$$;

REVOKE ALL ON FUNCTION printed_archive_stats() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION printed_archive_stats() TO anon, authenticated, service_role;

COMMENT ON FUNCTION printed_archive_stats() IS
  'Returns {days, stories, total_mb, kb_per_day} for the permanent printed '
  'archive (printed_days + printed_stories, incl. indexes/TOAST). Read-only.';

-- ── RPC 2: full-text search over the printed record ─────────────────────
-- ts_rank_cd, boosted by coverage breadth (more sources = more real) and
-- decayed by age (90-day half-ish life). collapse_threads returns one hit
-- per continuing story (its best printing) instead of every daily reprint.

CREATE OR REPLACE FUNCTION search_printed_stories(
  q                TEXT,
  max_results      INT     DEFAULT 10,
  offset_n         INT     DEFAULT 0,
  date_from        DATE    DEFAULT NULL,
  date_to          DATE    DEFAULT NULL,
  category_filter  TEXT    DEFAULT NULL,
  collapse_threads BOOLEAN DEFAULT TRUE
)
RETURNS TABLE (
  id                UUID,
  source_cluster_id UUID,
  story_thread_id   UUID,
  printed_on        DATE,
  edition_position          SMALLINT,
  title             TEXT,
  summary           TEXT,
  category          TEXT,
  source_count      INTEGER,
  mean_lean         REAL,
  polarization      SMALLINT,
  thread_printings  BIGINT,
  rank              REAL
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public
AS $$
  WITH tsq AS (
    SELECT websearch_to_tsquery('english', coalesce(q, '')) AS query
  ),
  scored AS (
    SELECT
      ps.id,
      ps.source_cluster_id,
      ps.story_thread_id,
      ps.printed_on,
      ps.edition_position,
      ps.title,
      ps.summary,
      ps.category,
      ps.source_count,
      ps.mean_lean,
      ps.polarization,
      (SELECT count(*) FROM printed_stories t
        WHERE t.story_thread_id = ps.story_thread_id)::bigint AS thread_printings,
      (
        ts_rank_cd(ps.search_tsv, tsq.query)
        * (1.0 + least(ps.source_count, 60)::numeric / 120.0)
        * (0.5 + 0.5 * exp(-((current_date - ps.printed_on)::numeric / 90.0)))
      )::real AS rank
    FROM printed_stories ps, tsq
    WHERE ps.search_tsv @@ tsq.query
      AND (date_from       IS NULL OR ps.printed_on >= date_from)
      AND (date_to         IS NULL OR ps.printed_on <= date_to)
      AND (category_filter IS NULL OR ps.category = category_filter)
  ),
  collapsed AS (
    -- one printing per thread (highest rank, then most recent) when collapsing
    SELECT DISTINCT ON (s.story_thread_id) s.*
    FROM scored s
    WHERE collapse_threads
    ORDER BY s.story_thread_id, s.rank DESC, s.printed_on DESC
  ),
  final AS (
    SELECT * FROM collapsed
    UNION ALL
    SELECT * FROM scored WHERE NOT collapse_threads
  )
  SELECT
    id, source_cluster_id, story_thread_id, printed_on, edition_position,
    title, summary, category, source_count, mean_lean, polarization,
    thread_printings, rank
  FROM final
  ORDER BY rank DESC, printed_on DESC
  LIMIT  LEAST(GREATEST(max_results, 1), 50)
  OFFSET GREATEST(offset_n, 0);
$$;

REVOKE ALL ON FUNCTION search_printed_stories(
  TEXT, INT, INT, DATE, DATE, TEXT, BOOLEAN) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION search_printed_stories(
  TEXT, INT, INT, DATE, DATE, TEXT, BOOLEAN)
  TO anon, authenticated, service_role;

COMMENT ON FUNCTION search_printed_stories(
  TEXT, INT, INT, DATE, DATE, TEXT, BOOLEAN) IS
  'Full-text search over the permanent printed archive. websearch_to_tsquery '
  'matching, ts_rank_cd scaled by coverage breadth and age decay; '
  'collapse_threads returns one hit per continuing story. Read-only.';
