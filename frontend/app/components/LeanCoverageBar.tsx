"use client";

import type { BiasSpread } from "../lib/types";

/* ---------------------------------------------------------------------------
   LeanCoverageBar — reveals the left/right SPLIT the mean lean conceals.

   The cluster's headline lean is a (rigor-weighted) mean. A story carried by
   far-left AND far-right sources averages to ~50 and reads "balanced" — but
   it is actually contested. This bar plots the actual coverage distribution
   as three proportional segments (Left · Center · Right) from the per-cluster
   source counts the pipeline stores in bias_diversity, and flags "Contested"
   when both wings are large (high polarization). The mean stays true; this
   adds the second, honest dimension: HOW SPLIT the coverage is.

   Shown only when both wings are present (left>0 && right>0) — a one-sided or
   all-center story is already well described by the Sigil's tilt alone.
   --------------------------------------------------------------------------- */

interface LeanCoverageBarProps {
  spread: BiasSpread | undefined;
  /** Compact variant trims the label for tight card footers. */
  compact?: boolean;
}

export default function LeanCoverageBar({ spread, compact }: LeanCoverageBarProps) {
  if (!spread) return null;
  const left = spread.leanLeftCount ?? 0;
  const center = spread.leanCenterCount ?? 0;
  const right = spread.leanRightCount ?? 0;
  const total = left + center + right;

  // Only surface when coverage genuinely spans both sides — that is exactly
  // the "false center" case the mean hides. One-sided / all-center stories
  // skip the bar (the Sigil tilt already tells that story).
  if (total < 3 || left === 0 || right === 0) return null;

  const polarization = spread.polarization ?? 0;
  const contested = polarization >= 50;

  const pct = (n: number) => `${(n / total) * 100}%`;
  const label = `Coverage split: ${left} left, ${center} center, ${right} right`;

  return (
    <div
      className={`lean-coverage${contested ? " lean-coverage--contested" : ""}${compact ? " lean-coverage--compact" : ""}`}
      role="img"
      aria-label={`${label}${contested ? " — contested" : ""}`}
    >
      <span className="lean-coverage__tag" aria-hidden="true">
        {contested ? "Contested" : "Coverage"}
      </span>
      <span className="lean-coverage__track" aria-hidden="true">
        {left > 0 && (
          <span
            className="lean-coverage__seg lean-coverage__seg--left"
            style={{ width: pct(left) }}
          />
        )}
        {center > 0 && (
          <span
            className="lean-coverage__seg lean-coverage__seg--center"
            style={{ width: pct(center) }}
          />
        )}
        {right > 0 && (
          <span
            className="lean-coverage__seg lean-coverage__seg--right"
            style={{ width: pct(right) }}
          />
        )}
      </span>
      <span className="lean-coverage__counts" aria-hidden="true">
        {left}<span className="lean-coverage__counts-sep">·</span>{center}<span className="lean-coverage__counts-sep">·</span>{right}
      </span>
    </div>
  );
}
