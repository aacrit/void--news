"use client";

import { useRef, useEffect } from "react";

/* ---------------------------------------------------------------------------
   ScaleIcon — the Sigil-O brand glyph

   The standalone version of the mark that sits inside the SigilWordmark's
   "O": a coverage ring (the analytical lens) with a level LEVEL balance beam
   passing through it and a weight tick at each end. Identical geometry to the
   wordmark's O (viewBox 0 0 100 100; ring cx50 cy50 r41 strokeWidth 8; beam
   x8->x92 y50 strokeWidth 6 round; ticks x9,43->x8,57 and x91,43->x92,57
   strokeWidth 5 round). No foot, post, or base. Stroked in --sigil-brass.

   At rest the mark is LEVEL and static. The animation prop tips the beam group
   around the ring center (50,50) for loading / analyzing / broadcast states,
   and animation="none" shows just the ring (pure favicon mark). All motion is
   suppressed under prefers-reduced-motion, leaving the level brass mark.

   Pure CSS keyframe animations scoped with `si-` prefix, injected once into
   <head>. Add `.si-hoverable` to any ancestor to get hover animation.
   --------------------------------------------------------------------------- */

export type ScaleAnimation =
  | "idle"
  | "loading"
  | "hover"
  | "analyzing"
  | "balanced"
  | "pulse"
  | "draw"
  | "broadcast"
  | "none";

export interface ScaleIconProps {
  size?: number;
  animation?: ScaleAnimation;
  className?: string;
  style?: React.CSSProperties;
}

const STYLES = `
/* === ScaleIcon (Sigil-O) keyframes === */

/* idle — gentle level settle */
@keyframes si-idle {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(1.2deg); }
  75% { transform: rotate(-1.2deg); }
}

/* loading — dramatic tipping */
@keyframes si-loading {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(8deg); }
  75% { transform: rotate(-8deg); }
}

/* hover — snappy single tip and return */
@keyframes si-hover {
  0% { transform: rotate(0deg); }
  35% { transform: rotate(-5deg); }
  65% { transform: rotate(1deg); }
  100% { transform: rotate(0deg); }
}

/* analyzing — deliberate read: tip left, pause, tip right, pause, settle */
@keyframes si-analyzing {
  0% { transform: rotate(0deg); }
  15% { transform: rotate(6deg); }
  30% { transform: rotate(6deg); }
  50% { transform: rotate(-6deg); }
  65% { transform: rotate(-6deg); }
  80% { transform: rotate(1deg); }
  100% { transform: rotate(0deg); }
}

/* balanced — spring settle from tipped to level */
@keyframes si-balanced {
  0% { transform: rotate(8deg); }
  40% { transform: rotate(-2deg); }
  65% { transform: rotate(0.8deg); }
  85% { transform: rotate(-0.3deg); }
  100% { transform: rotate(0deg); }
}

/* broadcast — VU meter needle oscillation, asymmetric amplitude */
@keyframes si-broadcast {
  0%, 100% { transform: rotate(0deg); }
  15% { transform: rotate(4deg); }
  35% { transform: rotate(-3deg); }
  55% { transform: rotate(3.5deg); }
  75% { transform: rotate(-2deg); }
}

/* pulse — whole-icon scale pulse */
@keyframes si-pulse {
  0% { transform: scale(1); }
  30% { transform: scale(0.95); }
  60% { transform: scale(1.05); }
  100% { transform: scale(1); }
}

/* draw — stroke reveal */
@keyframes si-draw {
  from { stroke-dashoffset: var(--si-len); }
  to { stroke-dashoffset: 0; }
}

/* ring-pulse — subtle lens activation on hover */
@keyframes si-void-pulse {
  0% { transform: scale(1); opacity: 1; }
  40% { transform: scale(1.06); opacity: 0.75; }
  100% { transform: scale(1); opacity: 1; }
}

/* === Animation classes — beam pivots around the ring center (50,50) === */

.si-beam--idle {
  transform-origin: 50px 50px;
  animation: si-idle 5.5s cubic-bezier(0.22, 1, 0.36, 1) infinite;
}

.si-beam--loading {
  transform-origin: 50px 50px;
  animation: si-loading 1.5s cubic-bezier(0.16, 1, 0.3, 1) infinite;
}

.si-beam--hover {
  transform-origin: 50px 50px;
  animation: si-hover 300ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.si-beam--analyzing {
  transform-origin: 50px 50px;
  animation: si-analyzing 2s cubic-bezier(0.65, 0, 0.35, 1) infinite;
}

.si-beam--balanced {
  transform-origin: 50px 50px;
  animation: si-balanced 600ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.si-beam--broadcast {
  transform-origin: 50px 50px;
  animation: si-broadcast 3s cubic-bezier(0.22, 1, 0.36, 1) infinite;
}

.si-root--pulse {
  animation: si-pulse 300ms linear(0, 0.006, 0.025 2.8%, 0.101 6.1%, 0.539 18.9%, 0.721 25.3%, 0.849 31.5%, 0.937 38.1%, 0.968 41.8%, 0.991 45.7%, 1.006 50.1%, 1.015 55%, 1.017 63.9%, 1.001 85.6%, 1) forwards;
}

/* === Hover — activated by .si-hoverable ancestor === */
.si-void { transform-origin: 50px 50px; }

.si-hoverable:hover .si-beam--idle {
  animation: si-hover 300ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.si-hoverable:hover .si-void {
  animation: si-void-pulse 300ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* === Draw animation — staggered per element === */
.si-draw-void {
  --si-len: 258;
  stroke-dasharray: 258;
  stroke-dashoffset: 258;
  animation: si-draw 400ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 0ms;
}

.si-draw-beam {
  --si-len: 84;
  stroke-dasharray: 84;
  stroke-dashoffset: 84;
  animation: si-draw 220ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 300ms;
}

.si-draw-left-tick {
  --si-len: 14;
  stroke-dasharray: 14;
  stroke-dashoffset: 14;
  animation: si-draw 140ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 460ms;
}

.si-draw-right-tick {
  --si-len: 14;
  stroke-dasharray: 14;
  stroke-dashoffset: 14;
  animation: si-draw 140ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 460ms;
}

/* === Reduced motion === */
@media (prefers-reduced-motion: reduce) {
  .si-beam--idle,
  .si-beam--loading,
  .si-beam--hover,
  .si-beam--analyzing,
  .si-beam--balanced,
  .si-beam--broadcast,
  .si-root--pulse,
  .si-void,
  .si-draw-void,
  .si-draw-beam,
  .si-draw-left-tick,
  .si-draw-right-tick {
    animation: none !important;
    stroke-dashoffset: 0 !important;
    transform: none !important;
  }

  .si-hoverable:hover .si-beam--idle,
  .si-hoverable:hover .si-void {
    animation: none !important;
  }
}
`;

/** Tracks whether we've already injected the style sheet into <head>. */
let stylesInjected = false;

function injectStyles() {
  if (stylesInjected) return;
  if (typeof document === "undefined") return;
  const style = document.createElement("style");
  style.setAttribute("data-si", "");
  style.textContent = STYLES;
  document.head.appendChild(style);
  stylesInjected = true;
}

export function ScaleIcon({
  size = 24,
  animation = "idle",
  className,
  style,
}: ScaleIconProps) {
  const injected = useRef(false);

  useEffect(() => {
    if (!injected.current) {
      injectStyles();
      injected.current = true;
    }
  }, []);

  /* Determine which CSS class to apply to the beam group */
  const beamClass =
    animation === "idle"
      ? "si-beam--idle"
      : animation === "loading"
        ? "si-beam--loading"
        : animation === "hover"
          ? "si-beam--hover"
          : animation === "analyzing"
            ? "si-beam--analyzing"
            : animation === "balanced"
              ? "si-beam--balanced"
              : animation === "broadcast"
                ? "si-beam--broadcast"
                : undefined;

  const rootClass = animation === "pulse" ? "si-root--pulse" : undefined;
  const isDraw = animation === "draw";
  const isNone = animation === "none";

  /* When animation="none", show only the coverage ring (pure favicon mark).
     For all other states, add the level balance beam + weight ticks. */
  const showBeam = !isNone;

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 100 100"
      fill="none"
      stroke="var(--sigil-brass)"
      role="img"
      aria-hidden="true"
      className={[rootClass, className].filter(Boolean).join(" ") || undefined}
      style={{
        height: size,
        width: size,
        display: "block",
        flexShrink: 0,
        overflow: "visible",
        ...style,
      }}
    >
      {/* Coverage ring — the analytical lens, the void. Hollow, no fill.
          This is what you see at favicon size (animation="none"). */}
      <circle
        cx="50"
        cy="50"
        r="41"
        strokeWidth={8}
        className={isDraw ? "si-draw-void" : "si-void"}
      />

      {showBeam && (
        /* Balance beam + weight ticks — level at rest, tips on animation.
           The ring is the fulcrum; the group pivots around (50,50). */
        <g className={beamClass}>
          <line
            x1="8" y1="50" x2="92" y2="50"
            strokeWidth={6} strokeLinecap="round"
            className={isDraw ? "si-draw-beam" : undefined}
          />
          <line
            x1="9" y1="43" x2="8" y2="57"
            strokeWidth={5} strokeLinecap="round"
            className={isDraw ? "si-draw-left-tick" : undefined}
          />
          <line
            x1="91" y1="43" x2="92" y2="57"
            strokeWidth={5} strokeLinecap="round"
            className={isDraw ? "si-draw-right-tick" : undefined}
          />
        </g>
      )}
    </svg>
  );
}

export default ScaleIcon;
