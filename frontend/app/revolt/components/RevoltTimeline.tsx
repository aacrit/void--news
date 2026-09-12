'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import type { Revolution } from '../types';
import { isActiveStatus, isLiveStatus, REVOLT_ERAS } from '../types';
import { OUTCOME_LABELS, STATUS_LABELS } from '../anatomy';
import { HOOKS } from '../hooks';
import { heroImageFor, thumbUrl } from '../images';
import { fetchRevolutions } from '../data';

function yearLabel(r: Revolution): string {
  if (r.dateStart < 0) return `${-r.dateStart} BCE`;
  return String(r.dateStart);
}

function eraLabel(era: string): string {
  return REVOLT_ERAS.find((e) => e.id === era)?.label ?? era;
}

/* "Everything on a timeline" — a horizontal chronological ink-timeline of every
   revolution (like void --history's organic timeline), cards alternating above
   and below a central axis, wheel-scrollable, blueprint-styled. Mobile flips to
   a vertical spine. */
export default function RevoltTimeline() {
  const [revs, setRevs] = useState<Revolution[] | null>(null);
  const trackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    fetchRevolutions().then((d) => {
      if (!cancelled) setRevs([...d].sort((a, b) => a.dateStart - b.dateStart));
    });
    return () => { cancelled = true; };
  }, []);

  // Translate vertical wheel into horizontal scroll on the track (desktop).
  useEffect(() => {
    const el = trackRef.current;
    if (!el) return;
    const onWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) <= Math.abs(e.deltaX)) return;
      if (window.matchMedia('(max-width: 767px)').matches) return;
      el.scrollLeft += e.deltaY;
      e.preventDefault();
    };
    el.addEventListener('wheel', onWheel, { passive: false });
    return () => el.removeEventListener('wheel', onWheel);
  }, [revs]);

  if (revs === null) return <p className="rev-loading">Laying out the record&hellip;</p>;
  if (revs.length === 0) return <p className="rev-empty">No revolutions loaded yet.</p>;

  const nodes: React.ReactNode[] = [];
  let lastEra = '';
  revs.forEach((r, i) => {
    if (r.era !== lastEra) {
      lastEra = r.era;
      nodes.push(
        <div className="rev-tl-era" key={`era-${r.era}-${i}`}>
          <span className="rev-tl-era__label">{eraLabel(r.era)}</span>
        </div>,
      );
    }

    const active = isActiveStatus(r.status);
    const live = isLiveStatus(r.status);
    const href = active ? `/revolt/active/${r.slug}` : `/revolt/${r.slug}`;
    const hero = r.heroImage ?? heroImageFor(r.slug);
    const tail = active ? STATUS_LABELS[r.status] : r.outcome ? OUTCOME_LABELS[r.outcome] : '';
    const side = i % 2 === 0 ? 'up' : 'down';

    nodes.push(
      <div className="rev-tl-node" data-side={side} key={r.slug}>
        <Link href={href} className={`rev-tl-card${live ? ' rev-tl-card--live' : ''}`}>
          {hero && (
            <span className="rev-tl-card__img" aria-hidden="true">
              <img src={thumbUrl(hero, 400)} alt="" loading="lazy" decoding="async" width={400} height={150} />
            </span>
          )}
          <span className="rev-tl-card__title">{r.title}</span>
          <span className="rev-tl-card__hook">{HOOKS[r.slug] ?? r.subtitle}</span>
          {tail && (
            <span className="rev-tl-card__tail">
              {live && <span className="rev-live-stamp__dot" aria-hidden="true" />}
              {tail}
            </span>
          )}
        </Link>
        <span className="rev-tl-node__stem" aria-hidden="true" />
        <span className={`rev-tl-node__dot${live ? ' rev-tl-node__dot--live' : ''}`} aria-hidden="true" />
        <span className="rev-tl-node__year">{yearLabel(r)}</span>
      </div>,
    );
  });

  return (
    <div className="rev-tl" ref={trackRef} role="list" aria-label="Timeline of revolutions">
      <div className="rev-tl__track">
        <span className="rev-tl__axis" aria-hidden="true" />
        {nodes}
      </div>
    </div>
  );
}
