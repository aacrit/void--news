"use client";

import { useState, useMemo, useRef, useEffect, useCallback } from "react";
import {
  getLeanColor,
  leanLabel,
  leanLabelAbbr,
  leanToBucket,
} from "../lib/biasColors";

/* ---------------------------------------------------------------------------
   DeepDiveSpectrum — Spectrum Visualization System
   Three toggleable views: Ink Ridge, Witness Line, Terrain Map.
   Container reads/writes localStorage "void-spectrum-view".
   --------------------------------------------------------------------------- */

export interface DeepDiveSpectrumSource {
  name: string;
  articleUrl: string;
  sourceUrl: string;
  tier: string;
  politicalLean: number;
  /** Factual rigor score 0-100 (from bias_scores) */
  factualRigor?: number;
  /** Raw confidence 0-1 from pipeline */
  confidence?: number;
}

type SpectrumView = "ridge" | "witness" | "terrain";

/* ── Helpers ────────────────────────────────────────────────────────────── */

function getFaviconUrl(sourceUrl: string): string {
  if (!sourceUrl) return "";
  try {
    const domain = new URL(
      sourceUrl.startsWith("http") ? sourceUrl : `https://${sourceUrl}`
    ).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return "";
  }
}

function tierLabel(tier: string): string {
  if (tier === "us_major") return "US Major";
  if (tier === "international") return "International";
  return "Independent";
}

function computeTrustScore(source: DeepDiveSpectrumSource): number {
  const tierScore = source.tier === "us_major" ? 60 : source.tier === "international" ? 50 : 40;
  const rigor = source.factualRigor ?? 50;
  const conf = (source.confidence ?? 0.5) * 100;
  return Math.round(tierScore * 0.4 + rigor * 0.4 + conf * 0.2);
}

/** Weighted mean lean (us_major = weight 3, international = 2, independent = 1) */
function weightedMeanLean(sources: DeepDiveSpectrumSource[]): number {
  let wSum = 0, wTotal = 0;
  for (const s of sources) {
    const w = s.tier === "us_major" ? 3 : s.tier === "international" ? 2 : 1;
    wSum += s.politicalLean * w;
    wTotal += w;
  }
  return wTotal > 0 ? wSum / wTotal : 50;
}

/* ── KDE ────────────────────────────────────────────────────────────────── */

function computeKDE(values: number[], bandwidth: number, points = 100): number[] {
  return Array.from({ length: points }, (_, i) => {
    const x = (i / (points - 1)) * 100;
    return values.reduce((sum, v) => {
      const z = (x - v) / bandwidth;
      return sum + Math.exp(-0.5 * z * z) / (bandwidth * Math.sqrt(2 * Math.PI));
    }, 0);
  });
}

function silvermanBandwidth(values: number[]): number {
  const n = values.length;
  if (n < 2) return 15;
  const mean = values.reduce((s, v) => s + v, 0) / n;
  const std = Math.sqrt(values.reduce((s, v) => s + (v - mean) ** 2, 0) / n);
  return Math.max(8, 1.06 * (std || 10) * Math.pow(n, -0.2));
}

/** Normalize KDE so peak = 1.0 */
function normalizeKDE(kde: number[]): number[] {
  const peak = Math.max(...kde, 1e-10);
  return kde.map((v) => v / peak);
}

/** Catmull-Rom to cubic bezier SVG path */
function kdeToCubicPath(
  densities: number[],
  svgHeight: number,
  svgWidth: number,
  bottomPad = 10
): { fillPath: string; strokePath: string } {
  const pts = densities.map((d, i) => ({
    x: (i / (densities.length - 1)) * svgWidth,
    y: svgHeight - d * (svgHeight - bottomPad),
  }));

  // Catmull-Rom -> Cubic Bezier
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

/** Get y position on KDE curve at a given lean (0-100) */
function getYOnCurve(
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

/* ── Lean gradient stops for SVG (CSS vars for theme reactivity) ────── */

const LEAN_GRADIENT_STOPS: Array<{ offset: string; color: string }> = [
  { offset: "0%", color: "var(--bias-far-left)" },
  { offset: "16%", color: "var(--bias-left)" },
  { offset: "32%", color: "var(--bias-center-left)" },
  { offset: "50%", color: "var(--bias-center)" },
  { offset: "68%", color: "var(--bias-center-right)" },
  { offset: "84%", color: "var(--bias-right)" },
  { offset: "100%", color: "var(--bias-far-right)" },
];

/* ── Tooltip shared ──────────────────────────────────────────────────── */

interface TooltipData {
  source: DeepDiveSpectrumSource;
  x: number;
  y: number;
}

function SpectrumTooltip({ data }: { data: TooltipData }) {
  return (
    <div
      className="dd-sv__tooltip"
      style={{ left: `${data.x}px`, top: `${data.y}px` }}
      role="tooltip"
    >
      <p className="dd-sv__tooltip-name">{data.source.name}</p>
      <p className="dd-sv__tooltip-lean">
        <span
          className="dd-sv__tooltip-dot"
          style={{ backgroundColor: getLeanColor(data.source.politicalLean) }}
          aria-hidden="true"
        />
        {leanLabel(data.source.politicalLean)}
        <span className="dd-sv__tooltip-score">{data.source.politicalLean}</span>
      </p>
      <p className="dd-sv__tooltip-tier">{tierLabel(data.source.tier)}</p>
      {(data.source.factualRigor != null || data.source.confidence != null) && (
        <p className="dd-sv__tooltip-trust">
          Trust {computeTrustScore(data.source)}
          {data.source.factualRigor != null && <> &middot; Rigor: {data.source.factualRigor}</>}
          {data.source.confidence != null && <> &middot; Conf: {Math.round(data.source.confidence * 100)}%</>}
        </p>
      )}
      <p className="dd-sv__tooltip-hint">
        <a
          href={data.source.articleUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="dd-sv__tooltip-link"
          onClick={(e) => e.stopPropagation()}
        >
          &#x2197; Open article
        </a>
      </p>
    </div>
  );
}

/* ── Axis ────────────────────────────────────────────────────────────── */

function SpectrumAxis({ mode }: { mode: "full" | "abbr" }) {
  const labels = mode === "full"
    ? [
        { pos: "0%", text: "L" },
        { pos: "50%", text: "C" },
        { pos: "100%", text: "R" },
      ]
    : [
        { pos: "0%", text: "FL" },
        { pos: "50%", text: "C" },
        { pos: "100%", text: "FR" },
      ];
  const ticks = [0, 14, 28, 50, 72, 86, 100];
  return (
    <div className="dd-sv__axis" aria-hidden="true">
      {ticks.map((p) => (
        <span key={p} className="dd-sv__axis-tick" style={{ left: `${p}%` }} />
      ))}
      {labels.map((l) => (
        <span key={l.pos} className="dd-sv__axis-label" style={{ left: l.pos }}>
          {l.text}
        </span>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   View A: Ink Ridge — KDE distribution curve with organic ink
   ═══════════════════════════════════════════════════════════════════════ */

function InkRidge({
  sources,
  tooltip,
  setTooltip,
}: {
  sources: DeepDiveSpectrumSource[];
  tooltip: TooltipData | null;
  setTooltip: (t: TooltipData | null) => void;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const strokeRef = useRef<SVGPathElement>(null);
  const [animated, setAnimated] = useState(false);
  const n = sources.length;
  const mean = weightedMeanLean(sources);
  const leans = sources.map((s) => s.politicalLean);

  // Determine rendering mode
  const isFlat = n <= 3;
  const isBroad = n >= 4 && n <= 7;
  const svgH = isFlat ? 60 : isBroad ? 60 : 80;
  const W = 400;

  // KDE computation
  const densities = useMemo(() => {
    if (isFlat) return null;
    const bw = isBroad ? 20 : silvermanBandwidth(leans);
    const raw = computeKDE(leans, bw, 100);
    return normalizeKDE(raw);
  }, [leans, isFlat, isBroad]);

  // Path
  const paths = useMemo(() => {
    if (!densities) return null;
    const peakH = isBroad ? 30 : 60;
    const scaled = densities.map((d) => d * (peakH / (svgH - 10)));
    return kdeToCubicPath(scaled, svgH, W, 10);
  }, [densities, svgH, isBroad]);

  // Stroke animation
  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 50);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (animated && strokeRef.current) {
      const len = strokeRef.current.getTotalLength();
      strokeRef.current.style.setProperty("--ridge-stroke-length", `${len}`);
      strokeRef.current.style.strokeDasharray = `${len}`;
      strokeRef.current.style.strokeDashoffset = `${len}`;
      // Force reflow then animate
      void strokeRef.current.getBoundingClientRect();
      strokeRef.current.style.strokeDashoffset = "0";
    }
  }, [animated, paths]);

  const gradStops = LEAN_GRADIENT_STOPS;

  // Dot positions — sort by distance from mean for stagger
  const sortedSources = useMemo(() => {
    return [...sources]
      .map((s, origIdx) => ({ s, origIdx }))
      .sort((a, b) => Math.abs(a.s.politicalLean - mean) - Math.abs(b.s.politicalLean - mean));
  }, [sources, mean]);

  // Overlap detection
  const dotPositions = useMemo(() => {
    const positions: Array<{ x: number; y: number; source: DeepDiveSpectrumSource; staggerIdx: number }> = [];
    const sorted = [...sortedSources];

    for (let si = 0; si < sorted.length; si++) {
      const { s } = sorted[si];
      const x = (s.politicalLean / 100) * W;
      let y: number;
      if (isFlat) {
        y = 45; // on baseline
      } else if (isBroad) {
        y = svgH - 10; // on baseline for broad
      } else if (densities) {
        y = getYOnCurve(s.politicalLean, densities.map((d) => d * (60 / (svgH - 10))), svgH, 10);
      } else {
        y = svgH - 10;
      }

      // Check overlap
      let offset = 0;
      for (const p of positions) {
        if (Math.abs(p.x - x) < 8 && Math.abs(p.y - y - offset) < 8) {
          offset -= 10;
        }
      }

      positions.push({ x, y: y + offset, source: s, staggerIdx: si });
    }
    return positions;
  }, [sortedSources, densities, svgH, isFlat, isBroad]);

  const handleDotEnter = useCallback(
    (e: React.PointerEvent, source: DeepDiveSpectrumSource) => {
      const rect = (e.currentTarget as Element).closest("svg")?.getBoundingClientRect();
      if (!rect) return;
      const cx = parseFloat((e.currentTarget as SVGElement).getAttribute("cx") || "0");
      setTooltip({
        source,
        x: rect.left + (cx / W) * rect.width,
        y: rect.top,
      });
    },
    [setTooltip]
  );

  return (
    <div className={`dd-sv-ridge${animated ? " dd-sv-ridge--animated" : ""}`}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${svgH}`}
        width="100%"
        height={svgH}
        preserveAspectRatio="none"
        className="dd-sv-ridge__svg"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="ridge-lean-grad" x1="0" y1="0" x2="1" y2="0">
            {gradStops.map((s) => (
              <stop key={s.offset} offset={s.offset} stopColor={s.color} stopOpacity="0.15" />
            ))}
          </linearGradient>
          {/* Organic ink filter — fill only */}
          {n >= 8 && (
            <filter id="ridge-ink-wobble" x="-5%" y="-5%" width="110%" height="110%">
              <feTurbulence
                type="turbulence"
                baseFrequency="0.015 0.03"
                numOctaves="1"
                seed="42"
                result="turb"
              />
              <feDisplacementMap in="SourceGraphic" in2="turb" scale="2" />
            </filter>
          )}
        </defs>

        {/* Flat baseline for 2-3 sources */}
        {isFlat && (
          <line
            x1="10"
            y1="45"
            x2="390"
            y2="45"
            stroke="var(--fg-tertiary)"
            strokeWidth="1.5"
            opacity="0.4"
          />
        )}

        {/* Fill path */}
        {paths && (
          <path
            d={paths.fillPath}
            fill="url(#ridge-lean-grad)"
            filter={n >= 8 ? "url(#ridge-ink-wobble)" : undefined}
            className="dd-sv-ridge__fill"
          />
        )}

        {/* Stroke path */}
        {paths && (
          <path
            ref={strokeRef}
            d={paths.strokePath}
            fill="none"
            stroke="var(--fg-tertiary)"
            strokeWidth="1.5"
            className="dd-sv-ridge__stroke"
          />
        )}

        {/* Weighted mean line */}
        <line
          x1={(mean / 100) * W}
          y1={isFlat ? 20 : 8}
          x2={(mean / 100) * W}
          y2={svgH - 5}
          stroke="var(--fg-tertiary)"
          strokeWidth="0.5"
          strokeDasharray="3 2"
          opacity="0.5"
          className="dd-sv-ridge__mean"
        />

        {/* Source dots */}
        {dotPositions.map((dp) => {
          const r = isFlat ? 8 : 5;
          const sw = dp.source.tier === "us_major" ? 2 : 1.5;
          const dashArr = dp.source.tier === "independent" ? "2 1.5" : undefined;
          const strokeC = dp.source.tier === "us_major" ? "var(--fg-primary)" : "var(--fg-tertiary)";
          return (
            <g
              key={`${dp.source.name}-${dp.source.politicalLean}`}
              style={{ cursor: "pointer" }}
              role="link"
              tabIndex={0}
              onClick={() => window.open(dp.source.articleUrl, "_blank", "noopener noreferrer")}
              onKeyDown={(e) => { if (e.key === "Enter") window.open(dp.source.articleUrl, "_blank", "noopener noreferrer"); }}
              onPointerEnter={(e) => handleDotEnter(e, dp.source)}
              onPointerLeave={() => setTooltip(null)}
            >
              <circle
                cx={dp.x}
                cy={dp.y}
                r={r}
                fill={getLeanColor(dp.source.politicalLean)}
                stroke={strokeC}
                strokeWidth={sw}
                strokeDasharray={dashArr}
                className="dd-sv-ridge__dot"
                style={{
                  animationDelay: `${dp.staggerIdx * 40 + 300}ms`,
                }}
              />
              {/* Show name below dot for flat mode */}
              {isFlat && (
                <text
                  x={dp.x}
                  y={dp.y + r + 10}
                  textAnchor="middle"
                  fill="var(--fg-tertiary)"
                  fontSize="7"
                  fontFamily="var(--font-data)"
                  className="dd-sv-ridge__dot-label"
                >
                  {dp.source.name.length > 12 ? dp.source.name.slice(0, 11) + "\u2026" : dp.source.name}
                </text>
              )}
            </g>
          );
        })}

        {/* Mean label */}
        <text
          x={(mean / 100) * W}
          y={svgH - 1}
          textAnchor="middle"
          fill="var(--fg-muted)"
          fontSize="7"
          fontFamily="var(--font-data)"
        >
          {leanLabelAbbr(mean)} {Math.round(mean)}
        </text>
      </svg>
      <SpectrumAxis mode="full" />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   View B: Witness Line — pure marks, one per source
   ═══════════════════════════════════════════════════════════════════════ */

function WitnessLine({
  sources,
  tooltip,
  setTooltip,
}: {
  sources: DeepDiveSpectrumSource[];
  tooltip: TooltipData | null;
  setTooltip: (t: TooltipData | null) => void;
}) {
  const [animated, setAnimated] = useState(false);
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);
  const [expandedBuckets, setExpandedBuckets] = useState<Set<number>>(new Set());
  const W = 400;
  const svgH = 64;
  const trackY = 56;
  const mean = weightedMeanLean(sources);

  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 50);
    return () => clearTimeout(timer);
  }, []);

  // Build stem layout with jitter for overlaps
  const stems = useMemo(() => {
    const result: Array<{
      x: number;
      stemH: number;
      source: DeepDiveSpectrumSource;
      jitterX: number;
      shortened: boolean;
      stackCount: number;
      hidden: boolean;
    }> = [];

    // Sort by lean to detect overlap
    const sorted = [...sources].sort((a, b) => a.politicalLean - b.politicalLean);
    const stacks = new Map<number, number>(); // bucket -> count

    for (const s of sorted) {
      const x = (s.politicalLean / 100) * W;
      const rigor = s.factualRigor ?? 50;
      let stemH = 12 + (rigor / 100) * 28;

      // Find nearby stems
      const bucket = Math.round(x / 4);
      const count = stacks.get(bucket) ?? 0;

      let jitterX = 0;
      let shortened = false;
      let hidden = false;

      if (count > 0 && count < 3) {
        jitterX = count * -5;
        stemH -= 6;
        shortened = true;
      } else if (count >= 3) {
        hidden = true;
      }

      stacks.set(bucket, count + 1);

      result.push({
        x,
        stemH,
        source: s,
        jitterX,
        shortened,
        stackCount: count,
        hidden,
      });
    }

    return result;
  }, [sources]);

  // Count hidden per bucket for +N badges
  const overflowBuckets = useMemo(() => {
    const counts = new Map<number, number>();
    for (const st of stems) {
      if (st.hidden) {
        const bucket = Math.round(st.x / 4);
        counts.set(bucket, (counts.get(bucket) ?? 0) + 1);
      }
    }
    return counts;
  }, [stems]);

  const handleStemEnter = useCallback(
    (e: React.PointerEvent, source: DeepDiveSpectrumSource, idx: number) => {
      const rect = (e.currentTarget as Element).closest("svg")?.getBoundingClientRect();
      if (!rect) return;
      const x = (source.politicalLean / 100) * W;
      setHoveredIdx(idx);
      setTooltip({
        source,
        x: rect.left + (x / W) * rect.width,
        y: rect.top - 8,
      });
    },
    [setTooltip]
  );

  const handleStemLeave = useCallback(() => {
    setHoveredIdx(null);
    setTooltip(null);
  }, [setTooltip]);

  return (
    <div className={`dd-sv-witness${animated ? " dd-sv-witness--animated" : ""}`}>
      <svg
        viewBox={`0 0 ${W} ${svgH}`}
        width="100%"
        height={svgH}
        preserveAspectRatio="none"
        className="dd-sv-witness__svg"
        aria-hidden="true"
      >
        <defs>
          <filter id="witness-ink" x="-5%" y="-5%" width="110%" height="110%">
            <feTurbulence type="turbulence" baseFrequency="0.015 0.03" numOctaves="1" seed="42" result="turb" />
            <feDisplacementMap in="SourceGraphic" in2="turb" scale="2" />
          </filter>
        </defs>

        {/* Track line */}
        <line
          x1="5"
          y1={trackY}
          x2={W - 5}
          y2={trackY}
          stroke="var(--fg-tertiary)"
          strokeWidth="1.5"
          opacity="0.4"
          filter="url(#witness-ink)"
          className="dd-sv-witness__track"
        />

        {/* Stems */}
        {stems.map((st, i) => {
          const bucket = Math.round(st.x / 4);
          const isBucketExpanded = expandedBuckets.has(bucket);
          if (st.hidden && !isBucketExpanded) return null;
          const fanJitterX = st.hidden && isBucketExpanded ? st.stackCount * -5 : st.jitterX;
          const sx = st.x + fanJitterX;
          const favY = trackY - (st.hidden ? st.stemH - 6 : st.stemH);
          const isHovered = hoveredIdx === i;
          const isDimmed = hoveredIdx !== null && hoveredIdx !== i;
          const dashArr = st.source.tier === "independent" ? "2.5 2" : undefined;
          const sw = st.source.tier === "us_major" ? 2 : 1.5;

          return (
            <g
              key={`witness-${st.source.name}-${i}`}
              className="dd-sv-witness__stem-group"
              style={{
                "--stem-delay": `${((i * 0.7) % 3).toFixed(1)}s`,
                opacity: isDimmed ? 0.35 : 1,
                filter: isHovered ? "saturate(1.5)" : undefined,
                transition: "opacity 120ms ease-out, filter 120ms ease-out",
                cursor: "pointer",
              } as React.CSSProperties}
              role="link"
              tabIndex={0}
              onClick={() => window.open(st.source.articleUrl, "_blank", "noopener noreferrer")}
              onKeyDown={(e) => { if (e.key === "Enter") window.open(st.source.articleUrl, "_blank", "noopener noreferrer"); }}
              onPointerEnter={(e) => handleStemEnter(e, st.source, i)}
              onPointerLeave={handleStemLeave}
            >
              {/* Stem */}
              <line
                x1={sx}
                y1={trackY}
                x2={sx}
                y2={favY}
                stroke={getLeanColor(st.source.politicalLean)}
                strokeWidth={sw}
                strokeDasharray={dashArr}
                className="dd-sv-witness__stem"
                style={{ animationDelay: `${80 + i * 25}ms` }}
              />

              {/* US Major crossbar */}
              {st.source.tier === "us_major" && (
                <line
                  x1={sx - 3}
                  y1={trackY}
                  x2={sx + 3}
                  y2={trackY}
                  stroke={getLeanColor(st.source.politicalLean)}
                  strokeWidth={2}
                />
              )}

              {/* Favicon circle */}
              <clipPath id={`fav-clip-${i}`}>
                <circle cx={sx} cy={favY} r={5} />
              </clipPath>
              <circle
                cx={sx}
                cy={favY}
                r={5}
                fill="var(--bg-card)"
                stroke={getLeanColor(st.source.politicalLean)}
                strokeWidth="1"
                className="dd-sv-witness__fav"
              />
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <image
                href={getFaviconUrl(st.source.sourceUrl)}
                x={sx - 4}
                y={favY - 4}
                width={8}
                height={8}
                clipPath={`url(#fav-clip-${i})`}
                className="dd-sv-witness__fav-img"
              />
              {/* Fallback letter */}
              <text
                x={sx}
                y={favY + 2.5}
                textAnchor="middle"
                fill="var(--fg-tertiary)"
                fontSize="6"
                fontFamily="var(--font-data)"
                fontWeight="700"
                className="dd-sv-witness__fav-fallback"
                style={{ display: "none" }}
              >
                {st.source.name.charAt(0)}
              </text>
            </g>
          );
        })}

        {/* Tilt plumb-bob */}
        <g className="dd-sv-witness__tilt">
          <polygon
            points={`${(mean / 100) * W},62 ${(mean / 100) * W - 4},${trackY} ${(mean / 100) * W + 4},${trackY}`}
            fill="var(--cin-amber)"
            opacity="0.8"
          />
          <text
            x={(mean / 100) * W}
            y={svgH + 1}
            textAnchor="middle"
            fill="var(--cin-amber)"
            fontSize="7"
            fontFamily="var(--font-data)"
          >
            {leanLabelAbbr(mean)} {Math.round(mean)}
          </text>
        </g>

        {/* Overflow badges */}
        {Array.from(overflowBuckets).map(([bucket, count]) => {
          const bx = bucket * 4;
          const isExpanded = expandedBuckets.has(bucket);
          return (
            <text
              key={`overflow-${bucket}`}
              x={bx}
              y={svgH + 1}
              textAnchor="middle"
              fill="var(--fg-muted)"
              fontSize="6"
              fontFamily="var(--font-data)"
              style={{ cursor: "pointer" }}
              role="button"
              tabIndex={0}
              onClick={() => {
                setExpandedBuckets((prev) => {
                  const next = new Set(prev);
                  if (next.has(bucket)) next.delete(bucket);
                  else next.add(bucket);
                  return next;
                });
              }}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  setExpandedBuckets((prev) => {
                    const next = new Set(prev);
                    if (next.has(bucket)) next.delete(bucket);
                    else next.add(bucket);
                    return next;
                  });
                }
              }}
            >
              {isExpanded ? "\u2212" : `+${count}`}
            </text>
          );
        })}
      </svg>
      <SpectrumAxis mode="abbr" />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   View C: Terrain Map — topographic landscape
   ═══════════════════════════════════════════════════════════════════════ */

function TerrainMap({
  sources,
  tooltip,
  setTooltip,
}: {
  sources: DeepDiveSpectrumSource[];
  tooltip: TooltipData | null;
  setTooltip: (t: TooltipData | null) => void;
}) {
  const svgRef = useRef<SVGSVGElement>(null);
  const terrainRef = useRef<SVGPathElement>(null);
  const [animated, setAnimated] = useState(false);
  const [crosshair, setCrosshair] = useState<{ x: number; leanZone: string; count: number } | null>(null);
  const rafRef = useRef<number>(0);
  const riseRafRef = useRef<number>(0);
  const n = sources.length;
  const mean = weightedMeanLean(sources);
  const leans = sources.map((s) => s.politicalLean);
  const W = 400;

  const isFlat = n <= 3;
  const isLow = n >= 4 && n <= 7;
  const isMed = n >= 8 && n <= 15;
  const svgH = isFlat ? 55 : isLow ? 60 : isMed ? 70 : 72;
  const peakH = isFlat ? 0 : isLow ? 25 : isMed ? 50 : 60;

  const densities = useMemo(() => {
    if (isFlat) return null;
    const bw = isLow ? 20 : silvermanBandwidth(leans);
    const raw = computeKDE(leans, bw, 100);
    return normalizeKDE(raw);
  }, [leans, isFlat, isLow]);

  const paths = useMemo(() => {
    if (!densities) return null;
    const scaled = densities.map((d) => d * (peakH / (svgH - 10)));
    return kdeToCubicPath(scaled, svgH, W, 10);
  }, [densities, svgH, peakH]);

  // Contour lines
  const contours = useMemo(() => {
    if (!densities || isFlat || isLow) return [];
    const thresholds = n >= 16 ? [0.33, 0.66] : [0.5];
    return thresholds.map((thresh) => {
      // Find contiguous regions above threshold
      const segments: Array<{ x1: number; x2: number; y: number }> = [];
      let inRegion = false;
      let startX = 0;
      for (let i = 0; i < densities.length; i++) {
        if (densities[i] >= thresh && !inRegion) {
          inRegion = true;
          startX = (i / (densities.length - 1)) * W;
        } else if ((densities[i] < thresh || i === densities.length - 1) && inRegion) {
          inRegion = false;
          const endX = (i / (densities.length - 1)) * W;
          const y = svgH - thresh * (peakH) - 10;
          segments.push({ x1: startX, x2: endX, y });
        }
      }
      return { thresh, segments };
    });
  }, [densities, n, svgH, peakH, isFlat, isLow]);

  // Peak position
  const peakInfo = useMemo(() => {
    if (!densities || isFlat) return null;
    let maxIdx = 0;
    for (let i = 1; i < densities.length; i++) {
      if (densities[i] > densities[maxIdx]) maxIdx = i;
    }
    const peakLean = (maxIdx / (densities.length - 1)) * 100;
    const x = (maxIdx / (densities.length - 1)) * W;
    const y = getYOnCurve(peakLean, densities.map((d) => d * (peakH / (svgH - 10))), svgH, 10);
    return { x, y, lean: peakLean };
  }, [densities, svgH, peakH, isFlat]);

  const gradStops = LEAN_GRADIENT_STOPS;

  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 50);
    return () => clearTimeout(timer);
  }, []);

  // Terrain rise animation via JS
  useEffect(() => {
    if (!animated || !terrainRef.current || !densities || !paths) return;
    const el = terrainRef.current;
    const flatD = densities.map(() => 0);
    const finalD = densities.map((d) => d * (peakH / (svgH - 10)));
    let start: number | null = null;
    const duration = 500;

    function step(ts: number) {
      if (!start) start = ts;
      const elapsed = ts - start;
      const progress = Math.min(elapsed / duration, 1);
      // Spring-like easing: overshoot then settle
      const t = 1 - Math.pow(1 - progress, 3); // ease-out cubic
      const interp = flatD.map((f, i) => f + (finalD[i] - f) * t);
      const { fillPath } = kdeToCubicPath(interp, svgH, W, 10);
      el.setAttribute("d", fillPath);
      if (progress < 1) {
        riseRafRef.current = requestAnimationFrame(step);
      }
    }
    riseRafRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(riseRafRef.current);
  }, [animated, densities, paths, svgH, peakH]);

  // Crosshair on pointer move
  const handlePointerMove = useCallback(
    (e: React.PointerEvent<SVGSVGElement>) => {
      cancelAnimationFrame(rafRef.current);
      const rect = e.currentTarget.getBoundingClientRect();
      const localX = ((e.clientX - rect.left) / rect.width) * W;
      const lean = (localX / W) * 100;
      const zone = leanLabel(lean);
      const bucket = leanToBucket(lean);
      const count = sources.filter((s) => leanToBucket(s.politicalLean) === bucket).length;
      setCrosshair({ x: localX, leanZone: zone, count });
    },
    [sources]
  );

  const handlePebbleEnter = useCallback(
    (e: React.PointerEvent, source: DeepDiveSpectrumSource) => {
      const rect = (e.currentTarget as Element).closest("svg")?.getBoundingClientRect();
      if (!rect) return;
      const x = (source.politicalLean / 100) * W;
      setTooltip({
        source,
        x: rect.left + (x / W) * rect.width,
        y: rect.top,
      });
    },
    [setTooltip]
  );

  return (
    <div className={`dd-sv-terrain${animated ? " dd-sv-terrain--animated" : ""}`}>
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${svgH}`}
        width="100%"
        height={svgH}
        preserveAspectRatio="none"
        className="dd-sv-terrain__svg"
        aria-hidden="true"
        onPointerMove={handlePointerMove}
        onPointerLeave={() => setCrosshair(null)}
      >
        <defs>
          <linearGradient id="terrain-lean-grad" x1="0" y1="0" x2="1" y2="0">
            {gradStops.map((s) => (
              <stop key={s.offset} offset={s.offset} stopColor={s.color} stopOpacity="0.08" />
            ))}
          </linearGradient>
        </defs>

        {/* Flat baseline for 2-3 sources */}
        {isFlat && (
          <line
            x1="5"
            y1={svgH - 15}
            x2={W - 5}
            y2={svgH - 15}
            stroke="var(--fg-tertiary)"
            strokeWidth="1.5"
            opacity="0.4"
          />
        )}

        {/* Terrain fill (animated via JS) */}
        {paths && (
          <path
            ref={terrainRef}
            d={paths.fillPath}
            fill="url(#terrain-lean-grad)"
            className="dd-sv-terrain__fill"
          />
        )}

        {/* Terrain stroke */}
        {paths && (
          <path
            d={paths.strokePath}
            fill="none"
            stroke="var(--fg-tertiary)"
            strokeWidth="1.5"
            opacity="0.6"
            className="dd-sv-terrain__stroke"
          />
        )}

        {/* Contour lines */}
        {contours.map((contour, ci) =>
          contour.segments.map((seg, si) => (
            <line
              key={`contour-${ci}-${si}`}
              x1={seg.x1}
              y1={seg.y}
              x2={seg.x2}
              y2={seg.y}
              stroke="var(--fg-tertiary)"
              strokeWidth="0.5"
              opacity="0.3"
              strokeDasharray="4 3"
              className="dd-sv-terrain__contour"
              style={{ animationDelay: `${400 + ci * 200}ms` }}
            />
          ))
        )}

        {/* Peak callout */}
        {peakInfo && !isFlat && (
          <g className="dd-sv-terrain__peak">
            <line
              x1={peakInfo.x}
              y1={peakInfo.y - 8}
              x2={peakInfo.x}
              y2={peakInfo.y}
              stroke="var(--fg-tertiary)"
              strokeWidth="0.5"
              opacity="0.6"
            />
            <text
              x={peakInfo.x}
              y={peakInfo.y - 10}
              textAnchor={peakInfo.x > W * 0.75 ? "end" : peakInfo.x < W * 0.25 ? "start" : "middle"}
              fill="var(--fg-muted)"
              fontSize="6.5"
              fontFamily="var(--font-data)"
            >
              Peak {leanLabelAbbr(peakInfo.lean)}
            </text>
          </g>
        )}

        {/* Tilt marker */}
        <line
          x1={(mean / 100) * W}
          y1={isFlat ? svgH - 15 : 8}
          x2={(mean / 100) * W}
          y2={svgH - 8}
          stroke="var(--cin-amber)"
          strokeWidth="0.75"
          strokeDasharray="3 2"
          opacity="0.6"
        />
        <text
          x={(mean / 100) * W}
          y={svgH - 2}
          textAnchor="middle"
          fill="var(--cin-amber)"
          fontSize="6.5"
          fontFamily="var(--font-data)"
        >
          Tilt {Math.round(mean)}
        </text>

        {/* Pebbles */}
        {sources.map((s, i) => {
          const px = (s.politicalLean / 100) * W;
          const py = isFlat ? svgH - 8 : svgH - 4;
          const op = s.tier === "us_major" ? 1.0 : s.tier === "international" ? 0.8 : 0.55;
          return (
            <g
              key={`pebble-${s.name}-${i}`}
              style={{ cursor: "pointer" }}
              role="link"
              tabIndex={0}
              onClick={() => window.open(s.articleUrl, "_blank", "noopener noreferrer")}
              onKeyDown={(e) => { if (e.key === "Enter") window.open(s.articleUrl, "_blank", "noopener noreferrer"); }}
              onPointerEnter={(e) => handlePebbleEnter(e, s)}
              onPointerLeave={() => setTooltip(null)}
            >
              <rect
                x={px - 3.5}
                y={py - 2.5}
                width={7}
                height={5}
                rx={2}
                fill={getLeanColor(s.politicalLean)}
                opacity={op}
                className="dd-sv-terrain__pebble"
                style={{ animationDelay: `${600 + i * 20}ms` }}
              />
              {/* Name labels for flat mode */}
              {isFlat && (
                <text
                  x={px}
                  y={py - 8}
                  textAnchor="middle"
                  fill="var(--fg-tertiary)"
                  fontSize="6.5"
                  fontFamily="var(--font-data)"
                >
                  {s.name.length > 12 ? s.name.slice(0, 11) + "\u2026" : s.name}
                </text>
              )}
            </g>
          );
        })}

        {/* Crosshair */}
        {crosshair && (
          <g className="dd-sv-terrain__crosshair">
            <line
              x1={crosshair.x}
              y1={0}
              x2={crosshair.x}
              y2={svgH}
              stroke="var(--fg-tertiary)"
              strokeWidth="0.5"
              opacity="0.3"
            />
            <text
              x={crosshair.x}
              y={10}
              textAnchor={crosshair.x > W * 0.7 ? "end" : crosshair.x < W * 0.3 ? "start" : "middle"}
              fill="var(--fg-muted)"
              fontSize="6"
              fontFamily="var(--font-data)"
            >
              {crosshair.leanZone} ({crosshair.count})
            </text>
          </g>
        )}
      </svg>
      <SpectrumAxis mode="abbr" />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   Toggle — 3-button pill
   ═══════════════════════════════════════════════════════════════════════ */

const VIEW_LABELS: Record<SpectrumView, string> = {
  ridge: "Ridge",
  witness: "Witness",
  terrain: "Terrain",
};

const VIEWS: SpectrumView[] = ["ridge", "witness", "terrain"];

function ViewToggle({
  active,
  onChange,
}: {
  active: SpectrumView;
  onChange: (v: SpectrumView) => void;
}) {
  const btnRefs = useRef<(HTMLButtonElement | null)[]>([]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return;
    e.preventDefault();
    const currentIdx = VIEWS.indexOf(active);
    const nextIdx =
      e.key === "ArrowLeft" || e.key === "ArrowUp"
        ? (currentIdx - 1 + VIEWS.length) % VIEWS.length
        : (currentIdx + 1) % VIEWS.length;
    onChange(VIEWS[nextIdx]);
    // Move DOM focus to the newly selected button (required by WAI-ARIA radiogroup)
    btnRefs.current[nextIdx]?.focus();
  };

  return (
    <div
      className="dd-sv-toggle"
      role="radiogroup"
      aria-label="Spectrum visualization style"
      onKeyDown={handleKeyDown}
    >
      {VIEWS.map((v, i) => (
        <button
          key={v}
          ref={(el) => { btnRefs.current[i] = el; }}
          type="button"
          role="radio"
          aria-checked={active === v}
          aria-label={VIEW_LABELS[v]}
          title={VIEW_LABELS[v]}
          tabIndex={active === v ? 0 : -1}
          className={`dd-sv-toggle__btn${active === v ? " dd-sv-toggle__btn--active" : ""}`}
          onClick={() => onChange(v)}
        >
          <svg viewBox="0 0 20 12" width="16" height="10" aria-hidden="true">
            {v === "ridge" && (
              <path d="M2 8 Q6 2 10 8 Q14 2 18 8" stroke="currentColor" fill="none" strokeWidth="1.5" />
            )}
            {v === "witness" && (
              <path d="M4 10V2M10 10V4M16 10V6" stroke="currentColor" fill="none" strokeWidth="1.5" />
            )}
            {v === "terrain" && (
              <path d="M1 10 L7 2 L13 6 L19 10 Z" stroke="currentColor" fill="none" strokeWidth="1.5" />
            )}
          </svg>
        </button>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   Container — DeepDiveSpectrum
   ═══════════════════════════════════════════════════════════════════════ */

interface DeepDiveSpectrumProps {
  sources: DeepDiveSpectrumSource[];
}

function readStoredView(): SpectrumView {
  if (typeof window === "undefined") return "witness";
  try {
    const v = localStorage.getItem("void-spectrum-view") as SpectrumView | null;
    if (v === "ridge" || v === "witness" || v === "terrain") return v;
  } catch { /* noop */ }
  return "witness";
}

export default function DeepDiveSpectrum({ sources }: DeepDiveSpectrumProps) {
  const [view, setView] = useState<SpectrumView>(() => readStoredView());
  const [displayView, setDisplayView] = useState<SpectrumView>(view);
  const [exiting, setExiting] = useState(false);
  const [entering, setEntering] = useState(false);
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);

  const handleViewChange = useCallback((v: SpectrumView) => {
    if (v === view) return;
    try { localStorage.setItem("void-spectrum-view", v); } catch { /* noop */ }
    setExiting(true);
    setTooltip(null);
    // After exit animation, swap view
    setTimeout(() => {
      setView(v);
      setDisplayView(v);
      setExiting(false);
      setEntering(true);
      requestAnimationFrame(() => {
        requestAnimationFrame(() => setEntering(false));
      });
    }, 160);
  }, [view]);

  // Initialize displayView on mount
  useEffect(() => {
    setDisplayView(view);
  }, [view]);

  if (sources.length === 0) {
    return (
      <div className="dd-sv" role="img" aria-label="No sources available for spectrum">
        <div className="dd-sv__empty">No sources</div>
      </div>
    );
  }

  return (
    <div className="dd-sv" role="img" aria-label="Source political lean spectrum visualization">
      <ViewToggle active={view} onChange={handleViewChange} />
      <div className={`dd-sv__view${exiting ? " dd-sv__view--exiting" : ""}${entering ? " dd-sv__view--entering" : ""}`}>
        {displayView === "ridge" && (
          <InkRidge sources={sources} tooltip={tooltip} setTooltip={setTooltip} />
        )}
        {displayView === "witness" && (
          <WitnessLine sources={sources} tooltip={tooltip} setTooltip={setTooltip} />
        )}
        {displayView === "terrain" && (
          <TerrainMap sources={sources} tooltip={tooltip} setTooltip={setTooltip} />
        )}
      </div>
      {tooltip && <SpectrumTooltip data={tooltip} />}
    </div>
  );
}
