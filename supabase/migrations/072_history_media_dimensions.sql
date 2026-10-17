-- 072_history_media_dimensions.sql
--
-- Persist image dimensions + capture location on history_media (2026-08-04).
--
-- History event images render small because dimensions captured at sourcing
-- (image_search.ImageResult.width/height) were discarded into the free-text
-- `description` (which also leaked "6000x4000px" as a caption). These columns
-- let the frontend render each photo at full size / correct aspect ratio and
-- show an archival "date | location | credit" metadata plate in the Lightbox.
--
-- All three are nullable: existing rows and rows sourced before the
-- re-enrichment run stay valid. `location` is populated per-image where a
-- source place is available, else the frontend falls back to the event's
-- location. Backfill higher-res URLs + width/height via a history
-- re-enrichment run (pipeline/history/image_enricher.py -> content_loader.py).
--
-- Guarded DO-block pattern (cf. 063 / 071): idempotent, safe to re-apply.

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'history_media' AND column_name = 'width'
  ) THEN
    ALTER TABLE history_media ADD COLUMN width INT;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'history_media' AND column_name = 'height'
  ) THEN
    ALTER TABLE history_media ADD COLUMN height INT;
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'history_media' AND column_name = 'location'
  ) THEN
    ALTER TABLE history_media ADD COLUMN location TEXT;
  END IF;
END $$;

COMMENT ON COLUMN history_media.width IS
  'Pixel width of the sourced image (image_search.ImageResult.width). Nullable; '
  'backfilled by the history re-enrichment run.';
COMMENT ON COLUMN history_media.height IS
  'Pixel height of the sourced image (image_search.ImageResult.height). Nullable; '
  'backfilled by the history re-enrichment run.';
COMMENT ON COLUMN history_media.location IS
  'Per-image capture location (e.g. "Nagasaki, Japan"). Nullable; the frontend '
  'falls back to the event location when absent.';
