'use client';

import Link from 'next/link';
import type { Revolution, LiveCard } from '../types';
import { phaseSpec, STATUS_LABELS } from '../anatomy';
import { heroImageFor } from '../images';
import SuccessScorecard from './SuccessScorecard';
import LiveRevoltCards from './LiveRevoltCards';
import RevoltAudioCue from './RevoltAudioCue';

/* The Active portal detail: The Situation (static phase placement) + the
   Scorecard (analytical) + Live coverage (visually separated). No reel. */
export default function ActiveRevolutionDetail({ revolution: r, liveCards }: { revolution: Revolution; liveCards: LiveCard[] }) {
  const reachedCount = r.phases.filter((p) => p.reached).length;

  return (
    <article>
      <section className="rev-stage">
        {(r.heroImage ?? heroImageFor(r.slug)) && (
          <img className="rev-stage__hero-img" src={r.heroImage ?? heroImageFor(r.slug)} alt="" aria-hidden="true" />
        )}
        <div className="rev-stage__inner">
          <p className="rev-stage__kicker">
            <span className="rev-live-stamp"><span className="rev-live-stamp__dot" aria-hidden="true" />Live</span>
            &nbsp; {r.dateDisplay} &middot; {r.country}
          </p>
          <h1 className="rev-stage__title">{r.title}</h1>
          <p className="rev-stage__sub">{r.subtitle}</p>
        </div>
      </section>

      <div className="rev-shell">
        <p className="rev-review-stamp" style={{ marginTop: 'var(--space-4)' }}>{STATUS_LABELS[r.status]}</p>

        {r.audioUrl && <RevoltAudioCue audioUrl={r.audioUrl} durationSeconds={r.audioDuration ?? 0} title={r.title} />}

        {r.analyticalOutlook && (
          <>
            <h2 className="rev-h2">The situation</h2>
            <p className="rev-prose">{r.analyticalOutlook}</p>
          </>
        )}

        {/* Where it is on the arc */}
        <h2 className="rev-h2">Where it is on the arc</h2>
        <ol className="rev-gauge" style={{ listStyle: 'none', padding: 0 }}>
          {r.phases.map((p, i) => {
            const spec = phaseSpec(p.phase);
            const isCurrent = p.reached && i === reachedCount - 1;
            return (
              <li key={i} className={p.reached ? '' : 'rev-frame--unreached'} style={{ borderLeft: `4px solid ${p.reached ? (spec?.hueVar ?? 'var(--rev-oxide)') : 'var(--rev-iron)'}`, paddingLeft: '0.75rem' }}>
                <div className="rev-actor__name">{p.label}{isCurrent ? ' (where it is now)' : ''}</div>
                <div className="rev-actor__role">{p.reached ? p.summary : 'Not reached.'}</div>
              </li>
            );
          })}
        </ol>

        <SuccessScorecard revolution={r} />

        <LiveRevoltCards cards={liveCards} />

        <p className="rev-prose" style={{ marginTop: 'var(--space-5)' }}>
          <Link href={`/revolt/compare?ids=${r.slug}`}>Compare against a past revolution &rarr;</Link>
          {r.relatedHistorySlugs.length > 0 && (
            <>
              {' '}&middot;{' '}
              <Link href={`/history/${r.relatedHistorySlugs[0]}`}>The deeper history &rarr;</Link>
            </>
          )}
        </p>
      </div>
    </article>
  );
}
