"use client";

import { useState, useEffect } from "react";
import type { SourceAccuracy } from "../lib/types";

/* ===========================================================================
   CredibilityArc — void --verify (Phase 2)
   Source accuracy sparkline for the Sources page.

   Renders a horizontal bar showing corroborated/contradicted/unverified
   proportions with a draw-in stroke animation (1200ms ease-cinematic).
   Only renders when total_unique_claims >= 10.
   =========================================================================== */

interface CredibilityArcProps {
  accuracy: SourceAccuracy;
}

const TREND_ARROWS: Record<SourceAccuracy["trend"], string> = {
  improving: "\u25B2",
  stable: "\u25AC",
  declining: "\u25BC",
};

const TREND_LABELS: Record<SourceAccuracy["trend"], string> = {
  improving: "Improving",
  stable: "Stable",
  declining: "Declining",
};

export default function CredibilityArc({ accuracy }: CredibilityArcProps) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 100);
    return () => clearTimeout(t);
  }, []);

  // Only render for sources with meaningful claim history
  if (accuracy.total_unique_claims < 10) return null;

  const total = accuracy.total_unique_claims;
  const corrobPct = (accuracy.later_corroborated / total) * 100;
  const contradPct = (accuracy.later_contradicted / total) * 100;
  const unverPct = 100 - corrobPct - contradPct;
  const rateDisplay = Math.round(accuracy.accuracy_rate * 100);

  return (
    <div
      className="cred-arc"
      aria-label={`${accuracy.source_name}: ${rateDisplay}% accuracy rate, ${TREND_LABELS[accuracy.trend]}`}
    >
      {/* Header: source name + rate + trend */}
      <div className="cred-arc__header">
        <span className="cred-arc__name">{accuracy.source_name}</span>
        <span className="cred-arc__rate">{rateDisplay}%</span>
        <span
          className={`cred-arc__trend cred-arc__trend--${accuracy.trend}`}
          aria-label={TREND_LABELS[accuracy.trend]}
        >
          {TREND_ARROWS[accuracy.trend]}
        </span>
      </div>

      {/* Horizontal proportional bar */}
      <div className="cred-arc__bar" role="img" aria-hidden="true">
        <div className="cred-arc__bar-track">
          <div
            className="cred-arc__bar-segment cred-arc__bar-segment--corroborated"
            style={{ width: mounted ? `${corrobPct}%` : "0%" }}
          />
          <div
            className="cred-arc__bar-segment cred-arc__bar-segment--contradicted"
            style={{ width: mounted ? `${contradPct}%` : "0%" }}
          />
          <div
            className="cred-arc__bar-segment cred-arc__bar-segment--unverified"
            style={{ width: mounted ? `${unverPct}%` : "0%" }}
          />
        </div>
      </div>

      {/* Stats line */}
      <div className="cred-arc__stats">
        <span>Unique claims: {total}</span>
        <span className="cred-arc__stat-sep" aria-hidden="true">|</span>
        <span>Confirmed: {accuracy.later_corroborated}</span>
        <span className="cred-arc__stat-sep" aria-hidden="true">|</span>
        <span>Contradicted: {accuracy.later_contradicted}</span>
      </div>
    </div>
  );
}
