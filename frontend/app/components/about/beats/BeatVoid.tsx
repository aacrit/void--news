"use client";

import { useRef, useState } from "react";
import { DIVERGENT_HEADLINES, BEATS } from "../../../film/data";
import { getLeanColor, leanToDisplayPos, leanLabel } from "../../../lib/biasColors";
import { useReducedMotion } from "../../../film/useReducedMotion";
import { useMotion } from "../useMotion";
import { hapticLight } from "../../../lib/haptics";

/* ---------------------------------------------------------------------------
   Beat 1 — "One story. Five versions."
   Five outlet headlines on the same event. The reader drags each chip along a
   left↔right spectrum rail (guessing the lean), then "Reveal" springs every
   chip to where its language actually lands, lit in its lean color.
   --------------------------------------------------------------------------- */

const BEAT = BEATS[0];

// Display x-position (%) for a true lean, using the perceptual-expansion curve
// so the spread matches what the feed Sigils show.
function leanToX(lean: number): number {
  return leanToDisplayPos(lean);
}

export default function BeatVoid() {
  const reduced = useReducedMotion();
  const motion = useMotion(!reduced.current);
  // Reduced motion / no-JS: start already revealed (no set-state-in-effect).
  const [revealed, setRevealed] = useState(
    () => typeof window !== "undefined" && window.matchMedia("(prefers-reduced-motion: reduce)").matches,
  );
  const chipRefs = useRef<(HTMLDivElement | null)[]>([]);
  const railRef = useRef<HTMLDivElement>(null);
  const dragState = useRef<{ i: number; startX: number; startPct: number } | null>(null);
  // Per-chip horizontal position as % of rail width (guess positions).
  const [pcts, setPcts] = useState<number[]>(() =>
    DIVERGENT_HEADLINES.map((_, i) => 18 + (i / (DIVERGENT_HEADLINES.length - 1)) * 64),
  );

  const reveal = () => {
    setRevealed(true);
    hapticLight();
    const targets = DIVERGENT_HEADLINES.map((h) => leanToX(h.leanScore));
    if (motion && !reduced.current) {
      DIVERGENT_HEADLINES.forEach((_, i) => {
        const el = chipRefs.current[i];
        if (!el) return;
        motion.animate(pcts[i], targets[i], {
          type: "spring",
          stiffness: 220,
          damping: 26,
          onUpdate: (v: number) => { el.style.left = `${v}%`; },
        });
      });
    }
    setPcts(targets);
  };

  // Pointer drag along the rail (horizontal).
  const onPointerDown = (i: number) => (e: React.PointerEvent) => {
    if (revealed) return;
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    dragState.current = { i, startX: e.clientX, startPct: pcts[i] };
  };
  const onPointerMove = (e: React.PointerEvent) => {
    const ds = dragState.current;
    const rail = railRef.current;
    if (!ds || !rail) return;
    const w = rail.getBoundingClientRect().width || 1;
    const deltaPct = ((e.clientX - ds.startX) / w) * 100;
    const next = Math.max(4, Math.min(96, ds.startPct + deltaPct));
    setPcts((prev) => { const c = [...prev]; c[ds.i] = next; return c; });
  };
  const onPointerUp = () => { dragState.current = null; };

  return (
    <section className="beat beat--void" aria-labelledby="beat-void-h">
      <div className="beat__head">
        <h2 id="beat-void-h" className="beat__headline">{BEAT.headline}</h2>
        <p className="beat__body">{BEAT.body}</p>
      </div>

      <div className="vrail" ref={railRef} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerLeave={onPointerUp}>
        <div className="vrail__track" aria-hidden="true">
          <span className="vrail__end vrail__end--l">Left</span>
          <span className="vrail__tick" />
          <span className="vrail__end vrail__end--r">Right</span>
        </div>
        {DIVERGENT_HEADLINES.map((h, i) => {
          const color = getLeanColor(leanToDisplayPos(h.leanScore));
          return (
            <div
              key={h.outlet}
              ref={(el) => { chipRefs.current[i] = el; }}
              className={`vchip${revealed ? " vchip--revealed" : ""}`}
              style={{ left: `${pcts[i]}%`, ...(revealed ? { ["--vchip-color" as string]: color } : {}) }}
              onPointerDown={onPointerDown(i)}
              role="group"
              aria-label={`${h.outlet}: ${h.headline}. ${revealed ? `Actual lean: ${leanLabel(h.leanScore)}.` : "Drag to place on the spectrum."}`}
            >
              <span className="vchip__outlet">{h.outlet}</span>
              <span className="vchip__headline">{h.headline}</span>
              {revealed && <span className="vchip__lean">{leanLabel(h.leanScore)}</span>}
            </div>
          );
        })}
      </div>

      {!revealed && (
        <button className="beat__action" onClick={reveal}>
          Reveal where they land
        </button>
      )}
      {revealed && (
        <p className="beat__note">Same facts. The words choose a side.</p>
      )}
    </section>
  );
}
