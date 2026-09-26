"use client";

import { useState, useRef, useEffect, useId } from "react";
import { Info } from "@phosphor-icons/react";
import { LEAN_SHAPE_LEGEND } from "../lib/biasColors";

/* ---------------------------------------------------------------------------
   LeanLabelLegend — a small info affordance next to the feed header that
   defines the coverage descriptors shown under each headline.

   Readers see the card's register (seven strokes) and one word under it:
   Leans left, Split, Balanced, Consensus, "9 measured". This popover defines
   exactly those words, from LEAN_SHAPE_LEGEND in lib/biasColors.ts, which is
   built from the same constants the card's rule uses (2026-09-26: it used to
   define the retired ladder's words, which no card printed). Accessible: a labelled toggle button (aria-expanded /
   aria-controls) reveals a labelled region; Escape and outside-click dismiss.
   --------------------------------------------------------------------------- */

export default function LeanLabelLegend() {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLSpanElement>(null);
  const rawId = useId();
  const panelId = `lean-legend-${rawId.replace(/:/g, "")}`;

  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <span className="lean-legend" ref={wrapRef}>
      <button
        type="button"
        className="lean-legend__btn"
        aria-expanded={open}
        aria-controls={open ? panelId : undefined}
        aria-label="What the coverage labels mean"
        onClick={() => setOpen((v) => !v)}
      >
        <Info size={14} weight="bold" aria-hidden="true" />
      </button>

      {open && (
        <div id={panelId} role="region" aria-label="Coverage label guide" className="lean-legend__panel">
          <p className="lean-legend__intro">
            Under each headline, seven short strokes show how many articles came
            from each point on the lean scale, far left to far right. The word
            under them reads that shape.
          </p>

          <dl className="lean-legend__list">
            {LEAN_SHAPE_LEGEND.map((t) => (
              <div className="lean-legend__row" key={t.shape}>
                <dt>{t.term}</dt>
                <dd>{t.definition}</dd>
              </div>
            ))}
          </dl>

          <p className="lean-legend__note">
            An underline in red marks a story whose sources frame it very
            differently; in green, one they frame alike. The number of sources
            is the count of outlets that covered the story.
          </p>
        </div>
      )}
    </span>
  );
}
