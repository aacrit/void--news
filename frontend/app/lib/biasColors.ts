/**
 * biasColors.ts — Single source of truth for bias color computation,
 * lean labels, lean buckets, and CSS variable caching.
 *
 * Replaces duplicated logic across BiasLens, BiasInspector, Sigil,
 * and DeepDiveSpectrum. One cache, one MutationObserver, one set of
 * thresholds.
 */

/* ── Lean bucket boundaries — used everywhere ───────────────────────────── */

export type LeanCategory =
  | "far-left"
  | "left"
  | "center-left"
  | "center"
  | "center-right"
  | "right"
  | "far-right";

/**
 * Unified lean boundaries — identical for bucket placement AND labels.
 * 0-20: Far Left, 21-35: Left, 36-45: Center-Left, 46-55: Center,
 * 56-65: Center-Right, 66-80: Right, 81-100: Far Right.
 */
export function leanToBucket(v: number): LeanCategory {
  if (v <= 20) return "far-left";
  if (v <= 35) return "left";
  if (v <= 45) return "center-left";
  if (v <= 55) return "center";
  if (v <= 65) return "center-right";
  if (v <= 80) return "right";
  return "far-right";
}

export function leanLabel(v: number): string {
  if (v <= 20) return "Far Left";
  if (v <= 35) return "Left";
  if (v <= 45) return "Center-Left";
  if (v <= 55) return "Center";
  if (v <= 65) return "Center-Right";
  if (v <= 80) return "Right";
  return "Far Right";
}

export function leanLabelAbbr(v: number): string {
  if (v <= 20) return "FL";
  if (v <= 35) return "L";
  if (v <= 45) return "CL";
  if (v <= 55) return "C";
  if (v <= 65) return "CR";
  if (v <= 80) return "R";
  return "FR";
}

export function senseLabel(v: number): string {
  if (v <= 25) return "Measured";
  if (v <= 50) return "Moderate";
  if (v <= 75) return "Elevated";
  return "Inflammatory";
}

export function rigorLabel(v: number): string {
  if (v >= 75) return "High rigor";
  if (v >= 50) return "Good rigor";
  if (v >= 25) return "Moderate rigor";
  return "Low rigor";
}

export function coverageLabel(v: number): string {
  if (v >= 75) return "Strongly sourced";
  if (v >= 50) return "Well sourced";
  if (v >= 25) return "Moderately sourced";
  return "Lightly sourced";
}

/* ── CSS variable cache — single observer ───────────────────────────────── */

const SSR_FALLBACK: Record<string, string> = {
  "--bias-far-left": "#1D4ED8",
  "--bias-left": "#3B82F6",
  "--bias-center-left": "#93C5FD",
  "--bias-center": "#9CA3AF",
  "--bias-center-right": "#FCA5A5",
  "--bias-right": "#EF4444",
  "--bias-far-right": "#B91C1C",
  "--sense-low": "#22C55E",
  "--sense-medium": "#EAB308",
  "--sense-high": "#EF4444",
  "--type-reporting": "#3B82F6",
  "--type-analysis": "#8B5CF6",
  "--type-opinion": "#F97316",
  "--rigor-high": "#22C55E",
  "--rigor-medium": "#EAB308",
  "--rigor-low": "#EF4444",
};

let cache: Record<string, string> | null = null;

export function getColors(): Record<string, string> {
  if (cache) return cache;
  if (typeof document === "undefined") return SSR_FALLBACK;
  const style = getComputedStyle(document.documentElement);
  cache = {};
  for (const v of Object.keys(SSR_FALLBACK)) {
    cache[v] = style.getPropertyValue(v).trim() || SSR_FALLBACK[v];
  }
  return cache;
}

// Single MutationObserver for theme changes
if (typeof window !== "undefined") {
  new MutationObserver((ms) => {
    for (const m of ms) {
      if (m.type === "attributes" && m.attributeName === "data-mode") {
        cache = null;
      }
    }
  }).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-mode"],
  });
}

/* ── Color interpolation ────────────────────────────────────────────────── */

export function lerpColor(a: string, b: string, t: number): string {
  const ah = parseInt(a.replace("#", ""), 16);
  const bh = parseInt(b.replace("#", ""), 16);
  const ar = (ah >> 16) & 0xff, ag = (ah >> 8) & 0xff, ab = ah & 0xff;
  const br = (bh >> 16) & 0xff, bg = (bh >> 8) & 0xff, bb = bh & 0xff;
  const r = Math.round(ar + (br - ar) * t);
  const g = Math.round(ag + (bg - ag) * t);
  const bl = Math.round(ab + (bb - ab) * t);
  return `#${((r << 16) | (g << 8) | bl).toString(16).padStart(6, "0")}`;
}

/* ── Semantic color getters ─────────────────────────────────────────────── */

export function getLeanColor(v: number): string {
  const c = getColors();
  if (v <= 14) return c["--bias-far-left"];
  if (v <= 20) return lerpColor(c["--bias-far-left"], c["--bias-left"], (v - 14) / 6);
  if (v <= 35) return lerpColor(c["--bias-left"], c["--bias-center-left"], (v - 20) / 15);
  if (v <= 45) return c["--bias-center-left"];
  if (v <= 55) return c["--bias-center"];
  if (v <= 65) return c["--bias-center-right"];
  if (v <= 80) return lerpColor(c["--bias-center-right"], c["--bias-right"], (v - 65) / 15);
  if (v <= 86) return lerpColor(c["--bias-right"], c["--bias-far-right"], (v - 80) / 6);
  return c["--bias-far-right"];
}

export function getCoverageColor(v: number): string {
  const c = getColors();
  if (v >= 60) return c["--sense-low"];
  if (v >= 30) return c["--sense-medium"];
  return c["--sense-high"];
}

export function getSenseColor(v: number): string {
  const c = getColors();
  if (v <= 50) return lerpColor(c["--sense-low"], c["--sense-medium"], v / 50);
  return lerpColor(c["--sense-medium"], c["--sense-high"], (v - 50) / 50);
}

export function getRigorColor(v: number): string {
  const c = getColors();
  if (v <= 50) return lerpColor(c["--rigor-low"], c["--rigor-medium"], v / 50);
  return lerpColor(c["--rigor-medium"], c["--rigor-high"], (v - 50) / 50);
}

export function getFramingColor(v: number): string {
  return getSenseColor(v);
}
