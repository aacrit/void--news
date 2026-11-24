/* ---------------------------------------------------------------------------
   MoreStories: the band under the front page's cards (CEO 2026-10-28, phase 1
   of the 30-story evaluation).

   The next FEED_MORE_STORIES ranks after the displayed cards, as a numbered
   list of headlines. Each one links to its printed /story/ page, the same page
   a card opens. Deliberately secondary to the cards: ranks 21 to 30 carry
   fewer sources (median 12 against 17) and earn a lean word less often (58%
   against 80%), so they get a line each, not a card.

   Only stories with a printed page are listed: a band entry is never a
   "/?story=" fallback link, and until the pipeline prints a story it simply is
   not here. An empty band renders nothing. The front page's count ("20
   stories") and the served-output gate's card count are the cards alone.
   --------------------------------------------------------------------------- */
import type { Story } from "../lib/types";
import { storyShapeLabel } from "../lib/biasColors";
import { BASE_PATH } from "../lib/utils";

const STORY_PAGE = /^\/story\/[0-9a-f-]{36}\/$/;

export default function MoreStories({ stories, startRank }: { stories: Story[]; startRank: number }) {
  const items = stories.filter((s) => s.permalink && STORY_PAGE.test(s.permalink));
  if (items.length === 0) return null;
  return (
    <section className="more-stories" aria-labelledby="more-stories-label">
      <h2 id="more-stories-label" className="more-stories__label">More stories</h2>
      <ol className="more-stories__list" start={startRank}>
        {items.map((s) => {
          const lean = storyShapeLabel(s.sigilData?.biasSpread, !!s.sigilData?.unscored);
          const sources = s.sigilData?.sourceCount ?? s.source?.count ?? 0;
          return (
            <li key={s.id} className="more-stories__item">
              <a className="more-stories__link" href={`${BASE_PATH}${s.permalink}`}>
                {s.title}
              </a>
              <span className="more-stories__meta">
                <span style={{ color: lean.color }}>{lean.text}</span>
                <span aria-hidden="true">{" · "}</span>
                {sources} sources
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
