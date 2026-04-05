"use client";

import { RANKING_SIGNALS } from "../data";

/* ==========================================================================
   SourceEngine — Scene III: "The Engine"
   Ranking signal bars + source spectrum gradient.
   "Importance, not popularity."
   ========================================================================== */

interface Props {
  mode: "prologue" | "manifesto";
  active: boolean;
}

export default function SourceEngine({ mode, active }: Props) {
  return (
    <div className={`film-engine film-engine--${mode}`} aria-hidden="true">
      {/* Ranking signal bars */}
      <div className="film-engine__bars" role="list">
        {RANKING_SIGNALS.map((s, i) => (
          <div key={s.name} className="film-engine__row" role="listitem">
            <span className="film-engine__signal">{s.name}</span>
            <div className="film-engine__bar-track">
              <div
                className="film-engine__bar-fill"
                style={{
                  transform: active ? `scaleX(${s.weight / 20})` : "scaleX(0)",
                  transitionDelay: `${i * 100}ms`,
                } as React.CSSProperties}
              />
            </div>
            <span className="film-engine__weight">{s.weight}%</span>
          </div>
        ))}
      </div>
      <p className="film-engine__caption">
        11 signals. Zero engagement metrics.
      </p>

      {/* Source spectrum bar */}
      <div className="film-engine__spectrum">
        <div
          className="film-engine__spectrum-bar"
          style={{
            transform: active ? "scaleX(1)" : "scaleX(0)",
          }}
        />
        <p className="film-engine__spectrum-stats">
          1,013 sources &middot; 158 countries &middot; 43 US major &middot;
          373 international &middot; 597 independent
        </p>
      </div>
    </div>
  );
}
