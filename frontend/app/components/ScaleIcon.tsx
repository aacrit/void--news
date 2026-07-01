"use client";

import { useRef, useEffect } from "react";

/* ---------------------------------------------------------------------------
   ScaleIcon — "Void Circle + Scale Beam" hybrid brand icon

   The void circle is the primary mark — a hollow ring representing emptiness,
   neutrality, the analytical lens. A scale beam passes through it, using the
   circle as a natural fulcrum/pivot point. The beam tips with animations.

   At rest/small sizes: the circle dominates.
   At larger sizes and during animations: the scale beam becomes visible
   and tips, revealing the balance/weighing metaphor.

   animation="none": Only the void circle (pure favicon mark).
   animation="idle"+: Circle + beam + post + base, with tipping.

   Pure CSS keyframe animations scoped with `si-` prefix.
   Styles injected once into <head>.
   All animations respect `prefers-reduced-motion: reduce`.
   Uses `stroke="currentColor"` for automatic light/dark mode.
   Add `.si-hoverable` to any ancestor to get hover animation on the icon.
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

/* ---- Approximate stroke-dasharray lengths for draw animation ---- */
// Void circle:      organic path length ~57
// Beam:             ~27 (organic S-curve from M3 to 29)
// Left tick:        ~4
// Right tick:       ~4
// Center post:      ~14 (from y1=19 to y2=27)
// Base:             ~9 (organic curve)

const STYLES = `
/* === ScaleIcon keyframes === */

/* idle — gentle tipping */
@keyframes si-idle {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(1.5deg); }
  75% { transform: rotate(-1.5deg); }
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

/* void-pulse — subtle lens activation on hover */
@keyframes si-void-pulse {
  0% { transform: scale(1); opacity: 1; }
  40% { transform: scale(1.08); opacity: 0.7; }
  100% { transform: scale(1); opacity: 1; }
}

/* === Animation classes === */

/* Beam pivot = circle center at (16, 13) */

.si-beam--idle {
  transform-origin: 16px 13px;
  animation: si-idle 5.5s cubic-bezier(0.22, 1, 0.36, 1) infinite;
}

.si-beam--loading {
  transform-origin: 16px 13px;
  animation: si-loading 1.5s cubic-bezier(0.16, 1, 0.3, 1) infinite;
}

.si-beam--hover {
  transform-origin: 16px 13px;
  animation: si-hover 300ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.si-beam--analyzing {
  transform-origin: 16px 13px;
  animation: si-analyzing 2s cubic-bezier(0.65, 0, 0.35, 1) infinite;
}

.si-beam--balanced {
  transform-origin: 16px 13px;
  animation: si-balanced 600ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.si-beam--broadcast {
  transform-origin: 16px 13px;
  animation: si-broadcast 3s cubic-bezier(0.22, 1, 0.36, 1) infinite;
}

.si-root--pulse {
  animation: si-pulse 300ms linear(0, 0.006, 0.025 2.8%, 0.101 6.1%, 0.539 18.9%, 0.721 25.3%, 0.849 31.5%, 0.937 38.1%, 0.968 41.8%, 0.991 45.7%, 1.006 50.1%, 1.015 55%, 1.017 63.9%, 1.001 85.6%, 1) forwards;
}

/* === Hover — activated by .si-hoverable ancestor === */
.si-void { transform-origin: 16px 13px; }

.si-hoverable:hover .si-beam--idle {
  animation: si-hover 300ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.si-hoverable:hover .si-void {
  animation: si-void-pulse 300ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* === Draw animation — staggered per element === */
.si-draw-void {
  --si-len: 57;
  stroke-dasharray: 57;
  stroke-dashoffset: 57;
  animation: si-draw 350ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 0ms;
}

.si-draw-beam {
  --si-len: 27;
  stroke-dasharray: 27;
  stroke-dashoffset: 27;
  animation: si-draw 180ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 280ms;
}

.si-draw-left-tick {
  --si-len: 4;
  stroke-dasharray: 4;
  stroke-dashoffset: 4;
  animation: si-draw 120ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 400ms;
}

.si-draw-right-tick {
  --si-len: 4;
  stroke-dasharray: 4;
  stroke-dashoffset: 4;
  animation: si-draw 120ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 400ms;
}

.si-draw-post {
  --si-len: 14;
  stroke-dasharray: 14;
  stroke-dashoffset: 14;
  animation: si-draw 180ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 480ms;
}

.si-draw-base {
  --si-len: 9;
  stroke-dasharray: 9;
  stroke-dashoffset: 9;
  animation: si-draw 150ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 600ms;
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
  .si-draw-right-tick,
  .si-draw-post,
  .si-draw-base {
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

  /* When animation="none", show only the void circle (pure favicon mark).
     For all other states, show the full scale apparatus. */
  const showScale = !isNone;

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 32 32"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      role="img"
      aria-hidden="true"
      className={[rootClass, className].filter(Boolean).join(" ") || undefined}
      style={{
        height: size,
        width: "auto",
        display: "block",
        flexShrink: 0,
        ...style,
      }}
    >
      {/* Void circle — organic hand-drawn path, the analytical lens, the void.
          Approximately centered at (16, 13), radius ~9. Hollow ring, no fill.
          This is what you see at favicon size (animation="none"). */}
      <path
        d="M16 4 C24 3.5 25.5 7.5 25 13 C24.5 18.5 22.5 22 16 22 C9.5 22 7.5 18.5 7 13 C6.5 7.5 8 3.5 16 4"
        className={isDraw ? "si-draw-void" : "si-void"}
      />

      {showScale && (
        <>
          {/* Beam group — horizontal beam through the circle + weight ticks.
              The circle is the fulcrum. Pivots around (16, 13). */}
          <g className={beamClass}>
            {/* Beam — organic S-curve extending beyond circle edges */}
            <path
              d="M3 13 C10 12.2 22 13.8 29 13"
              className={isDraw ? "si-draw-beam" : undefined}
            />
            {/* Left weight tick */}
            <line
              x1="5" y1="11" x2="5" y2="15"
              className={isDraw ? "si-draw-left-tick" : undefined}
            />
            {/* Right weight tick */}
            <line
              x1="27" y1="11" x2="27" y2="15"
              className={isDraw ? "si-draw-right-tick" : undefined}
            />
          </g>

          {/* Center post — from bottom of circle to base */}
          <line
            x1="16" y1="22" x2="16" y2="29"
            className={isDraw ? "si-draw-post" : undefined}
          />

          {/* Base — organic subtle curve */}
          <path
            d="M12 29 C14 28.7 18 29.3 20 29"
            className={isDraw ? "si-draw-base" : undefined}
          />
        </>
      )}
    </svg>
  );
}

export default ScaleIcon;
