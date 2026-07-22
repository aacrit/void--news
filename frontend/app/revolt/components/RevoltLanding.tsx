'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import type { Revolution } from '../types';
import { isActiveStatus, statusRank } from '../types';
import { OUTCOME_LABELS } from '../anatomy';
import { fetchRevolutions } from '../data';
import RevolutionCard from './RevolutionCard';

/* A few high-signal browse entry points into the phase/outcome browsers. */
const BROWSE_OUTCOMES: { key: string; label: string }[] = [
  { key: 'independence', label: OUTCOME_LABELS['independence'] },
  { key: 'consolidated-democracy', label: OUTCOME_LABELS['consolidated-democracy'] },
  { key: 'consolidated-autocracy', label: OUTCOME_LABELS['consolidated-autocracy'] },
  { key: 'civil-war', label: OUTCOME_LABELS['civil-war'] },
  { key: 'failed-suppressed', label: OUTCOME_LABELS['failed-suppressed'] },
];
const BROWSE_PHASES: { key: string; label: string }[] = [
  { key: 'terror-virtue', label: 'Reached the Terror' },
  { key: 'consolidation', label: 'Reached consolidation' },
];

export default function RevoltLanding() {
  const [revolutions, setRevolutions] = useState<Revolution[] | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchRevolutions().then((data) => {
      if (!cancelled) setRevolutions(data);
    });
    return () => { cancelled = true; };
  }, []);

  const concluded = (revolutions ?? []).filter((r) => !isActiveStatus(r.status));
  const active = (revolutions ?? [])
    .filter((r) => isActiveStatus(r.status))
    .sort((a, b) => statusRank(a.status) - statusRank(b.status));

  return (
    <div className="rev-shell">
      <section className="rev-hero">
        <p className="rev-hero__kicker">void --revolt</p>
        <h1 className="rev-hero__title">The Anatomy of Revolution</h1>
        <p className="rev-hero__sub">
          Revolutions are not random. They share a skeleton: a broke and brittle regime, a
          spark, a radical turn, a reckoning. Here every major revolution is laid over that
          same arc, so you can see where each one broke from the pattern. Then a living portal
          into the uprisings happening now, read against what the record predicts.
        </p>
      </section>

      {revolutions === null && <p className="rev-loading">Reading the record&hellip;</p>}

      {active.length > 0 && (
        <section>
          <h2 className="rev-banner">The Living &middot; movements on the arc</h2>
          <p className="rev-prose" style={{ marginBottom: 'var(--space-4)' }}>
            Active uprisings first, then the dormant and suppressed ones kept here for
            comparison, each placed on the arc and weighed against the historical record.
            Analytical, not predictive. Not an endorsement.
          </p>
          <div className="rev-grid">
            {active.map((r) => <RevolutionCard key={r.slug} r={r} />)}
          </div>
        </section>
      )}

      {concluded.length > 0 && (
        <section>
          <h2 className="rev-banner">The Archive &middot; revolutions of the past</h2>
          <div className="rev-grid">
            {concluded.map((r) => <RevolutionCard key={r.slug} r={r} />)}
          </div>
        </section>
      )}

      {revolutions !== null && revolutions.length > 0 && (
        <section>
          <h2 className="rev-banner">Browse the arc</h2>
          <p className="rev-browse__group-label">By how it ended</p>
          <div className="rev-browse">
            {BROWSE_OUTCOMES.map((o) => (
              <Link key={o.key} href={`/revolt/outcome/${o.key}`} className="rev-browse__chip">{o.label}</Link>
            ))}
            <Link href="/revolt/compare" className="rev-browse__chip rev-browse__chip--accent">Compare side by side &rarr;</Link>
          </div>
          <p className="rev-browse__group-label">By how far it went</p>
          <div className="rev-browse">
            {BROWSE_PHASES.map((p) => (
              <Link key={p.key} href={`/revolt/phase/${p.key}`} className="rev-browse__chip">{p.label}</Link>
            ))}
          </div>
        </section>
      )}

      {revolutions !== null && revolutions.length === 0 && (
        <p className="rev-empty">No revolutions loaded yet.</p>
      )}
    </div>
  );
}
