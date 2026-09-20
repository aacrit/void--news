/* ---------------------------------------------------------------------------
   History share cards.

   Composition lives in `app/lib/ogCard.tsx`, shared with Weekly. What is here
   is the part that is about HISTORY: what the kicker says, and the fact that
   the tagline is the section's own claim rather than the feed's.

   The spectrum along the bottom is kept deliberately. In the daily feed it is
   coverage placed left to right rather than averaged; in History it is the
   five-lens perspective set. Same mark, same meaning: every side, placed.
   --------------------------------------------------------------------------- */

import { sectionCard, size, contentType, ACCENT_HISTORY } from "../lib/ogCard";
import { HISTORY_TAGLINE } from "./historyMeta";

export { size, contentType };

export function landingCard(eventCount: number) {
  return sectionCard({
    wordmark: "VOID HISTORY",
    kicker: `${eventCount || 78} events  ·  every side`,
    headline: "One event. Every side.",
    tagline: HISTORY_TAGLINE,
    accent: ACCENT_HISTORY,
  });
}

export function eventCard(opts: { title: string; era?: string; region?: string }) {
  // Era and region are what an event page's own furniture leads with, and
  // between them they place the story in time and on the map before the
  // reader has read a word of the headline.
  // The catalog stores these as slugs, so the card was setting "SOUTH-ASIA".
  // A share card is the most public surface in the product; it does not get to
  // show the taxonomy's punctuation.
  const human = (v?: string) => (v || "").replace(/[-_]+/g, " ").trim();
  const parts = [human(opts.era), human(opts.region)].filter(Boolean);
  return sectionCard({
    wordmark: "VOID HISTORY",
    kicker: parts.length ? parts.join("  ·  ") : "every side",
    headline: opts.title,
    tagline: HISTORY_TAGLINE,
    accent: ACCENT_HISTORY,
  });
}
