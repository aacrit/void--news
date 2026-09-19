/* ---------------------------------------------------------------------------
   feedConfig: the feed-size constants, imported from frontend/config/feed.json.

   The same file is read by pipeline/utils/feed_config.py (Python),
   scripts/verify-production.sh (shell) and tests/test_feed_config.py (CI).
   Never restate these numbers as literals in a component: the front page,
   the JSON-LD ItemList, the build guard and the pipeline's summary window all
   drifted apart when they were literals (2026-09-06).
   --------------------------------------------------------------------------- */
import cfg from "../../config/feed.json";

/** Cards rendered on the homepage. */
export const FEED_DISPLAYED: number = cfg.displayed;
/** Stage 2 bench size: clusters summarized, critiqued and validated. */
export const FEED_CANDIDATES: number = cfg.candidates;
/** Build fails below this many displayable stories. */
export const FEED_MIN_DISPLAYABLE: number = cfg.minDisplayable;
/** Top band governed by the diversity partition and lead gates. */
export const FEED_LEAD_BAND: number = cfg.leadBand;
