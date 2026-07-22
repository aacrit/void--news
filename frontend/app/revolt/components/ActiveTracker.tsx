'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import type { Revolution } from '../types';
import { STATUS_LABELS, phaseSpec } from '../anatomy';
import { successBand, bandClass } from '../scoring';
import { fetchActiveRevolutions } from '../data';

function currentPhaseLabel(r: Revolution): string {
  const reached = r.phases.filter((p) => p.reached);
  const last = reached[reached.length - 1];
  if (!last) return 'Preconditions';
  return phaseSpec(last.phase)?.label ?? last.label;
}

export default function ActiveTracker() {
  const [rows, setRows] = useState<Revolution[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchActiveRevolutions().then((d) => { if (!cancelled) setRows(d); });
    return () => { cancelled = true; };
  }, []);

  return (
    <div className="rev-shell">
      <section className="rev-hero">
        <p className="rev-hero__kicker">void --revolt &middot; the living</p>
        <h1 className="rev-hero__title">The Situation Board</h1>
        <p className="rev-hero__sub">
          Uprisings and revolutions underway now, each placed on the arc and weighed against the
          historical record. Analytical, not predictive. Not an endorsement of any movement.
        </p>
      </section>

      {rows === null && <p className="rev-loading">Reading the record&hellip;</p>}

      <div className="rev-tracker" style={{ marginTop: 'var(--space-4)' }}>
        {(rows ?? []).map((r) => {
          const band = successBand(r.successFactors);
          return (
            <Link href={`/revolt/active/${r.slug}`} className="rev-card rev-card--active" key={r.slug}>
              <div className="rev-card__meta">
                <span className="rev-live-stamp"><span className="rev-live-stamp__dot" aria-hidden="true" />Live</span>
                <span>{r.country}</span>
              </div>
              <div className="rev-card__title">{r.title}</div>
              <div className="rev-card__outcome">{STATUS_LABELS[r.status]}</div>
              <div className="rev-card__outcome">Phase: {currentPhaseLabel(r)}</div>
              {band && <div style={{ marginTop: 8 }}><span className={`rev-band ${bandClass(band)}`}>{band}</span></div>}
            </Link>
          );
        })}
      </div>

      {rows !== null && rows.length === 0 && <p className="rev-empty">No active movements tracked right now.</p>}
    </div>
  );
}
