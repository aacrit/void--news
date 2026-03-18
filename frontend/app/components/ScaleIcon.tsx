"use client";

import { useRef, useEffect } from "react";

/* ---------------------------------------------------------------------------
   ScaleIcon — Reusable weighing scale brand icon with animation variants.

   Pure CSS keyframe animations scoped with `si-` prefix. The <style> tag is
   injected once into the document head via a ref guard.

   All animations respect `prefers-reduced-motion: reduce`.
   Uses `stroke="currentColor"` for automatic light/dark mode support.
   --------------------------------------------------------------------------- */

export type ScaleAnimation =
  | "idle"
  | "loading"
  | "hover"
  | "analyzing"
  | "balanced"
  | "pulse"
  | "draw"
  | "none";

export interface ScaleIconProps {
  size?: number;
  animation?: ScaleAnimation;
  className?: string;
  style?: React.CSSProperties;
}

/* ---- Approximate stroke-dasharray lengths for draw animation ---- */
// Fulcrum triangle: ~18
// Beam: 24
// Left pan path: ~26
// Right pan path: ~26
// Center post: 18
// Base: 8

const STYLES = `
/* === ScaleIcon keyframes === */

/* idle — gentle tipping */
@keyframes si-idle {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(2.5deg); }
  75% { transform: rotate(-2.5deg); }
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
  65% { transform: rotate(1.5deg); }
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

/* === Animation classes === */

.si-beam--idle {
  transform-origin: 16px 9px;
  animation: si-idle 4s cubic-bezier(0.16, 1, 0.3, 1) infinite;
}

.si-beam--loading {
  transform-origin: 16px 9px;
  animation: si-loading 1.5s cubic-bezier(0.16, 1, 0.3, 1) infinite;
}

.si-beam--hover {
  transform-origin: 16px 9px;
  animation: si-hover 300ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.si-beam--analyzing {
  transform-origin: 16px 9px;
  animation: si-analyzing 2s cubic-bezier(0.65, 0, 0.35, 1) infinite;
}

.si-beam--balanced {
  transform-origin: 16px 9px;
  animation: si-balanced 600ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.si-root--pulse {
  animation: si-pulse 300ms linear(0, 0.006, 0.025 2.8%, 0.101 6.1%, 0.539 18.9%, 0.721 25.3%, 0.849 31.5%, 0.937 38.1%, 0.968 41.8%, 0.991 45.7%, 1.006 50.1%, 1.015 55%, 1.017 63.9%, 1.001 85.6%, 1) forwards;
}

/* Draw animation — staggered per element */
.si-draw-fulcrum {
  --si-len: 18;
  stroke-dasharray: 18;
  stroke-dashoffset: 18;
  animation: si-draw 200ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 0ms;
}

.si-draw-beam {
  --si-len: 24;
  stroke-dasharray: 24;
  stroke-dashoffset: 24;
  animation: si-draw 180ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 120ms;
}

.si-draw-left-pan {
  --si-len: 26;
  stroke-dasharray: 26;
  stroke-dashoffset: 26;
  animation: si-draw 200ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 250ms;
}

.si-draw-right-pan {
  --si-len: 26;
  stroke-dasharray: 26;
  stroke-dashoffset: 26;
  animation: si-draw 200ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 250ms;
}

.si-draw-post {
  --si-len: 18;
  stroke-dasharray: 18;
  stroke-dashoffset: 18;
  animation: si-draw 180ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 450ms;
}

.si-draw-base {
  --si-len: 8;
  stroke-dasharray: 8;
  stroke-dashoffset: 8;
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
  .si-root--pulse,
  .si-draw-fulcrum,
  .si-draw-beam,
  .si-draw-left-pan,
  .si-draw-right-pan,
  .si-draw-post,
  .si-draw-base {
    animation: none !important;
    stroke-dashoffset: 0 !important;
    transform: none !important;
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
              : undefined;

  const rootClass = animation === "pulse" ? "si-root--pulse" : undefined;
  const isDraw = animation === "draw";

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 32 32"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
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
      {/* Fulcrum triangle */}
      <path
        d="M16,4 L13,9 L19,9 Z"
        className={isDraw ? "si-draw-fulcrum" : undefined}
      />

      {/* Beam group — beam + suspensions + pans */}
      <g className={beamClass}>
        {/* Beam */}
        <line
          x1="4" y1="9" x2="28" y2="9"
          className={isDraw ? "si-draw-beam" : undefined}
        />
        {/* Left suspension + pan */}
        <path
          d="M7,9 L5,18 L11,18 L9,9"
          className={isDraw ? "si-draw-left-pan" : undefined}
        />
        {/* Right suspension + pan */}
        <path
          d="M23,9 L21,18 L27,18 L25,9"
          className={isDraw ? "si-draw-right-pan" : undefined}
        />
      </g>

      {/* Center post */}
      <line
        x1="16" y1="9" x2="16" y2="27"
        className={isDraw ? "si-draw-post" : undefined}
      />

      {/* Base */}
      <line
        x1="12" y1="27" x2="20" y2="27"
        className={isDraw ? "si-draw-base" : undefined}
      />
    </svg>
  );
}

export default ScaleIcon;
