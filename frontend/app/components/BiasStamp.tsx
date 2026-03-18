"use client";

import { useState, useId, useRef, useEffect, useCallback } from "react";
import type { BiasScores } from "../lib/types";

interface BiasStampProps {
  scores: BiasScores;
  size?: "sm" | "lg";
}

/* ---------------------------------------------------------------------------
   BiasStamp — Newspaper-inspired bias indicator
   Compact circular stamp with colored ring (lean), inner letter (type),
   and rigor arc. Expands into a detailed bias card on hover/tap.
   --------------------------------------------------------------------------- */

/* ── Score-to-label mappings ─────────────────────────────────────────────── */

function getLeanLabel(v: number): string {
  if (v <= 20) return "Far Left";
  if (v <= 35) return "Left";
  if (v <= 45) return "Center-Left";
  if (v <= 55) return "Center";
  if (v <= 65) return "Center-Right";
  if (v <= 80) return "Right";
  return "Far Right";
}

function getSensationalismLabel(v: number): string {
  if (v <= 25) return "Measured";
  if (v <= 50) return "Moderate";
  if (v <= 75) return "Sensational";
  return "Inflammatory";
}

function getTypeLabel(v: number): string {
  if (v <= 25) return "Reporting";
  if (v <= 50) return "Analysis";
  if (v <= 75) return "Opinion";
  return "Editorial";
}

function getTypeLetter(v: number): string {
  if (v <= 25) return "R";
  if (v <= 50) return "A";
  if (v <= 75) return "O";
  return "E";
}

function getRigorLabel(v: number): string {
  if (v <= 25) return "Poorly sourced";
  if (v <= 50) return "Some sourcing";
  if (v <= 75) return "Well-sourced";
  return "Heavily sourced";
}

function getFramingLabel(v: number): string {
  if (v <= 25) return "Neutral";
  if (v <= 50) return "Slight framing";
  if (v <= 75) return "Notable framing";
  return "Heavy framing";
}

/* ── Cached CSS variable reader ──────────────────────────────────────────── */

/** Module-level cache for bias CSS custom properties. Read once, reuse. */
let cssVarCache: Record<string, string> | null = null;

function getBiasColors(): Record<string, string> {
  if (cssVarCache) return cssVarCache;
  if (typeof document === "undefined") {
    // SSR fallback
    return {
      "--bias-left": "#3B82F6",
      "--bias-center-left": "#60A5FA",
      "--bias-center": "#9CA3AF",
      "--bias-center-right": "#F97316",
      "--bias-right": "#EF4444",
      "--rigor-high": "#22C55E",
      "--rigor-medium": "#EAB308",
      "--rigor-low": "#EF4444",
      "--sense-low": "#22C55E",
      "--sense-medium": "#EAB308",
      "--sense-high": "#EF4444",
    };
  }

  const style = getComputedStyle(document.documentElement);
  const vars = [
    "--bias-left", "--bias-center-left", "--bias-center",
    "--bias-center-right", "--bias-right",
    "--rigor-high", "--rigor-medium", "--rigor-low",
    "--sense-low", "--sense-medium", "--sense-high",
  ];

  cssVarCache = {};
  for (const v of vars) {
    cssVarCache[v] = style.getPropertyValue(v).trim() || {
      "--bias-left": "#3B82F6",
      "--bias-center-left": "#60A5FA",
      "--bias-center": "#9CA3AF",
      "--bias-center-right": "#F97316",
      "--bias-right": "#EF4444",
      "--rigor-high": "#22C55E",
      "--rigor-medium": "#EAB308",
      "--rigor-low": "#EF4444",
      "--sense-low": "#22C55E",
      "--sense-medium": "#EAB308",
      "--sense-high": "#EF4444",
    }[v]!;
  }
  return cssVarCache;
}

/** Invalidate cache on theme change */
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

/* ── Color computations ──────────────────────────────────────────────────── */

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

function getLeanColor(v: number): string {
  const c = getBiasColors();
  const left = c["--bias-left"];
  const centerLeft = c["--bias-center-left"];
  const center = c["--bias-center"];
  const centerRight = c["--bias-center-right"];
  const right = c["--bias-right"];

  if (v <= 20) return left;
  if (v <= 35) return lerpColor(left, centerLeft, (v - 20) / 15);
  if (v <= 45) return centerLeft;
  if (v <= 55) return center;
  if (v <= 65) return centerRight;
  if (v <= 80) return lerpColor(centerRight, right, (v - 65) / 15);
  return right;
}

function getRigorColor(v: number): string {
  const c = getBiasColors();
  if (v >= 60) return c["--rigor-high"];
  if (v >= 30) return c["--rigor-medium"];
  return c["--rigor-low"];
}

function getSensationalismColor(v: number): string {
  const c = getBiasColors();
  if (v <= 25) return c["--sense-low"];
  if (v <= 50) return c["--sense-medium"];
  return c["--sense-high"];
}

function getFramingColor(v: number): string {
  const c = getBiasColors();
  if (v <= 25) return c["--sense-low"];
  if (v <= 50) return c["--sense-medium"];
  return c["--sense-high"];
}

function getRingThickness(lean: number): number {
  const distance = Math.abs(lean - 50);
  return 2 + (distance / 50) * 1.5;
}

/* ── SVG arc helper ──────────────────────────────────────────────────────── */

function describeArc(cx: number, cy: number, r: number, startAngle: number, endAngle: number): string {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArc = endAngle - startAngle <= 180 ? "0" : "1";
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

/* ── Component ───────────────────────────────────────────────────────────── */

export default function BiasStamp({ scores, size = "sm" }: BiasStampProps) {
  const [expanded, setExpanded] = useState(false);
  const [animated, setAnimated] = useState(false);
  const [barAnimated, setBarAnimated] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const leaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const expandedId = `bias-card-${useId()}`;

  const stampSize = size === "lg" ? 36 : 32;

  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 50);
    return () => clearTimeout(t);
  }, []);

  useEffect(() => {
    const t = setTimeout(() => setBarAnimated(expanded), expanded ? 60 : 0);
    return () => clearTimeout(t);
  }, [expanded]);

  useEffect(() => {
    return () => {
      if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current);
    };
  }, []);

  useEffect(() => {
    if (!expanded) return;
    function handleOutsideClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setExpanded(false);
      }
    }
    document.addEventListener("click", handleOutsideClick, true);
    return () => document.removeEventListener("click", handleOutsideClick, true);
  }, [expanded]);

  const handleMouseEnter = useCallback(() => {
    if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current);
    setExpanded(true);
  }, []);

  const handleMouseLeave = useCallback(() => {
    leaveTimerRef.current = setTimeout(() => setExpanded(false), 200);
  }, []);

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setExpanded((prev) => !prev);
  }, []);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      setExpanded((prev) => !prev);
    }
    if (e.key === "Escape") setExpanded(false);
  }, []);

  const handleFocus = useCallback(() => setExpanded(true), []);
  const handleBlur = useCallback((e: React.FocusEvent) => {
    if (containerRef.current && !containerRef.current.contains(e.relatedTarget as Node)) {
      setExpanded(false);
    }
  }, []);

  const leanColor = getLeanColor(scores.politicalLean);
  const ringThickness = getRingThickness(scores.politicalLean);
  const typeLetter = getTypeLetter(scores.opinionFact);
  const rigorColor = getRigorColor(scores.factualRigor);

  const arcSweep = (scores.factualRigor / 100) * 120;
  const arcStart = 210 - arcSweep / 2;
  const arcEnd = 210 + arcSweep / 2;
  const arcR = stampSize / 2 + 3;

  const ariaLabel = `Bias: ${getLeanLabel(scores.politicalLean)} lean, ${getTypeLabel(scores.opinionFact)}, ${getRigorLabel(scores.factualRigor)}, ${getSensationalismLabel(scores.sensationalism)} tone, ${getFramingLabel(scores.framing)}`;

  return (
    <div
      ref={containerRef}
      className="bias-stamp"
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onFocus={handleFocus}
      onBlur={handleBlur}
    >
      {/* ── Stamp ─────────────────────────────────────────────────────── */}
      <div
        role="img"
        aria-label={ariaLabel}
        aria-describedby={expanded ? expandedId : undefined}
        tabIndex={0}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        className="bias-stamp__circle"
        style={{
          width: stampSize,
          height: stampSize,
          transform: animated ? "scale(1)" : "scale(0.9)",
          opacity: animated ? 1 : 0,
          transition: "transform 200ms var(--ease-out), opacity 200ms var(--ease-out)",
        }}
      >
        {/* Colored ring (lean) */}
        <div
          className="bias-stamp__ring"
          style={{ border: `${ringThickness}px solid ${leanColor}` }}
        />

        {/* Inner letter (type) */}
        <span
          className="bias-stamp__letter"
          style={{ fontSize: size === "lg" ? "var(--text-sm)" : "var(--text-xs)" }}
        >
          {typeLetter}
        </span>

        {/* Rigor arc (below stamp) */}
        <svg
          width={stampSize + 8}
          height={12}
          viewBox={`0 0 ${stampSize + 8} 12`}
          style={{ position: "absolute", bottom: -8, left: -4, overflow: "visible" }}
          aria-hidden="true"
        >
          <path
            d={describeArc((stampSize + 8) / 2, -stampSize / 2 + 6, arcR, 150, 210 + 60)}
            fill="none"
            stroke="var(--border-subtle)"
            strokeWidth="2"
            strokeLinecap="round"
          />
          {arcSweep > 0 && (
            <path
              d={describeArc((stampSize + 8) / 2, -stampSize / 2 + 6, arcR, arcStart, arcEnd)}
              fill="none"
              stroke={rigorColor}
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          )}
        </svg>

        {/* Type label */}
        <span className="bias-stamp__type-label">
          {getTypeLabel(scores.opinionFact)}
        </span>
      </div>

      {/* ── Expanded Bias Card ────────────────────────────────────────── */}
      {expanded && (
        <div
          id={expandedId}
          role="tooltip"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          className="bias-stamp__expanded anim-fade-in"
          style={{ left: stampSize + 8 }}
        >
          <div className="bias-stamp__expanded-header">Bias Analysis</div>

          {/* Lean spectrum */}
          <div className="bias-row">
            <div className="bias-row__label">Lean</div>
            <LeanSpectrum value={scores.politicalLean} animated={barAnimated} />
            <div className="bias-row__value">{getLeanLabel(scores.politicalLean)}</div>
          </div>

          {/* Rigor bar */}
          <div className="bias-row">
            <div className="bias-row__label">Rigor</div>
            <ProgressBar value={scores.factualRigor} color={getRigorColor(scores.factualRigor)} animated={barAnimated} delay={40} />
            <div className="bias-row__value">{getRigorLabel(scores.factualRigor)}</div>
          </div>

          {/* Tone */}
          <div className="bias-row">
            <div className="bias-row__label">Tone</div>
            <ProgressBar value={100 - scores.sensationalism} color={getSensationalismColor(scores.sensationalism)} animated={barAnimated} delay={80} />
            <div className="bias-row__value">{getSensationalismLabel(scores.sensationalism)}</div>
          </div>

          {/* Type badge */}
          <div className="bias-row">
            <div className="bias-row__label">Type</div>
            <span className="type-badge">{getTypeLabel(scores.opinionFact)}</span>
          </div>

          {/* Framing bar */}
          <div className="bias-row">
            <div className="bias-row__label">Framing</div>
            <ProgressBar value={100 - scores.framing} color={getFramingColor(scores.framing)} animated={barAnimated} delay={120} />
            <div className="bias-row__value">{getFramingLabel(scores.framing)}</div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────────────────────────── */

function LeanSpectrum({ value, animated }: { value: number; animated: boolean }) {
  const pct = Math.max(0, Math.min(100, value));
  const dotColor = getLeanColor(value);

  return (
    <div style={{ position: "relative", height: 12, display: "flex", alignItems: "center" }}>
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          height: 2,
          background: "linear-gradient(to right, var(--bias-left), var(--bias-center) 50%, var(--bias-right))",
          borderRadius: 1,
          opacity: 0.35,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: animated ? `${pct}%` : "50%",
          top: "50%",
          width: 8,
          height: 8,
          borderRadius: "50%",
          backgroundColor: dotColor,
          transform: "translate(-50%, -50%)",
          transition: "left 200ms var(--ease-out)",
          boxShadow: "0 0 0 2px var(--bg-card)",
        }}
      />
    </div>
  );
}

function ProgressBar({ value, color, animated, delay = 0 }: { value: number; color: string; animated: boolean; delay?: number }) {
  const pct = Math.max(0, Math.min(100, value));

  return (
    <div className="progress-bar">
      <div className="progress-bar__track">
        <div
          className="progress-bar__fill"
          style={{
            width: animated ? `${pct}%` : "0%",
            backgroundColor: color,
            transitionDelay: `${delay}ms`,
          }}
        />
      </div>
      <span className="progress-bar__label">{pct}%</span>
    </div>
  );
}
