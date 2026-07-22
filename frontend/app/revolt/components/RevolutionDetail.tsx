'use client';

import { useEffect, useRef, useState, type ReactNode } from 'react';
import Link from 'next/link';
import type { Revolution } from '../types';
import { phaseSpec, OUTCOME_LABELS, RESISTANCE_LABELS, DEFECTION_LABELS } from '../anatomy';
import { verdictChip } from '../scoring';
import { heroImageFor } from '../images';
import RevoltScrubber, { type ScrubNode } from './RevoltScrubber';
import RevoltAudioCue from './RevoltAudioCue';

const ACTOR_COLOR: Record<string, string> = {
  vanguard: 'var(--rev-actor-vanguard)',
  masses: 'var(--rev-actor-masses)',
  'organized-labor': 'var(--rev-actor-masses)',
  'students-youth': 'var(--rev-actor-masses)',
  'military-defectors': 'var(--rev-actor-defect)',
  'security-forces': 'var(--rev-actor-reaction)',
  'old-regime': 'var(--rev-actor-reaction)',
  regime: 'var(--rev-actor-reaction)',
  'counter-revolutionaries': 'var(--rev-actor-reaction)',
  'religious-clergy': 'var(--rev-actor-defect)',
  'foreign-backer': 'var(--rev-actor-foreign)',
  'foreign-intervener': 'var(--rev-actor-foreign)',
  diaspora: 'var(--rev-actor-foreign)',
};

interface Frame {
  key: string;
  label: string;
  color: string;
  node: ReactNode;
}

function durationText(r: Revolution): string {
  if (r.durationDays && r.durationDays > 0) {
    const yrs = Math.round((r.durationDays / 365) * 10) / 10;
    return yrs >= 1 ? `${yrs} years` : `${r.durationDays} days`;
  }
  return r.dateDisplay;
}

export default function RevolutionDetail({ revolution: r }: { revolution: Revolution }) {
  const frameRefs = useRef<(HTMLElement | null)[]>([]);
  const [active, setActive] = useState(0);

  const frames = buildFrames(r);

  useEffect(() => {
    const els = frameRefs.current.filter(Boolean) as HTMLElement[];
    if (els.length === 0) return;
    const io = new IntersectionObserver(
      (entries) => {
        let best = -1;
        let bestRatio = 0;
        entries.forEach((e) => {
          if (e.isIntersecting && e.intersectionRatio > bestRatio) {
            bestRatio = e.intersectionRatio;
            best = Number((e.target as HTMLElement).dataset.frameIndex);
          }
        });
        if (best >= 0) setActive(best);
      },
      { threshold: [0.25, 0.5, 0.75], rootMargin: '0px' },
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [r.slug]);

  const select = (i: number) => {
    frameRefs.current[i]?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'center' });
  };

  const nodes: ScrubNode[] = frames.map((f) => ({ key: f.key, label: f.label, color: f.color }));

  return (
    <article>
      {/* Cold-open stage */}
      <section className="rev-stage">
        {(r.heroImage ?? heroImageFor(r.slug)) && (
          <img className="rev-stage__hero-img" src={r.heroImage ?? heroImageFor(r.slug)} alt="" aria-hidden="true" />
        )}
        <div className="rev-stage__inner">
          <p className="rev-stage__kicker">{r.dateDisplay} &middot; {r.country}</p>
          <h1 className="rev-stage__title">{r.title}</h1>
          <p className="rev-stage__sub">{r.subtitle}</p>
        </div>
      </section>

      {/* The Ledger */}
      <div className="rev-ledger">
        <dl className="rev-ledger__facts">
          <div><dt>Duration</dt><dd>{durationText(r)}</dd></div>
          <div><dt>Peak mobilization</dt><dd>{r.crossedParticipationThreshold === true ? 'Crossed 3.5%' : r.peakParticipationDisplay ? 'See notes' : 'Unknown'}</dd></div>
          <div><dt>Death toll</dt><dd>{r.deathTollLow ? `${(r.deathTollLow / 1000).toFixed(0)}k+` : r.deathToll ? 'See notes' : 'Unknown'}</dd></div>
          <div><dt>Military</dt><dd>{r.militaryDefection ? DEFECTION_LABELS[r.militaryDefection] : 'Unknown'}</dd></div>
          <div><dt>Repertoire</dt><dd>{r.resistanceType ? RESISTANCE_LABELS[r.resistanceType] : 'Mixed'}</dd></div>
          <div><dt>Outcome</dt><dd>{r.outcome ? OUTCOME_LABELS[r.outcome] : 'Unresolved'}</dd></div>
        </dl>
        {verdictChip(r) && <p className="rev-verdict">{verdictChip(r)}</p>}
        {r.audioUrl && <RevoltAudioCue audioUrl={r.audioUrl} durationSeconds={r.audioDuration ?? 0} title={r.title} />}
      </div>

      {/* The Anatomy Reel */}
      <div className="rev-reel">
        {frames.map((f, i) => (
          <section
            key={f.key}
            className="rev-reel__frame"
            data-frame-index={i}
            ref={(el) => { frameRefs.current[i] = el; }}
          >
            {f.node}
          </section>
        ))}
      </div>

      <RevoltScrubber nodes={nodes} activeIndex={active} onSelect={select} />
    </article>
  );
}

function buildFrames(r: Revolution): Frame[] {
  const frames: Frame[] = [];

  // 0 — Preconditions
  frames.push({
    key: 'preconditions',
    label: 'Preconditions',
    color: 'var(--rev-phase-1)',
    node: (
      <>
        <p className="rev-frame__index">The pressure builds</p>
        <h2 className="rev-frame__label">Why it broke</h2>
        <div className="rev-gauge" style={{ ['--rev-phase-hue' as string]: 'var(--rev-phase-1)' }}>
          {r.grievances.map((g, i) => (
            <div className="rev-gauge__row" key={i}>
              <span className="rev-gauge__label"><span>{g.kind}</span><span>{g.intensity}</span></span>
              <span className="rev-gauge__bar"><span className="rev-gauge__fill" style={{ width: `${g.intensity}%` }} /></span>
              <span className="rev-frame__date">{g.evidence}</span>
            </div>
          ))}
        </div>
      </>
    ),
  });

  // 1..n — phases
  r.phases.forEach((p, i) => {
    const spec = phaseSpec(p.phase);
    const hue = spec?.hueVar ?? 'var(--rev-accent)';
    frames.push({
      key: `phase-${p.phase}-${i}`,
      label: spec?.short ?? p.label,
      color: hue,
      node: (
        <div className={p.reached ? '' : 'rev-frame--unreached'} style={{ ['--rev-phase-hue' as string]: hue }}>
          <p className="rev-frame__index" style={{ color: hue }}>{spec?.label ?? p.phase}</p>
          <h2 className="rev-frame__label">{p.label}</h2>
          {p.dateStart && <p className="rev-frame__date">{p.dateStart}</p>}
          <p className="rev-frame__body">{p.reached ? p.summary : 'This revolution never reached this stage. The absence is the story.'}</p>
          {p.reached && p.keyEvents.length > 0 && (
            <ul className="rev-frame__events">
              {p.keyEvents.map((e, j) => <li key={j}>{e}</li>)}
            </ul>
          )}
        </div>
      ),
    });
  });

  // Cast
  frames.push({
    key: 'cast',
    label: 'The Cast',
    color: 'var(--rev-actor-masses)',
    node: (
      <>
        <p className="rev-frame__index">Who moved</p>
        <h2 className="rev-frame__label">The Cast</h2>
        <div className="rev-actors">
          {r.actors.map((a, i) => (
            <div className="rev-actor" key={i} style={{ ['--actor-color' as string]: ACTOR_COLOR[a.actorType] ?? 'var(--rev-iron)' }}>
              <div className="rev-actor__name">{a.name}</div>
              <div className="rev-actor__role">{a.roleInArc}</div>
              {a.defected && <div className="rev-actor__badge">Defected to the movement</div>}
            </div>
          ))}
        </div>
      </>
    ),
  });

  // Repertoire
  frames.push({
    key: 'repertoire',
    label: 'The Repertoire',
    color: 'var(--rev-iron)',
    node: (
      <>
        <p className="rev-frame__index">How they fought</p>
        <h2 className="rev-frame__label">The Repertoire</h2>
        <p className="rev-frame__body">
          Primarily {r.resistanceType ? RESISTANCE_LABELS[r.resistanceType].toLowerCase() : 'mixed'}.
          {r.crossedParticipationThreshold === true
            ? ' Peak turnout crossed the 3.5 percent threshold the record associates with success.'
            : r.crossedParticipationThreshold === false
              ? ' Peak turnout stayed below the 3.5 percent threshold the record associates with success.'
              : ''}
        </p>
        <ul className="rev-frame__events">
          {r.tactics.map((t, i) => <li key={i}>{t.description}</li>)}
        </ul>
        {r.peakParticipationDisplay && <p className="rev-frame__date" style={{ marginTop: 12 }}>{r.peakParticipationDisplay}</p>}
      </>
    ),
  });

  // Reckoning
  frames.push({
    key: 'reckoning',
    label: 'The Reckoning',
    color: 'var(--rev-phase-6)',
    node: (
      <>
        <p className="rev-frame__index">What it became</p>
        <h2 className="rev-frame__label">The Reckoning</h2>
        <p className="rev-frame__body">
          {r.outcome ? OUTCOME_LABELS[r.outcome] + '.' : 'Still unresolved.'}
          {r.ateItsChildren ? ' The revolution turned on its own founders.' : ''}
        </p>
        {r.deathToll && <p className="rev-frame__body">{r.deathToll}</p>}
        {typeof r.democratizationDelta === 'number' && (
          <p className="rev-frame__date">Democratization change: {r.democratizationDelta > 0 ? '+' : ''}{r.democratizationDelta} on a -3 to +3 scale.</p>
        )}
      </>
    ),
  });

  // Threads
  frames.push({
    key: 'threads',
    label: 'Threads',
    color: 'var(--rev-accent)',
    node: (
      <>
        <p className="rev-frame__index">Where it leads</p>
        <h2 className="rev-frame__label">Threads</h2>
        {r.connections.length > 0 && (
          <ul className="rev-frame__events" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
            {r.connections.map((c, i) => (
              <li key={i}>{c.type.replace(/-/g, ' ')}: {c.targetTitle}. {c.description}</li>
            ))}
          </ul>
        )}
        <p className="rev-frame__body" style={{ marginTop: 16 }}>
          <Link href={`/revolt/compare?ids=${r.slug}`}>Compare this revolution &rarr;</Link>
        </p>
        {r.relatedHistorySlugs.length > 0 && (
          <p className="rev-frame__body">
            <Link href={`/history/${r.relatedHistorySlugs[0]}`}>See the testimony &rarr; void --history</Link>
          </p>
        )}
      </>
    ),
  });

  return frames;
}
