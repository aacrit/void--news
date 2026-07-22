'use client';

import type { LiveCard } from '../types';
import { timeAgo } from '../../lib/utils';

/* Matched story_clusters as timestamped tiles. Labeled and visually separated
   from the analysis: "related coverage from the feed", never an endorsed fact. */
export default function LiveRevoltCards({ cards }: { cards: LiveCard[] }) {
  if (cards.length === 0) return null;
  return (
    <section aria-label="Related live coverage" style={{ marginTop: 'var(--space-5)' }}>
      <p className="rev-livecards__label">Related coverage from the void --news feed</p>
      <div className="rev-livecards">
        {cards.map((c) => (
          <article className="rev-livecard" key={c.id}>
            <div className="rev-livecard__title">{c.title}</div>
            <div className="rev-livecard__meta">
              {c.category}
              {c.lastUpdated ? ` · ${timeAgo(c.lastUpdated)}` : ''}
              {c.sourceCount ? ` · ${c.sourceCount} sources` : ''}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
