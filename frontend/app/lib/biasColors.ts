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

/* ── Tilt vocabulary — story/cluster-level lean ────────────────────────────
   Distinct from source lean labels (leanLabel). "Tilt" describes a
   measurement of aggregate text lean, not an editorial identity.
   Boundaries are data-driven from production score distribution:
   53.6% at 50, 21.6% at 37-38, 9.5% at 62, 6.1% at 75-79.            ── */

export type TiltCategory =
  | "far-left-tilt"
  | "left-tilt"
  | "balanced"
  | "right-tilt"
  | "far-right-tilt";

export function tiltToBucket(v: number): TiltCategory {
  if (v <= 29) return "far-left-tilt";
  if (v <= 46) return "left-tilt";
  if (v <= 53) return "balanced";
  if (v <= 72) return "right-tilt";
  return "far-right-tilt";
}

export function tiltLabel(v: number): string {
  if (v <= 29) return "Far Left Tilt";
  if (v <= 46) return "Left Tilt";
  if (v <= 53) return "Balanced";
  if (v <= 72) return "Right Tilt";
  return "Far Right Tilt";
}

export function tiltLabelAbbr(v: number): string {
  if (v <= 29) return "FL";
  if (v <= 46) return "LT";
  if (v <= 53) return "BAL";
  if (v <= 72) return "RT";
  return "FR";
}

/** Human-readable descriptor for the Sigil popup — explains what the score means */
export function tiltDescriptor(v: number): string {
  if (v <= 15) return "Strong left lean in coverage language";
  if (v <= 29) return "Clear left lean in coverage framing";
  if (v <= 38) return "Moderate left lean detected";
  if (v <= 46) return "Slight left lean in text analysis";
  if (v <= 53) return "Balanced coverage from multiple perspectives";
  if (v <= 60) return "Slight right lean in text analysis";
  if (v <= 72) return "Moderate right lean detected";
  if (v <= 85) return "Clear right lean in coverage framing";
  return "Strong right lean in coverage language";
}

/* ── Unscored gate — story lacks analytical signal for tilt label ───────── */

/**
 * Returns true when a story's lean falls in the balanced range (47-53)
 * but lacks enough analytical signal to genuinely call it "Balanced."
 * Three gates, any failure → unscored:
 *   A: all articles defaulted to 50 (no spread, no range, avg=50)
 *   B: single-source cluster (one voice isn't balance)
 *   C: low analytical confidence (<0.4)
 */
export function isUnscoredTilt(
  lean: number,
  sourceCount: number,
  leanSpread: number,
  leanRange: number,
  aggregateConfidence: number,
): boolean {
  if (lean < 47 || lean > 53) return false;
  const allDefault = lean === 50 && leanSpread === 0 && leanRange === 0;
  if (allDefault) return true;
  if (sourceCount < 2) return true;
  if (aggregateConfidence < 0.4) return true;
  return false;
}

/* ── Sigil label — lean + divergence combined ──────────────────────────────
   For balanced stories: label communicates divergence state (the lean is neutral,
   so divergence IS the useful information). For tilted stories: lean direction
   remains primary, with divergence flag suffix when top/bottom 10%.          ── */

export function sigilLabelInfo(
  lean: number,
  agreement: number,
  divergenceFlag?: "divergent" | "consensus" | null,
  unscored?: boolean,
): { text: string; color: string } {
  if (unscored) return { text: "\u2014", color: "var(--fg-tertiary)" };

  const isBalanced = lean >= 47 && lean <= 53;

  if (isBalanced) {
    if (divergenceFlag === "divergent" || agreement > 60) {
      return { text: "Divergent", color: "var(--sense-high)" };
    }
    if (divergenceFlag === "consensus" || agreement < 20) {
      return { text: "Aligned", color: "var(--sense-low)" };
    }
    return { text: "Balanced", color: "var(--bias-center)" };
  }

  // Tilted — lean direction is primary info
  const dir = lean <= 29 ? "Far Left"
    : lean <= 46 ? "Left"
    : lean <= 72 ? "Right"
    : "Far Right";

  if (divergenceFlag === "divergent") {
    return { text: `${dir} · Split`, color: getLeanColor(lean) };
  }
  if (divergenceFlag === "consensus") {
    return { text: `${dir} · Agreed`, color: getLeanColor(lean) };
  }
  return { text: dir, color: getLeanColor(lean) };
}

/* ── CSS variable cache — single observer ───────────────────────────────── */

const SSR_FALLBACK: Record<string, string> = {
  "--bias-far-left": "#1A4D8E",
  "--bias-left": "#2C6B9A",
  "--bias-center-left": "#3978A0",
  "--bias-center": "#2D6B45",
  "--bias-center-right": "#A8554D",
  "--bias-right": "#B5403A",
  "--bias-far-right": "#8C2B26",
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
  // Green reserved for center only. Left of center = blue family, right = red family.
  // Narrow green band at 46-54. Sharp transition to blue/red outside that.
  if (v <= 10) return c["--bias-far-left"];
  if (v <= 20) return lerpColor(c["--bias-far-left"], c["--bias-left"], (v - 10) / 10);
  if (v <= 35) return lerpColor(c["--bias-left"], c["--bias-center-left"], (v - 20) / 15);
  if (v <= 45) return lerpColor(c["--bias-center-left"], c["--bias-center"], (v - 35) / 10);
  if (v <= 55) return c["--bias-center"];
  if (v <= 65) return lerpColor(c["--bias-center"], c["--bias-center-right"], (v - 55) / 10);
  if (v <= 80) return lerpColor(c["--bias-center-right"], c["--bias-right"], (v - 65) / 15);
  if (v <= 90) return lerpColor(c["--bias-right"], c["--bias-far-right"], (v - 80) / 10);
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
