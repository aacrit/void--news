'use client';

import Link from 'next/link';
import { OUTCOME_LABELS } from '../anatomy';
import RevoltTimeline from './RevoltTimeline';

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
  return (
    <div className="rev-shell">
      <section className="rev-hero">
        <p className="rev-hero__kicker">void --revolt</p>
        <h1 className="rev-hero__title">The Anatomy of Revolution</h1>
        <p className="rev-hero__sub">
          Revolutions are not random. They share a skeleton: a broke and brittle regime, a
          spark, a radical turn, a reckoning. Here every major revolution is laid over that
          same arc, in order, so you can see where each one broke from the pattern. Active
          uprisings are marked live and read against what the record predicts.
        </p>
      </section>

      <section>
        <h2 className="rev-banner">Every revolution, on one arc</h2>
        <p className="rev-prose" style={{ marginBottom: 'var(--space-2)' }}>
          The whole record in order, from the English Civil War to the uprisings of this year.
          Scroll sideways to walk the timeline; the live ones are marked. Analytical, not
          predictive. Not an endorsement.
        </p>
      </section>

      <RevoltTimeline />

      <section>
        <h2 className="rev-banner">Browse the arc</h2>
        <p className="rev-browse__group-label">By how it ended</p>
        <div className="rev-browse">
          {BROWSE_OUTCOMES.map((o) => (
            <Link key={o.key} href={`/revolt/outcome/${o.key}`} className="rev-browse__chip">{o.label}</Link>
          ))}
          <Link href="/revolt/active" className="rev-browse__chip rev-browse__chip--accent">The Living &rarr;</Link>
          <Link href="/revolt/compare" className="rev-browse__chip rev-browse__chip--accent">Compare &rarr;</Link>
        </div>
        <p className="rev-browse__group-label">By how far it went</p>
        <div className="rev-browse">
          {BROWSE_PHASES.map((p) => (
            <Link key={p.key} href={`/revolt/phase/${p.key}`} className="rev-browse__chip">{p.label}</Link>
          ))}
        </div>
      </section>
    </div>
  );
}
