-- Add a short generated "Editor's Note" to weekly digests.
-- Italic editorial sidebar beside the two cover features (magazine layout).
-- ~120-150 words of flowing prose in the void editorial voice; generated on
-- gemini-2.5-flash (flagship-only flash routing), rule-based fallback = "".
ALTER TABLE weekly_digests
    ADD COLUMN IF NOT EXISTS editor_note TEXT;
