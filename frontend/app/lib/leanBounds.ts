/* ---------------------------------------------------------------------------
   leanBounds: the two engine constants that page copy is allowed to quote.

   How far an article's own words may move its outlet's lean, and the length
   under which they are not read for lean at all. Both are code constants, not
   measurements, so they do not go stale between runs; the day's MEASURED
   numbers (how far the words actually moved scores) come from
   frontend/build-data/engine.json and are printed only where that file is read.

   Mirrors, asserted equal by tests/test_engine_health.py:
     RATED_DELTA_MAX   pipeline/analyzers/political_lean.py  _TEXT_DELTA_MAX
     UNRATED_DELTA_MAX pipeline/analyzers/political_lean.py  _CENTER_TEXT_DELTA_MAX
     FULL_TEXT_WORDS   pipeline/main.py word-count gate, validation/engine_health.py

   Why this file exists: /about said "a full article leans on its words". On a
   rated outlet a full article's words can move the score 10 points at most, and
   on 2026-09-25 they moved it 1.54 on average. The copy was the architecture's
   intent, not its behaviour.
   --------------------------------------------------------------------------- */

/** Most a rated outlet's article can move off the outlet's lean, in points. */
export const RATED_DELTA_MAX = 10;
/** Most an unrated outlet's article can move off the neutral midpoint. */
export const UNRATED_DELTA_MAX = 24;
/** Under this many words an article is scored on its outlet's record alone. */
export const FULL_TEXT_WORDS = 150;
