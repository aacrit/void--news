-- v5.0: Editorial intelligence columns for Gemini-augmented ranking
-- These fields are populated by Gemini during cluster summarization (Tasks 5-7)
-- and used by the ranking engine as signals and gates.
-- All nullable — NULL means Gemini did not run for this cluster.

ALTER TABLE story_clusters
  ADD COLUMN IF NOT EXISTS editorial_importance SMALLINT,
  ADD COLUMN IF NOT EXISTS story_type TEXT,
  ADD COLUMN IF NOT EXISTS has_binding_consequences BOOLEAN;

-- Index on editorial_importance for ranking queries
CREATE INDEX IF NOT EXISTS idx_story_clusters_editorial_importance
  ON story_clusters (editorial_importance DESC NULLS LAST);

-- Index on story_type for gate filtering
CREATE INDEX IF NOT EXISTS idx_story_clusters_story_type
  ON story_clusters (story_type);
