'use client';

import type { LiveCard } from '../types';
import { timeAgo, BASE_PATH } from '../../lib/utils';

/* Matched story_clusters as timestamped tiles. Labeled and visually separated
   from the analysis: "related coverage from the feed", never an endorsed fact.
   Each links into the story's deep-dive popout on void --news (?story=<id>). */
export default function LiveRevoltCards({ cards }: { cards: LiveCard[] }) {
  if (cards.length === 0) return null;
  return (
    <section aria-label="Related live coverage" style={{ marginTop: 'var(--space-5)' }}>
      <p className="rev-livecards__label">Related coverage from the void --news feed</p>
      <div className="rev-livecards">
        {cards.map((c) => (
          <a
            className="rev-livecard"
            key={c.id}
            href={`${BASE_PATH}/?story=${c.id}`}
            aria-label={`Open the deep dive for: ${c.title}`}
          >
            <div className="rev-livecard__title">{c.title}</div>
            <div className="rev-livecard__meta">
              {c.category}
              {c.lastUpdated ? ` · ${timeAgo(c.lastUpdated)}` : ''}
              {c.sourceCount ? ` · ${c.sourceCount} sources` : ''}
              <span className="rev-livecard__cta" aria-hidden="true"> · open deep dive &rarr;</span>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}
