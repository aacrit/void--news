"use client";

import { useRef, useEffect } from "react";

/* ---------------------------------------------------------------------------
   ScaleIcon — "The Void Scale" brand icon

   Blends three concepts:
   • Void — empty circle at top (the analytical lens, seeing through)
   • Newspaper — rectangular pans with headline rules (news pages)
   • Scale — balance beam, suspensions, post, base (weighing/measuring)

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
  | "none";

export interface ScaleIconProps {
  size?: number;
  animation?: ScaleAnimation;
  className?: string;
  style?: React.CSSProperties;
}

/* ---- Approximate stroke-dasharray lengths for draw animation ---- */
// Void circle:      circumference ≈ 16
// Beam:             26
// Left page path:   ~38
// Left headline:    5
// Right page path:  ~38
// Right headline:   5
// Center post:      19
// Base:             8

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

/* void-pulse — subtle lens activation on hover */
@keyframes si-void-pulse {
  0% { transform: scale(1); opacity: 1; }
  40% { transform: scale(1.15); opacity: 0.7; }
  100% { transform: scale(1); opacity: 1; }
}

/* === Animation classes === */

.si-beam--idle {
  transform-origin: 16px 8px;
  animation: si-idle 4s cubic-bezier(0.16, 1, 0.3, 1) infinite;
}

.si-beam--loading {
  transform-origin: 16px 8px;
  animation: si-loading 1.5s cubic-bezier(0.16, 1, 0.3, 1) infinite;
}

.si-beam--hover {
  transform-origin: 16px 8px;
  animation: si-hover 300ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.si-beam--analyzing {
  transform-origin: 16px 8px;
  animation: si-analyzing 2s cubic-bezier(0.65, 0, 0.35, 1) infinite;
}

.si-beam--balanced {
  transform-origin: 16px 8px;
  animation: si-balanced 600ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.si-root--pulse {
  animation: si-pulse 300ms linear(0, 0.006, 0.025 2.8%, 0.101 6.1%, 0.539 18.9%, 0.721 25.3%, 0.849 31.5%, 0.937 38.1%, 0.968 41.8%, 0.991 45.7%, 1.006 50.1%, 1.015 55%, 1.017 63.9%, 1.001 85.6%, 1) forwards;
}

/* === Hover — activated by .si-hoverable ancestor === */
.si-void { transform-origin: 16px 4px; }

.si-hoverable:hover .si-beam--idle {
  animation: si-hover 400ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

.si-hoverable:hover .si-void {
  animation: si-void-pulse 400ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
}

/* === Draw animation — staggered per element === */
.si-draw-void {
  --si-len: 16;
  stroke-dasharray: 16;
  stroke-dashoffset: 16;
  animation: si-draw 200ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 0ms;
}

.si-draw-beam {
  --si-len: 26;
  stroke-dasharray: 26;
  stroke-dashoffset: 26;
  animation: si-draw 180ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 120ms;
}

.si-draw-left-page {
  --si-len: 38;
  stroke-dasharray: 38;
  stroke-dashoffset: 38;
  animation: si-draw 220ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 220ms;
}

.si-draw-right-page {
  --si-len: 38;
  stroke-dasharray: 38;
  stroke-dashoffset: 38;
  animation: si-draw 220ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 220ms;
}

.si-draw-left-hl {
  --si-len: 5;
  stroke-dasharray: 5;
  stroke-dashoffset: 5;
  animation: si-draw 120ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 380ms;
}

.si-draw-right-hl {
  --si-len: 5;
  stroke-dasharray: 5;
  stroke-dashoffset: 5;
  animation: si-draw 120ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 380ms;
}

.si-draw-post {
  --si-len: 19;
  stroke-dasharray: 19;
  stroke-dashoffset: 19;
  animation: si-draw 180ms cubic-bezier(0.16, 1, 0.3, 1) forwards;
  animation-delay: 480ms;
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
  .si-void,
  .si-draw-void,
  .si-draw-beam,
  .si-draw-left-page,
  .si-draw-right-page,
  .si-draw-left-hl,
  .si-draw-right-hl,
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
      {/* Void circle — the analytical lens, empty center */}
      <circle
        cx="16" cy="4" r="2.5"
        className={isDraw ? "si-draw-void" : "si-void"}
      />

      {/* Beam group — beam + newspaper page pans (tips on animation) */}
      <g className={beamClass}>
        {/* Beam */}
        <line
          x1="3" y1="8" x2="29" y2="8"
          className={isDraw ? "si-draw-beam" : undefined}
        />
        {/* Left suspension + newspaper page */}
        <path
          d="M7,8 L4,13 L4,22 L12,22 L12,13 L9,8"
          className={isDraw ? "si-draw-left-page" : undefined}
        />
        {/* Left headline rule */}
        <line
          x1="5.5" y1="16.5" x2="10.5" y2="16.5"
          className={isDraw ? "si-draw-left-hl" : undefined}
        />
        {/* Right suspension + newspaper page */}
        <path
          d="M23,8 L20,13 L20,22 L28,22 L28,13 L25,8"
          className={isDraw ? "si-draw-right-page" : undefined}
        />
        {/* Right headline rule */}
        <line
          x1="21.5" y1="16.5" x2="26.5" y2="16.5"
          className={isDraw ? "si-draw-right-hl" : undefined}
        />
      </g>

      {/* Center post */}
      <line
        x1="16" y1="8" x2="16" y2="27"
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
