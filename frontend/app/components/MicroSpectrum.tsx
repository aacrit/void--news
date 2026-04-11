"use client";

import { useId, useMemo } from "react";
import { gaussianDensities, kdeToCubicPath, getYOnCurve } from "../lib/kde";

/* ---------------------------------------------------------------------------
   MicroSpectrum — Compact KDE bell-curve sparkline of lean distribution.

   Renders a Gaussian curve synthesized from politicalLean (μ) and
   biasSpread.leanSpread (σ). No per-article data needed.

   The SVG fills its container width (width="100%") at a fixed height with
   preserveAspectRatio="none" — the curve stretches horizontally across the
   card, keeping the height fixed. Color maps via the same 7-stop bias
   gradient (Blue=Left → Green=Center → Red=Right) so the shape and color
   tell the same story simultaneously.

   Usage:
     <MicroSpectrum mean={story.sigilData.politicalLean}
                    spread={story.sigilData.biasSpread?.leanSpread ?? 12} />
   --------------------------------------------------------------------------- */

interface MicroSpectrumProps {
  /** Political lean 0–100 (center of Gaussian) */
  mean: number;
  /** leanSpread std dev (width of Gaussian). Floor 4 enforced internally. */
  spread: number;
  /** SVG height in px (viewBox height). Default 28. */
  height?: number;
  /** Show dashed needle + ring dot at mean position. Default true. */
  showMarker?: boolean;
  /** Curve stroke width in viewBox units. Default 1.5. */
  strokeWidth?: number;
  /** Extra class on the root <svg> element. */
  className?: string;
}

/** 7-stop lean gradient — matches spectrum.css and DeepDiveSpectrum */
const LEAN_STOPS: Array<{ offset: string; color: string }> = [
  { offset: "0%",   color: "var(--bias-far-left)" },
  { offset: "16%",  color: "var(--bias-left)" },
  { offset: "32%",  color: "var(--bias-center-left)" },
  { offset: "50%",  color: "var(--bias-center)" },
  { offset: "68%",  color: "var(--bias-center-right)" },
  { offset: "84%",  color: "var(--bias-right)" },
  { offset: "100%", color: "var(--bias-far-right)" },
];

// viewBox width — internal coordinate system only (SVG stretches via CSS)
const VB_W = 200;

export default function MicroSpectrum({
  mean,
  spread,
  height = 28,
  showMarker = true,
  strokeWidth = 1.5,
  className,
}: MicroSpectrumProps) {
  const uid = useId();
  const fillId  = `ms-fill-${uid}`;
  const strokeId = `ms-stroke-${uid}`;

  // bottomPad: pixels of flat baseline below curve bottom
  const bottomPad = Math.max(3, Math.round(height * 0.12));

  const densities = useMemo(
    () => gaussianDensities(mean, spread, 80),
    [mean, spread]
  );

  const { fillPath, strokePath } = useMemo(
    () => kdeToCubicPath(densities, height, VB_W, bottomPad),
    [densities, height, bottomPad]
  );

  const markerX = (mean / 100) * VB_W;
  const markerY = showMarker
    ? getYOnCurve(mean, densities, height, bottomPad)
    : 0;

  return (
    <svg
      viewBox={`0 0 ${VB_W} ${height}`}
      width="100%"
      height={height}
      preserveAspectRatio="none"
      aria-hidden="true"
      className={className}
      style={{ display: "block" }}
    >
      <defs>
        {/* gradientUnits="userSpaceOnUse" → gradient spans full viewBox width
            even when SVG is stretched via preserveAspectRatio="none" */}
        <linearGradient id={fillId} x1="0" y1="0" x2={VB_W} y2="0" gradientUnits="userSpaceOnUse">
          {LEAN_STOPS.map((s) => (
            <stop key={s.offset} offset={s.offset} stopColor={s.color} stopOpacity={0.28} />
          ))}
        </linearGradient>
        <linearGradient id={strokeId} x1="0" y1="0" x2={VB_W} y2="0" gradientUnits="userSpaceOnUse">
          {LEAN_STOPS.map((s) => (
            <stop key={s.offset} offset={s.offset} stopColor={s.color} stopOpacity={0.88} />
          ))}
        </linearGradient>
      </defs>

      {/* Gradient fill under curve */}
      <path d={fillPath} fill={`url(#${fillId})`} />

      {/* Colored curve stroke */}
      <path
        d={strokePath}
        fill="none"
        stroke={`url(#${strokeId})`}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {showMarker && (
        <>
          {/* Dashed needle from peak to baseline */}
          <line
            x1={markerX} y1={markerY}
            x2={markerX} y2={height - 1}
            stroke="var(--fg-secondary)"
            strokeWidth={0.7}
            strokeDasharray="1.4 1.4"
            opacity={0.45}
          />
          {/* Ring dot at curve peak */}
          <circle
            cx={markerX}
            cy={markerY}
            r={2.5}
            fill="var(--bg-card)"
            stroke={`url(#${strokeId})`}
            strokeWidth={1.4}
          />
        </>
      )}
    </svg>
  );
}
