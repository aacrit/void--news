"use client";

import { useState, useEffect } from "react";
import { COMPARISON_SCORES, LANDSCAPE } from "../data";

/* ==========================================================================
   ArticleDifference — Scene IV: "The Difference"
   "Left" label morphs into 6-axis scorecard.
   Prologue: auto-morph after 2s. Manifesto: IO-triggered morph.
   ========================================================================== */

interface Props {
  mode: "prologue" | "manifesto";
  active: boolean;
}

export default function ArticleDifference({ mode, active }: Props) {
  const [morphed, setMorphed] = useState(false);

  useEffect(() => {
    if (!active) { setMorphed(false); return; }
    // Auto-morph after delay
    const delay = mode === "prologue" ? 2000 : 1500;
    const t = setTimeout(() => setMorphed(true), delay);
    return () => clearTimeout(t);
  }, [active, mode]);

  return (
    <div className={`film-diff film-diff--${mode}`} aria-hidden="true">
      {/* Comparison morph */}
      <div className={`film-diff__comparison${morphed ? " film-diff__comparison--morphed" : ""}`}>
        <div className="film-diff__them">
          <span className="film-diff__label">Outlet label</span>
          <span className="film-diff__value-them">&ldquo;Left&rdquo;</span>
        </div>
        <div className="film-diff__vs">vs</div>
        <div className="film-diff__us">
          <span className="film-diff__label">Per-article score</span>
          <div className="film-diff__scores">
            {COMPARISON_SCORES.map((s, i) => (
              <div key={s.name} className="film-diff__score-row">
                <span className="film-diff__score-name">{s.name}</span>
                <div className="film-diff__score-track">
                  <div
                    className="film-diff__score-fill"
                    style={{
                      transform: morphed ? `scaleX(${s.value / 100})` : "scaleX(0)",
                      transitionDelay: `${i * 100}ms`,
                    } as React.CSSProperties}
                  />
                </div>
                <span className="film-diff__score-num">{s.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Manifesto: competitive landscape below */}
      {mode === "manifesto" && (
        <div className="film-diff__landscape" role="list">
          {LANDSCAPE.map((l) => (
            <div key={l.them} className="film-diff__pair" role="listitem">
              <p className="film-diff__pair-them">{l.them}</p>
              <p className="film-diff__pair-us">{l.us}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
