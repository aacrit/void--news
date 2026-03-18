"use client";

import { useState, useId, useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import type { BiasScores } from "../lib/types";

interface BiasStampProps {
  scores: BiasScores;
  size?: "sm" | "lg";
}

/* ---------------------------------------------------------------------------
   BiasStamp — "The Bias Pulse"

   Compact form: 5 thin vertical bars side by side, each representing one
   bias axis. Height encodes score intensity. Color encodes the value.
   Creates a unique "fingerprint" per article — no two stories look alike.

   Like an EKG or seismograph reading — you can see at a glance whether
   coverage is calm and centered, or volatile and extreme.

   Hover/tap expands a detailed card rendered via portal (fixed positioning)
   to avoid z-index and overflow clipping issues.
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

let cssVarCache: Record<string, string> | null = null;

const SSR_FALLBACK: Record<string, string> = {
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
  "--type-reporting": "#3B82F6",
  "--type-analysis": "#8B5CF6",
  "--type-opinion": "#F97316",
};

function getBiasColors(): Record<string, string> {
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
  if (v <= 20) return c["--bias-left"];
  if (v <= 35) return lerpColor(c["--bias-left"], c["--bias-center-left"], (v - 20) / 15);
  if (v <= 45) return c["--bias-center-left"];
  if (v <= 55) return c["--bias-center"];
  if (v <= 65) return c["--bias-center-right"];
  if (v <= 80) return lerpColor(c["--bias-center-right"], c["--bias-right"], (v - 65) / 15);
  return c["--bias-right"];
}

function getRigorColor(v: number): string {
  const c = getBiasColors();
  if (v >= 60) return c["--rigor-high"];
  if (v >= 30) return c["--rigor-medium"];
  return c["--rigor-low"];
}

function getToneColor(v: number): string {
  const c = getBiasColors();
  if (v <= 25) return c["--sense-low"];
  if (v <= 50) return c["--sense-medium"];
  return c["--sense-high"];
}

function getTypeColor(v: number): string {
  const c = getBiasColors();
  if (v <= 25) return c["--type-reporting"];
  if (v <= 50) return c["--type-analysis"];
  return c["--type-opinion"];
}

function getFramingColor(v: number): string {
  const c = getBiasColors();
  if (v <= 25) return c["--sense-low"];
  if (v <= 50) return c["--sense-medium"];
  return c["--sense-high"];
}

/* ── The 5 bars definition ───────────────────────────────────────────────── */

interface BarDef {
  key: string;
  label: string;
  value: number;       // 0-100, raw score
  intensity: number;   // 0-100, how "intense" for bar height (distance from ideal)
  color: string;
  labelText: string;
}

function getBars(scores: BiasScores): BarDef[] {
  // For each axis, "intensity" = how far from ideal.
  // Lean: distance from 50 (center). Rigor: inverted (low rigor = high bar).
  // Tone: sensationalism as-is. Type: opinion distance from 0. Framing: as-is.
  return [
    {
      key: "lean",
      label: "Lean",
      value: scores.politicalLean,
      intensity: Math.abs(scores.politicalLean - 50) * 2, // 0-100
      color: getLeanColor(scores.politicalLean),
      labelText: getLeanLabel(scores.politicalLean),
    },
    {
      key: "rigor",
      label: "Rigor",
      value: scores.factualRigor,
      intensity: 100 - scores.factualRigor, // Low rigor = tall bar (bad)
      color: getRigorColor(scores.factualRigor),
      labelText: getRigorLabel(scores.factualRigor),
    },
    {
      key: "tone",
      label: "Tone",
      value: scores.sensationalism,
      intensity: scores.sensationalism, // High sensationalism = tall bar
      color: getToneColor(scores.sensationalism),
      labelText: getSensationalismLabel(scores.sensationalism),
    },
    {
      key: "type",
      label: "Type",
      value: scores.opinionFact,
      intensity: scores.opinionFact, // More opinion = taller
      color: getTypeColor(scores.opinionFact),
      labelText: getTypeLabel(scores.opinionFact),
    },
    {
      key: "framing",
      label: "Framing",
      value: scores.framing,
      intensity: scores.framing, // More framing = taller
      color: getFramingColor(scores.framing),
      labelText: getFramingLabel(scores.framing),
    },
  ];
}

/* ── Component ───────────────────────────────────────────────────────────── */

export default function BiasStamp({ scores, size = "sm" }: BiasStampProps) {
  const [expanded, setExpanded] = useState(false);
  const [animated, setAnimated] = useState(false);
  const [barAnimated, setBarAnimated] = useState(false);
  const [tooltipPos, setTooltipPos] = useState<{ x: number; y: number } | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const leaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const expandedId = `bias-card-${useId()}`;

  const barH = size === "lg" ? 24 : 18;   // max bar height
  const barW = size === "lg" ? 4 : 3;     // bar width
  const gap = size === "lg" ? 3 : 2;      // gap between bars
  const minBarH = 3;                       // minimum bar height (always visible)

  const bars = getBars(scores);

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

  const open = useCallback(() => {
    if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current);
    // Calculate tooltip position from element bounding rect
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const cardW = 240;
      // Prefer right side, fall back to left if near viewport edge
      const spaceRight = window.innerWidth - rect.right;
      const x = spaceRight > cardW + 12
        ? rect.right + 8
        : rect.left - cardW - 8;
      // Vertically align to stamp, clamped to viewport
      const y = Math.max(8, Math.min(rect.top, window.innerHeight - 300));
      setTooltipPos({ x, y });
    }
    setExpanded(true);
  }, []);

  const close = useCallback(() => {
    leaveTimerRef.current = setTimeout(() => {
      setExpanded(false);
      setTooltipPos(null);
    }, 200);
  }, []);

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    if (expanded) {
      setExpanded(false);
      setTooltipPos(null);
    } else {
      open();
    }
  }, [expanded, open]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      if (expanded) { setExpanded(false); setTooltipPos(null); }
      else open();
    }
    if (e.key === "Escape") { setExpanded(false); setTooltipPos(null); }
  }, [expanded, open]);

  const handleFocus = useCallback(() => open(), [open]);
  const handleBlur = useCallback((e: React.FocusEvent) => {
    if (containerRef.current && !containerRef.current.contains(e.relatedTarget as Node)) {
      setExpanded(false);
      setTooltipPos(null);
    }
  }, []);

  const ariaLabel = `Bias: ${getLeanLabel(scores.politicalLean)} lean, ${getTypeLabel(scores.opinionFact)}, ${getRigorLabel(scores.factualRigor)}, ${getSensationalismLabel(scores.sensationalism)} tone, ${getFramingLabel(scores.framing)}`;

  return (
    <div
      ref={containerRef}
      style={{ position: "relative", display: "inline-flex" }}
      onMouseEnter={open}
      onMouseLeave={close}
      onFocus={handleFocus}
      onBlur={handleBlur}
    >
      {/* ── The Bias Pulse — 5 vertical bars ──────────────────────────── */}
      <div
        role="img"
        aria-label={ariaLabel}
        aria-describedby={expanded ? expandedId : undefined}
        tabIndex={0}
        onClick={handleClick}
        onKeyDown={handleKeyDown}
        style={{
          display: "flex",
          alignItems: "flex-end",
          gap: gap,
          height: barH,
          cursor: "pointer",
          padding: "0 2px",
          opacity: animated ? 1 : 0,
          transform: animated ? "translateY(0)" : "translateY(4px)",
          transition: "opacity 300ms var(--ease-out), transform 300ms var(--ease-out)",
        }}
      >
        {bars.map((bar, i) => {
          const h = minBarH + ((barH - minBarH) * bar.intensity) / 100;
          return (
            <div
              key={bar.key}
              title={`${bar.label}: ${bar.labelText}`}
              style={{
                width: barW,
                height: animated ? h : minBarH,
                backgroundColor: bar.color,
                borderRadius: 1,
                transition: `height 400ms var(--ease-out)`,
                transitionDelay: `${i * 50}ms`,
              }}
            />
          );
        })}
      </div>

      {/* ── Expanded Card (portal to body for correct z-index) ─────── */}
      {expanded && tooltipPos && typeof document !== "undefined" &&
        createPortal(
          <div
            id={expandedId}
            role="tooltip"
            onMouseEnter={() => {
              if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current);
            }}
            onMouseLeave={close}
            style={{
              position: "fixed",
              top: tooltipPos.y,
              left: tooltipPos.x,
              width: 240,
              background: "var(--bg-card)",
              border: "1px solid var(--border-subtle)",
              boxShadow: "var(--shadow-e3)",
              zIndex: 9999,
              padding: "var(--space-3) var(--space-4)",
              animation: "fadeIn 150ms var(--ease-out)",
              pointerEvents: "auto",
            }}
          >
            {/* Header */}
            <div style={{
              fontFamily: "var(--font-data)",
              fontSize: "var(--text-xs)",
              fontWeight: 500,
              letterSpacing: "0.06em",
              textTransform: "uppercase" as const,
              color: "var(--fg-tertiary)",
              paddingBottom: 6,
              borderBottom: "1px solid var(--border-subtle)",
              marginBottom: 10,
            }}>
              Bias Analysis
            </div>

            {/* 5 axis rows */}
            {bars.map((bar, i) => (
              <div key={bar.key} style={{ marginBottom: i < bars.length - 1 ? 8 : 0 }}>
                <div style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "baseline",
                  marginBottom: 3,
                }}>
                  <span style={{
                    fontFamily: "var(--font-data)",
                    fontSize: "var(--text-xs)",
                    fontWeight: 500,
                    letterSpacing: "0.04em",
                    textTransform: "uppercase" as const,
                    color: "var(--fg-tertiary)",
                  }}>
                    {bar.label}
                  </span>
                  <span style={{
                    fontFamily: "var(--font-structural)",
                    fontSize: "var(--text-xs)",
                    color: "var(--fg-secondary)",
                  }}>
                    {bar.labelText}
                  </span>
                </div>
                {/* Bar visualization */}
                {bar.key === "lean" ? (
                  <LeanSpectrum value={bar.value} animated={barAnimated} />
                ) : (
                  <AxisBar
                    value={bar.key === "rigor" ? bar.value : 100 - bar.value}
                    color={bar.color}
                    animated={barAnimated}
                    delay={i * 40}
                  />
                )}
              </div>
            ))}
          </div>,
          document.body
        )
      }
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

function AxisBar({ value, color, animated, delay = 0 }: {
  value: number; color: string; animated: boolean; delay?: number;
}) {
  const pct = Math.max(0, Math.min(100, value));

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{
        flex: 1,
        height: 4,
        backgroundColor: "var(--border-subtle)",
        borderRadius: 2,
        overflow: "hidden",
      }}>
        <div style={{
          width: animated ? `${pct}%` : "0%",
          height: "100%",
          backgroundColor: color,
          borderRadius: 2,
          transition: "width 300ms var(--ease-out)",
          transitionDelay: `${delay}ms`,
        }} />
      </div>
    </div>
  );
}
