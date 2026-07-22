'use client';

import { useEffect, useMemo, useState } from 'react';
import type { Revolution } from '../types';
import { OUTCOME_LABELS, RESISTANCE_LABELS, DEFECTION_LABELS, phaseSpec } from '../anatomy';
import { fetchRevolutions } from '../data';
import { phaseArc } from '../lib/phaseArc';

const SLOT_COLORS = ['#7E2E20', '#2A6560', '#8A6D1E', '#5E3A66'];
const MAX = 4;

export default function ComparisonLab() {
  const [all, setAll] = useState<Revolution[]>([]);
  const [selected, setSelected] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;
    fetchRevolutions().then((d) => {
      if (cancelled) return;
      setAll(d);
      const params = new URLSearchParams(window.location.search);
      const ids = (params.get('ids') ?? '').split(',').map((s) => s.trim()).filter(Boolean);
      const valid = ids.filter((id) => d.some((r) => r.slug === id)).slice(0, MAX);
      setSelected(valid.length ? valid : d.slice(0, 2).map((r) => r.slug));
    });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (selected.length === 0) return;
    const url = `${window.location.pathname}?ids=${selected.join(',')}`;
    window.history.replaceState(null, '', url);
  }, [selected]);

  const chosen = useMemo(
    () => selected.map((s) => all.find((r) => r.slug === s)).filter(Boolean) as Revolution[],
    [selected, all],
  );

  const toggle = (slug: string) => {
    setSelected((prev) => {
      if (prev.includes(slug)) return prev.filter((s) => s !== slug);
      if (prev.length >= MAX) return prev;
      return [...prev, slug];
    });
  };

  return (
    <div className="rev-shell">
      <section className="rev-hero">
        <p className="rev-hero__kicker">void --revolt &middot; comparison lab</p>
        <h1 className="rev-hero__title">Lay Them Side by Side</h1>
        <p className="rev-hero__sub">
          Pick up to four revolutions and see them over one shared anatomy. The chart overlays each
          one&rsquo;s trajectory on the Brinton arc, so a fast collapse reads steep and a stalled one
          flatlines before it reaches the end.
        </p>
      </section>

      {/* Picker */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, margin: 'var(--space-4) 0' }}>
        {all.map((r) => {
          const on = selected.includes(r.slug);
          const idx = selected.indexOf(r.slug);
          return (
            <button
              key={r.slug}
              type="button"
              onClick={() => toggle(r.slug)}
              className="rev-topbar__link"
              style={{
                border: `2px solid ${on ? SLOT_COLORS[idx] : 'var(--rev-iron)'}`,
                background: on ? SLOT_COLORS[idx] : 'transparent',
                color: on ? 'var(--rev-oxide-fg)' : 'var(--rev-ink-secondary)',
                padding: '4px 10px',
              }}
              aria-pressed={on}
            >
              {r.title}
            </button>
          );
        })}
      </div>

      {/* Phase-arc overlay */}
      <svg viewBox="0 0 1000 320" width="100%" role="img" aria-label="Overlaid phase arcs" style={{ border: '2px solid var(--rev-iron)', background: 'var(--rev-newsprint)' }}>
        {phaseSpec('the-spark') && (
          <>
            {[0.12, 0.34, 0.6, 0.84, 0.92].map((t, i) => (
              <line key={i} x1={20 + t * 960} y1={20} x2={20 + t * 960} y2={300} stroke="var(--rev-iron)" strokeOpacity="0.18" strokeDasharray="3 4" />
            ))}
          </>
        )}
        {chosen.map((r, i) => {
          const arc = phaseArc(r.phases, 1000, 300, 20);
          if (!arc.path) return null;
          return (
            <g key={r.slug}>
              <path d={arc.path} fill="none" stroke={SLOT_COLORS[i]} strokeWidth={2.5} />
              {arc.points.map((p, j) => (
                <circle key={j} cx={p.x} cy={p.y} r={3.5} fill={SLOT_COLORS[i]} />
              ))}
            </g>
          );
        })}
      </svg>

      {chosen.length === 0 && <p className="rev-empty">Select revolutions above to compare.</p>}

      {/* Anatomy grid */}
      {chosen.length > 0 && (
        <div style={{ overflowX: 'auto', marginTop: 'var(--space-4)' }}>
          <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: 480 }}>
            <thead>
              <tr>
                <th style={cellHead}>Axis</th>
                {chosen.map((r, i) => (
                  <th key={r.slug} style={{ ...cellHead, color: SLOT_COLORS[i] }}>{r.title}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {ROWS.map((row) => (
                <tr key={row.label}>
                  <td style={cellLabel}>{row.label}</td>
                  {chosen.map((r) => <td key={r.slug} style={cell}>{row.get(r)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const cellHead: React.CSSProperties = {
  textAlign: 'left', padding: '8px', borderBottom: '2px solid var(--rev-iron)',
  fontFamily: 'var(--font-meta), sans-serif', textTransform: 'uppercase', fontSize: 'var(--text-sm)',
};
const cellLabel: React.CSSProperties = {
  padding: '8px', borderBottom: '1px solid var(--rev-iron)', fontFamily: 'var(--font-data), monospace',
  fontSize: 'var(--text-xs)', textTransform: 'uppercase', color: 'var(--rev-ink-muted)', whiteSpace: 'nowrap',
};
const cell: React.CSSProperties = {
  padding: '8px', borderBottom: '1px solid var(--rev-iron)', fontSize: 'var(--text-sm)', verticalAlign: 'top',
};

const ROWS: { label: string; get: (r: Revolution) => string }[] = [
  { label: 'Period', get: (r) => r.dateDisplay },
  { label: 'Type', get: (r) => r.revoltType.replace(/-/g, ' ') },
  { label: 'Repertoire', get: (r) => (r.resistanceType ? RESISTANCE_LABELS[r.resistanceType] : 'Mixed') },
  { label: 'Military', get: (r) => (r.militaryDefection ? DEFECTION_LABELS[r.militaryDefection] : 'Unknown') },
  { label: 'Peak reached', get: (r) => { const rc = r.phases.filter((p) => p.reached); const last = rc[rc.length - 1]; return last ? (phaseSpec(last.phase)?.label ?? last.label) : 'None'; } },
  { label: 'Outcome', get: (r) => (r.outcome ? OUTCOME_LABELS[r.outcome] : 'Unresolved') },
  { label: 'Ate its children', get: (r) => (r.ateItsChildren ? 'Yes' : 'No') },
];
