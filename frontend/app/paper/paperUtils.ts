import type { Story } from "../lib/types";

/* ---------------------------------------------------------------------------
   Paper layout helpers.

   Paper prints the SAME stories in the SAME order as the front page, so every
   function here is pure presentation over an already-ranked list: nothing
   re-sorts, nothing re-ranks, nothing invents a fact. The category-to-city
   datelines, the per-edition section names and the filler copy that used to
   live here were removed on 2026-09-21: a Ukraine story datelined BEIRUT is a
   published factual error, and the edition routes they served no longer exist.
   --------------------------------------------------------------------------- */

/** Display weight of one article. Assigned by rank position only, so the
 *  printed page reads in the order the ranker produced. */
export type ArticleTier = "banner" | "major" | "standard" | "brief" | "bulletin";

export function assignTier(index: number): ArticleTier {
  if (index === 0) return "banner";
  if (index <= 2) return "major";
  if (index <= 8) return "standard";
  if (index <= 14) return "brief";
  return "bulletin";
}

/** How many decks (sub-heads under the headline) a tier carries. */
function deckCount(tier: ArticleTier): number {
  if (tier === "banner") return 3;
  if (tier === "major") return 2;
  if (tier === "standard") return 1;
  return 0;
}

/**
 * Pull the opening sentences of a summary up as headline decks and return the
 * rest as body copy. Verbatim: a deck is a sentence the summary already says,
 * never a rewrite. When lifting the decks would leave no body behind, the
 * summary stays whole and the article runs without decks.
 */
export function splitDecks(
  summary: string,
  tier: ArticleTier,
): { decks: string[]; body: string } {
  const whole = { decks: [] as string[], body: summary };
  const want = deckCount(tier);
  if (want === 0 || !summary) return whole;

  const sentences = summary
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter((s) => s.length > 15);
  if (sentences.length <= want) return whole;

  const decks = sentences.slice(0, want).map((s) => s.replace(/\.$/, ""));
  let body = summary;
  for (const deck of decks) {
    const at = body.indexOf(deck);
    if (at === -1) return whole;
    body = body.slice(at + deck.length).replace(/^[.!?\s]+/, "");
  }
  return body.length > 0 ? { decks, body } : whole;
}

/* --- Front page distribution -------------------------------------------- */

export interface FrontPageLayout {
  /** Rank 0, run across the top of the page. */
  lead: Story | null;
  /** Ranks below the lead, split left / centre / right in reading order. */
  zoneA: Story[];
  zoneB: Story[];
  zoneC: Story[];
}

/**
 * Split an already-ranked list across the three zones WITHOUT reordering it.
 * Document order is rank order (lead, then A, then B, then C), which is what
 * the P-02 gate compares against the front page. Zone widths are 2:1:2 reading
 * columns, so the slices are sized the same way.
 */
export function distributeStories(stories: Story[]): FrontPageLayout {
  if (stories.length === 0) {
    return { lead: null, zoneA: [], zoneB: [], zoneC: [] };
  }
  const [lead, ...rest] = stories;
  const a = Math.round((rest.length * 2) / 5);
  const b = Math.round(rest.length / 5);
  return {
    lead,
    zoneA: rest.slice(0, a),
    zoneB: rest.slice(a, a + b),
    zoneC: rest.slice(a + b),
  };
}
