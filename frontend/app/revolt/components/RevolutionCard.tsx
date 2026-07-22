import Link from 'next/link';
import type { Revolution } from '../types';
import { REVOLT_ERAS, isActiveStatus } from '../types';
import { OUTCOME_LABELS, STATUS_LABELS } from '../anatomy';
import { HOOKS } from '../hooks';

function eraLabel(era: string): string {
  return REVOLT_ERAS.find((e) => e.id === era)?.label ?? era;
}

/* Shared feed card for a revolution (landing + browsers). Active movements
   route to /revolt/active/<slug> and carry the live stamp. */
export default function RevolutionCard({ r }: { r: Revolution }) {
  const active = isActiveStatus(r.status);
  const href = active ? `/revolt/active/${r.slug}` : `/revolt/${r.slug}`;
  const tail = active ? STATUS_LABELS[r.status] : r.outcome ? OUTCOME_LABELS[r.outcome] : '';
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
