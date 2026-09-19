-- Expand history_media constraints for Unsplash/Pexels licenses and artwork media type

ALTER TABLE history_media DROP CONSTRAINT IF EXISTS history_media_license_check;
ALTER TABLE history_media ADD CONSTRAINT history_media_license_check
  CHECK (license IN ('public-domain', 'cc0', 'cc-by', 'cc-by-sa', 'fair-use', 'unsplash-license', 'pexels-license'));

ALTER TABLE history_media DROP CONSTRAINT IF EXISTS history_media_media_type_check;
ALTER TABLE history_media ADD CONSTRAINT history_media_media_type_check
  CHECK (media_type IN ('image', 'map', 'video', 'document', 'painting', 'photograph', 'artwork'));
