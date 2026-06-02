"use client";

import { DIVERGENT_HEADLINES } from "../data";

/* ==========================================================================
   DivergentHeadlines — Scene I: "The Void"
   Five outlet cards cascade in, each with a different lean-colored edge.
   Prologue: compact stack. Manifesto: wider with pullquote.
   ========================================================================== */

interface Props {
  mode: "prologue" | "manifesto";
  active: boolean;
}

export default function DivergentHeadlines({ mode, active }: Props) {
  return (
    <div className={`film-void film-void--${mode}`} aria-hidden="true">
      <p className="film-void__event">Same event: US-China trade talks resume</p>
      <div className="film-void__headlines">
        {DIVERGENT_HEADLINES.map((h, i) => (
          <div
            key={h.outlet}
            className={`film-void__card${active ? " film-void__card--in" : ""}`}
            style={{ transitionDelay: `${200 + i * 120}ms` }}
          >
            <div className="film-void__source">
              <span className="film-void__outlet">{h.outlet}</span>
              <span className="film-void__lean-dot" style={{ backgroundColor: h.color }} />
              <span className="film-void__lean-label">{h.lean} &middot; {h.leanScore}</span>
            </div>
            <p className="film-void__headline">{h.headline}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
