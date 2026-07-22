/* ===========================================================================
   void --revolt — The Anatomy (shared spine)
   The single source of truth for the Brinton phase skeleton, the 9-key -> 6-band
   display grouping, and the scholarly base-rate constants. The reel, the phase
   ramp, and the Comparison Lab all read from here so they never disagree.
   =========================================================================== */

import type {
  PhaseKey, RevoltOutcome, RevoltStatus, ResistanceType, MilitaryDefection,
} from './types';

export interface PhaseSpec {
  key: PhaseKey;
  label: string;
  short: string;
  /** Fixed band on the normalized [0,1] arc (alignment is by phase-key alone) */
  band: [number, number];
  /** Which of the 6 legible display bands this DB phase folds into (1-6) */
  displayBand: 1 | 2 | 3 | 4 | 5 | 6;
  /** CSS var driving the frame hue */
  hueVar: string;
  gloss: string;
}

/* The canonical 9-phase Brinton skeleton. 9 keys preserve analytic fidelity;
   displayBand collapses them into the 6 frames the reel actually renders. */
export const PHASE_SKELETON: PhaseSpec[] = [
  { key: 'old-regime-crisis', label: 'Old-regime crisis', short: 'Crisis', band: [0.00, 0.12], displayBand: 1, hueVar: 'var(--rev-phase-1)', gloss: 'The state can no longer pay its debts or command loyalty.' },
  { key: 'intellectual-desertion', label: 'Intellectual desertion', short: 'Desertion', band: [0.12, 0.22], displayBand: 1, hueVar: 'var(--rev-phase-1)', gloss: 'The educated and the elite stop believing the regime deserves to rule.' },
  { key: 'the-spark', label: 'The spark', short: 'Spark', band: [0.22, 0.34], displayBand: 2, hueVar: 'var(--rev-phase-2)', gloss: 'A single event turns grievance into a crowd that cannot be dispersed.' },
  { key: 'moderate-phase', label: 'The moderates take charge', short: 'Moderates', band: [0.34, 0.48], displayBand: 3, hueVar: 'var(--rev-phase-3)', gloss: 'Reformers try to build a new order without breaking everything.' },
  { key: 'dual-power', label: 'Dual power', short: 'Dual power', band: [0.48, 0.60], displayBand: 3, hueVar: 'var(--rev-phase-3)', gloss: 'Two authorities claim the same nation; neither fully controls it.' },
  { key: 'radical-phase', label: 'The radicals win', short: 'Radicals', band: [0.60, 0.72], displayBand: 4, hueVar: 'var(--rev-phase-4)', gloss: 'The old order is torn down; the maximalists take the wheel.' },
  { key: 'terror-virtue', label: 'Terror and virtue', short: 'Terror', band: [0.72, 0.84], displayBand: 4, hueVar: 'var(--rev-phase-4)', gloss: 'The revolution turns on its enemies, then on itself.' },
  { key: 'thermidor', label: 'Thermidor', short: 'Thermidor', band: [0.84, 0.92], displayBand: 5, hueVar: 'var(--rev-phase-5)', gloss: 'Exhaustion and reaction. The fever breaks.' },
  { key: 'consolidation', label: 'Consolidation', short: 'Consolidation', band: [0.92, 1.00], displayBand: 6, hueVar: 'var(--rev-phase-6)', gloss: 'A new order hardens, for better or worse.' },
];

/** The 6 legible display bands the reel renders, each grouping 1-2 DB phases. */
export const DISPLAY_BANDS: { band: 1 | 2 | 3 | 4 | 5 | 6; label: string; hueVar: string }[] = [
  { band: 1, label: 'The old order cracks', hueVar: 'var(--rev-phase-1)' },
  { band: 2, label: 'The spark', hueVar: 'var(--rev-phase-2)' },
  { band: 3, label: 'The moderates try', hueVar: 'var(--rev-phase-3)' },
  { band: 4, label: 'The radical turn', hueVar: 'var(--rev-phase-4)' },
  { band: 5, label: 'Thermidor', hueVar: 'var(--rev-phase-5)' },
  { band: 6, label: 'Consolidation', hueVar: 'var(--rev-phase-6)' },
];

const PHASE_BY_KEY: Record<string, PhaseSpec> = Object.fromEntries(
  PHASE_SKELETON.map((p) => [p.key, p]),
);

export function phaseSpec(key: PhaseKey): PhaseSpec | undefined {
  return PHASE_BY_KEY[key];
}

export function displayBandFor(key: PhaseKey): number {
  return PHASE_BY_KEY[key]?.displayBand ?? 1;
}

/* ── Label maps ── */

export const OUTCOME_LABELS: Record<RevoltOutcome, string> = {
  'independence': 'Won independence',
  'consolidated-democracy': 'Became a democracy',
  'consolidated-autocracy': 'Became an autocracy',
  'restored-old-regime': 'Old regime restored',
  'failed-suppressed': 'Crushed',
  'civil-war': 'Collapsed into civil war',
  'ongoing-unresolved': 'Ongoing, unresolved',
  'intra-regime-purge': 'Internal purge, not overthrow',
  'secession-partition': 'Ended in partition',
};

export const STATUS_LABELS: Record<RevoltStatus, string> = {
  'concluded': 'Concluded',
  'active': 'Active',
  'consolidating': 'Recently overthrown, consolidating',
  'dormant': 'Dormant',
  'watchlist': 'Watchlist',
};

export const RESISTANCE_LABELS: Record<ResistanceType, string> = {
  'nonviolent': 'Nonviolent',
  'armed': 'Armed',
  'hybrid': 'Hybrid',
};

export const DEFECTION_LABELS: Record<MilitaryDefection, string> = {
  'none': 'Held with the regime',
  'partial': 'Partially defected',
  'full': 'Defected',
  'unknown': 'Unknown',
};

/* ── The scholarly base rates the success scorecard quotes verbatim ──
   Curated, cited constants. The whole active-portal thesis rests on quoting
   these exactly (never paraphrasing a probability). */
export const BASE_RATES = {
  nonviolentSuccess: 'About 53 percent of nonviolent campaigns from 1900 to 2006 succeeded, versus about 26 percent of armed ones.',
  participationThreshold: 'No campaign that mobilized at least 3.5 percent of the population at its peak has failed.',
  securityDefection: 'Defection of the security forces is the single strongest predictor of a campaign’s success.',
  eliteFracture: 'Revolutions rarely succeed until the ruling elite splits against itself.',
  externalSupport: 'Foreign sponsorship of a campaign correlates with lower, not higher, long-run success.',
} as const;

export const SUCCESS_FACTOR_CITATIONS = {
  chenoweth: 'Chenoweth and Stephan, Why Civil Resistance Works (2011)',
  brinton: 'Crane Brinton, The Anatomy of Revolution (1938)',
  skocpol: 'Theda Skocpol, States and Social Revolutions (1979)',
  goldstone: 'Jack Goldstone, Revolution and Rebellion in the Early Modern World (1991)',
  tilly: 'Charles Tilly, From Mobilization to Revolution (1978)',
} as const;
