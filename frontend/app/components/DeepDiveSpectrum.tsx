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

/**
 * Robust bandwidth — normal reference rule with IQR correction.
 * Uses min(std, IQR/1.34) to avoid over-smoothing bimodal distributions.
 * Silverman's rule uses std alone, which smears two peaks into one hump.
 */
function robustBandwidth(values: number[]): number {
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

/* ── Lean zone positions for source row ────────────────────────────── */

const LEAN_ZONE_POSITIONS = [
  { key: "far-left",     pct: 10,  label: "FL" },
  { key: "left",         pct: 28,  label: "L"  },
  { key: "center-left",  pct: 40,  label: "CL" },
  { key: "center",       pct: 50,  label: "C"  },
  { key: "center-right", pct: 60,  label: "CR" },
  { key: "right",        pct: 72,  label: "R"  },
  { key: "far-right",    pct: 90,  label: "FR" },
] as const;

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
   SourceFaviconRow — HTML source cluster row below every SVG
   ═══════════════════════════════════════════════════════════════════════ */

const MAX_VISIBLE_DESKTOP = 3;
const MAX_VISIBLE_MOBILE = 2;

function SourceFaviconRow({
  sources,
  setTooltip,
}: {
  sources: DeepDiveSpectrumSource[];
  setTooltip: (t: TooltipData | null) => void;
}) {
  const [expandedZone, setExpandedZone] = useState<string | null>(null);
  const rowRef = useRef<HTMLDivElement>(null);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const maxVisible = isMobile ? MAX_VISIBLE_MOBILE : MAX_VISIBLE_DESKTOP;
  const avatarSize = isMobile ? 16 : 20;

  // Group sources into lean zones
  const zoneMap = useMemo(() => {
    const map = new Map<string, DeepDiveSpectrumSource[]>();
    for (const zone of LEAN_ZONE_POSITIONS) {
      map.set(zone.key, []);
    }
    for (const s of sources) {
      const bucket = leanToBucket(s.politicalLean);
      const existing = map.get(bucket);
      if (existing) existing.push(s);
    }
    return map;
  }, [sources]);

  const handleAvatarEnter = useCallback(
    (e: React.PointerEvent, source: DeepDiveSpectrumSource) => {
      const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
      setTooltip({
        source,
        x: rect.left + rect.width / 2,
        y: rect.top,
      });
    },
    [setTooltip]
  );

  const handleAvatarLeave = useCallback(() => {
    setTooltip(null);
  }, [setTooltip]);

  // Mobile dismiss: close expanded zone when clicking outside the row
  useEffect(() => {
    if (!expandedZone || !isMobile) return;
    const handleClickOutside = (e: MouseEvent) => {
      if (rowRef.current && !rowRef.current.contains(e.target as Node)) {
        setExpandedZone(null);
        setTooltip(null);
      }
    };
    document.addEventListener("click", handleClickOutside);
    return () => document.removeEventListener("click", handleClickOutside);
  }, [expandedZone, isMobile, setTooltip]);

  return (
    <div className="dd-sv-sources" ref={rowRef}>
      {LEAN_ZONE_POSITIONS.map((zone) => {
        const zoneSources = zoneMap.get(zone.key) ?? [];
        if (zoneSources.length === 0) return null;

        const isExpanded = expandedZone === zone.key;
        const visibleSources = isExpanded ? zoneSources : zoneSources.slice(0, maxVisible);
        const overflow = zoneSources.length - maxVisible;

        const isEdgeLeft = zone.pct <= 15;
        const isEdgeRight = zone.pct >= 85;
        const slotClass = [
          "dd-sv-sources__slot",
          isExpanded ? "dd-sv-sources__slot--expanded" : "",
          isEdgeLeft ? "dd-sv-sources__slot--edge-left" : "",
          isEdgeRight ? "dd-sv-sources__slot--edge-right" : "",
        ].filter(Boolean).join(" ");

        return (
          <div
            key={zone.key}
            className={slotClass}
            style={{ left: `${zone.pct}%` }}
            onPointerEnter={() => setExpandedZone(zone.key)}
            onPointerLeave={() => { setExpandedZone(null); setTooltip(null); }}
          >
            <div className="dd-sv-sources__avatars">
              {visibleSources.map((s, i) => (
                <FaviconAvatar
                  key={`${s.name}-${s.articleUrl}-${i}`}
                  source={s}
                  size={avatarSize}
                  onPointerEnter={(e) => handleAvatarEnter(e, s)}
                  onPointerLeave={handleAvatarLeave}
                />
              ))}
              {!isExpanded && overflow > 0 && (
                <div
                  className="dd-sv-avatar dd-sv-avatar--count"
                  style={{ width: avatarSize, height: avatarSize }}
                  title={`${overflow} more source${overflow > 1 ? "s" : ""}`}
                >
                  +{overflow}
                </div>
              )}
            </div>
            {isExpanded && zoneSources.length > 0 && (
              <div className="dd-sv-sources__names">
                {zoneSources.map((s, i) => (
                  <a
                    key={`${s.articleUrl}-${i}`}
                    href={s.articleUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="dd-sv-sources__name-link"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {s.name}
                  </a>
                ))}
              </div>
            )}
          </div>
        );
      })}
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
   ═══════════════════════════════════════════════════════════════════════ */

function SpectrumView({ sources }: { sources: DeepDiveSpectrumSource[] }) {
  const fillRef = useRef<SVGPathElement>(null);
  const strokeRef = useRef<SVGPathElement>(null);
  const riseRafRef = useRef<number>(0);
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
      <svg
        viewBox={`0 0 ${W} ${svgH}`}
        width="100%"
        className="dd-sv-view__svg"
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="sv-lean-grad" x1="0" y1="0" x2="1" y2="0">
            {gradStops.map((s) => (
              <stop key={s.offset} offset={s.offset} stopColor={s.color} stopOpacity="0.12" />
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
              stroke="var(--fg-muted)" strokeWidth="0.75" opacity="0.25"
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

        {/* Beat 2 (150ms): Stroke — cartographer's nib, crisp (no ink filter) */}
        {paths && (
          <path
            ref={strokeRef}
            d={paths.strokePath}
            fill="none"
            stroke="var(--fg-tertiary)"
            strokeWidth="1.5"
            className="dd-sv-view__stroke"
          />
        )}

        {/* Source dots overlay — n=4-7 only: ground truth on the KDE curve */}
        {isLow && densities && sources.map((s, i) => {
          const x = (s.politicalLean / 100) * W;
          const scaledD = densities.map((d) => d * (peakH / (svgH - 12)));
          const y = getYOnCurve(s.politicalLean, scaledD, svgH, 12);
          return (
            <circle
              key={`src-dot-${i}`}
              cx={x}
              cy={y}
              r="2.5"
              fill="none"
              strokeWidth="1.5"
              className="dd-sv-view__src-dot"
              data-lean={leanToBucket(s.politicalLean)}
            />
          );
        })}

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
      <SourceFaviconRow sources={sources} setTooltip={setTooltip} />
      <SpectrumAxis mode="full" />
      {tooltip && <SpectrumTooltip data={tooltip} />}
    </div>
  );
}
