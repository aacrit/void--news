-- ============================================================================
-- Migration 053: Instagram engagement — comments, DMs, mentions, hashtags
-- Date: 2026-05-14
-- Trigger: §14a of the Instagram plan. Adds the inbound/listener surface
--   that drives the credibility flywheel (press-list mining via warm DMs,
--   high-value comment reply queueing).
--
-- Architecture: a CF Pages Function at /api/ig-webhook receives Meta
-- webhook events, verifies the X-Hub-Signature-256 header against
-- META_APP_SECRET, then writes the relevant row to one of these tables.
-- The /admin/ig/inbox page then surfaces them for human review.
-- ============================================================================

-- Comments on our own posts.
CREATE TABLE IF NOT EXISTS ig_comments (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ig_comment_id   TEXT NOT NULL UNIQUE,
  ig_media_id     TEXT NOT NULL,         -- post the comment is on
  parent_id       TEXT,                  -- thread parent if reply
  ig_user_id      TEXT NOT NULL,
  ig_username     TEXT,
  text            TEXT NOT NULL,
  is_reply        BOOLEAN NOT NULL DEFAULT FALSE,
  -- Routing
  score           NUMERIC DEFAULT 0,     -- heuristic priority (0..100)
  auto_replied    BOOLEAN NOT NULL DEFAULT FALSE,
  reply_drafted   TEXT,                  -- queued response for admin approval
  reply_sent_at   TIMESTAMPTZ,
  reply_ig_id     TEXT,                  -- our reply's comment id
  hidden_or_deleted BOOLEAN NOT NULL DEFAULT FALSE,
  -- Audit
  signature_ok    BOOLEAN NOT NULL DEFAULT TRUE,
  raw             JSONB
);

CREATE INDEX IF NOT EXISTS idx_ig_comments_media ON ig_comments (ig_media_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ig_comments_pending_reply
  ON ig_comments (score DESC, created_at DESC)
  WHERE auto_replied = FALSE AND reply_sent_at IS NULL AND hidden_or_deleted = FALSE;

-- DMs received on @void.news.
CREATE TABLE IF NOT EXISTS ig_dms (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ig_thread_id    TEXT NOT NULL,         -- conversation id
  ig_message_id   TEXT NOT NULL UNIQUE,
  ig_user_id      TEXT NOT NULL,
  ig_username     TEXT,
  text            TEXT,
  inbound         BOOLEAN NOT NULL DEFAULT TRUE,  -- TRUE = from someone to us
  priority        TEXT NOT NULL DEFAULT 'inbox'
                  CHECK (priority IN ('press', 'inbox', 'noise')),
  matched_keywords TEXT[],
  first_touch_sent BOOLEAN NOT NULL DEFAULT FALSE,
  read_by_admin   BOOLEAN NOT NULL DEFAULT FALSE,
  raw             JSONB
);

CREATE INDEX IF NOT EXISTS idx_ig_dms_priority_unread
  ON ig_dms (priority, created_at DESC)
  WHERE read_by_admin = FALSE;
CREATE INDEX IF NOT EXISTS idx_ig_dms_thread
  ON ig_dms (ig_thread_id, created_at DESC);

-- Mentions of @void.news anywhere on IG (caption or comment).
CREATE TABLE IF NOT EXISTS ig_mentions (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ig_media_id     TEXT NOT NULL UNIQUE,  -- the media that mentioned us
  ig_user_id      TEXT,                  -- mentioning account
  ig_username     TEXT,
  caption         TEXT,
  permalink       TEXT,
  is_seed_list    BOOLEAN NOT NULL DEFAULT FALSE,  -- author on our seed list
  archived        BOOLEAN NOT NULL DEFAULT FALSE,
  raw             JSONB
);

CREATE INDEX IF NOT EXISTS idx_ig_mentions_fresh
  ON ig_mentions (created_at DESC)
  WHERE archived = FALSE;

-- Hashtag monitoring — surfaces engagement opportunities for the admin
-- to manually reply to (per §14a we do NOT auto-comment on others' posts).
CREATE TABLE IF NOT EXISTS ig_hashtag_candidates (
  id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  hashtag         TEXT NOT NULL,
  ig_media_id     TEXT NOT NULL UNIQUE,
  ig_user_id      TEXT,
  ig_username     TEXT,
  caption         TEXT,
  permalink       TEXT,
  engagement_score NUMERIC DEFAULT 0,   -- proxy: likes+comments at sample time
  dismissed       BOOLEAN NOT NULL DEFAULT FALSE,
  acted_on        BOOLEAN NOT NULL DEFAULT FALSE  -- admin pressed "open" / "replied"
);

CREATE INDEX IF NOT EXISTS idx_ig_hashtag_candidates_fresh
  ON ig_hashtag_candidates (hashtag, engagement_score DESC, created_at DESC)
  WHERE dismissed = FALSE AND acted_on = FALSE;

-- RLS — same posture as ig_posts: deny anon, service role bypasses.
ALTER TABLE ig_comments           ENABLE ROW LEVEL SECURITY;
ALTER TABLE ig_dms                ENABLE ROW LEVEL SECURITY;
ALTER TABLE ig_mentions           ENABLE ROW LEVEL SECURITY;
ALTER TABLE ig_hashtag_candidates ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  EXECUTE 'DROP POLICY IF EXISTS ig_engagement_no_anon_c   ON ig_comments';
  EXECUTE 'DROP POLICY IF EXISTS ig_engagement_no_anon_d   ON ig_dms';
  EXECUTE 'DROP POLICY IF EXISTS ig_engagement_no_anon_m   ON ig_mentions';
  EXECUTE 'DROP POLICY IF EXISTS ig_engagement_no_anon_h   ON ig_hashtag_candidates';
END $$;

CREATE POLICY ig_engagement_no_anon_c ON ig_comments
  FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
CREATE POLICY ig_engagement_no_anon_d ON ig_dms
  FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
CREATE POLICY ig_engagement_no_anon_m ON ig_mentions
  FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);
CREATE POLICY ig_engagement_no_anon_h ON ig_hashtag_candidates
  FOR ALL TO anon, authenticated USING (false) WITH CHECK (false);

COMMENT ON TABLE ig_comments IS 'Inbound comments on our own posts. score+auto_replied drive the /admin/ig/inbox queue.';
COMMENT ON TABLE ig_dms IS 'DMs to @void.news. priority=press is auto-replied with the first-touch template.';
COMMENT ON TABLE ig_mentions IS 'Public posts that tag @void.news. Press-list mining input.';
COMMENT ON TABLE ig_hashtag_candidates IS 'Top public posts on our niche hashtags. Surfaces engagement opportunities; manual reply only.';
