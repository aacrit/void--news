/* ---------------------------------------------------------------------------
   rosterConfig: the roster's size, imported from frontend/config/roster.json.

   That file is generated from data/sources.json by
   scripts/roster/emit_roster_config.py, which runs at the end of
   scripts/roster/add_sources.py --apply so the two cannot be updated
   separately, and tests/test_roster_config.py asserts they agree.

   Never restate these numbers as literals in a component. "1,016 sources" was
   hand-written in nine files under app/ plus the served manifest, four docs,
   two pipeline modules and two tests, which is fifteen places to be wrong the
   next time an outlet is added. feedConfig.ts carried exactly this warning for
   the feed size and the prose restated it anyway; that is what
   frontend/test/copy-facts.test.mjs exists to catch.

   Two integers rather than the roster itself: data/sources.json is over a
   megabyte, and importing it into a client component would ship the whole
   roster to every reader to print one number.
   --------------------------------------------------------------------------- */
import cfg from "../../config/roster.json";

/** Outlets on the curated roster (data/sources.json). */
export const ROSTER_SOURCES: number = cfg.sources;
/** Distinct countries those outlets publish from. */
export const ROSTER_COUNTRIES: number = cfg.countries;

/** The count as page copy writes it: grouped with a thousands separator. */
export const ROSTER_SOURCES_TEXT: string = ROSTER_SOURCES.toLocaleString("en-US");

/* The three credibility tiers, which /about and /sources print as exact
   counts. These were literals too (43 / 373 / 600). A breakdown that does not
   sum to its own total is the kind of error a reader can check, and
   emit_roster_config.py refuses to write one. */
export const ROSTER_US_MAJOR: number = cfg.us_major;
export const ROSTER_INTERNATIONAL: number = cfg.international;
export const ROSTER_INDEPENDENT: number = cfg.independent;
