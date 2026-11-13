'use client';

import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import type { Revolution, LiveCard } from '../../types';
import { fetchRevolution, fetchLiveClustersFor } from '../../data';
import ActiveRevolutionDetail from '../../components/ActiveRevolutionDetail';

export default function ActiveDetailClient({ slugPromise }: { slugPromise: Promise<{ slug: string }> }) {
  const { slug } = use(slugPromise);
  const [state, setState] = useState<'loading' | 'ready' | 'missing'>('loading');
  const [revolution, setRevolution] = useState<Revolution | null>(null);
  const [liveCards, setLiveCards] = useState<LiveCard[]>([]);

  useEffect(() => {
    let cancelled = false;
    setState('loading');
    fetchRevolution(slug).then(async (r) => {
      if (cancelled) return;
      if (!r) { setState('missing'); return; }
      setRevolution(r);
      setState('ready');
      const cards = await fetchLiveClustersFor(r);
      if (!cancelled) setLiveCards(cards);
    });
    return () => { cancelled = true; };
  }, [slug]);

  if (state === 'loading') return <p className="rev-loading">Reading the record&hellip;</p>;
  if (state === 'missing' || !revolution) {
    return (
      <div className="rev-empty">
        <p>That movement is not tracked yet.</p>
        <p><Link href="/revolt/active">&larr; Back to The Living</Link></p>
      </div>
    );
  }
  return <ActiveRevolutionDetail revolution={revolution} liveCards={liveCards} />;
}
