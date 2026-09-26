-- Track which LLM generated each daily brief (claude-sonnet / gemini-flash / rule-based)
ALTER TABLE daily_briefs ADD COLUMN IF NOT EXISTS generator TEXT;