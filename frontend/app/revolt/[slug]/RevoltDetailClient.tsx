'use client';

import { use, useEffect, useState } from 'react';
import Link from 'next/link';
import type { Revolution } from '../types';
import { fetchRevolution } from '../data';
import RevolutionDetail from '../components/RevolutionDetail';

export default function RevoltDetailClient({ slugPromise }: { slugPromise: Promise<{ slug: string }> }) {
  const { slug } = use(slugPromise);
  const [state, setState] = useState<'loading' | 'ready' | 'missing'>('loading');
  const [revolution, setRevolution] = useState<Revolution | null>(null);

  useEffect(() => {
    let cancelled = false;
    setState('loading');
    fetchRevolution(slug).then((r) => {
      if (cancelled) return;
      if (r) { setRevolution(r); setState('ready'); }
      else setState('missing');
    });
    return () => { cancelled = true; };
  }, [slug]);

  if (state === 'loading') return <p className="rev-loading">Reading the record&hellip;</p>;
  if (state === 'missing' || !revolution) {
    return (
      <div className="rev-empty">
        <p>That revolution is not in the archive yet.</p>
        <p><Link href="/revolt">&larr; Back to void --revolt</Link></p>
      </div>
    );
  }
  return <RevolutionDetail revolution={revolution} />;
}
