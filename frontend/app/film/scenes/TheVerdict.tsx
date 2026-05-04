"use client";

import {
  VOID_CIRCLE, BEAM_CURVE, BASE_CURVE, VOID_CIRC_LEN,
} from "../constants";
import { NUMBERS } from "../data";

/* ==========================================================================
   TheVerdict — Scene VI: "Read with clarity."
   Three archetypal Sigils + key numbers + CTA.
   The final frame of The Film.
   ========================================================================== */

interface Props {
  mode: "prologue" | "manifesto";
  active: boolean;
}

function MiniSigil({ lean, leanColor: lc, coverage, coverageColor }: {
  lean: number; leanColor: string; coverage: number; coverageColor: string;
}) {
  const beamAngle = (lean - 50) * 0.30;
  const ringFill = coverage * VOID_CIRC_LEN;
  return (
    <svg width="48" height="48" viewBox="0 0 32 32" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <path d={VOID_CIRCLE} stroke="var(--border-subtle)" strokeWidth="1.8" opacity={0.3} />
      <path d={VOID_CIRCLE} stroke={coverageColor} strokeWidth="1.8"
        strokeDasharray={`${ringFill} ${VOID_CIRC_LEN}`}
        style={{ transform: "rotate(-90deg)", transformOrigin: "16px 13px" }}
        opacity={0.9}
      />
      <g style={{ transformOrigin: "16px 13px", transform: `rotate(${beamAngle}deg)` }}>
        <path d={BEAM_CURVE} stroke={lc} strokeWidth="1.8" />
        <line x1="5" y1="11" x2="5" y2="15" stroke={lc} strokeWidth="1.4" opacity={0.85} />
        <line x1="27" y1="11" x2="27" y2="15" stroke={lc} strokeWidth="1.4" opacity={0.85} />
      </g>
      <line x1="16" y1="22" x2="16" y2="29" stroke="var(--fg-tertiary)" strokeWidth="1.4" opacity={0.4} />
      <path d={BASE_CURVE} stroke="var(--fg-tertiary)" strokeWidth="1.8" opacity={0.3} />
    </svg>
  );
}

export default function TheVerdict({ mode, active }: Props) {
  return (
    <div className={`film-verdict film-verdict--${mode}`} aria-hidden="true">
      {/* Three archetypal Sigils */}
      <div className={`film-verdict__row${active ? " film-verdict__row--in" : ""}`}>
        <div className="film-verdict__card" style={{ transitionDelay: "200ms" }}>
          <MiniSigil lean={25} leanColor="var(--bias-left)" coverage={0.8} coverageColor="var(--sense-low)" />
          <span className="film-verdict__label">Left, Broad</span>
          <span className="film-verdict__sub">Well sourced</span>
        </div>
        <div className="film-verdict__card" style={{ transitionDelay: "350ms" }}>
          <MiniSigil lean={50} leanColor="var(--bias-center)" coverage={0.92} coverageColor="var(--sense-low)" />
          <span className="film-verdict__label">Center, Deep</span>
          <span className="film-verdict__sub">Most reliable</span>
        </div>
        <div className="film-verdict__card" style={{ transitionDelay: "500ms" }}>
          <MiniSigil lean={78} leanColor="var(--bias-right)" coverage={0.25} coverageColor="var(--sense-high)" />
          <span className="film-verdict__label">Right, Thin</span>
          <span className="film-verdict__sub">Scrutinize more</span>
        </div>
      </div>

      {/* Key numbers */}
      <div className={`film-verdict__numbers${active ? " film-verdict__numbers--in" : ""}`}>
        {NUMBERS.map((n, i) => (
          <span key={n.label} className="film-verdict__num" style={{ transitionDelay: `${600 + i * 80}ms` }}>
            <span className="film-verdict__num-value">{n.value}</span> {n.label}
            {i < NUMBERS.length - 1 && <span className="film-verdict__num-sep">&middot;</span>}
          </span>
        ))}
      </div>

      {/* Sub-message */}
      <p className={`film-verdict__sub-msg${active ? " film-verdict__sub-msg--in" : ""}`}>
        No signup. No paywall. No tracking.
      </p>
    </div>
  );
}
