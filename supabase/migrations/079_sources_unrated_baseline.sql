-- 079: admit 'unrated' to the sources political_lean_baseline CHECK.
--
-- WHY THIS IS A SEPARATE FILE FROM 078
-- The same constraint change was added to 078 after 078 had already been
-- applied to production. Migrations are tracked by FILENAME in _migrations, so
-- editing an applied file is a no-op against any database that already has it:
--
--   run @ 2026-08-13T23:34  [ok]   078_lean_unscored.sql          <- pre-edit content
--   run @ 2026-08-14T01:14  [skip] 078_lean_unscored.sql (already applied)
--
-- Production therefore has 078's column, index, view and function, but NOT the
-- widened constraint. It needs its own file to be picked up. 078 keeps the
-- block as well so a fresh bootstrap is self-consistent; this migration is
-- written idempotently (DROP IF EXISTS then ADD) so applying both in sequence
-- on a new database converges to the same state.
--
-- WHY IT MATTERS BEFORE THE NEXT PIPELINE RUN
-- main.py step 1 upserts data/sources.json into the sources table on every run,
-- and 294 rows now carry political_lean_baseline = 'unrated'. Against the
-- 7-point constraint from migration 007 that upsert fails on every one of them
-- at the first step of the run:
--
--   ERROR:  new row for relation "sources" violates check constraint
--           "sources_political_lean_baseline_check"
--   DETAIL: Failing row contains (k, k, Nation Africa, international, unrated).
--
-- 'unrated' is NOT an eighth point on the spectrum. It records that an outlet
-- has no placement on the left/right axis at all, as distinct from 'center',
-- which is a positive finding of centrism (a wire cooperative, a broadcaster
-- under an impartiality charter). See BASELINE_MAP in
-- pipeline/analyzers/political_lean.py.

ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_political_lean_baseline_check;

ALTER TABLE sources ADD CONSTRAINT sources_political_lean_baseline_check
  CHECK (political_lean_baseline IN (
    'far-left', 'left', 'center-left', 'center',
    'center-right', 'right', 'far-right', 'varies', 'unrated'
  ));
