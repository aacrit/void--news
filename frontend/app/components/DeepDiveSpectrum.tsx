"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { createPortal } from "react-dom";
import "../styles/spectrum.css";
import {
  getLeanColor,
  leanLabel,
  leanLabelAbbr,
  leanToBucket,
} from "../lib/biasColors";
import { sourceLogoUrl } from "../lib/sourceLogos";
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

/* ── Row cap for the source pin strip ────────────────────────────────────
   A dense cluster (30+ sources) packs into many greedy rows and the strip
   grows very tall. Show only the first ROW_CAP rows by default; a subtle
   "Show all N sources" toggle expands the rest in place. Pins in hidden rows
   are never rendered, so nothing off-screen is a stray tab stop. */
const ROW_CAP = 8;

/* ── Tooltip shared ──────────────────────────────────────────────────── */

interface TooltipData {
  source: DeepDiveSpectrumSource;
  x: number;
  y: number;
}

function SpectrumTooltip({ data }: { data: TooltipData }) {
  // Portal to document.body so the tooltip's `position: fixed` is viewport-
  // anchored. Without this, the tooltip inherits the deep-dive-panel's
  // transform-induced containing block (panel uses `translate(-50%, -50%)`)
  // — `position: fixed` then resolves against the panel, not the viewport,
  // and `data.x/y` (viewport coords from getBoundingClientRect on hover)
  // land in the wrong place. Per CEO 2026-05-15: tooltip "in random place."
  if (typeof document === "undefined") return null;
  return createPortal(
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
    </div>,
    document.body,
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
  // Self-hosted first-party outlet favicon (see sourceLogoUrl); "" -> monogram.
  const url = sourceLogoUrl(source.name);
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
   SourceFaviconRow — continuous lean% positioning, GREEDY MULTI-ROW placement.

   With the separate Source Ledger removed (2026-08-10), the spectrum's
   positioned logos ARE the source display: every source must stay individually
   hittable and nameable, no matter how many pile at the same lean. So placement
   is no longer capped at 2 rows: each source drops into the first row where it
   clears its neighbour by `minGap`, adding a new row when none fits. No two
   pins ever overlap, so a ~30-source cluster simply grows a few rows tall and
   every source stays tappable.

   Row cap: a very dense cluster would make the strip too tall, so only the
   first ROW_CAP rows show by default. When the greedy pass produces more than
   ROW_CAP rows, a Barlow small-caps "Show all N sources" text button appears
   below the strip; it expands the container height in place (no inner scroll)
   to reveal every row, and collapses back to ROW_CAP ("Show fewer"). Pins in
   the hidden rows are not rendered while collapsed, so nothing off-screen is a
   focusable tab stop.

   Naming:
     - Fine pointer (desktop): pins are <a> links. Hover shows the tooltip
       (name + lean + score + "Open article"); click opens the article.
     - Coarse pointer (mobile): pins are <button>s. A tap does NOT navigate; it
       toggles that source's tooltip (name + lean + score + an explicit
       "Open article" link inside). Tapping elsewhere, another pin, or Escape
       dismisses it.
   ═══════════════════════════════════════════════════════════════════════ */

function SourceFaviconRow({
  sources,
  setTooltip,
}: {
  sources: DeepDiveSpectrumSource[];
  setTooltip: (t: TooltipData | null) => void;
}) {
  const [isMobile, setIsMobile] = useState(false);
  const [isCoarse, setIsCoarse] = useState(false);
  // Coarse-pointer only: which source's tooltip is currently pinned open.
  const [pinnedName, setPinnedName] = useState<string | null>(null);
  // Row cap: strip shows the first ROW_CAP rows until the reader expands it.
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    const mqW = window.matchMedia("(max-width: 767px)");
    const mqP = window.matchMedia("(pointer: coarse)");
    setIsMobile(mqW.matches);
    setIsCoarse(mqP.matches);
    const hW = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    const hP = (e: MediaQueryListEvent) => setIsCoarse(e.matches);
    mqW.addEventListener("change", hW);
    mqP.addEventListener("change", hP);
    return () => {
      mqW.removeEventListener("change", hW);
      mqP.removeEventListener("change", hP);
    };
  }, []);

  const avatarSize = isMobile ? 14 : 20;
  const rowH = avatarSize + 4; // 4px gap between rows

  // A slightly larger min-gap on mobile keeps the smaller 14px tiles from
  // stacking too tightly.
  const minGap = isMobile ? 6 : MIN_GAP_PCT;

  // Greedy multi-row placement. Sort by lean, then for each source pick the
  // first row whose last-placed pin clears it by minGap; open a new row when
  // none fits. Guarantees no overlap -> every source individually hittable.
  const { placed, rowCount } = useMemo(() => {
    const sorted = [...sources].sort((a, b) => a.politicalLean - b.politicalLean);
    const rowsLast: number[] = []; // last leftPct placed per row
    const out = sorted.map((s) => {
      const leftPct = 2 + (s.politicalLean / 100) * 96;
      let row = rowsLast.findIndex((last) => leftPct - last >= minGap);
      if (row === -1) {
        row = rowsLast.length;
        rowsLast.push(leftPct);
      } else {
        rowsLast[row] = leftPct;
      }
      return { source: s, leftPct, row };
    });
    return { placed: out, rowCount: Math.max(1, rowsLast.length) };
  }, [sources, minGap]);

  // Coarse: dismiss the pinned tooltip on an outside tap or Escape.
  useEffect(() => {
    if (!pinnedName) return;
    const onDown = (e: PointerEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.closest(".dd-sv-sources__pin") || t.closest(".dd-sv__tooltip"))) return;
      setPinnedName(null);
      setTooltip(null);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setPinnedName(null);
        setTooltip(null);
      }
    };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [pinnedName, setTooltip]);

  const showTip = (el: HTMLElement, source: DeepDiveSpectrumSource) => {
    const rect = el.getBoundingClientRect();
    setTooltip({ source, x: rect.left + rect.width / 2, y: rect.top });
  };

  const capped = rowCount > ROW_CAP;
  const visibleRows = expanded ? rowCount : Math.min(rowCount, ROW_CAP);
  // Only render pins whose row is currently visible. Hidden-row pins are never
  // mounted, so they are neither painted nor part of the tab order.
  const visiblePlaced = capped && !expanded
    ? placed.filter((p) => p.row < ROW_CAP)
    : placed;

  const toggleExpanded = () => {
    if (expanded) {
      // Collapsing: a coarse-tap tooltip may be pinned to a row that is about
      // to disappear, so dismiss it.
      setPinnedName(null);
      setTooltip(null);
    }
    setExpanded((v) => !v);
  };

  return (
    <>
      <div className="dd-sv-sources" style={{ height: rowH * visibleRows }}>
      {visiblePlaced.map(({ source, leftPct, row }, i) => {
        const posStyle: React.CSSProperties = { left: `${leftPct}%`, top: `${row * rowH}px` };

        if (isCoarse) {
          const isPinned = pinnedName === source.name;
          return (
            <button
              key={`pin-${i}`}
              type="button"
              className="dd-sv-sources__pin"
              style={posStyle}
              aria-label={`${source.name}, ${leanLabel(source.politicalLean)}. Show details.`}
              aria-expanded={isPinned}
              onClick={(e) => {
                e.preventDefault();
                if (isPinned) {
                  setPinnedName(null);
                  setTooltip(null);
                } else {
                  setPinnedName(source.name);
                  showTip(e.currentTarget, source);
                }
              }}
            >
              <FaviconAvatar source={source} size={avatarSize} />
            </button>
          );
        }

        return (
          <a
            key={`pin-${i}`}
            href={source.articleUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="dd-sv-sources__pin"
            style={posStyle}
            onPointerEnter={(e) => showTip(e.currentTarget, source)}
            onPointerLeave={() => setTooltip(null)}
          >
            <FaviconAvatar source={source} size={avatarSize} />
          </a>
        );
      })}
      </div>
      {capped && (
        <button
          type="button"
          className="dd-sv-sources__toggle"
          aria-expanded={expanded}
          onClick={toggleExpanded}
        >
          {expanded ? "Show fewer" : `Show all ${sources.length} sources`}
          <span className="dd-sv-sources__toggle-caret" aria-hidden="true">
            ›
          </span>
        </button>
      )}
    </>
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
   MobileLCR — at-a-glance Left/Center/Right source counts for mobile.

   The desktop TiltRow (mean needle + label) is hidden on mobile, so a phone
   reader gets no split without hovering each pin. This compact L/C/R line
   restores that glance: how many sources sit left, center, and right. Buckets
   match the spectrum's center band (46-55 = center).
   ═══════════════════════════════════════════════════════════════════════ */

function MobileLCR({ sources }: { sources: DeepDiveSpectrumSource[] }) {
  let left = 0, center = 0, right = 0;
  for (const s of sources) {
    const v = s.politicalLean;
    if (v <= 45) left++;
    else if (v >= 56) right++;
    else center++;
  }
  return (
    <div
      className="dd-sv__lcr"
      role="img"
      aria-label={`Source split: ${left} left, ${center} center, ${right} right`}
    >
      <span className="dd-sv__lcr-seg dd-sv__lcr-seg--left" aria-hidden="true">L&nbsp;{left}</span>
      <span className="dd-sv__lcr-seg dd-sv__lcr-seg--center" aria-hidden="true">C&nbsp;{center}</span>
      <span className="dd-sv__lcr-seg dd-sv__lcr-seg--right" aria-hidden="true">R&nbsp;{right}</span>
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

function SpectrumView({ sources, isMobile = false, settled = false, aggregateLean }: { sources: DeepDiveSpectrumSource[]; isMobile?: boolean; settled?: boolean; aggregateLean?: number }) {
  const fillRef = useRef<SVGPathElement>(null);
  const strokeRef = useRef<SVGPathElement>(null);
  const riseRafRef = useRef<number>(0);
  const svgWrapRef = useRef<HTMLDivElement>(null);
  // settled: the spectrum mounts already-drawn (no entrance choreography).
  // Used inside the inline Deep Dive, where the accordion expansion is the one
  // continuous open motion and the chart must not add a second beat.
  const [animated, setAnimated] = useState(settled);
  // Ink-wash filter (feTurbulence + feDisplacementMap) is CPU-rasterized —
  // re-running it on every rAF frame of the 450ms rise caused a visible hitch
  // on phones. The filter attaches only after the rise settles.
  const [riseDone, setRiseDone] = useState(false);

  const n = sources.length;
  const leans = sources.map((s) => s.politicalLean);
  // Plumb line / mean: prefer the Sigil's aggregate lean (same value the Sigil
  // renders) so the spectrum's center line agrees with the tilt shown alongside
  // it. Fall back to the tier-weighted mean only when no aggregate is supplied.
  const mean = aggregateLean ?? weightedMeanLean(sources);

  const W = 400;
  const svgH = isMobile ? 52 : 60;  // Slightly reduced on mobile to fit safe area
  // Small clusters (n <= 7) get a fixed bandwidth so the KDE is a soft, non
  // degenerate mound instead of a spike; every count renders the SAME way (KDE
  // wave + favicon pins below), regardless of source count.
  const smallN = n <= 7;
  const peakH = 48;

  // Standard deviation of lean — used for divergence classification
  const std = useMemo(() => {
    if (leans.length < 2) return 0;
    const m = leans.reduce((s, v) => s + v, 0) / leans.length;
    return Math.sqrt(leans.reduce((s, v) => s + (v - m) ** 2, 0) / leans.length);
  }, [leans]);

  const densities = useMemo(() => {
    // Fixed bw=6 for small clusters (Silverman at n=5 gives ~12 and obliterates
    // two clusters; for n=1 or 2 it yields a gentle single mound). Robust
    // bandwidth, floored at 6, for larger clusters.
    const bw = smallN ? 6 : Math.max(6, robustBandwidth(leans));
    const raw = computeKDE(leans, bw, 100);
    return normalizeKDE(raw);
  }, [leans, smallN]);

  // Paths
  const paths = useMemo(() => {
    if (!densities) return null;
    const scaled = densities.map((d) => d * (peakH / (svgH - 12)));
    return kdeToCubicPath(scaled, svgH, W, 12);
  }, [densities, svgH, peakH]);

  // Contour lines: 1 at 50%; 2 (33%+66%) for 16+ sources
  const contours = useMemo(() => {
    // Topographic contours only add signal on denser clusters; keep them off
    // for small n (the single soft mound reads fine without them).
    if (!densities || n <= 7) return [];
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
  }, [densities, n, svgH, peakH]);

  // Bimodal & dead-zone detection
  const bimodal = useMemo(() => {
    if (!densities || n < 5) return null;
    return detectBimodal(densities);
  }, [densities, n]);

  const deadZones = useMemo(() => {
    if (!densities || n < 4) return [];
    return detectDeadZones(densities);
  }, [densities, n]);

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

  // Trigger entrance (skipped when settled — the chart mounts already-drawn)
  useEffect(() => {
    if (settled) return;
    const timer = setTimeout(() => setAnimated(true), 50);
    return () => clearTimeout(timer);
  }, [settled]);

  // Fill rises from flat via rAF — 450ms ease-out cubic. The stroke draw,
  // contours, mean line, and labels all arrive INSIDE this same 450ms window
  // (see spectrum.css), so the whole entrance reads as one continuous breath
  // rather than a chain of beats. settled: final path immediately, no rAF.
  useEffect(() => {
    if (!animated || !fillRef.current || !densities || !paths) return;
    const el = fillRef.current;
    const finalD = densities.map((d) => d * (peakH / (svgH - 12)));

    if (settled || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.setAttribute("d", kdeToCubicPath(finalD, svgH, W, 12).fillPath);
      setRiseDone(true);
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
      if (progress < 1) {
        riseRafRef.current = requestAnimationFrame(step);
      } else {
        setRiseDone(true);
      }
    }
    riseRafRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(riseRafRef.current);
  }, [animated, densities, paths, svgH, peakH, settled]);

  // Stroke draws via CSS transition on dashoffset, starting on the next frame
  // so it rides the same timeline as the rise (the old 150ms gate made it a
  // separate second beat). settled: full stroke immediately, no draw-on.
  useEffect(() => {
    if (!animated || !strokeRef.current || !paths) return;
    const el = strokeRef.current;

    if (settled) return; // untouched dasharray = fully drawn stroke

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
    let raf2 = 0;
    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => { el.style.strokeDashoffset = "0"; });
    });
    return () => { cancelAnimationFrame(raf1); cancelAnimationFrame(raf2); };
  }, [animated, paths, settled]);

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

          {/* Ink wash fill — rises via rAF, soft organic texture */}
          {paths && (
            <path
              ref={fillRef}
              d={paths.fillPath}
              fill="url(#sv-lean-grad)"
              filter={riseDone && n >= 8 ? "url(#sv-ink-wash)" : undefined}
              className="dd-sv-view__fill"
            />
          )}

          {/* Contour lines — topographic depth, dashed. Delays sit inside the
              450ms rise window so the whole entrance is one continuous motion. */}
          {contours.map((contour, ci) =>
            contour.segments.map((seg, si) => (
              <line
                key={`contour-${ci}-${si}`}
                x1={seg.x1} y1={seg.y} x2={seg.x2} y2={seg.y}
                stroke="var(--fg-tertiary)"
                strokeWidth="0.5"
                strokeDasharray="4 3"
                className="dd-sv-view__contour"
                style={{ transitionDelay: `${120 + ci * 60}ms` }}
              />
            ))
          )}

          {/* Stroke — chromatic curve, blue→green→red spectrum */}
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

          {/* Amber plumb line — aggregate lean (Sigil tilt), fades during rise */}
          <line
            x1={(mean / 100) * W} y1={4}
            x2={(mean / 100) * W} y2={svgH - 4}
            stroke="var(--cin-amber)"
            strokeWidth="0.75"
            strokeDasharray="3 2"
            className="dd-sv-view__mean"
          />

          {/* Bimodal peak dots — only when split detected */}
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

      {/* Coverage banner removed per CEO 2026-05-13 — the visualization itself
          already shows whether coverage is split / divergent / leaning; the
          redundant text label was visually misplaced and added no signal. */}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════
   Container — DeepDiveSpectrum
   ═══════════════════════════════════════════════════════════════════════ */

interface DeepDiveSpectrumProps {
  sources: DeepDiveSpectrumSource[];
  /** Mount already-drawn: no rise / stroke-draw / reveal choreography. Used
      where a parent container owns the one continuous open motion (the inline
      Deep Dive accordion) and the chart must not add a second beat. */
  settled?: boolean;
  /** The Sigil's aggregate political lean (0-100). When supplied it drives the
      amber plumb line AND the TiltRow label, so the spectrum's center line
      lands exactly where the Sigil's tilt says. The per-source pins still show
      the true distribution. Falls back to the tier-weighted mean when absent. */
  aggregateLean?: number;
}

export default function DeepDiveSpectrum({ sources, settled = false, aggregateLean }: DeepDiveSpectrumProps) {
  const [tooltip, setTooltip] = useState<TooltipData | null>(null);
  const [isMobile, setIsMobile] = useState(false);
  const mean = useMemo(
    () => aggregateLean ?? weightedMeanLean(sources),
    [sources, aggregateLean],
  );

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  if (sources.length === 0) {
    return (
      <div className="dd-sv" role="img" aria-label="No sources available for spectrum">
        <div className="dd-sv__empty">No sources</div>
      </div>
    );
  }

  return (
    <div className="dd-sv" role="img" aria-label="Source political lean spectrum">
      <SpectrumView sources={sources} isMobile={isMobile} settled={settled} aggregateLean={aggregateLean} />
      {/* Desktop: mean needle + label (TiltRow). Mobile: TiltRow is too much
          clutter, so show a compact L/C/R source-count readout instead so the
          split is glanceable without hovering each pin. */}
      {!isMobile ? <TiltRow mean={mean} /> : <MobileLCR sources={sources} />}
      <SpectrumAxis />
      <SourceFaviconRow sources={sources} setTooltip={setTooltip} />
      {tooltip && <SpectrumTooltip data={tooltip} />}
    </div>
  );
}
