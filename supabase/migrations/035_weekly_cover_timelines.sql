-- Add data-driven timeline storage to weekly digests
-- Separates real cluster-timestamp timelines from Gemini-generated essay text
ALTER TABLE weekly_digests
    ADD COLUMN IF NOT EXISTS cover_timelines JSONB DEFAULT '[]'::jsonb;
-- Format: [{"story_index": 0, "entries": [{"date": "Mon Mar 31", "title": "...", "source_count": 28, "cluster_id": "uuid"}]}]
