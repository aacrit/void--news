/* ---------------------------------------------------------------------------
   The per-story share card, and the one decision about which stories get one.

   Composition lives in `app/lib/ogCard.tsx`, the composer every Void card is
   drawn by. What is here is the part that is about a STORY: the headline, how
   many outlets it was read across, and the card's own word with its count.

   THE SHARE CARD SAYS WHAT THE PAGE SAYS (CEO decision 4, 2026-10-02). It
   used to gate on `leanLabelState`, the confidence-gated MEAN, a third rule
   beside the card's roster word and the Bench: audit 6 (2026-10-02) found a
   card printing "Leans right" whose share card would print no lean at all,
   at aggregate confidence 0.463. It now prints `storyShapeLabel` and
   `leanShapeCount`, the feed card's word and count from the same per-outlet
   histogram, and test/labels.test.mjs asserts the two agree on every story
   of the latest edition. The share card is the least correctable surface,
   which is the reason it must never disagree with the page it links to.

   WHICH STORIES. The archive is 1,577 rows and every card is a satori render
   at build time, so cards are emitted for the LATEST EDITION only, which is
   what anyone is actually sharing. Older permalinks keep the site-wide brand
   card (page.tsx re-declares it for exactly those). Raising this is one
   constant: EDITIONS_WITH_CARDS.
   --------------------------------------------------------------------------- */

import {
  getArchiveRows,
  archiveRowToStory,
  type PrintedStoryRow,
} from "../../lib/archive";
import { storyShapeLabel, leanShapeCount, leanShape } from "../../lib/biasColors";
import { voidCard, size, contentType, ACCENT_NEWS } from "../../lib/ogCard";

export { size, contentType };

/** Deep Dive is the section a standalone story page belongs to (CLAUDE.md,
 *  Brand): the full cross-source read, not the feed. */
export const STORY_SECTION = "Deep Dive";

/** How many of the most recent editions get their own cards. One edition is
 *  20 stories, which is 20 renders on top of the build. */
const EDITIONS_WITH_CARDS = 1;

let _ids: Promise<Set<string>> | null = null;

/** The ids that have a card of their own, memoized for the build process.
 *  Read by BOTH the image route (which params to emit) and the page's
 *  metadata (whether to yield to the file convention or re-declare the
 *  site-wide card); they cannot be allowed to disagree. */
export function storyCardIds(): Promise<Set<string>> {
  if (_ids) return _ids;
  _ids = (async () => {
    const rows = await getArchiveRows();
    const editions = [...new Set(rows.map((r) => r.printed_on).filter(Boolean))]
      .sort()
      .slice(-EDITIONS_WITH_CARDS);
    const keep = new Set(editions);
    return new Set(rows.filter((r) => keep.has(r.printed_on)).map((r) => r.id));
  })();
  return _ids;
}

export async function hasStoryCard(id: string): Promise<boolean> {
  return (await storyCardIds()).has(id);
}

/** The words the share card prints about a story's lean: the card's own word
 *  and the count behind it. Exported so the gate can compare it with the
 *  feed card's word on every story of the latest edition. */
export function storyCardLean(row: PrintedStoryRow): { word: string; count: string | null } {
  const story = archiveRowToStory(row);
  const unscored = !!story.sigilData.unscored;
  const word = storyShapeLabel(story.biasSpread, unscored).text;
  const tally = unscored ? null : leanShapeCount(story.biasSpread);
  const shape = unscored ? "unscored" : leanShape(story.biasSpread);
  /* The full sentence where it is short ("15 of 22 outlets right of
     centre"); both wings where the full one would run off a 1200px card. */
  const count = !tally ? null
    : shape === "split" || shape === "balanced" ? tally.short : tally.full;
  return { word, count };
}

export function storyCard(row: PrintedStoryRow) {
  const { word, count } = storyCardLean(row);
  const n = row.source_count || 0;
  return voidCard({
    section: STORY_SECTION,
    accent: ACCENT_NEWS,
    title: row.title,
    meta: [n > 0 ? `${n} ${n === 1 ? "source" : "sources"}` : null, word, count],
    tagline: "Every source, placed. Not averaged.",
  });
}
