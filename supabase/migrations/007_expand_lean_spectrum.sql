-- Expand political_lean_baseline from 5-point to 7-point spectrum
-- Old: left, center-left, center, center-right, right, varies
-- New: far-left, left, center-left, center, center-right, right, far-right, varies

ALTER TABLE sources DROP CONSTRAINT IF EXISTS sources_political_lean_baseline_check;

ALTER TABLE sources ADD CONSTRAINT sources_political_lean_baseline_check
  CHECK (political_lean_baseline IN (
    'far-left', 'left', 'center-left', 'center',
    'center-right', 'right', 'far-right', 'varies'
  ));
