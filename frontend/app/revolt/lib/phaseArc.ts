/* ===========================================================================
   phaseArc — hand-rolled SVG path math for the overlaid Brinton phase-arc.
   x = pre-normalized phase position (t_start..t_end), y = intensity.
   Unreached phases truncate the curve (a stalled revolution flatlines mid-arc).
   Zero chart libs (the lib/kde.ts precedent).
   =========================================================================== */

import type { RevoltPhase } from '../types';

export interface ArcPoint { x: number; y: number; label: string; }

export interface ArcResult {
  path: string;
  points: ArcPoint[];
  /** true if the revolution never reached consolidation (curve truncates) */
  truncated: boolean;
}

export function phaseArc(phases: RevoltPhase[], width = 1000, height = 300, pad = 20): ArcResult {
  const reached = phases.filter((p) => p.reached).sort((a, b) => a.tStart - b.tStart);
  const usableH = height - pad * 2;

  const xFor = (t: number) => pad + t * (width - pad * 2);
  const yFor = (intensity: number) => pad + (1 - Math.max(0, Math.min(100, intensity)) / 100) * usableH;

  const points: ArcPoint[] = [];
  for (const p of reached) {
    const mid = (p.tStart + p.tEnd) / 2;
    points.push({ x: xFor(mid), y: yFor(p.intensity), label: p.label });
  }

  if (points.length === 0) return { path: '', points: [], truncated: true };

  let path = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;
  for (let i = 1; i < points.length; i++) {
    path += ` L ${points[i].x.toFixed(1)} ${points[i].y.toFixed(1)}`;
  }

  const truncated = reached.length === 0 || reached[reached.length - 1].tEnd < 0.9;
  return { path, points, truncated };
}
