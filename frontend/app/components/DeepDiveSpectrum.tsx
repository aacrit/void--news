"use client";

import { useState, useMemo, useRef, useEffect, useCallback } from "react";
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
   DeepDiveSpectrum — Political lean spectrum visualization
   Individual source pins at actual lean values on the KDE curve.
   Desktop: hover → tooltip (interactive, pointer-events:auto).
   Mobile: tap → persistent info bar.
   12+ sources: compact source list below axis.
   Keyboard: roving tabindex, arrow keys cycle by lean.
   --------------------------------------------------------------------------- */

export interface DeepDiveSpectrumSource {
  name: string;
  articleUrl: string;
  sourceUrl: string;
  tier: string;
  politicalLean: number;
  factualRigor?: number;
  confidence?: number;
}

/* ── Constants ─────────────────────────────────────────────────────────── */

const W = 400;
const SVG_H = 60;
const PIN_MIN_GAP = 14;       // SVG units; within this → row 1
const SOURCE_LIST_THRESHOLD = 12;

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

function computeTrustScore(s: DeepDiveSpectrumSource): number {
  const tierScore = s.tier === "us_major" ? 60 : s.tier === "international" ? 50 : 40;
  return Math.round(tierScore * 0.4 + (s.factualRigor ?? 50) * 0.4 + (s.confidence ?? 0.5) * 100 * 0.2);
}

function weightedMeanLean(sources: DeepDiveSpectrumSource[]): number {
  let wSum = 0, wTotal = 0;
  for (const s of sources) {
    const w = s.tier === "us_major" ? 3 : s.tier === "international" ? 2 : 1;
    wSum += s.politicalLean * w;
    wTotal += w;
  }
  return wTotal > 0 ? wSum / wTotal : 50;
}

const LEAN_GRADIENT_STOPS: Array<{ offset: string; color: string }> = [
  { offset: "0%",   color: "var(--bias-far-left)" },
  { offset: "16%",  color: "var(--bias-left)" },
  { offset: "32%",  color: "var(--bias-center-left)" },
  { offset: "50%",  color: "var(--bias-center)" },
  { offset: "68%",  color: "var(--bias-center-right)" },
  { offset: "84%",  color: "var(--bias-right)" },
  { offset: "100%", color: "var(--bias-far-right)" },
];

/* ── Tooltip ─────────────────────────────────────────────────────────────
   pointer-events: auto so the "Open article" link is reachable.
   Dismiss is delayed 150ms so cursor can travel pin → tooltip.
   ─────────────────────────────────────────────────────────────────────── */

interface TooltipData {
  source: DeepDiveSpectrumSource;
  x: number;
  y: number;
}

function SpectrumTooltip({
  data,
  onEnter,
  onLeave,
}: {
  data: TooltipData;
  onEnter: () => void;
  onLeave: () => void;
}) {
  return (
    <div
      className="dd-sv__tooltip"
      style={{ left: `${data.x}px`, top: `${data.y}px` }}
      role="tooltip"
      onPointerEnter={onEnter}
      onPointerLeave={onLeave}
    >
      {/* Bridge: transparent extension below tooltip closes the hover gap */}
      <span className="dd-sv__tooltip-bridge" aria-hidden="true" />
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
      <a
        href={data.source.articleUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="dd-sv__tooltip-link"
      >
        Open article ↗
      </a>
    </div>
  );
}

/* ── Mobile info bar ─────────────────────────────────────────────────────
   Persistent selected-source bar. Full-width tap target for article link.
   ─────────────────────────────────────────────────────────────────────── */

function SourceInfoBar({
  source,
  onDismiss,
}: {
  source: DeepDiveSpectrumSource;
  onDismiss: () => void;
}) {
  return (
    <div className="dd-sv__info-bar" role="status" aria-live="polite">
      <span
        className="dd-sv__info-bar__dot"
        style={{ background: getLeanColor(source.politicalLean) }}
        aria-hidden="true"
      />
      <span className="dd-sv__info-bar__name">{source.name}</span>
      <span className="dd-sv__info-bar__lean" data-lean={leanToBucket(source.politicalLean)}>
        {leanLabelAbbr(source.politicalLean)}
      </span>
      <a
        href={source.articleUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="dd-sv__info-bar__link"
      >
        Read article ↗
      </a>
      <button
        type="button"
        className="dd-sv__info-bar__dismiss"
        onClick={onDismiss}
        aria-label="Dismiss"
      >
        ×
      </button>
    </div>
  );
}

/* ── Compact source list (12+ sources) ──────────────────────────────────
   Always-visible, scrollable, sorted by lean. Two columns on desktop.
   ─────────────────────────────────────────────────────────────────────── */

function SourceList({ sources }: { sources: DeepDiveSpectrumSource[] }) {
  const sorted = useMemo(
    () => [...sources].sort((a, b) => a.politicalLean - b.politicalLean),
    [sources]
  );
  return (
    <ul className="dd-sv__source-list" aria-label="All sources">
      {sorted.map((s, i) => (
        <li key={`sl-${i}`} className="dd-sv__source-list__item">
          <span
            className="dd-sv__source-list__dot"
            data-lean={leanToBucket(s.politicalLean)}
            aria-hidden="true"
          />
          <a
            href={s.articleUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="dd-sv__source-list__link"
          >
            {s.name}
          </a>
          <span className="dd-sv__source-list__lean">
            {leanLabelAbbr(s.politicalLean)}
          </span>
        </li>
      ))}
    </ul>
  );
}

/* ── SpectrumAxis ────────────────────────────────────────────────────── */

function SpectrumAxis() {
  const ticks = [0, 14, 28, 50, 72, 86, 100];
  return (
    <div className="dd-sv__axis" aria-hidden="true">
      {ticks.map((p) => (
        <span key={p} className="dd-sv__axis-tick" style={{ left: `${p}%` }} />
      ))}
      <span className="dd-sv__axis-label" style={{ left: "0%" }}>L</span>
      <span className="dd-sv__axis-label" style={{ left: "50%" }}>C</span>
      <span className="dd-sv__axis-label" style={{ left: "100%" }}>R</span>
    </div>
  );
}

/* ── TiltRow ─────────────────────────────────────────────────────────── */

function TiltRow({ mean }: { mean: number }) {
  return (
    <div className="dd-sv__tilt-row" aria-hidden="true">
      <div className="dd-sv__tilt-needle" style={{ left: `${mean}%` }} />
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
   Bimodal + dead-zone detection (unchanged)
   ═══════════════════════════════════════════════════════════════════════ */

interface BimodalPeak { lean: number; density: number; }
interface BimodalInfo { peaks: BimodalPeak[]; valleyLean: number; valleyDensity: number; }

function detectBimodal(densities: number[]): BimodalInfo | null {
  if (densities.length < 10) return null;
  const peaks: Array<{ idx: number; density: number }> = [];
  for (let i = 2; i < densities.length - 2; i++) {
    if (densities[i] > densities[i - 1] && densities[i] > densities[i + 1] && densities[i] >= 0.20) {
      peaks.push({ idx: i, density: densities[i] });
    }
  }
  if (peaks.length < 2) return null;
  peaks.sort((a, b) => b.density - a.density);
  const [p1, p2] = peaks.slice(0, 2);
  const [left, right] = p1.idx < p2.idx ? [p1, p2] : [p2, p1];
  const leftLean  = (left.idx  / (densities.length - 1)) * 100;
  const rightLean = (right.idx / (densities.length - 1)) * 100;
  if (rightLean - leftLean < 15) return null;
  let valleyIdx = left.idx, valleyDensity = densities[left.idx];
  for (let i = left.idx; i <= right.idx; i++) {
    if (densities[i] < valleyDensity) { valleyDensity = densities[i]; valleyIdx = i; }
  }
  if (valleyDensity >= Math.min(left.density, right.density) * 0.55) return null;
  return {
    peaks: [{ lean: leftLean, density: left.density }, { lean: rightLean, density: right.density }],
    valleyLean: (valleyIdx / (densities.length - 1)) * 100,
    valleyDensity,
  };
}

function detectDeadZones(densities: number[]): Array<{ startLean: number; endLean: number; midLean: number }> {
  const zones: Array<{ startLean: number; endLean: number; midLean: number }> = [];
  let inZone = false, zoneStart = 0;
  for (let i = 0; i < densities.length; i++) {
    const lean = (i / (densities.length - 1)) * 100;
    if (densities[i] < 0.03 && !inZone) { inZone = true; zoneStart = lean; }
    else if (densities[i] >= 0.03 && inZone) {
      inZone = false;
      if (lean - zoneStart >= 14) zones.push({ startLean: zoneStart, endLean: lean, midLean: (zoneStart + lean) / 2 });
    }
  }
  return zones;
}

/* ═══════════════════════════════════════════════════════════════════════
   SpectrumView — KDE curve + individual source pins
   ═══════════════════════════════════════════════════════════════════════ */

interface PinData {
  source: DeepDiveSpectrumSource;
  origIdx: number;
  x: number;    // SVG units
  y: number;    // SVG units (on curve)
  row: 0 | 1;   // vertical row (collision detection)
  leanBucket: string;
}

function SpectrumView({
  sources,
  isMobile,
  focusedIdx,
  setFocusedIdx,
  onPinHover,
  onPinHoverEnd,
  onPinTap,
  selectedIdx,
}: {
  sources: DeepDiveSpectrumSource[];
  isMobile: boolean;
  focusedIdx: number | null;
  setFocusedIdx: (i: number | null) => void;
  onPinHover: (pin: PinData, svgEl: SVGElement) => void;
  onPinHoverEnd: () => void;
  onPinTap: (idx: number) => void;
  selectedIdx: number | null;
}) {
  const fillRef   = useRef<SVGPathElement>(null);
  const strokeRef = useRef<SVGPathElement>(null);
  const riseRaf   = useRef<number>(0);
  const [animated, setAnimated] = useState(false);

  const n     = sources.length;
  const leans = useMemo(() => sources.map((s) => s.politicalLean), [sources]);
  const mean  = useMemo(() => weightedMeanLean(sources), [sources]);

  const isFlat = n <= 3;
  const isLow  = n >= 4 && n <= 7;
  const peakH  = isFlat ? 0 : isLow ? 26 : 48;

  const std = useMemo(() => {
    if (leans.length < 2) return 0;
    const m = leans.reduce((s, v) => s + v, 0) / leans.length;
    return Math.sqrt(leans.reduce((s, v) => s + (v - m) ** 2, 0) / leans.length);
  }, [leans]);

  const densities = useMemo(() => {
    if (isFlat) return null;
    const bw  = isLow ? 6 : robustBandwidth(leans);
    return normalizeKDE(computeKDE(leans, bw, 100));
  }, [leans, isFlat, isLow]);

  const paths = useMemo(() => {
    if (!densities) return null;
    return kdeToCubicPath(densities.map((d) => d * (peakH / (SVG_H - 12))), SVG_H, W, 12);
  }, [densities, peakH]);

  const contours = useMemo(() => {
    if (!densities || isFlat || isLow) return [];
    return (n >= 16 ? [0.33, 0.66] : [0.5]).map((thresh) => {
      const segs: Array<{ x1: number; x2: number; y: number }> = [];
      let inR = false, startX = 0;
      for (let i = 0; i < densities.length; i++) {
        if (densities[i] >= thresh && !inR) { inR = true; startX = (i / (densities.length - 1)) * W; }
        else if ((densities[i] < thresh || i === densities.length - 1) && inR) {
          inR = false;
          segs.push({ x1: startX, x2: (i / (densities.length - 1)) * W, y: SVG_H - thresh * peakH - 12 });
        }
      }
      return { thresh, segs };
    });
  }, [densities, n, peakH, isFlat, isLow]);

  const bimodal  = useMemo(() => (!densities || isFlat || n < 5) ? null : detectBimodal(densities),  [densities, isFlat, n]);
  const deadZones = useMemo(() => (!densities || isFlat || n < 4) ? [] : detectDeadZones(densities), [densities, isFlat, n]);

  type CC = "consensus" | "leaning" | "divergent" | "split";
  const coverage = useMemo((): CC => {
    if (bimodal)    return "split";
    if (std >= 18)  return "divergent";
    if (mean < 38 || mean > 62) return "leaning";
    return "consensus";
  }, [bimodal, std, mean]);

  // Pin positions — 2-row vertical collision detection
  const pins = useMemo((): PinData[] => {
    const scaledD = densities ? densities.map((d) => d * (peakH / (SVG_H - 12))) : null;
    const list = sources.map((s, origIdx) => ({
      source: s,
      origIdx,
      x: (s.politicalLean / 100) * W,
      y: scaledD ? getYOnCurve(s.politicalLean, scaledD, SVG_H, 12) : SVG_H - 8,
      row: 0 as 0 | 1,
      leanBucket: leanToBucket(s.politicalLean),
    }));
    // Sort by x, assign rows
    const byX = [...list].sort((a, b) => a.x - b.x);
    const lastX: [number, number] = [-Infinity, -Infinity];
    for (const pin of byX) {
      if (pin.x - lastX[0] >= PIN_MIN_GAP) { pin.row = 0; lastX[0] = pin.x; }
      else                                   { pin.row = 1; lastX[1] = pin.x; }
    }
    return list; // restore original order
  }, [densities, sources, peakH]);

  // Row-1 pins are shifted 10px down toward baseline (clamped)
  const pinY = useCallback((pin: PinData) =>
    pin.row === 1 ? Math.min(pin.y + 10, SVG_H - 6) : pin.y,
  []);

  // Keyboard: sorted by lean, roving tabindex
  const byLean = useMemo(() => [...pins].sort((a, b) => a.x - b.x), [pins]);

  const handleGroupKey = useCallback((e: React.KeyboardEvent) => {
    if (!["ArrowLeft","ArrowRight","Home","End"].includes(e.key)) return;
    e.preventDefault();
    const cur = focusedIdx ?? byLean[0]?.origIdx ?? 0;
    const curPos = byLean.findIndex((p) => p.origIdx === cur);
    if (e.key === "ArrowRight") setFocusedIdx(byLean[Math.min(curPos + 1, byLean.length - 1)].origIdx);
    if (e.key === "ArrowLeft")  setFocusedIdx(byLean[Math.max(curPos - 1, 0)].origIdx);
    if (e.key === "Home") setFocusedIdx(byLean[0].origIdx);
    if (e.key === "End")  setFocusedIdx(byLean[byLean.length - 1].origIdx);
  }, [byLean, focusedIdx, setFocusedIdx]);

  // Entrance animation
  useEffect(() => { const t = setTimeout(() => setAnimated(true), 50); return () => clearTimeout(t); }, []);

  useEffect(() => {
    if (!animated || !fillRef.current || !densities || !paths) return;
    const el = fillRef.current;
    const finalD = densities.map((d) => d * (peakH / (SVG_H - 12)));
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      el.setAttribute("d", kdeToCubicPath(finalD, SVG_H, W, 12).fillPath); return;
    }
    const flatD = densities.map(() => 0);
    let start: number | null = null;
    function step(ts: number) {
      if (!start) start = ts;
      const t = 1 - Math.pow(1 - Math.min((ts - start) / 450, 1), 3);
      el.setAttribute("d", kdeToCubicPath(flatD.map((f, i) => f + (finalD[i] - f) * t), SVG_H, W, 12).fillPath);
      if (t < 1) riseRaf.current = requestAnimationFrame(step);
    }
    riseRaf.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(riseRaf.current);
  }, [animated, densities, paths, peakH]);

  useEffect(() => {
    if (!animated || !strokeRef.current || !paths) return;
    const el = strokeRef.current;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const len = el.getTotalLength(); el.style.strokeDasharray = `${len}`; el.style.strokeDashoffset = "0"; return;
    }
    const len = el.getTotalLength();
    el.style.strokeDasharray = `${len}`; el.style.strokeDashoffset = `${len}`;
    void el.getBoundingClientRect();
    const t = setTimeout(() => { el.style.strokeDashoffset = "0"; }, 150);
    return () => clearTimeout(t);
  }, [animated, paths]);

  return (
    <div className={`dd-sv-view${animated ? " dd-sv-view--animated" : ""}`}>
      <svg
        viewBox={`0 0 ${W} ${SVG_H}`}
        width="100%"
        className="dd-sv-view__svg"
        preserveAspectRatio="xMidYMid meet"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="sv-lean-grad" x1="0" y1="0" x2="1" y2="0">
            {LEAN_GRADIENT_STOPS.map((s) => (
              <stop key={s.offset} offset={s.offset} stopColor={s.color} stopOpacity="0.38" />
            ))}
          </linearGradient>
          <linearGradient id="sv-lean-stroke-grad" x1="0" y1="0" x2="1" y2="0">
            {LEAN_GRADIENT_STOPS.map((s) => (
              <stop key={`sk-${s.offset}`} offset={s.offset} stopColor={s.color} stopOpacity="0.9" />
            ))}
          </linearGradient>
          {n >= 8 && (
            <filter id="sv-ink-wash" x="-5%" y="-5%" width="110%" height="110%">
              <feTurbulence type="turbulence" baseFrequency="0.012 0.025" numOctaves="1" seed="42" result="turb" />
              <feDisplacementMap in="SourceGraphic" in2="turb" scale="1.8" />
            </filter>
          )}
        </defs>

        {/* Dot strip — ≤3 sources */}
        {isFlat && (
          <>
            <line x1="10" y1={SVG_H - 8} x2={W - 10} y2={SVG_H - 8}
              stroke="url(#sv-lean-stroke-grad)" strokeWidth="0.75" opacity="0.4" />
          </>
        )}

        {/* Fill */}
        {paths && (
          <path ref={fillRef} d={paths.fillPath} fill="url(#sv-lean-grad)"
            filter={n >= 8 ? "url(#sv-ink-wash)" : undefined} className="dd-sv-view__fill" />
        )}

        {/* Contours */}
        {contours.map((c, ci) =>
          c.segs.map((seg, si) => (
            <line key={`c-${ci}-${si}`} x1={seg.x1} y1={seg.y} x2={seg.x2} y2={seg.y}
              stroke="var(--fg-tertiary)" strokeWidth="0.5" strokeDasharray="4 3"
              className="dd-sv-view__contour" style={{ transitionDelay: `${350 + ci * 80}ms` }} />
          ))
        )}

        {/* Stroke */}
        {paths && (
          <path ref={strokeRef} d={paths.strokePath} fill="none"
            stroke="url(#sv-lean-stroke-grad)" strokeWidth="1.8" className="dd-sv-view__stroke" />
        )}

        {/* Mean line */}
        {!isFlat && (
          <line x1={(mean / 100) * W} y1={4} x2={(mean / 100) * W} y2={SVG_H - 4}
            stroke="var(--cin-amber)" strokeWidth="0.75" strokeDasharray="3 2" className="dd-sv-view__mean" />
        )}

        {/* Bimodal peaks */}
        {bimodal && bimodal.peaks.map((peak, pi) => {
          const px = (peak.lean / 100) * W;
          const scaledD = densities!.map((d) => d * (peakH / (SVG_H - 12)));
          const py = getYOnCurve(peak.lean, scaledD, SVG_H, 12);
          const anchor = px > W * 0.75 ? "end" : px < W * 0.25 ? "start" : "middle";
          return (
            <g key={`bm-${pi}`} className="dd-sv-view__bm-peak">
              <circle cx={px} cy={py} r="2.5" fill="var(--fg-muted)" opacity="0.6" />
              <text x={px} y={py - 7} textAnchor={anchor} fill="var(--fg-muted)"
                fontSize="6" fontFamily="var(--font-data)" letterSpacing="0.04em">
                {leanLabelAbbr(peak.lean)}
              </text>
            </g>
          );
        })}

        {/* Dead zones */}
        {deadZones.map((zone, zi) => (
          <text key={`dz-${zi}`} x={(zone.midLean / 100) * W} y={SVG_H - 3}
            textAnchor="middle" fill="var(--fg-muted)" fontSize="5.5"
            fontFamily="var(--font-data)" className="dd-sv-view__dead-label">
            no coverage
          </text>
        ))}

        {/* ── Source pins — native SVG <a> with 44×44 hit rects ── */}
        <g
          role="group"
          aria-label="Source positions on political lean spectrum"
          onKeyDown={handleGroupKey}
        >
          {pins.map((pin, i) => {
            const cy = pinY(pin);
            const isFocused  = focusedIdx  === pin.origIdx;
            const isSelected = selectedIdx === pin.origIdx;
            return (
              <a
                key={`pin-${i}`}
                href={isMobile ? undefined : pin.source.articleUrl}
                target={isMobile ? undefined : "_blank"}
                rel={isMobile ? undefined : "noopener noreferrer"}
                className={`dd-sv-pin${isFocused ? " dd-sv-pin--focused" : ""}${isSelected ? " dd-sv-pin--selected" : ""}`}
                data-lean={pin.leanBucket}
                tabIndex={isFocused || (focusedIdx === null && i === 0) ? 0 : -1}
                aria-label={`${pin.source.name} — ${leanLabel(pin.source.politicalLean)} — open article`}
                onFocus={() => setFocusedIdx(pin.origIdx)}
                onPointerEnter={(e) => {
                  if (isMobile) return;
                  onPinHover(pin, e.currentTarget as unknown as SVGElement);
                }}
                onPointerLeave={() => {
                  if (!isMobile) onPinHoverEnd();
                }}
                onClick={(e) => {
                  if (isMobile) {
                    e.preventDefault();
                    onPinTap(pin.origIdx);
                  }
                }}
              >
                {/* Invisible 44×44 hit area */}
                <rect
                  x={pin.x - 22} y={cy - 22}
                  width="44" height="44"
                  fill="transparent"
                  className="dd-sv-pin__hit"
                />
                {/* Visible circle */}
                <circle
                  cx={pin.x} cy={cy} r="4"
                  fill="var(--bg-card)"
                  strokeWidth="2"
                  className="dd-sv-pin__circle"
                />
              </a>
            );
          })}
        </g>
      </svg>

      {/* Coverage banner */}
      {coverage !== "consensus" && (
        <div className={`dd-sv-view__banner dd-sv-view__banner--${coverage}`} aria-live="polite">
          <span className="dd-sv-view__banner-icon" aria-hidden="true">
            {coverage === "split" ? "◈" : coverage === "divergent" ? "◐" : "◑"}
          </span>
          {coverage === "split"     && "Left-right split — sources diverge"}
          {coverage === "divergent" && "Wide spectrum — no consensus"}
          {coverage === "leaning"   && `Leaning ${mean < 50 ? "left" : "right"}`}
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
  const [tooltip, setTooltip]         = useState<TooltipData | null>(null);
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const [focusedIdx, setFocusedIdx]   = useState<number | null>(null);
  const [isMobile, setIsMobile]       = useState(false);

  const dismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const mean = useMemo(() => weightedMeanLean(sources), [sources]);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobile(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // Mobile: tap outside → dismiss info bar
  useEffect(() => {
    if (selectedIdx === null || !isMobile) return;
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setSelectedIdx(null);
      }
    };
    document.addEventListener("click", handler);
    return () => document.removeEventListener("click", handler);
  }, [selectedIdx, isMobile]);

  const scheduleHide = useCallback(() => {
    dismissTimer.current = setTimeout(() => setTooltip(null), 150);
  }, []);

  const cancelHide = useCallback(() => {
    if (dismissTimer.current) { clearTimeout(dismissTimer.current); dismissTimer.current = null; }
  }, []);

  const handlePinHover = useCallback((pin: PinData, svgEl: SVGElement) => {
    cancelHide();
    const rect = svgEl.closest("svg")!.getBoundingClientRect();
    const svgWidth = rect.width;
    const x = rect.left + (pin.x / W) * svgWidth;
    const svgHeight = rect.height;
    const y = rect.top + (pin.y / SVG_H) * svgHeight;
    setTooltip({ source: pin.source, x, y });
  }, [cancelHide]);

  const handlePinHoverEnd = useCallback(() => { scheduleHide(); }, [scheduleHide]);

  const handlePinTap = useCallback((idx: number) => {
    setSelectedIdx((prev) => prev === idx ? null : idx);
  }, []);

  if (sources.length === 0) {
    return (
      <div className="dd-sv" role="img" aria-label="No sources available for spectrum">
        <div className="dd-sv__empty">No sources</div>
      </div>
    );
  }

  const selectedSource = selectedIdx !== null ? sources[selectedIdx] : null;
  const showSourceList = sources.length > SOURCE_LIST_THRESHOLD;

  return (
    <div className="dd-sv" ref={containerRef}>
      <SpectrumView
        sources={sources}
        isMobile={isMobile}
        focusedIdx={focusedIdx}
        setFocusedIdx={setFocusedIdx}
        onPinHover={handlePinHover}
        onPinHoverEnd={handlePinHoverEnd}
        onPinTap={handlePinTap}
        selectedIdx={selectedIdx}
      />
      <TiltRow mean={mean} />
      <SpectrumAxis />

      {/* Mobile info bar — tap-to-select */}
      {isMobile && selectedSource && (
        <SourceInfoBar source={selectedSource} onDismiss={() => setSelectedIdx(null)} />
      )}

      {/* Compact source list — 12+ sources */}
      {showSourceList && <SourceList sources={sources} />}

      {/* Desktop tooltip — pointer-events:auto, hover bridge inside */}
      {!isMobile && tooltip && (
        <SpectrumTooltip
          data={tooltip}
          onEnter={cancelHide}
          onLeave={scheduleHide}
        />
      )}
    </div>
  );
}
