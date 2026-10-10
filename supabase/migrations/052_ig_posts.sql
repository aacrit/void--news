-- ============================================================================
-- Migration 052: Instagram automation — ig_posts table + ig-renders bucket
-- Date: 2026-05-14
-- Trigger: Instagram strategy & content system buildout (see plan
--   /home/aacrit/.claude/plans/i-want-to-build-tingly-cloud.md).
--
-- One row per scheduled or shipped Instagram post. The state column drives
-- the workflow:
--
--   draft           → row created by ig_generator.py, awaiting render
--   rendering       → ig_capture.py picked it up
--   render_failed   → Playwright/render error; surfaces in /admin/ig
--   captioning      → ig_caption.py picked it up
--   caption_review  → 3 retries failed brand-rules check; needs human edit
--   approved        → human approved in /admin/ig; ig_publisher.py will ship
--                     it the next time the cron fires past scheduled_for
--   posting         → publisher in flight
--   posted          → Graph API returned ig_media_id; cross_post.py runs next
--   failed          → publisher hit a terminal error; error column has detail
--   rejected        → human rejected via /admin/ig (kept for audit)
--
-- The publisher only reads rows where state = 'approved' AND scheduled_for
-- <= now(). No code path mutates state to 'approved' except the admin page,
-- which requires the basic-auth password. Editorial fail-safe is architectural.
--
-- Storage bucket `ig-renders` (public) holds the PNG output of ig_capture.py.
-- Public is required because the Graph API fetches `image_url` from a public
-- HTTPS URL; signed URLs are not supported by Instagram media containers.
-- ============================================================================

CREATE TABLE IF NOT EXISTS ig_posts (
  id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  -- Workflow
  state          TEXT NOT NULL DEFAULT 'draft'
                 CHECK (state IN (
                   'draft', 'rendering', 'render_failed',
                   'captioning', 'caption_review',
                   'approved', 'posting', 'posted',
                   'failed', 'rejected'
                 )),
  scheduled_for  TIMESTAMPTZ NOT NULL,

  -- Editorial
  pillar         TEXT NOT NULL
                 CHECK (pillar IN ('receipt', 'method', 'history', 'brief', 'bts', 'heatmap')),
  surface        TEXT NOT NULL DEFAULT 'feed'
                 CHECK (surface IN ('feed', 'story', 'reel')),
  launch_slot    INT,                   -- 1..10 for the launch sequence, NULL otherwise
  slide_specs    JSONB NOT NULL,        -- array of slide spec objects; see templates/*.tsx
  caption        TEXT,
  hashtags       TEXT[],

  -- Render output
  image_urls     TEXT[],                -- public URLs in ig-renders bucket, ordered by slide

  -- Publish output
  ig_media_id    TEXT,                  -- Instagram Graph API media id (carousel container)
  ig_permalink   TEXT,                  -- canonical instagram.com URL
  posted_at      TIMESTAMPTZ,
  bluesky_uri    TEXT,                  -- atproto record URI after cross-post

  -- Telemetry
  metrics        JSONB,                 -- {impressions, reach, saved, shares, profile_visits, website_clicks, updated_at}
  metrics_updated_at TIMESTAMPTZ,

  -- Failure detail
  error          TEXT,
  retry_count    INT NOT NULL DEFAULT 0
);

-- Workflow queries: "what's pending in the next 48h?" / "what's approved past due?"
CREATE INDEX IF NOT EXISTS idx_ig_posts_state_scheduled
  ON ig_posts (state, scheduled_for);

-- Analytics: posted timeline per pillar
CREATE INDEX IF NOT EXISTS idx_ig_posts_pillar_posted
  ON ig_posts (pillar, posted_at DESC)
  WHERE posted_at IS NOT NULL;

-- Lookups by the publisher cron
CREATE INDEX IF NOT EXISTS idx_ig_posts_approved_due
  ON ig_posts (scheduled_for)
  WHERE state = 'approved';

-- Audit comments
COMMENT ON TABLE ig_posts IS
  'One row per scheduled or shipped Instagram post. State machine drives generator → capture → caption → admin approval → publisher → cross-post.';
COMMENT ON COLUMN ig_posts.state IS
  'Workflow state. Only the /admin/ig page may transition to approved or rejected; only ig_publisher.py may transition to posting/posted/failed.';
COMMENT ON COLUMN ig_posts.slide_specs IS
  'Array of slide spec objects matching the pillar template schema. Receipt: {event_id, headlines[]}. Method: {axis_name, samples[]}. History: {event_yaml_path, perspectives[]}. Brief: {type, content}.';
COMMENT ON COLUMN ig_posts.image_urls IS
  'Public Supabase Storage URLs in ig-renders bucket. Required public because Graph API fetches by URL.';
COMMENT ON COLUMN ig_posts.launch_slot IS
  'Sequence number (1-10) for the launch posts. NULL for posts generated after week 5.';
COMMENT ON COLUMN ig_posts.metrics IS
  'JSON snapshot of Graph API insights, refreshed daily by ig-metrics.yml cron.';

-- updated_at trigger
CREATE OR REPLACE FUNCTION set_ig_posts_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_ig_posts_updated_at ON ig_posts;
CREATE TRIGGER trg_ig_posts_updated_at
  BEFORE UPDATE ON ig_posts
  FOR EACH ROW EXECUTE FUNCTION set_ig_posts_updated_at();

-- RLS: deny all by default; the service-role key (used by pipeline + admin)
-- bypasses RLS. Anon key gets nothing. There is no public read path for
-- ig_posts — the admin page is server-rendered with basic-auth and uses the
-- service key, the storage bucket exposes only the rendered PNGs.
ALTER TABLE ig_posts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS ig_posts_no_anon ON ig_posts;
CREATE POLICY ig_posts_no_anon ON ig_posts
  FOR ALL TO anon, authenticated
  USING (false) WITH CHECK (false);

-- ============================================================================
-- Storage bucket: ig-renders (public)
-- ============================================================================
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES ('ig-renders', 'ig-renders', true, 8388608,           -- 8 MB matches IG carousel ceiling
        ARRAY['image/png', 'image/jpeg', 'image/webp'])
ON CONFLICT (id) DO UPDATE
  SET public = EXCLUDED.public,
      file_size_limit = EXCLUDED.file_size_limit,
      allowed_mime_types = EXCLUDED.allowed_mime_types;

-- Public read policy on the bucket
DROP POLICY IF EXISTS "ig-renders public read" ON storage.objects;
CREATE POLICY "ig-renders public read" ON storage.objects
  FOR SELECT TO public
  USING (bucket_id = 'ig-renders');

-- Service role can write (anon/authenticated cannot)
DROP POLICY IF EXISTS "ig-renders service write" ON storage.objects;
CREATE POLICY "ig-renders service write" ON storage.objects
  FOR ALL TO service_role
  USING (bucket_id = 'ig-renders')
  WITH CHECK (bucket_id = 'ig-renders');
