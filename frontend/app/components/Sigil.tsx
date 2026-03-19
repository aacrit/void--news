"use client";

import { useState, useRef, useEffect, useCallback, useId } from "react";
import { createPortal } from "react-dom";
import type { SigilData, BiasSpread } from "../lib/types";

/* ==========================================================================
   Sigil — Unified 6-Axis Bias Indicator

   A compact hexagonal glyph that encodes 6 bias dimensions via colored edge
   segments. On hover/tap, a portal popup reveals a full radar chart with
   animated score reveals, spread shadows, and axis legends.

   Axes (clockwise from top):
     0. Political Lean    — blue-gray-red
     1. Sensationalism    — green-yellow-red
     2. Opinion/Reporting — blue-purple-orange
     3. Factual Rigor     — red-yellow-green (inverted: high=good)
     4. Framing           — green-yellow-red
     5. Source Agreement   — green-yellow-red (low divergence=good)
   ========================================================================== */

interface SigilProps {
  data: SigilData;
  size?: "sm" | "lg";
}

/* ── Axis definitions ──────────────────────────────────────────────────── */

const AXIS_COUNT = 6;
const AXES = [
  { key: "lean",           label: "Lean",       shortLabel: "L" },
  { key: "sensationalism", label: "Sensation",  shortLabel: "S" },
  { key: "opinion",        label: "Opinion",    shortLabel: "O" },
  { key: "rigor",          label: "Rigor",      shortLabel: "R" },
  { key: "framing",        label: "Framing",    shortLabel: "F" },
  { key: "agreement",      label: "Agreement",  shortLabel: "A" },
] as const;

/* ── Geometry helpers ──────────────────────────────────────────────────── */

function hexVertex(cx: number, cy: number, r: number, i: number): [number, number] {
  const angle = (-Math.PI / 2) + (i * Math.PI * 2) / AXIS_COUNT;
  return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
}

function hexPoints(cx: number, cy: number, r: number): string {
  return Array.from({ length: AXIS_COUNT }, (_, i) =>
    hexVertex(cx, cy, r, i).map(v => v.toFixed(2)).join(",")
  ).join(" ");
}

function radarVertex(
  cx: number, cy: number, rMax: number, score: number, i: number
): [number, number] {
  const norm = Math.max(0.08, score / 100); // min 8% so polygon is always visible
  return hexVertex(cx, cy, rMax * norm, i);
}

function radarPoints(cx: number, cy: number, rMax: number, scores: number[]): string {
  return scores.map((s, i) =>
    radarVertex(cx, cy, rMax, s, i).map(v => v.toFixed(2)).join(",")
  ).join(" ");
}

/* ── Cached CSS variable reader (shared pattern from BiasLens) ─────────── */

let cssVarCache: Record<string, string> | null = null;

const SSR_FALLBACK: Record<string, string> = {
  "--bias-left": "#3B82F6",
  "--bias-center-left": "#60A5FA",
  "--bias-center": "#9CA3AF",
  "--bias-center-right": "#F97316",
  "--bias-right": "#EF4444",
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

function getColors(): Record<string, string> {
  if (cssVarCache) return cssVarCache;
  if (typeof document === "undefined") return SSR_FALLBACK;
  const style = getComputedStyle(document.documentElement);
  cssVarCache = {};
  for (const v of Object.keys(SSR_FALLBACK)) {
    cssVarCache[v] = style.getPropertyValue(v).trim() || SSR_FALLBACK[v];
  }
  return cssVarCache;
}

if (typeof window !== "undefined") {
  const observer = new MutationObserver((mutations) => {
    for (const m of mutations) {
      if (m.type === "attributes" && m.attributeName === "data-mode") {
        cssVarCache = null;
      }
    }
  });
  observer.observe(document.documentElement, { attributes: true, attributeFilter: ["data-mode"] });
}

/* ── Color interpolation ──────────────────────────────────────────────── */

function lerpColor(a: string, b: string, t: number): string {
  const ah = parseInt(a.slice(1), 16);
  const bh = parseInt(b.slice(1), 16);
  const ar = (ah >> 16) & 0xff, ag = (ah >> 8) & 0xff, ab = ah & 0xff;
  const br = (bh >> 16) & 0xff, bg = (bh >> 8) & 0xff, bb = bh & 0xff;
  const rr = Math.round(ar + (br - ar) * t);
  const rg = Math.round(ag + (bg - ag) * t);
  const rb = Math.round(ab + (bb - ab) * t);
  return `#${((rr << 16) | (rg << 8) | rb).toString(16).padStart(6, "0")}`;
}

/* ── Per-axis color functions ─────────────────────────────────────────── */

function getLeanColor(v: number): string {
  const c = getColors();
  if (v <= 20) return c["--bias-left"];
  if (v <= 35) return lerpColor(c["--bias-left"], c["--bias-center-left"], (v - 20) / 15);
  if (v <= 45) return c["--bias-center-left"];
  if (v <= 55) return c["--bias-center"];
  if (v <= 65) return c["--bias-center-right"];
  if (v <= 80) return lerpColor(c["--bias-center-right"], c["--bias-right"], (v - 65) / 15);
  return c["--bias-right"];
}

function getSensationalismColor(v: number): string {
  const c = getColors();
  if (v <= 30) return c["--sense-low"];
  if (v <= 60) return lerpColor(c["--sense-low"], c["--sense-medium"], (v - 30) / 30);
  if (v <= 80) return lerpColor(c["--sense-medium"], c["--sense-high"], (v - 60) / 20);
  return c["--sense-high"];
}

function getOpinionColor(v: number): string {
  const c = getColors();
  if (v <= 25) return c["--type-reporting"];
  if (v <= 50) return lerpColor(c["--type-reporting"], c["--type-analysis"], (v - 25) / 25);
  if (v <= 75) return lerpColor(c["--type-analysis"], c["--type-opinion"], (v - 50) / 25);
  return c["--type-opinion"];
}

function getFactualRigorColor(v: number): string {
  const c = getColors();
  if (v >= 70) return c["--rigor-high"];
  if (v >= 40) return lerpColor(c["--rigor-medium"], c["--rigor-high"], (v - 40) / 30);
  if (v >= 20) return lerpColor(c["--rigor-low"], c["--rigor-medium"], (v - 20) / 20);
  return c["--rigor-low"];
}

function getFramingColor(v: number): string {
  const c = getColors();
  if (v <= 25) return c["--sense-low"];
  if (v <= 55) return lerpColor(c["--sense-low"], c["--sense-medium"], (v - 25) / 30);
  if (v <= 80) return lerpColor(c["--sense-medium"], c["--sense-high"], (v - 55) / 25);
  return c["--sense-high"];
}

function getAgreementColor(v: number): string {
  const c = getColors();
  if (v <= 25) return c["--sense-low"];
  if (v <= 55) return lerpColor(c["--sense-low"], c["--sense-medium"], (v - 25) / 30);
  if (v <= 80) return lerpColor(c["--sense-medium"], c["--sense-high"], (v - 55) / 25);
  return c["--sense-high"];
}

const AXIS_COLOR_FNS = [
  getLeanColor,
  getSensationalismColor,
  getOpinionColor,
  getFactualRigorColor,
  getFramingColor,
  getAgreementColor,
];

/* ── Label helpers ─────────────────────────────────────────────────────── */

function getLeanLabel(v: number): string {
  if (v <= 20) return "Far Left";
  if (v <= 35) return "Left";
  if (v <= 45) return "Center-Left";
  if (v <= 55) return "Center";
  if (v <= 65) return "Center-Right";
  if (v <= 80) return "Right";
  return "Far Right";
}

function getSensLabel(v: number): string {
  if (v <= 25) return "Measured";
  if (v <= 50) return "Moderate";
  if (v <= 75) return "Elevated";
  return "Inflammatory";
}

function getRigorLabel(v: number): string {
  if (v >= 70) return "High rigor";
  if (v >= 40) return "Moderate";
  return "Low rigor";
}

function getFrameLabel(v: number): string {
  if (v <= 25) return "Neutral";
  if (v <= 55) return "Some framing";
  return "Heavy framing";
}

function getAgreeLabel(v: number): string {
  if (v <= 25) return "Sources agree";
  if (v <= 55) return "Mixed views";
  return "High disagreement";
}

/* ── Composite grade ───────────────────────────────────────────────────── */

function computeGrade(data: SigilData): string {
  const rigorNorm = data.factualRigor / 100;
  const senseNorm = 1 - data.sensationalism / 100;
  const frameNorm = 1 - data.framing / 100;
  const agreeNorm = 1 - data.agreement / 100;
  const leanNorm = 1 - Math.abs(data.politicalLean - 50) / 50;
  const opinNorm = data.opinionFact <= 50 ? 1 - data.opinionFact / 100 : 0.5;

  const composite =
    rigorNorm * 0.25 +
    senseNorm * 0.20 +
    frameNorm * 0.15 +
    agreeNorm * 0.15 +
    leanNorm * 0.10 +
    opinNorm * 0.15;

  if (composite >= 0.82) return "A";
  if (composite >= 0.68) return "B";
  if (composite >= 0.52) return "C";
  if (composite >= 0.38) return "D";
  return "F";
}

function getGradeColor(grade: string): string {
  const c = getColors();
  switch (grade) {
    case "A": return c["--sense-low"];
    case "B": return c["--rigor-high"];
    case "C": return c["--sense-medium"];
    case "D": return c["--sense-high"];
    case "F": return c["--bias-right"];
    default:  return c["--bias-center"];
  }
}

/* ── Extract scores array from SigilData ──────────────────────────────── */

function getScores(data: SigilData): number[] {
  return [
    data.politicalLean,
    data.sensationalism,
    data.opinionFact,
    data.factualRigor,
    data.framing,
    data.agreement,
  ];
}

function getAxisLabels(data: SigilData): string[] {
  return [
    getLeanLabel(data.politicalLean),
    getSensLabel(data.sensationalism),
    data.opinionLabel,
    getRigorLabel(data.factualRigor),
    getFrameLabel(data.framing),
    getAgreeLabel(data.agreement),
  ];
}

/* ── Interaction hook (reused from BiasLens pattern) ───────────────────── */

function useSigilInteraction() {
  const [open, setOpen] = useState(false);
  const leaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback(() => {
    if (leaveTimer.current) clearTimeout(leaveTimer.current);
    setOpen(true);
  }, []);

  const hide = useCallback(() => {
    leaveTimer.current = setTimeout(() => setOpen(false), 250);
  }, []);

  const toggle = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setOpen((v) => !v);
  }, []);

  const onKey = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setOpen((v) => !v); }
    if (e.key === "Escape") setOpen(false);
  }, []);

  const keepOpen = useCallback(() => {
    if (leaveTimer.current) clearTimeout(leaveTimer.current);
  }, []);

  useEffect(() => () => { if (leaveTimer.current) clearTimeout(leaveTimer.current); }, []);

  return { open, show, hide, toggle, onKey, keepOpen, setOpen };
}

/* ── Count-up hook ─────────────────────────────────────────────────────── */

function useCountUp(target: number, duration: number, active: boolean): number {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!active) { setValue(0); return; }
    const start = performance.now();
    let raf: number;
    function tick(now: number) {
      const elapsed = now - start;
      const t = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      setValue(Math.round(eased * target));
      if (t < 1) raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, duration, active]);
  return value;
}

/* ── Radar popup ──────────────────────────────────────────────────────── */

interface SigilPopupProps {
  triggerRef: React.RefObject<HTMLElement | null>;
  isOpen: boolean;
  onClose: () => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  id: string;
  data: SigilData;
}

function SigilPopup({ triggerRef, isOpen, onClose, onMouseEnter, onMouseLeave, id, data }: SigilPopupProps) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const [revealed, setRevealed] = useState(false);

  const scores = getScores(data);
  const labels = getAxisLabels(data);
  const grade = computeGrade(data);
  const gradeColor = getGradeColor(grade);

  // Position popup adjacent to trigger
  useEffect(() => {
    if (!isOpen || !triggerRef.current) { setRevealed(false); return; }
    const rect = triggerRef.current.getBoundingClientRect();
    const popupW = 320;
    const popupH = 400;
    const spaceRight = window.innerWidth - rect.right;
    const spaceLeft = rect.left;
    let x: number;
    if (spaceRight > popupW + 16) {
      x = rect.right + 10;
    } else if (spaceLeft > popupW + 16) {
      x = rect.left - popupW - 10;
    } else {
      x = Math.max(8, (window.innerWidth - popupW) / 2);
    }
    const y = Math.max(8, Math.min(rect.top - 40, window.innerHeight - popupH - 16));
    setPos({ x, y });
    // Delay reveal for clip-path animation
    requestAnimationFrame(() => requestAnimationFrame(() => setRevealed(true)));
  }, [isOpen, triggerRef]);

  // Close on outside click
  useEffect(() => {
    if (!isOpen) return;
    function handleClick(e: MouseEvent) {
      if (triggerRef.current && !triggerRef.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("click", handleClick, true);
    return () => document.removeEventListener("click", handleClick, true);
  }, [isOpen, onClose, triggerRef]);

  if (!isOpen || !pos || typeof document === "undefined") return null;

  const RCX = 110, RCY = 110, R_MAX = 85;

  return createPortal(
    <div
      id={id}
      role="tooltip"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{
        position: "fixed",
        top: pos.y,
        left: pos.x,
        width: 320,
        background: "var(--bg-card)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "var(--shadow-e3)",
        zIndex: 9999,
        padding: "12px 16px 16px",
        animation: "sigilPopupIn 300ms var(--spring) both",
        pointerEvents: "auto",
      }}
    >
      {/* Header */}
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        paddingBottom: 8,
        borderBottom: "1px solid var(--border-subtle)",
        marginBottom: 12,
      }}>
        <span style={{
          fontFamily: "var(--font-data)",
          fontSize: "var(--text-xs)",
          fontWeight: 500,
          letterSpacing: "0.06em",
          textTransform: "uppercase" as const,
          color: "var(--fg-tertiary)",
        }}>
          Bias Analysis
        </span>
        <span style={{
          fontFamily: "var(--font-data)",
          fontSize: 16,
          fontWeight: 700,
          color: gradeColor,
        }}>
          {grade}
        </span>
      </div>

      {/* Radar chart */}
      <svg
        viewBox={`0 0 ${RCX * 2} ${RCY * 2}`}
        width="100%"
        height="auto"
        style={{ display: "block", maxWidth: 288, margin: "0 auto" }}
        aria-hidden="true"
      >
        <defs>
          <filter id="sigil-spread-blur">
            <feGaussianBlur stdDeviation="4" />
          </filter>
        </defs>

        {/* Background grid — 3 concentric hexagons */}
        {[0.33, 0.66, 1].map((scale) => (
          <polygon
            key={scale}
            points={hexPoints(RCX, RCY, R_MAX * scale)}
            fill="none"
            stroke="var(--border-subtle)"
            strokeWidth={0.5}
            opacity={0.25}
          />
        ))}

        {/* Axis spokes */}
        {Array.from({ length: AXIS_COUNT }, (_, i) => {
          const [ox, oy] = hexVertex(RCX, RCY, R_MAX, i);
          return (
            <line
              key={`spoke-${i}`}
              x1={RCX} y1={RCY}
              x2={ox} y2={oy}
              stroke="var(--border-subtle)"
              strokeWidth={0.5}
              opacity={0.2}
            />
          );
        })}

        {/* Spread shadow polygon (disagreement range) */}
        {data.biasSpread && (
          <SigilSpreadPolygon
            cx={RCX} cy={RCY} rMax={R_MAX}
            scores={scores}
            spread={data.biasSpread}
            revealed={revealed}
          />
        )}

        {/* Data polygon — clip-path reveal animation */}
        <g style={{
          clipPath: revealed ? `circle(60% at 50% 50%)` : `circle(0% at 50% 50%)`,
          transition: "clip-path 500ms var(--spring)",
        }}>
          <polygon
            points={radarPoints(RCX, RCY, R_MAX, scores)}
            fill={gradeColor}
            fillOpacity={0.12}
            stroke={gradeColor}
            strokeWidth={1.5}
            strokeOpacity={0.6}
            strokeLinejoin="round"
          />
        </g>

        {/* Vertex dots */}
        {scores.map((s, i) => {
          const [vx, vy] = radarVertex(RCX, RCY, R_MAX, s, i);
          const color = AXIS_COLOR_FNS[i](s);
          return (
            <circle
              key={`dot-${i}`}
              cx={vx} cy={vy}
              r={4}
              fill={color}
              style={{
                opacity: revealed ? 1 : 0,
                transition: `opacity 300ms var(--ease-out) ${i * 50}ms`,
              }}
            />
          );
        })}

        {/* Axis labels at outer ring */}
        {AXES.map((axis, i) => {
          const [lx, ly] = hexVertex(RCX, RCY, R_MAX + 16, i);
          const anchor = lx < RCX - 5 ? "end" : lx > RCX + 5 ? "start" : "middle";
          return (
            <text
              key={`label-${i}`}
              x={lx} y={ly + 4}
              textAnchor={anchor}
              style={{
                fontFamily: "var(--font-structural)",
                fontSize: 10,
                fill: "var(--fg-tertiary)",
                opacity: revealed ? 1 : 0,
                transition: `opacity 300ms var(--ease-out) ${100 + i * 50}ms`,
              }}
            >
              {axis.label}
            </text>
          );
        })}

        {/* Score values near each vertex */}
        {scores.map((s, i) => {
          const [vx, vy] = radarVertex(RCX, RCY, R_MAX, s, i);
          // Offset score labels outward from the vertex
          const [ox, oy] = hexVertex(RCX, RCY, 12, i);
          const anchor = ox < 0 ? "end" : ox > 0 ? "start" : "middle";
          const color = AXIS_COLOR_FNS[i](s);
          return (
            <SigilScoreLabel
              key={`score-${i}`}
              x={vx + ox * 0.15}
              y={vy + oy * 0.15 - 6}
              target={s}
              color={color}
              anchor={anchor}
              revealed={revealed}
              delay={150 + i * 60}
            />
          );
        })}
      </svg>

      {/* Legend */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "1fr 1fr",
        gap: "4px 12px",
        marginTop: 8,
      }}>
        {AXES.map((axis, i) => {
          const color = AXIS_COLOR_FNS[i](scores[i]);
          return (
            <div key={axis.key} style={{
              display: "flex",
              alignItems: "center",
              gap: 6,
              opacity: revealed ? 1 : 0,
              transition: `opacity 300ms var(--ease-out) ${200 + i * 40}ms`,
            }}>
              <div style={{
                width: 8, height: 8,
                borderRadius: 1,
                backgroundColor: color,
                flexShrink: 0,
              }} />
              <span style={{
                fontFamily: "var(--font-structural)",
                fontSize: "var(--text-xs)",
                color: "var(--fg-tertiary)",
                lineHeight: 1.4,
              }}>
                {axis.label}:{" "}
                <span style={{ color: "var(--fg-secondary)", fontWeight: 500 }}>
                  {labels[i]}
                </span>
              </span>
            </div>
          );
        })}
      </div>

      {/* Source count footer */}
      <div style={{
        marginTop: 10,
        paddingTop: 8,
        borderTop: "1px solid var(--border-subtle)",
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
      }}>
        <span style={{
          fontFamily: "var(--font-data)",
          fontSize: "var(--text-xs)",
          color: "var(--fg-tertiary)",
        }}>
          {data.sourceCount} source{data.sourceCount !== 1 ? "s" : ""}
        </span>
        {data.tierBreakdown && (
          <div style={{ display: "flex", gap: 6 }}>
            {Object.entries(data.tierBreakdown).map(([tier, count]) =>
              (count as number) > 0 ? (
                <span key={tier} style={{
                  fontFamily: "var(--font-data)",
                  fontSize: 9,
                  padding: "1px 4px",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: 2,
                  color: "var(--fg-tertiary)",
                }}>
                  {tier === "us_major" ? "US" : tier === "international" ? "Intl" : "Ind"}: {count as number}
                </span>
              ) : null
            )}
          </div>
        )}
      </div>
    </div>,
    document.body,
  );
}

/* ── Spread polygon sub-component ─────────────────────────────────────── */

function SigilSpreadPolygon({ cx, cy, rMax, scores, spread, revealed }: {
  cx: number; cy: number; rMax: number;
  scores: number[]; spread: BiasSpread; revealed: boolean;
}) {
  // Build outer polygon using score + half spread
  const spreadValues = [
    spread.leanSpread ?? 0,
    spread.sensationalismSpread ?? 0,
    spread.opinionSpread ?? 0,
    0, // no factual rigor spread in BiasSpread
    spread.framingSpread ?? 0,
    0, // no agreement spread
  ];

  const outerScores = scores.map((s, i) => Math.min(100, s + spreadValues[i] / 2));
  const innerScores = scores.map((s, i) => Math.max(0, s - spreadValues[i] / 2));

  const hasSpread = spreadValues.some(v => v > 5);
  if (!hasSpread) return null;

  return (
    <g style={{
      opacity: revealed ? 1 : 0,
      transition: "opacity 400ms var(--ease-out) 200ms",
    }}>
      <polygon
        points={radarPoints(cx, cy, rMax, outerScores)}
        fill="var(--fg-muted)"
        fillOpacity={0.06}
        stroke="none"
        filter="url(#sigil-spread-blur)"
      />
      <polygon
        points={radarPoints(cx, cy, rMax, innerScores)}
        fill="var(--bg-card)"
        fillOpacity={0.5}
        stroke="none"
        filter="url(#sigil-spread-blur)"
      />
    </g>
  );
}

/* ── Animated score label ──────────────────────────────────────────────── */

function SigilScoreLabel({ x, y, target, color, anchor, revealed, delay }: {
  x: number; y: number; target: number; color: string;
  anchor: "start" | "middle" | "end"; revealed: boolean; delay: number;
}) {
  const value = useCountUp(target, 500, revealed);
  return (
    <text
      x={x} y={y}
      textAnchor={anchor}
      style={{
        fontFamily: "var(--font-data)",
        fontSize: 11,
        fontWeight: 600,
        fill: color,
        opacity: revealed ? 1 : 0,
        transition: `opacity 250ms var(--ease-out) ${delay}ms`,
      }}
    >
      {value}
    </text>
  );
}

/* ── Main Sigil component ─────────────────────────────────────────────── */

export default function Sigil({ data, size = "sm" }: SigilProps) {
  const ref = useRef<HTMLDivElement>(null);
  const { open, show, hide, toggle, onKey, keepOpen } = useSigilInteraction();
  const [mounted, setMounted] = useState(false);
  const tooltipId = `sigil-${useId()}`;

  const scores = getScores(data);
  const grade = computeGrade(data);
  const gradeColor = getGradeColor(grade);
  const labels = getAxisLabels(data);

  const dim = size === "lg" ? 56 : 40;
  const vb = size === "lg" ? 64 : 48;
  const cx = vb / 2, cy = vb / 2;
  const R = size === "lg" ? 28 : 20;
  const strokeW = size === "lg" ? 3.5 : 2.5;
  const gradeSize = size === "lg" ? 15 : 11;

  // Entrance animation
  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 60);
    return () => clearTimeout(t);
  }, []);

  // Divergence pulse intensity
  const showPulse = data.agreement > 30;
  const pulseSpeed = 3 - (data.agreement / 100) * 1.5; // 1.5s fast - 3s slow

  const ariaLabel = `Bias grade ${grade}. ${AXES.map((a, i) => `${a.label}: ${labels[i]} (${scores[i]})`).join(". ")}. ${data.sourceCount} sources. Press Enter for details.`;

  return (
    <div
      ref={ref}
      className="sigil"
      onMouseEnter={show}
      onFocus={show}
      onMouseLeave={hide}
      onBlur={hide}
      onClick={toggle}
      onKeyDown={onKey}
      tabIndex={0}
      role="button"
      aria-expanded={open}
      aria-label={ariaLabel}
      aria-controls={open ? tooltipId : undefined}
      style={{
        width: Math.max(44, dim),
        height: Math.max(44, dim),
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "pointer",
        position: "relative",
        opacity: data.pending ? 0.35 : 1,
        filter: data.pending ? "grayscale(1)" : "none",
        transition: "opacity 300ms var(--ease-out), filter 300ms var(--ease-out)",
      }}
    >
      <svg
        viewBox={`0 0 ${vb} ${vb}`}
        width={dim}
        height={dim}
        style={{
          animation: mounted ? undefined : "sigilHexIn 450ms var(--spring) both",
        }}
      >
        {/* Divergence pulse glow */}
        {showPulse && (
          <circle
            cx={cx} cy={cy}
            r={R + 2}
            fill="none"
            stroke={getAgreementColor(data.agreement)}
            strokeWidth={1}
            opacity={0.25}
            style={{
              transformOrigin: "center",
              animation: `sigilPulse ${pulseSpeed}s ease-in-out infinite`,
            }}
          />
        )}

        {/* Hex outline (subtle reference) */}
        <polygon
          points={hexPoints(cx, cy, R)}
          fill="none"
          stroke="var(--border-subtle)"
          strokeWidth={0.5}
          opacity={0.3}
        />

        {/* 6 colored edge segments */}
        {Array.from({ length: AXIS_COUNT }, (_, i) => {
          const [x1, y1] = hexVertex(cx, cy, R, i);
          const [x2, y2] = hexVertex(cx, cy, R, (i + 1) % AXIS_COUNT);
          const color = AXIS_COLOR_FNS[i](scores[i]);
          // Opacity encodes score intensity
          const intensity = i === 3
            ? 0.4 + (scores[i] / 100) * 0.6        // rigor: high=bright
            : 0.4 + ((100 - scores[i]) / 100) * 0.6; // others: low=bright (good)
          // For lean: center is good, so intensity is different
          const edgeOpacity = i === 0
            ? 0.4 + (1 - Math.abs(scores[0] - 50) / 50) * 0.6
            : i === 2
              ? 0.5 + (scores[2] <= 50 ? 0.5 : 0) // opinion: reporting=bright
              : intensity;

          return (
            <line
              key={`edge-${i}`}
              x1={x1} y1={y1}
              x2={x2} y2={y2}
              stroke={color}
              strokeWidth={strokeW}
              strokeLinecap="round"
              opacity={mounted ? edgeOpacity : 0.2}
              style={{
                transition: `stroke 300ms var(--ease-out), opacity 400ms var(--ease-out) ${i * 30}ms`,
              }}
            />
          );
        })}

        {/* Center grade letter */}
        <text
          x={cx}
          y={cy + gradeSize * 0.36}
          textAnchor="middle"
          style={{
            fontFamily: "var(--font-data)",
            fontSize: gradeSize,
            fontWeight: 700,
            fill: gradeColor,
            opacity: mounted ? 1 : 0,
            transition: "opacity 300ms var(--ease-out) 150ms, fill 300ms var(--ease-out)",
          }}
        >
          {grade}
        </text>
      </svg>

      {/* Pending label */}
      {data.pending && (
        <span style={{
          position: "absolute",
          bottom: -2,
          fontFamily: "var(--font-data)",
          fontSize: 7,
          fontWeight: 500,
          letterSpacing: "0.04em",
          textTransform: "uppercase" as const,
          color: "var(--fg-tertiary)",
          whiteSpace: "nowrap",
        }}>
          Pending
        </span>
      )}

      {/* Expanded radar popup */}
      <SigilPopup
        triggerRef={ref}
        isOpen={open}
        onClose={() => hide()}
        onMouseEnter={keepOpen}
        onMouseLeave={hide}
        id={tooltipId}
        data={data}
      />
    </div>
  );
}
