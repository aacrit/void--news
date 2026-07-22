'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import type { Revolution } from '../types';
import { REVOLT_ERAS, isActiveStatus } from '../types';
import { OUTCOME_LABELS, STATUS_LABELS } from '../anatomy';
import { HOOKS } from '../hooks';
import { fetchRevolutions } from '../data';

function eraLabel(era: string): string {
  return REVOLT_ERAS.find((e) => e.id === era)?.label ?? era;
}

function RevolutionCard({ r }: { r: Revolution }) {
  const active = isActiveStatus(r.status);
  const href = active ? `/revolt/active/${r.slug}` : `/revolt/${r.slug}`;
  const tail = active
    ? STATUS_LABELS[r.status]
    : r.outcome
      ? OUTCOME_LABELS[r.outcome]
      : '';
  return (
    <Link href={href} className={`rev-card${active ? ' rev-card--active' : ''}`}>
      <div className="rev-card__meta">
        <span>{eraLabel(r.era)}</span>
        <span>&middot;</span>
        <span>{r.country}</span>
        {active && (
          <span className="rev-live-stamp">
            <span className="rev-live-stamp__dot" aria-hidden="true" />
            Live
          </span>
        )}
      </div>
      <div className="rev-card__title">{r.title}</div>
      <div className="rev-card__hook">{HOOKS[r.slug] ?? r.subtitle}</div>
      {tail && <div className="rev-card__outcome">{tail}</div>}
    </Link>
  );
}

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
  const active = (revolutions ?? []).filter((r) => isActiveStatus(r.status));

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
          <h2 className="rev-banner">The Living &middot; happening now</h2>
          <p className="rev-prose" style={{ marginBottom: 'var(--space-4)' }}>
            Curated ongoing movements, placed on the arc and weighed against the historical
            record. Analytical, not predictive. Not an endorsement.
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

      {revolutions !== null && revolutions.length === 0 && (
        <p className="rev-empty">No revolutions loaded yet.</p>
      )}
    </div>
  );
}
