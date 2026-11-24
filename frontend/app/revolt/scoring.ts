/* ===========================================================================
   void --revolt — Scoring (PRESENTATION ONLY)
   This module NEVER invents a verdict. It reads the analyst-curated
   success_factors + denormalized comparison fields and derives display
   aggregates: a descriptive count and a 3-band label. All judgment lives in
   the curated data; this only counts and labels it.
   =========================================================================== */

import type { Revolution, SuccessFactor } from './types';
import { RESISTANCE_LABELS, DEFECTION_LABELS } from './anatomy';

export type SuccessBand = 'Low' | 'Contested' | 'Favorable';

export interface FactorTally {
  favorsMovement: number;
  favorsRegime: number;
  indeterminate: number;
  total: number;
}

export function tallyFactors(factors: SuccessFactor[]): FactorTally {
  const t: FactorTally = { favorsMovement: 0, favorsRegime: 0, indeterminate: 0, total: factors.length };
  for (const f of factors) {
    if (f.direction === 'favors-movement') t.favorsMovement += 1;
    else if (f.direction === 'favors-regime') t.favorsRegime += 1;
    else t.indeterminate += 1;
  }
  return t;
}

/** Descriptive count string. Never a probability. */
export function factorCountLabel(factors: SuccessFactor[]): string {
  const t = tallyFactors(factors);
  if (t.total === 0) return 'No success factors recorded yet.';
  return `${t.favorsMovement} of ${t.total} factors historically tied to success are present.`;
}

/** A 3-band label derived from the net of curated factor directions.
   Favorable / Contested / Low. A band, never a percentage. */
export function successBand(factors: SuccessFactor[]): SuccessBand | null {
  const t = tallyFactors(factors);
  if (t.total === 0) return null;
  const net = t.favorsMovement - t.favorsRegime;
  if (net >= 2) return 'Favorable';
  if (net <= -2) return 'Low';
  return 'Contested';
}

/** The glanceable Ledger chip for a deep-dive: neutral facts, no forecast. */
export function verdictChip(r: Revolution): string {
  const parts: string[] = [];
  if (r.resistanceType) parts.push(RESISTANCE_LABELS[r.resistanceType]);
  if (r.militaryDefection && r.militaryDefection !== 'unknown') {
    parts.push(DEFECTION_LABELS[r.militaryDefection].toLowerCase());
  }
  if (r.crossedParticipationThreshold === true) parts.push('crossed the 3.5% threshold');
  return parts.join('. ') + (parts.length ? '.' : '');
}

/** CSS class suffix for a band, for theme-aware coloring. */
export function bandClass(band: SuccessBand | null): string {
  if (band === 'Favorable') return 'rev-band--favorable';
  if (band === 'Low') return 'rev-band--low';
  if (band === 'Contested') return 'rev-band--contested';
  return 'rev-band--none';
}
