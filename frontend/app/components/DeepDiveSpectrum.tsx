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
   View A: Ink Ridge — KDE distribution curve (shape only, no dots)
   ═══════════════════════════════════════════════════════════════════════ */

function InkRidge({ sources }: { sources: DeepDiveSpectrumSource[] }) {
  const strokeRef = useRef<SVGPathElement>(null);
  const [animated, setAnimated] = useState(false);
  const n = sources.length;
  const mean = weightedMeanLean(sources);
  const leans = sources.map((s) => s.politicalLean);

  // Determine rendering mode
  const isFlat = n <= 3;
  const isBroad = n >= 4 && n <= 7;
  const W = 400;
  const svgH = isFlat ? 40 : isBroad ? 48 : 52;

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
    const peakH = isBroad ? 28 : 42;
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

  return (
    <div className={`dd-sv-ridge${animated ? " dd-sv-ridge--animated" : ""}`}>
      <svg
        viewBox={`0 0 ${W} ${svgH}`}
        width="100%"
        className="dd-sv-ridge__svg"
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="ridge-lean-grad" x1="0" y1="0" x2="1" y2="0">
            {gradStops.map((s) => (
              <stop key={s.offset} offset={s.offset} stopColor={s.color} stopOpacity="0.15" />
            ))}
          </linearGradient>
          {/* Organic ink filter — 8+ sources only */}
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
            y1={svgH - 4}
            x2="390"
            y2={svgH - 4}
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

        {/* Weighted mean dashed line */}
        <line
          x1={(mean / 100) * W}
          y1={isFlat ? 8 : 4}
          x2={(mean / 100) * W}
          y2={svgH - 2}
          stroke="var(--fg-tertiary)"
          strokeWidth="0.5"
          strokeDasharray="3 2"
          opacity="0.5"
          className="dd-sv-ridge__mean"
        />
      </svg>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   View B: Witness Line — whisker stems only, no source markers
   ═══════════════════════════════════════════════════════════════════════ */

function WitnessLine({ sources }: { sources: DeepDiveSpectrumSource[] }) {
  const [animated, setAnimated] = useState(false);
  const W = 400;
  const svgH = 48;
  const trackY = 44;

  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 50);
    return () => clearTimeout(timer);
  }, []);

  // Sort by lean for clean whisker rendering
  const sortedSources = useMemo(() => {
    return [...sources].sort((a, b) => a.politicalLean - b.politicalLean);
  }, [sources]);

  return (
    <div className={`dd-sv-witness${animated ? " dd-sv-witness--animated" : ""}`}>
      <svg
        viewBox={`0 0 ${W} ${svgH}`}
        width="100%"
        className="dd-sv-witness__svg"
        preserveAspectRatio="xMidYMid meet"
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

        {/* Whisker stems — height encodes factual rigor */}
        {sortedSources.map((s, i) => {
          const x = (s.politicalLean / 100) * W;
          const rigor = s.factualRigor ?? 50;
          const h = 6 + (rigor / 100) * 28; // 6-34px height
          return (
            <line
              key={`whisker-${s.name}-${i}`}
              x1={x}
              y1={trackY}
              x2={x}
              y2={trackY - h}
              stroke={getLeanColor(s.politicalLean)}
              strokeWidth="1"
              opacity="0.7"
              className="dd-sv-witness__whisker"
              style={{ animationDelay: `${60 + i * 20}ms` }}
            />
          );
        })}
      </svg>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   View C: Terrain Map — topographic landscape (shape only)
   ═══════════════════════════════════════════════════════════════════════ */

function TerrainMap({ sources }: { sources: DeepDiveSpectrumSource[] }) {
  const terrainRef = useRef<SVGPathElement>(null);
  const riseRafRef = useRef<number>(0);
  const [animated, setAnimated] = useState(false);
  const n = sources.length;
  const leans = sources.map((s) => s.politicalLean);
  const W = 400;

  const isFlat = n <= 3;
  const isLow = n >= 4 && n <= 7;
  const svgH = 56;
  const peakH = isFlat ? 0 : isLow ? 20 : 46;

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
          const y = svgH - thresh * peakH - 10;
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
    const finalD = densities.map((d) => d * (peakH / (svgH - 10)));

    // Skip animation for users who prefer reduced motion
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const { fillPath } = kdeToCubicPath(finalD, svgH, W, 10);
      el.setAttribute("d", fillPath);
      return;
    }

    const flatD = densities.map(() => 0);
    let start: number | null = null;
    const duration = 500;

    function step(ts: number) {
      if (!start) start = ts;
      const elapsed = ts - start;
      const progress = Math.min(elapsed / duration, 1);
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

  return (
    <div className={`dd-sv-terrain${animated ? " dd-sv-terrain--animated" : ""}`}>
      <svg
        viewBox={`0 0 ${W} ${svgH}`}
        width="100%"
        className="dd-sv-terrain__svg"
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
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
            y1={svgH - 12}
            x2={W - 5}
            y2={svgH - 12}
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

        {/* Tilt dashed line inside SVG */}
        {!isFlat && (
          <line
            x1={(weightedMeanLean(sources) / 100) * W}
            y1={4}
            x2={(weightedMeanLean(sources) / 100) * W}
            y2={svgH - 4}
            stroke="var(--cin-amber)"
            strokeWidth="0.75"
            strokeDasharray="3 2"
            opacity="0.6"
          />
        )}
      </svg>
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
  const mean = useMemo(() => weightedMeanLean(sources), [sources]);

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
        {displayView === "ridge" && <InkRidge sources={sources} />}
        {displayView === "witness" && <WitnessLine sources={sources} />}
        {displayView === "terrain" && <TerrainMap sources={sources} />}
      </div>

      {/* Shared HTML elements below SVG — tilt, sources, axis */}
      <TiltRow mean={mean} />
      <SourceFaviconRow sources={sources} setTooltip={setTooltip} />
      <SpectrumAxis mode="full" />

      {tooltip && <SpectrumTooltip data={tooltip} />}
    </div>
  );
}
