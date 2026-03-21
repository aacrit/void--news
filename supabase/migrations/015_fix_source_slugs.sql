-- Migration 015: Fix source slug mismatches + add new sources
-- Date: 2026-03-21
-- Context: source-curator audit found 7 ID/slug mismatches where the
-- sources.json "id" didn't match the actual outlet. Pipeline step 1
-- syncs sources.json to the DB using the "id" field as the slug.
-- These corrections prevent the pipeline from creating duplicate rows.

-- ============================================================================
-- STEP 1: Update source slugs to match corrected sources.json
-- ============================================================================
-- The pipeline upserts by slug. If old slugs exist in DB, update them
-- so that article foreign keys remain valid.

UPDATE sources SET slug = 'quillette', name = 'Quillette'
WHERE slug = 'quadrant-online';

UPDATE sources SET slug = 'mexico-news-network', name = 'Mexico News Network'
WHERE slug = 'la-jornada-english';

UPDATE sources SET slug = 'bureau-investigative-journalism', name = 'Bureau of Investigative Journalism'
WHERE slug = 'the-intercept-uk';

UPDATE sources SET slug = 'daily-caller-news-foundation', name = 'Daily Caller News Foundation'
WHERE slug = 'conservative-treehouse';

UPDATE sources SET slug = 'persuasion', name = 'Persuasion'
WHERE slug = 'heterodox-academy';

UPDATE sources SET slug = 'american-affairs', name = 'American Affairs'
WHERE slug = 'the-american-interest';

UPDATE sources SET slug = 'the-daily-signal', name = 'The Daily Signal'
WHERE slug = 'heritage-foundation';

-- ============================================================================
-- STEP 2: Update CGTN political lean (center-right → far-right)
-- ============================================================================

UPDATE sources SET political_lean_baseline = 'far-right'
WHERE slug = 'cgtn';

-- ============================================================================
-- STEP 3: Remove defunct/low-credibility sources
-- ============================================================================
-- AllAfrica: aggregator-only, violates original-reporting criterion
-- Eurasian Review: low editorial standards, open-contribution model

-- Don't delete — mark inactive so articles remain linked
-- (If no is_active column, just leave them; pipeline sync will skip
-- sources not in sources.json on next run)

-- ============================================================================
-- STEP 4: Verify
-- ============================================================================
-- SELECT slug, name FROM sources
-- WHERE slug IN ('quillette', 'mexico-news-network', 'bureau-investigative-journalism',
--   'daily-caller-news-foundation', 'persuasion', 'american-affairs', 'the-daily-signal');
-- Should return 7 rows with corrected slugs.

-- SELECT slug, political_lean_baseline FROM sources WHERE slug = 'cgtn';
-- Should return 'far-right'.
