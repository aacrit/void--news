/* ---------------------------------------------------------------------------
   engineStats: the shape of frontend/build-data/engine.json, and the few
   phrasings page copy may build from it.

   engine.json is written by pipeline/export_static.py from
   pipeline/validation/engine_health.py after every run: what the bias engine
   read (body length by feed class) and what it did (how far an article's words
   moved a rated outlet's lean). It is read at BUILD time by app/sources/page.tsx
   and passed down as a prop, so the served HTML carries the day's numbers and
   no client fetch is needed.

   The numbers change every day, so copy must never restate them as literals
   (Rule 1: "a number that goes stale is a future error"). It prints them from
   this object, dated by the run they describe.
   --------------------------------------------------------------------------- */

export interface EngineStats {
  run: { newest_fetch: string; window_hours: number; articles: number } | null;
  feeds?: {
    direct: FeedClass;
    google_news: FeedClass;
  };
  scoring?: { text_read: number; outlet_only: number; outlet_only_share: number };
  text_movement_rated?: {
    articles: number;
    mean_abs?: number;
    zero_share?: number;
    min?: number;
    max?: number;
  };
}

interface FeedClass {
  sources: number;
  articles: number;
  median_words: number;
  full_share: number;
  headline_share: number;
}

/** "25 September 2026", from the run's newest fetch. Empty if unknown. */
export function engineRunDate(e: EngineStats | null): string {
  const iso = e?.run?.newest_fetch;
  if (!iso) return "";
  const d = new Date(iso.replace(" ", "T") + "Z");
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
}

/** A share as a whole percentage: 0.6111 -> "61%". */
export const pct = (x: number | undefined): string =>
  x === undefined ? "" : `${Math.round(x * 100)}%`;

export type CompleteEngineStats = {
  run: NonNullable<EngineStats["run"]>;
  feeds: NonNullable<EngineStats["feeds"]>;
  scoring: NonNullable<EngineStats["scoring"]>;
  text_movement_rated: Required<NonNullable<EngineStats["text_movement_rated"]>>;
};

/** Google News articles under the full-text threshold: the count copy may print
 *  as "of them", which stays true whatever share of the outlet-only total they are. */
export const googleNewsHeadlineOnly = (e: CompleteEngineStats): number =>
  Math.round(e.feeds.google_news.articles * (1 - e.feeds.google_news.full_share));

/** True when the object carries everything the methodology copy prints. */
export function engineComplete(e: EngineStats | null): e is CompleteEngineStats {
  return !!(e?.run && e.scoring && e.feeds && e.text_movement_rated?.mean_abs !== undefined
            && e.text_movement_rated.zero_share !== undefined);
}
