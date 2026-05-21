/* ==========================================================================
   film/constants.ts — SVG paths, timing tokens, spring easings

   Organic hand-drawn brand mark coordinates matching ScaleIcon/Sigil.
   All paths are bezier curves — no perfect circles anywhere.
   ========================================================================== */

/* ── Organic SVG Paths (matching ScaleIcon.tsx production marks) ── */

/** Void circle — analytical lens. Approx center (16, 13), radius ~9. */
export const VOID_CIRCLE = "M16 4 C24 3.5 25.5 7.5 25 13 C24.5 18.5 22.5 22 16 22 C9.5 22 7.5 18.5 7 13 C6.5 7.5 8 3.5 16 4";

/** Beam — horizontal S-curve through the circle. Fulcrum at (16, 13). */
export const BEAM_CURVE = "M3 13 C10 12.2 22 13.8 29 13";

/** Base — organic subtle curve beneath the post. */
export const BASE_CURVE = "M12 29 C14 28.7 18 29.3 20 29";

/** Approximate stroke-dasharray lengths for draw animation. */
export const VOID_CIRC_LEN = 57;
export const BEAM_LEN = 27;
export const TICK_LEN = 4;
export const POST_LEN = 14;
export const BASE_LEN = 9;

/** Transform origin — circle center, beam fulcrum. */
export const PIVOT = "16px 13px";

/** Tick positions (vertical weight marks on beam). */
export const LEFT_TICK = { x1: 5, y1: 11, x2: 5, y2: 15 };
export const RIGHT_TICK = { x1: 27, y1: 11, x2: 27, y2: 15 };

/** Post (center vertical support). */
export const POST = { x1: 16, y1: 22, x2: 16, y2: 29 };

/* ── Spring Easing (CSS linear() approximation) ── */

export const SPRING = "linear(0, 0.009, 0.035 2.1%, 0.141 4.4%, 0.723 15.5%, 0.938 20.7%, 1.017 24.3%, 1.061 27.7%, 1.085 32%, 1.078 36.3%, 1.042 44.4%, 1.014 53.3%, 0.996 64.4%, 1.001 78.8%, 1)";

export const SPRING_BOUNCY = "linear(0, 0.009, 0.038 2.4%, 0.156 5.2%, 0.614 15%, 0.812 20%, 0.946 26%, 1.035 32%, 1.075 37%, 1.08 40%, 1.065 44%, 1.033 50%, 1.008 58%, 0.998 68%, 1.002 82%, 1)";

export const SPRING_GENTLE = "linear(0, 0.007, 0.028 3.2%, 0.113 6.8%, 0.458 17.5%, 0.636 23%, 0.778 29%, 0.879 35.5%, 0.942 42%, 0.975 49%, 0.993 57%, 1.003 66%, 1.005 76%, 1.001 88%, 1)";

/* ── Draw Animation Stagger Timing (matches ScaleIcon) ── */

export const DRAW_TIMING = {
  void:  { duration: 350, delay: 0 },
  beam:  { duration: 180, delay: 280 },
  tickL: { duration: 120, delay: 400 },
  tickR: { duration: 120, delay: 400 },
  post:  { duration: 180, delay: 480 },
  base:  { duration: 150, delay: 600 },
};

/* ── Sigil Breakdown Stage Durations ── */

export const BREAKDOWN_TIMING = {
  drawEnd: 1200,
  separateEnd: 2500,
  labelEnd: 4500,
  reassembleEnd: 5500,
  activateEnd: 8000,
};

/* ── Separation Transforms (exploded view offsets) ── */

export const EXPLODE_TRANSFORMS = {
  circle: "translate(0, -18)",
  beam:   "translate(28, 0)",
  tickL:  "translate(-12, -8)",
  tickR:  "translate(12, -8)",
  post:   "translate(0, 16)",
  base:   "translate(0, 30)",
};

/* ── Preview Thumbnails (deterministic pseudo-random positions) ── */

export const SRC_DOTS = Array.from({ length: 12 }, (_, i) => ({
  left: `${8 + ((i * 37 + 13) % 84)}%`,
  top: `${20 + ((i * 23 + 7) % 40)}%`,
  opacity: 0.3 + ((i * 17 + 5) % 50) / 100,
}));

export const WAVE_HEIGHTS = Array.from({ length: 16 }, (_, i) =>
  `${20 + Math.sin(i * 0.7) * 40 + ((i * 13 + 3) % 15)}%`
);
