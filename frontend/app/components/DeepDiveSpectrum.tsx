"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import {
  getLeanColor,
  leanLabel,
  leanLabelAbbr,
  leanToBucket,
} from "../lib/biasColors";
import {
  computeKDE,
  robustBandwidth,
  normalizeKDE,
  kdeToCubicPath,
  getYOnCurve,
} from "../lib/kde";

/* ---------------------------------------------------------------------------
   DeepDiveSpectrum — Spectrum Visualization System
   Three toggleable views: Ink Ridge, Witness Line, Terrain Map.
   Container reads/writes localStorage "void-spectrum-view".

   Architecture: SVG renders distribution shape only; HTML renders sources.
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

// (single organic view — no toggle)

/* ── Helpers ────────────────────────────────────────────────────────────── */

function getFaviconUrl(sourceUrl: string): string {
  if (!sourceUrl) return "";
  try {
    const domain = new URL(
      sourceUrl.startsWith("http") ? sourceUrl : `https://${sourceUrl}`
    ).hostname;
    // Clearbit Logo API — returns actual publication logos, not browser favicons
    return `https://logo.clearbit.com/${domain}`;
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

/* ── Min gap for 2-row source collision detection (% of container width) ── */
const MIN_GAP_PCT = 5.5;

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

/* ── Axis — gradient bar with explicit Left / Center / Right labels ──── */

function SpectrumAxis() {
  return (
    <div className="dd-sv__axis" aria-hidden="true">
      <div className="dd-sv__axis-bar" />
      <div className="dd-sv__axis-labels">
        <span className="dd-sv__axis-label dd-sv__axis-label--left">Left</span>
        <span className="dd-sv__axis-label dd-sv__axis-label--center">Center</span>
        <span className="dd-sv__axis-label dd-sv__axis-label--right">Right</span>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   FaviconAvatar — HTML avatar with img + fallback letter
   ═══════════════════════════════════════════════════════════════════════ */

function FaviconAvatar({
  source,
  size = 20,
  onPointerEnter,
  onPointerLeave,
}: {
  source: DeepDiveSpectrumSource;
  size?: number;
  onPointerEnter?: (e: React.PointerEvent) => void;
  onPointerLeave?: (e: React.PointerEvent) => void;
}) {
  const [failed, setFailed] = useState(false);
  const url = getFaviconUrl(source.sourceUrl);
  // Use data-lean for border/letter color — CSS vars are theme-reactive, no inline getLeanColor()
  const leanBucket = leanToBucket(source.politicalLean);

  return (
    <div
      className="dd-sv-avatar"
      data-lean={leanBucket}
      style={{ width: size, height: size }}
      title={source.name}
      onPointerEnter={onPointerEnter}
      onPointerLeave={onPointerLeave}
    >
      {!failed && url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={url}
          alt={source.name}
          width={size - 6}
          height={size - 6}
          onError={() => setFailed(true)}
          className="dd-sv-avatar__img"
        />
      ) : (
        <span className="dd-sv-avatar__letter">
          {source.name.charAt(0).toUpperCase()}
        </span>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   SourceFaviconRow — continuous lean% positioning, 2-row collision
   Each source placed at its actual lean value. No zone buckets.
   ═══════════════════════════════════════════════════════════════════════ */

function SourceFaviconRow({
  sources,
  setTooltip,
}: {
  sources: DeepDiveSpectrumSource[];
  setTooltip: (t: TooltipData | null) => void;
}) {
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const avatarSize = isMobile ? 16 : 20;
  const rowH = avatarSize + 4; // 4px gap between rows

  // Sort by lean, assign row via 2-row collision detection
  const placed = useMemo(() => {
    const sorted = [...sources].sort((a, b) => a.politicalLean - b.politicalLean);
    const lastRight: [number, number] = [-Infinity, -Infinity];
    return sorted.map((s) => {
      const leftPct = 2 + (s.politicalLean / 100) * 96;
      let row: 0 | 1;
      if (leftPct - lastRight[0] >= MIN_GAP_PCT) {
        row = 0;
      } else if (leftPct - lastRight[1] >= MIN_GAP_PCT) {
        row = 1;
      } else {
        row = 1; // overlap row 1 as last resort
      }
      lastRight[row] = leftPct;
      return { source: s, leftPct, row };
    });
  }, [sources]);

  return (
    <div className="dd-sv-sources" style={{ height: rowH * 2 }}>
      {placed.map(({ source, leftPct, row }, i) => (
        <a
          key={`pin-${i}`}
          href={source.articleUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="dd-sv-sources__pin"
          style={{ left: `${leftPct}%`, top: `${row * rowH}px` }}
          onPointerEnter={(e) => {
            const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
            setTooltip({ source, x: rect.left + rect.width / 2, y: rect.top });
          }}
          onPointerLeave={() => setTooltip(null)}
        >
          <FaviconAvatar source={source} size={avatarSize} />
        </a>
      ))}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   TiltRow — HTML tilt indicator below SVG, above source row
   ═══════════════════════════════════════════════════════════════════════ */

function TiltRow({ mean }: { mean: number }) {
  return (
    <div className="dd-sv__tilt-row" aria-hidden="true">
      <div
        className="dd-sv__tilt-needle"
        style={{ left: `${mean}%` }}
      />
      <span
        className="dd-sv__tilt-label"
        style={{ left: `clamp(20px, ${mean}%, calc(100% - 20px))` }}
      >
        {leanLabelAbbr(mean)} {Math.round(mean)}
      </span>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   Bimodal detection — two significant peaks with deep valley between them
   ═══════════════════════════════════════════════════════════════════════ */

interface BimodalPeak { lean: number; density: number; }
interface BimodalInfo {
  peaks: BimodalPeak[];
  valleyLean: number;
  valleyDensity: number;
}

function detectBimodal(densities: number[]): BimodalInfo | null {
  if (densities.length < 10) return null;

  // Find local maxima ≥ 20% of normalized max
  const peaks: Array<{ idx: number; density: number }> = [];
  for (let i = 2; i < densities.length - 2; i++) {
    if (
      densities[i] > densities[i - 1] &&
      densities[i] > densities[i + 1] &&
      densities[i] >= 0.20
    ) {
      peaks.push({ idx: i, density: densities[i] });
    }
  }
  if (peaks.length < 2) return null;

  // Top 2 peaks by density
  peaks.sort((a, b) => b.density - a.density);
  const [p1, p2] = peaks.slice(0, 2);
  const [left, right] = p1.idx < p2.idx ? [p1, p2] : [p2, p1];

  // Peaks must be ≥ 15 lean-points apart — prevents noise within center from triggering
  const leftLean = (left.idx / (densities.length - 1)) * 100;
  const rightLean = (right.idx / (densities.length - 1)) * 100;
  if (rightLean - leftLean < 15) return null;

  // Valley between peaks
  let valleyIdx = left.idx;
  let valleyDensity = densities[left.idx];
  for (let i = left.idx; i <= right.idx; i++) {
    if (densities[i] < valleyDensity) { valleyDensity = densities[i]; valleyIdx = i; }
  }

  // Bimodal when valley < 55% of lower peak — catches real editorial splits,
  // not just polar extremes (loosened from 30% per CEO advisory)
  if (valleyDensity >= Math.min(left.density, right.density) * 0.55) return null;

  return {
    peaks: [
      { lean: leftLean, density: left.density },
      { lean: rightLean, density: right.density },
    ],
    valleyLean: (valleyIdx / (densities.length - 1)) * 100,
    valleyDensity,
  };
}

/* ── Dead zone detection — spectrum regions with no coverage ─────────── */

function detectDeadZones(
  densities: number[]
): Array<{ startLean: number; endLean: number; midLean: number }> {
  const zones: Array<{ startLean: number; endLean: number; midLean: number }> = [];
  const threshold = 0.03; // < 3% of normalized peak = dead zone
  const minWidth = 14;    // minimum 14 lean-point span to annotate

  let inZone = false;
  let zoneStart = 0;
  for (let i = 0; i < densities.length; i++) {
    const lean = (i / (densities.length - 1)) * 100;
    if (densities[i] < threshold && !inZone) {
      inZone = true; zoneStart = lean;
    } else if (densities[i] >= threshold && inZone) {
      inZone = false;
      if (lean - zoneStart >= minWidth) {
        zones.push({ startLean: zoneStart, endLean: lean, midLean: (zoneStart + lean) / 2 });
      }
    }
  }
  return zones;
}

/* ═══════════════════════════════════════════════════════════════════════
   SpectrumView — merged organic view
   Ink wash rises (rAF) → stroke draws (dashoffset) → contours settle →
   amber plumb line drops → bimodal callout appears.
   Expand toggle: source pins on curve + label strip + scrub line.
   ═══════════════════════════════════════════════════════════════════════ */

function SpectrumView({ sources }: { sources: DeepDiveSpectrumSource[] }) {
  const fillRef = useRef<SVGPathElement>(null);
  const strokeRef = useRef<SVGPathElement>(null);
  const riseRafRef = useRef<number>(0);
  const svgWrapRef = useRef<HTMLDivElement>(null);
  const [animated, setAnimated] = useState(false);

  const n = sources.length;
  const leans = sources.map((s) => s.politicalLean);
  const mean = weightedMeanLean(sources);

  const W = 400;
  const svgH = 60;
  const isFlat = n <= 3;  // dot strip — no KDE
  const isLow = n >= 4 && n <= 7; // tight bandwidth + source dots overlay
  const peakH = isFlat ? 0 : isLow ? 26 : 48;

  // Standard deviation of lean — used for divergence classification
  const std = useMemo(() => {
    if (leans.length < 2) return 0;
    const m = leans.reduce((s, v) => s + v, 0) / leans.length;
    return Math.sqrt(leans.reduce((s, v) => s + (v - m) ** 2, 0) / leans.length);
  }, [leans]);

  const densities = useMemo(() => {
    if (isFlat) return null;
    // isLow: fixed bw=6 (Silverman at n=5 gives ~12 — obliterates two clusters)
    const bw = isLow ? 6 : robustBandwidth(leans);
    const raw = computeKDE(leans, bw, 100);
    return normalizeKDE(raw);
  }, [leans, isFlat, isLow]);

  // Paths
  const paths = useMemo(() => {
    if (!densities) return null;
    const scaled = densities.map((d) => d * (peakH / (svgH - 12)));
    return kdeToCubicPath(scaled, svgH, W, 12);
  }, [densities, svgH, peakH]);

  // Contour lines: 1 at 50%; 2 (33%+66%) for 16+ sources
  const contours = useMemo(() => {
    if (!densities || isFlat || isLow) return [];
    const thresholds = n >= 16 ? [0.33, 0.66] : [0.5];
    return thresholds.map((thresh) => {
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
          const y = svgH - thresh * peakH - 12;
          segments.push({ x1: startX, x2: endX, y });
        }
      }
      return { thresh, segments };
    });
  }, [densities, n, svgH, peakH, isFlat, isLow]);

  // Bimodal & dead-zone detection
  const bimodal = useMemo(() => {
    if (!densities || isFlat || n < 5) return null;
    return detectBimodal(densities);
  }, [densities, isFlat, n]);

  const deadZones = useMemo(() => {
    if (!densities || isFlat || n < 4) return [];
    return detectDeadZones(densities);
  }, [densities, isFlat, n]);

  // 4-state coverage classification
  // consensus (silent) / leaning / divergent / split
  type CoverageClass = "consensus" | "leaning" | "divergent" | "split";
  const coverage = useMemo((): CoverageClass => {
    if (bimodal) return "split";
    if (std >= 18) return "divergent";
    if (mean < 38 || mean > 62) return "leaning";
    return "consensus";
  }, [bimodal, std, mean]);

  const gradStops = LEAN_GRADIENT_STOPS;

  // Source pins — each source mapped to its KDE curve (x,y) position
  const sourcePins = useMemo(() => {
    const scaledD = densities
      ? densities.map((d) => d * (peakH / (svgH - 12)))
      : null;
    return sources.map((s) => ({
      source: s,
      x: (s.politicalLean / 100) * W,
      y: scaledD ? getYOnCurve(s.politicalLean, scaledD, svgH, 12) : svgH - 8,
      leanBucket: leanToBucket(s.politicalLean),
    }));
  }, [densities, sources, peakH, svgH]);

  // Trigger entrance
  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 50);
    return () => clearTimeout(timer);
  }, []);

  // Beat 1 (0ms): fill rises from flat via rAF — 450ms ease-out cubic
  useEffect(() => {
    if (!animated || !fillRef.current || !densities || !paths) return;
    const el = fillRef.current;
    const finalD = densities.map((d) => d * (peakH / (svgH - 12)));

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.setAttribute("d", kdeToCubicPath(finalD, svgH, W, 12).fillPath);
      return;
    }

    const flatD = densities.map(() => 0);
    let start: number | null = null;
    function step(ts: number) {
      if (!start) start = ts;
      const progress = Math.min((ts - start) / 450, 1);
      const t = 1 - Math.pow(1 - progress, 3);
      const interp = flatD.map((f, i) => f + (finalD[i] - f) * t);
      el.setAttribute("d", kdeToCubicPath(interp, svgH, W, 12).fillPath);
      if (progress < 1) riseRafRef.current = requestAnimationFrame(step);
    }
    riseRafRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(riseRafRef.current);
  }, [animated, densities, paths, svgH, peakH]);

  // Beat 2 (150ms): stroke draws via CSS transition on dashoffset
  useEffect(() => {
    if (!animated || !strokeRef.current || !paths) return;
    const el = strokeRef.current;

    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const len = el.getTotalLength();
      el.style.strokeDasharray = `${len}`;
      el.style.strokeDashoffset = "0";
      return;
    }

    const len = el.getTotalLength();
    el.style.strokeDasharray = `${len}`;
    el.style.strokeDashoffset = `${len}`;
    void el.getBoundingClientRect();
    const timer = setTimeout(() => { el.style.strokeDashoffset = "0"; }, 150);
    return () => clearTimeout(timer);
  }, [animated, paths]);

  return (
    <div className={`dd-sv-view${animated ? " dd-sv-view--animated" : ""}`}>
      {/* SVG wrapper */}
      <div
        ref={svgWrapRef}
        className="dd-sv-view__svg-wrap"
      >
        <svg
          viewBox={`0 0 ${W} ${svgH}`}
          width="100%"
          className="dd-sv-view__svg"
          preserveAspectRatio="xMidYMid meet"
          aria-hidden="true"
        >
          <defs>
            {/* Fill gradient — spectrum colors at medium opacity */}
            <linearGradient id="sv-lean-grad" x1="0" y1="0" x2="1" y2="0">
              {gradStops.map((s) => (
                <stop key={s.offset} offset={s.offset} stopColor={s.color} stopOpacity="0.38" />
              ))}
            </linearGradient>
            {/* Stroke gradient — same spectrum, full opacity for the curve line */}
            <linearGradient id="sv-lean-stroke-grad" x1="0" y1="0" x2="1" y2="0">
              {gradStops.map((s) => (
                <stop key={`stroke-${s.offset}`} offset={s.offset} stopColor={s.color} stopOpacity="0.9" />
              ))}
            </linearGradient>
            {/* Ink wash filter on fill only — not stroke — 8+ sources */}
            {n >= 8 && (
              <filter id="sv-ink-wash" x="-5%" y="-5%" width="110%" height="110%">
                <feTurbulence
                  type="turbulence"
                  baseFrequency="0.012 0.025"
                  numOctaves="1"
                  seed="42"
                  result="turb"
                />
                <feDisplacementMap in="SourceGraphic" in2="turb" scale="1.8" />
              </filter>
            )}
          </defs>

          {/* Dot strip — ≤3 sources: honest dots, no KDE curve */}
          {isFlat && (
            <>
              <line
                x1="10" y1={svgH - 8} x2={W - 10} y2={svgH - 8}
                stroke="url(#sv-lean-stroke-grad)" strokeWidth="0.75" opacity="0.4"
              />
              {sources.map((s, i) => (
                <circle
                  key={`dot-${i}`}
                  cx={(s.politicalLean / 100) * W}
                  cy={svgH - 8}
                  r="5"
                  fill="none"
                  strokeWidth="1.5"
                  className="dd-sv-view__dot"
                  data-lean={leanToBucket(s.politicalLean)}
                />
              ))}
            </>
          )}

          {/* Beat 1: Ink wash fill — rises first, soft organic texture */}
          {paths && (
            <path
              ref={fillRef}
              d={paths.fillPath}
              fill="url(#sv-lean-grad)"
              filter={n >= 8 ? "url(#sv-ink-wash)" : undefined}
              className="dd-sv-view__fill"
            />
          )}

          {/* Beat 3 (350ms): Contour lines — topographic depth, dashed */}
          {contours.map((contour, ci) =>
            contour.segments.map((seg, si) => (
              <line
                key={`contour-${ci}-${si}`}
                x1={seg.x1} y1={seg.y} x2={seg.x2} y2={seg.y}
                stroke="var(--fg-tertiary)"
                strokeWidth="0.5"
                strokeDasharray="4 3"
                className="dd-sv-view__contour"
                style={{ transitionDelay: `${350 + ci * 80}ms` }}
              />
            ))
          )}

          {/* Beat 2 (150ms): Stroke — chromatic curve, blue→green→red spectrum */}
          {paths && (
            <path
              ref={strokeRef}
              d={paths.strokePath}
              fill="none"
              stroke="url(#sv-lean-stroke-grad)"
              strokeWidth="1.8"
              className="dd-sv-view__stroke"
            />
          )}

          {/* Source dots overlay — n=4-7 only */}
          {isLow && densities && sourcePins.map((pin, i) => (
            <circle
              key={`src-dot-${i}`}
              cx={pin.x}
              cy={pin.y}
              r="2.5"
              fill="none"
              strokeWidth="1.5"
              className="dd-sv-view__src-dot"
              data-lean={pin.leanBucket}
            />
          ))}

          {/* Beat 4 (400ms): Amber plumb line — weighted mean */}
          {!isFlat && (
            <line
              x1={(mean / 100) * W} y1={4}
              x2={(mean / 100) * W} y2={svgH - 4}
              stroke="var(--cin-amber)"
              strokeWidth="0.75"
              strokeDasharray="3 2"
              className="dd-sv-view__mean"
            />
          )}

          {/* Beat 5 (500ms): Bimodal peak dots — only when split detected */}
          {bimodal && bimodal.peaks.map((peak, pi) => {
            const x = (peak.lean / 100) * W;
            const scaledD = densities!.map((d) => d * (peakH / (svgH - 12)));
            const y = getYOnCurve(peak.lean, scaledD, svgH, 12);
            const anchor = x > W * 0.75 ? "end" : x < W * 0.25 ? "start" : "middle";
            return (
              <g key={`bm-peak-${pi}`} className="dd-sv-view__bm-peak">
                <circle cx={x} cy={y} r="2.5" fill="var(--fg-muted)" opacity="0.6" />
                <text
                  x={x} y={y - 7}
                  textAnchor={anchor}
                  fill="var(--fg-muted)"
                  fontSize="6"
                  fontFamily="var(--font-data)"
                  letterSpacing="0.04em"
                >
                  {leanLabelAbbr(peak.lean)}
                </text>
              </g>
            );
          })}

          {/* Dead zone annotations */}
          {deadZones.map((zone, zi) => (
            <text
              key={`dead-${zi}`}
              x={(zone.midLean / 100) * W}
              y={svgH - 3}
              textAnchor="middle"
              fill="var(--fg-muted)"
              fontSize="5.5"
              fontFamily="var(--font-data)"
              className="dd-sv-view__dead-label"
            >
              no coverage
            </text>
          ))}

        </svg>
      </div>

      {/* 4-state coverage banner — consensus is silent (no banner) */}
      {coverage !== "consensus" && (
        <div
          className={`dd-sv-view__banner dd-sv-view__banner--${coverage}`}
          aria-live="polite"
        >
          <span className="dd-sv-view__banner-icon" aria-hidden="true">
            {coverage === "split" ? "◈" : coverage === "divergent" ? "◐" : "◑"}
          </span>
          {coverage === "split"    && "Left-right split — sources diverge"}
          {coverage === "divergent" && "Wide spectrum — no consensus"}
          {coverage === "leaning"  && `Leaning ${mean < 50 ? "left" : "right"}`}
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   Container — DeepDiveSpectrum
   ═══════════════════════════════════════════════════════════════════════ */

interface DeepDiveSpectrumProps {
  sources: DeepDiveSpectrumSource[];
}

export default function DeepDiveSpectrum({ sources }: DeepDiveSpectrumProps) {
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const mean = useMemo(() => weightedMeanLean(sources), [sources]);

  if (sources.length === 0) {
    return (
      <div className="dd-sv" role="img" aria-label="No sources available for spectrum">
        <div className="dd-sv__empty">No sources</div>
      </div>
    );
  }

  return (
    <div className="dd-sv" role="img" aria-label="Source political lean spectrum">
      <SpectrumView sources={sources} />
      <TiltRow mean={mean} />
      <SpectrumAxis />
      <SourceFaviconRow sources={sources} setTooltip={setTooltip} />
      {tooltip && <SpectrumTooltip data={tooltip} />}
    </div>
  );
}
