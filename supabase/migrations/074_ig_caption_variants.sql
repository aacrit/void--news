-- 074_ig_caption_variants.sql
--
-- Per-platform caption variants + a one-sentence director's note on ig_posts
-- (2026-08-05). Part of the social pipeline pivot from auto-post-on-cron to
-- generate-a-downloadable-bundle-for-MANUAL-upload (posting parked).
--
-- The single Gemini caption call (ig_caption.py) now returns, alongside the
-- existing Instagram `caption` + `hashtags`:
--   caption_x        an X/Twitter variant, <= 280 chars, at most 1-2 hashtags
--   caption_bluesky  a Bluesky variant, <= 300 chars, plain (no hashtag wall)
--   intent           a one-sentence director's note (the message/emotion the
--                    post is going for) so the CEO can add a personal touch
--                    before pasting the copy into each platform by hand.
--
-- ig_export.py reads these into the per-post caption-*.txt + intent.txt files
-- and the index.html preview. All three are nullable: rows generated before
-- this migration, and the rule-based derive-from-IG fallback path, stay valid.
--
-- Guarded DO-block pattern (cf. 063 / 071 / 072): idempotent, safe to re-apply.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'ig_posts' AND column_name = 'caption_x'
  ) THEN
    ALTER TABLE ig_posts ADD COLUMN caption_x TEXT;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'ig_posts' AND column_name = 'caption_bluesky'
  ) THEN
    ALTER TABLE ig_posts ADD COLUMN caption_bluesky TEXT;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'ig_posts' AND column_name = 'intent'
  ) THEN
    ALTER TABLE ig_posts ADD COLUMN intent TEXT;
  END IF;
END $$;

COMMENT ON COLUMN ig_posts.caption_x IS
  'X/Twitter caption variant, <= 280 chars, at most 1-2 hashtags. Written by '
  'ig_caption.py; derived by trimming the IG caption when the model omits it. Nullable.';
COMMENT ON COLUMN ig_posts.caption_bluesky IS
  'Bluesky caption variant, <= 300 chars, plain prose with no hashtag wall. '
  'Written by ig_caption.py; derived by trimming the IG caption when omitted. Nullable.';
COMMENT ON COLUMN ig_posts.intent IS
  'One-sentence director''s note: the message/emotion the post is going for, so '
  'the CEO can add a personal touch before manual upload. Nullable.';
