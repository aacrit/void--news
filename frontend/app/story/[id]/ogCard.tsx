/* ---------------------------------------------------------------------------
   The per-story share card, and the one decision about which stories get one.

   Composition lives in `app/lib/ogCard.tsx`, the composer every Void card is
   drawn by. What is here is the part that is about a STORY: the headline, how
   many outlets it was read across, and the measured lean when the measurement
   is one the product is willing to state.

   THE LEAN IS SHOWN ONLY WHEN IT IS CONFIDENT. A share card is the most public
   surface in the product and the least correctable, so it goes through the
   SAME gate as the feed card, the Sigil popup and the Deep Dive
   (`leanLabelState` in lib/biasColors). "Contested", "Flat" and "Unscored" are
   honest on a page that can explain them; on a card, with no room to say what
   they mean, the line is simply left out and the card shows the source count
   alone.

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
import { leanLabel, leanLabelState } from "../../lib/biasColors";
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

export function storyCard(row: PrintedStoryRow) {
  const story = archiveRowToStory(row);
  const lean = story.biasScores.politicalLean;
  const confident =
    !story.sigilData.unscored &&
    leanLabelState(lean, story.biasSpread, row.source_count) === "confident";

  const n = row.source_count || 0;
  return voidCard({
    section: STORY_SECTION,
    accent: ACCENT_NEWS,
    title: row.title,
    meta: [n > 0 ? `${n} ${n === 1 ? "source" : "sources"}` : null,
           confident ? leanLabel(lean) : null],
    tagline: "Every source, placed. Not averaged.",
  });
}
