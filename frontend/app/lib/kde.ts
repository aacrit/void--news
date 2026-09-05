/* ---------------------------------------------------------------------------
   KDE — Kernel Density Estimation utilities
   Shared between DeepDiveSpectrum and MicroSpectrum.
   --------------------------------------------------------------------------- */

/** Gaussian KDE: densities at 'points' equally-spaced positions across [0,100] */
export function computeKDE(values: number[], bandwidth: number, points = 100): number[] {
  return Array.from({ length: points }, (_, i) => {
    const x = (i / (points - 1)) * 100;
    return values.reduce((sum, v) => {
      const z = (x - v) / bandwidth;
      return sum + Math.exp(-0.5 * z * z) / (bandwidth * Math.sqrt(2 * Math.PI));
    }, 0);
  });
}

/**
 * Robust bandwidth — normal reference rule with IQR correction.
 * Uses min(std, IQR/1.34) to avoid over-smoothing bimodal distributions.
 * Silverman's rule uses std alone, which smears two peaks into one hump.
 */
export function robustBandwidth(values: number[]): number {
  const n = values.length;
  if (n < 2) return 8;
  const mean = values.reduce((s, v) => s + v, 0) / n;
  const std = Math.sqrt(values.reduce((s, v) => s + (v - mean) ** 2, 0) / n);
  const sorted = [...values].sort((a, b) => a - b);
  const q1 = sorted[Math.floor(n * 0.25)] ?? sorted[0];
  const q3 = sorted[Math.floor(n * 0.75)] ?? sorted[n - 1];
  const iqrNorm = (q3 - q1) / 1.34; // IQR scaled to std units
  const spread = Math.min(std || 10, iqrNorm > 0 ? iqrNorm : std || 10);
  return Math.max(4, 0.9 * spread * Math.pow(n, -0.2));
}

/** Normalize KDE so peak = 1.0 */
export function normalizeKDE(kde: number[]): number[] {
  const peak = Math.max(...kde, 1e-10);
  return kde.map((v) => v / peak);
}

/** Catmull-Rom to cubic bezier SVG path */
export function kdeToCubicPath(
  densities: number[],
  svgHeight: number,
  svgWidth: number,
  bottomPad = 10
): { fillPath: string; strokePath: string } {
  const pts = densities.map((d, i) => ({
    x: (i / (densities.length - 1)) * svgWidth,
    y: svgHeight - d * (svgHeight - bottomPad),
  }));

  // Catmull-Rom → Cubic Bezier
  let d = `M${pts[0].x.toFixed(2)},${pts[0].y.toFixed(2)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[Math.min(pts.length - 1, i + 2)];
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C${cp1x.toFixed(2)},${cp1y.toFixed(2)} ${cp2x.toFixed(2)},${cp2y.toFixed(2)} ${p2.x.toFixed(2)},${p2.y.toFixed(2)}`;
  }
  const strokePath = d;
  const fillPath = d + ` L${svgWidth},${svgHeight} L0,${svgHeight} Z`;
  return { fillPath, strokePath };
}

/**
 * Synthesize Gaussian densities from aggregate statistics (mean + std dev).
 * Used when per-article lean values are unavailable — story cards have only
 * biasSpread.leanSpread (σ) and politicalLean (μ). Returns values in [0, 1]
 * (peak = 1.0 at mean), ready for kdeToCubicPath without normalizeKDE.
 *
 * σ floor at 4: prevents a needle-thin spike that renders as a vertical line.
 */
export function gaussianDensities(
  mean: number,
  sigma: number,
  points = 80
): number[] {
  const s = Math.max(sigma, 4);
  return Array.from({ length: points }, (_, i) => {
    const x = (i / (points - 1)) * 100;
    const z = (x - mean) / s;
    return Math.exp(-0.5 * z * z); // peak at mean = exp(0) = 1.0
  });
}

/** Get y position on KDE curve at a given lean value (0–100) */
export function getYOnCurve(
  lean: number,
  densities: number[],
  svgHeight: number,
  bottomPad = 10
): number {
  const idx = (lean / 100) * (densities.length - 1);
  const lo = Math.floor(idx);
  const hi = Math.min(lo + 1, densities.length - 1);
  const t = idx - lo;
  const d = densities[lo] * (1 - t) + densities[hi] * t;
  return svgHeight - d * (svgHeight - bottomPad);
}
