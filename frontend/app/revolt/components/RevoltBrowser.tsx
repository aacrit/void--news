'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import type { Revolution } from '../types';
import RevolutionCard from './RevolutionCard';

interface RevoltBrowserProps {
  kicker: string;
  heading: string;
  blurb: string;
  fetcher: () => Promise<Revolution[]>;
  /** re-run the fetch when this changes (the phase/outcome slug) */
  dep: string;
}

/* Shared list view for the phase + outcome browsers. */
export default function RevoltBrowser({ kicker, heading, blurb, fetcher, dep }: RevoltBrowserProps) {
  const [rows, setRows] = useState<Revolution[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    setRows(null);
    fetcher().then((d) => { if (!cancelled) setRows(d); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dep]);

  return (
    <div className="rev-shell">
      <section className="rev-hero">
        <p className="rev-hero__kicker">{kicker}</p>
        <h1 className="rev-hero__title">{heading}</h1>
        <p className="rev-hero__sub">{blurb}</p>
      </section>

      {rows === null && <p className="rev-loading">Reading the record&hellip;</p>}

      {rows !== null && rows.length === 0 && (
        <div className="rev-empty">
          <p>No revolutions in the archive match this yet.</p>
          <p><Link href="/revolt">&larr; Back to void --revolt</Link></p>
        </div>
      )}

      {rows !== null && rows.length > 0 && (
        <div className="rev-grid" style={{ marginTop: 'var(--space-4)' }}>
          {rows.map((r) => <RevolutionCard key={r.slug} r={r} />)}
        </div>
      )}
    </div>
  );
}
