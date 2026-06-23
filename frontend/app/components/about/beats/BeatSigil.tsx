"use client";

import { useState, useMemo } from "react";
import Sigil from "../../Sigil";
import { demoSigil } from "../demoSigil";
import { BEATS, SIX_AXES } from "../../../film/data";
import { leanLabel } from "../../../lib/biasColors";

/* ---------------------------------------------------------------------------
   Beat 2 — "One mark reads the bias."
   The centerpiece: a LIVE <Sigil> driven by three controls. Dragging lean
   recolors + tilts the beam; raising spread opens the divergence fan; sources
   fills the coverage ring; dead-center + low spread shows strict green
   (consensus), center + high spread the neutral divergent standoff.
   Teaches the REAL mark — no bespoke SVG.
   --------------------------------------------------------------------------- */

const BEAT = BEATS[1];

export default function BeatSigil() {
  const [lean, setLean] = useState(38);
  const [spread, setSpread] = useState(20);
  const [sources, setSources] = useState(9);

  const data = useMemo(() => demoSigil(lean, spread, sources), [lean, spread, sources]);

  const leanText = leanLabel(lean);
  const spreadText = spread >= 10 ? "Divergent" : spread <= 4 ? "Strong agreement" : "Some spread";
  const balanced = lean >= 47 && lean <= 53;

  return (
    <section className="beat beat--sigil" aria-labelledby="beat-sigil-h">
      <div className="beat__head">
        <h2 id="beat-sigil-h" className="beat__headline">{BEAT.headline}</h2>
        <p className="beat__body">{BEAT.body}</p>
      </div>

      <div className="sigdemo">
        <div className="sigdemo__stage" aria-hidden="true">
          <Sigil data={data} size="xl" instant />
        </div>

        <dl className="sigdemo__readout" aria-live="polite">
          <div><dt>Lean</dt><dd>{leanText}</dd></div>
          <div><dt>Sources</dt><dd>{sources}</dd></div>
          <div><dt>Agreement</dt><dd>{spreadText}</dd></div>
        </dl>

        <div className="sigdemo__controls">
          <label className="sigdemo__ctl">
            <span>Lean — {leanText}</span>
            <input
              type="range" min={0} max={100} value={lean}
              onChange={(e) => setLean(+e.target.value)}
              aria-label="Political lean"
              aria-valuetext={leanText}
            />
          </label>
          <label className="sigdemo__ctl">
            <span>Source agreement — {spreadText}</span>
            <input
              type="range" min={0} max={40} value={spread}
              onChange={(e) => setSpread(+e.target.value)}
              aria-label="Source agreement to divergence"
              aria-valuetext={spreadText}
            />
          </label>
          <label className="sigdemo__ctl">
            <span>Sources — {sources}</span>
            <input
              type="range" min={1} max={15} value={sources}
              onChange={(e) => setSources(+e.target.value)}
              aria-label="Number of sources covering the story"
              aria-valuetext={`${sources} sources`}
            />
          </label>
        </div>

        <p className="sigdemo__hint">
          {balanced && spread >= 10
            ? "Balanced on average — but the sources are split. The mark goes neutral, not green."
            : balanced
              ? "Dead center and in agreement: genuine consensus reads green."
              : "The beam takes a side. Darker = stronger tilt."}
        </p>
      </div>

      <details className="beat__more">
        <summary>How the six axes work</summary>
        <ul className="beat__axes">
          {SIX_AXES.map((a) => (
            <li key={a.name}>
              <strong>{a.name}.</strong> {a.brief} <span className="beat__axes-signals">{a.signals}</span>
            </li>
          ))}
        </ul>
        <p className="beat__more-note">
          Every score is rule-based NLP on the article text. No LLM, no outlet label. We read the article, not the masthead.
        </p>
      </details>
    </section>
  );
}
