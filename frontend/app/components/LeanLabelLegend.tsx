"use client";

import { useState, useRef, useEffect, useId } from "react";
import { Info } from "@phosphor-icons/react";

/* ---------------------------------------------------------------------------
   LeanLabelLegend — a small info affordance next to the feed header that
   defines the coverage descriptors shown under each headline.

   Readers see tags like "Right", "Flat", "Contested", "Split" but nothing
   tells them which read the LEAN (which way coverage tilts) and which read the
   SPREAD (how much sources agree). This popover names both groups once, at the
   top of the feed. Accessible: a labelled toggle button (aria-expanded /
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
            The tag under each headline reads the coverage two ways: which way it
            leans, and how much the sources agree.
          </p>

          <p className="lean-legend__group-title">Lean</p>
          <dl className="lean-legend__list">
            <div className="lean-legend__row">
              <dt>Left / Right</dt>
              <dd>The aggregated coverage clearly leans that way (Far for the strongest tilt).</dd>
            </div>
            <div className="lean-legend__row">
              <dt>Balanced</dt>
              <dd>Sources sit at the center.</dd>
            </div>
            <div className="lean-legend__row">
              <dt>Flat</dt>
              <dd>No clear lean; the coverage does not tilt either way.</dd>
            </div>
          </dl>

          <p className="lean-legend__group-title">Agreement</p>
          <dl className="lean-legend__list">
            <div className="lean-legend__row">
              <dt>Contested</dt>
              <dd>Left and right sources both cover it and genuinely disagree.</dd>
            </div>
            <div className="lean-legend__row">
              <dt>Split / Divergent</dt>
              <dd>Sources frame the same story very differently.</dd>
            </div>
            <div className="lean-legend__row">
              <dt>Aligned</dt>
              <dd>Sources tell it largely the same way.</dd>
            </div>
          </dl>
        </div>
      )}
    </span>
  );
}
