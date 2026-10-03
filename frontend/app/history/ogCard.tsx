/* ---------------------------------------------------------------------------
   History share cards.

   Composition lives in `app/lib/ogCard.tsx`, the one composer every Void card
   is drawn by. What is here is the part that is about HISTORY: that the
   nameplate reads "History" in the section's umber, what the meta line places
   (when it happened, and where), and that the tagline is the section's own
   claim rather than the feed's.

   History is a SECTION of Void News, not a product, so the card carries the
   VOID NEWS lockup and a History nameplate. It used to set a letter-spaced
   "VOID HISTORY" wordmark, which named a publication that does not exist.

   The spectrum along the bottom is kept deliberately. In the daily feed it is
   coverage placed left to right rather than averaged; in History it is the
   five-lens perspective set. Same mark, same meaning: every side, placed.
   --------------------------------------------------------------------------- */

import { voidCard, size, contentType, ACCENT_HISTORY } from "../lib/ogCard";
import { HISTORY_TAGLINE } from "./historyMeta";

export { size, contentType };

export const HISTORY_SECTION = "History";

export function landingCard(eventCount: number) {
  const n = eventCount || 78;
  return voidCard({
    section: HISTORY_SECTION,
    accent: ACCENT_HISTORY,
    title: "One event. Every side.",
    meta: [`${n} events`],
    tagline: "Primary sources. Named perspectives.",
  });
}

export function eventCard(opts: { title: string; date?: string; region?: string }) {
  // When it happened, and where: between them they place the story in time and
  // on the map before the reader has read a word of the headline.
  // The catalog stores the region as a slug, so the card was setting
  // "SOUTH-ASIA". A share card is the most public surface in the product; it
  // does not get to show the taxonomy's punctuation.
  const human = (v?: string) =>
    (v || "")
      .replace(/[-_]+/g, " ")
      .trim()
      .replace(/\b[a-z]/g, (c) => c.toUpperCase());
  return voidCard({
    section: HISTORY_SECTION,
    accent: ACCENT_HISTORY,
    title: opts.title,
    meta: [(opts.date || "").trim(), human(opts.region)],
    tagline: HISTORY_TAGLINE,
  });
}
