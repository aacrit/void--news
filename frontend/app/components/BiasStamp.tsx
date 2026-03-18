"use client";

import { useState, useRef, useEffect, useCallback } from "react";
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

/* ── Color computations ──────────────────────────────────────────────────── */

/** Interpolate lean color from the 0-100 spectrum */
function getLeanColor(v: number): string {
  if (v <= 20) return "#3B82F6";
  if (v <= 35) {
    const t = (v - 20) / 15;
    return lerpColor("#3B82F6", "#60A5FA", t);
  }
  if (v <= 45) return "#60A5FA";
  if (v <= 55) return "#9CA3AF";
  if (v <= 65) return "#F97316";
  if (v <= 80) {
    const t = (v - 65) / 15;
    return lerpColor("#F97316", "#EF4444", t);
  }
  return "#EF4444";
}

function getRigorColor(v: number): string {
  if (v >= 60) return "#22C55E";
  if (v >= 30) return "#EAB308";
  return "#EF4444";
}

function getSensationalismColor(v: number): string {
  if (v <= 25) return "#22C55E";
  if (v <= 50) return "#EAB308";
  if (v <= 75) return "#EF4444";
  return "#EF4444";
}

function getFramingColor(v: number): string {
  if (v <= 25) return "#22C55E";
  if (v <= 50) return "#EAB308";
  if (v <= 75) return "#EF4444";
  return "#EF4444";
}

/** Hex color lerp */
function lerpColor(a: string, b: string, t: number): string {
  const ah = parseInt(a.slice(1), 16);
  const bh = parseInt(b.slice(1), 16);
  const ar = (ah >> 16) & 0xff,
    ag = (ah >> 8) & 0xff,
    ab = ah & 0xff;
  const br = (bh >> 16) & 0xff,
    bg = (bh >> 8) & 0xff,
    bb = bh & 0xff;
  const rr = Math.round(ar + (br - ar) * t);
  const rg = Math.round(ag + (bg - ag) * t);
  const rb = Math.round(ab + (bb - ab) * t);
  return `#${((rr << 16) | (rg << 8) | rb).toString(16).padStart(6, "0")}`;
}

/** Ring thickness based on distance from center (0-50 mapped to 2-3.5px) */
function getRingThickness(lean: number): number {
  const distance = Math.abs(lean - 50);
  return 2 + (distance / 50) * 1.5;
}

/* ── SVG arc helper ──────────────────────────────────────────────────────── */

function describeArc(
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number,
): string {
  const start = polarToCartesian(cx, cy, r, endAngle);
  const end = polarToCartesian(cx, cy, r, startAngle);
  const largeArc = endAngle - startAngle <= 180 ? "0" : "1";
  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArc} 0 ${end.x} ${end.y}`;
}

function polarToCartesian(
  cx: number,
  cy: number,
  r: number,
  angleDeg: number,
) {
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
  const expandedId = useRef(
    `bias-card-${Math.random().toString(36).slice(2, 9)}`,
  ).current;

  const stampSize = size === "lg" ? 36 : 32;

  /* Animate stamp on mount */
  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 50);
    return () => clearTimeout(t);
  }, []);

  /* Animate progress bars when expanded */
  useEffect(() => {
    if (expanded) {
      const t = setTimeout(() => setBarAnimated(true), 60);
      return () => clearTimeout(t);
    }
    setBarAnimated(false);
  }, [expanded]);

  /* Cleanup */
  useEffect(() => {
    return () => {
      if (leaveTimerRef.current) clearTimeout(leaveTimerRef.current);
    };
  }, []);

  /* Close on outside click (mobile) */
  useEffect(() => {
    if (!expanded) return;
    function handleOutsideClick(e: MouseEvent) {
      if (
        containerRef.current &&
        !containerRef.current.contains(e.target as Node)
      ) {
        setExpanded(false);
      }
    }
    document.addEventListener("click", handleOutsideClick, true);
    return () =>
      document.removeEventListener("click", handleOutsideClick, true);
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
    if (e.key === "Escape") {
      setExpanded(false);
    }
  }, []);

  const handleFocus = useCallback(() => setExpanded(true), []);
  const handleBlur = useCallback((e: React.FocusEvent) => {
    if (
      containerRef.current &&
      !containerRef.current.contains(e.relatedTarget as Node)
    ) {
      setExpanded(false);
    }
  }, []);

  /* Derived values */
  const leanColor = getLeanColor(scores.politicalLean);
  const ringThickness = getRingThickness(scores.politicalLean);
  const typeLetter = getTypeLetter(scores.opinionFact);
  const rigorColor = getRigorColor(scores.factualRigor);

  /* Rigor arc: map score 0-100 to sweep angle (max 120 degrees, centered) */
  const arcSweep = (scores.factualRigor / 100) * 120;
  const arcStart = 210 - arcSweep / 2;
  const arcEnd = 210 + arcSweep / 2;
  const arcR = stampSize / 2 + 3;

  const ariaLabel = `Bias: ${getLeanLabel(scores.politicalLean)} lean, ${getTypeLabel(scores.opinionFact)}, ${getRigorLabel(scores.factualRigor)}, ${getSensationalismLabel(scores.sensationalism)} tone, ${getFramingLabel(scores.framing)}`;

  return (
    <div
      ref={containerRef}
      style={{ position: "relative", display: "inline-flex" }}
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
        style={{
          width: `${stampSize}px`,
          height: `${stampSize}px`,
          position: "relative",
          cursor: "pointer",
          transform: animated ? "scale(1)" : "scale(0.9)",
          opacity: animated ? 1 : 0,
          transition: `transform 200ms var(--ease-out), opacity 200ms var(--ease-out)`,
        }}
      >
        {/* Colored ring (lean) */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            borderRadius: "50%",
            border: `${ringThickness}px solid ${leanColor}`,
            boxSizing: "border-box",
          }}
        />

        {/* Inner letter (type) */}
        <span
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontFamily: "var(--font-data)",
            fontWeight: 700,
            fontSize: size === "lg" ? "14px" : "12px",
            lineHeight: 1,
            color: "var(--fg-primary)",
            userSelect: "none",
          }}
        >
          {typeLetter}
        </span>

        {/* Rigor arc (below stamp) */}
        <svg
          width={stampSize + 8}
          height={12}
          viewBox={`0 0 ${stampSize + 8} 12`}
          style={{
            position: "absolute",
            bottom: "-8px",
            left: "-4px",
            overflow: "visible",
          }}
          aria-hidden="true"
        >
          {/* Track arc (faint) */}
          <path
            d={describeArc(
              (stampSize + 8) / 2,
              -stampSize / 2 + 6,
              arcR,
              150,
              210 + 60,
            )}
            fill="none"
            stroke="var(--border-subtle)"
            strokeWidth="2"
            strokeLinecap="round"
          />
          {/* Value arc */}
          {arcSweep > 0 && (
            <path
              d={describeArc(
                (stampSize + 8) / 2,
                -stampSize / 2 + 6,
                arcR,
                arcStart,
                arcEnd,
              )}
              fill="none"
              stroke={rigorColor}
              strokeWidth="2.5"
              strokeLinecap="round"
            />
          )}
        </svg>
      </div>

      {/* ── Expanded Bias Card ────────────────────────────────────────── */}
      {expanded && (
        <div
          id={expandedId}
          role="tooltip"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          style={{
            position: "absolute",
            top: 0,
            left: `${stampSize + 8}px`,
            width: "220px",
            background: "var(--bg-card)",
            border: "1px solid var(--border-subtle)",
            borderRadius: 0,
            boxShadow: "var(--shadow-e2)",
            zIndex: "var(--z-tooltip)" as string,
            padding: "10px 12px",
            animation: "fadeIn 150ms var(--ease-out)",
            pointerEvents: "auto",
          }}
        >
          {/* Header */}
          <div
            style={{
              fontFamily: "var(--font-data)",
              fontSize: "var(--text-xs)",
              fontWeight: 500,
              letterSpacing: "0.06em",
              textTransform: "uppercase" as const,
              color: "var(--fg-tertiary)",
              paddingBottom: "6px",
              borderBottom: "1px solid var(--border-subtle)",
              marginBottom: "10px",
            }}
          >
            Bias Analysis
          </div>

          {/* Lean spectrum */}
          <BiasRow label="Lean">
            <LeanSpectrum value={scores.politicalLean} animated={barAnimated} />
            <RowValue>{getLeanLabel(scores.politicalLean)}</RowValue>
          </BiasRow>

          {/* Rigor bar */}
          <BiasRow label="Rigor">
            <ProgressBar
              value={scores.factualRigor}
              color={getRigorColor(scores.factualRigor)}
              animated={barAnimated}
              delay={40}
            />
            <RowValue>{getRigorLabel(scores.factualRigor)}</RowValue>
          </BiasRow>

          {/* Tone (sensationalism, inverted — low = good) */}
          <BiasRow label="Tone">
            <ProgressBar
              value={100 - scores.sensationalism}
              color={getSensationalismColor(scores.sensationalism)}
              animated={barAnimated}
              delay={80}
            />
            <RowValue>{getSensationalismLabel(scores.sensationalism)}</RowValue>
          </BiasRow>

          {/* Type badge */}
          <BiasRow label="Type">
            <TypeBadge value={scores.opinionFact} />
          </BiasRow>

          {/* Framing bar */}
          <BiasRow label="Framing">
            <ProgressBar
              value={100 - scores.framing}
              color={getFramingColor(scores.framing)}
              animated={barAnimated}
              delay={120}
            />
            <RowValue>{getFramingLabel(scores.framing)}</RowValue>
          </BiasRow>
        </div>
      )}
    </div>
  );
}

/* ── Sub-components ──────────────────────────────────────────────────────── */

function BiasRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div style={{ marginBottom: "8px" }}>
      <div
        style={{
          fontFamily: "var(--font-data)",
          fontSize: "var(--text-xs)",
          fontWeight: 500,
          letterSpacing: "0.04em",
          textTransform: "uppercase" as const,
          color: "var(--fg-tertiary)",
          marginBottom: "3px",
        }}
      >
        {label}
      </div>
      {children}
    </div>
  );
}

function RowValue({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        fontFamily: "var(--font-structural)",
        fontSize: "var(--text-sm)",
        color: "var(--fg-secondary)",
        marginTop: "2px",
      }}
    >
      {children}
    </div>
  );
}

function LeanSpectrum({
  value,
  animated,
}: {
  value: number;
  animated: boolean;
}) {
  const pct = Math.max(0, Math.min(100, value));
  const dotColor = getLeanColor(value);

  return (
    <div
      style={{
        position: "relative",
        height: "12px",
        display: "flex",
        alignItems: "center",
      }}
    >
      {/* Track */}
      <div
        style={{
          position: "absolute",
          left: 0,
          right: 0,
          height: "2px",
          background:
            "linear-gradient(to right, #3B82F6, #9CA3AF 50%, #EF4444)",
          borderRadius: "1px",
          opacity: 0.35,
        }}
      />
      {/* Dot */}
      <div
        style={{
          position: "absolute",
          left: animated ? `${pct}%` : "50%",
          top: "50%",
          width: "8px",
          height: "8px",
          borderRadius: "50%",
          backgroundColor: dotColor,
          transform: "translate(-50%, -50%)",
          transition: "left 200ms var(--ease-out)",
          boxShadow: `0 0 0 2px var(--bg-card)`,
        }}
      />
    </div>
  );
}

function ProgressBar({
  value,
  color,
  animated,
  delay = 0,
}: {
  value: number;
  color: string;
  animated: boolean;
  delay?: number;
}) {
  const pct = Math.max(0, Math.min(100, value));

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "6px",
      }}
    >
      <div
        style={{
          flex: 1,
          height: "4px",
          backgroundColor: "var(--border-subtle)",
          borderRadius: "2px",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            width: animated ? `${pct}%` : "0%",
            height: "100%",
            backgroundColor: color,
            borderRadius: "2px",
            transition: `width 300ms var(--ease-out)`,
            transitionDelay: `${delay}ms`,
          }}
        />
      </div>
      <span
        style={{
          fontFamily: "var(--font-data)",
          fontSize: "var(--text-xs)",
          color: "var(--fg-tertiary)",
          minWidth: "28px",
          textAlign: "right",
          fontFeatureSettings: '"tnum" 1',
        }}
      >
        {pct}%
      </span>
    </div>
  );
}

function TypeBadge({ value }: { value: number }) {
  return (
    <span
      style={{
        display: "inline-block",
        fontFamily: "var(--font-data)",
        fontSize: "var(--text-xs)",
        fontWeight: 500,
        color: "var(--fg-secondary)",
        border: "1px solid var(--border-subtle)",
        padding: "1px 6px",
        letterSpacing: "0.02em",
      }}
    >
      {getTypeLabel(value)}
    </span>
  );
}
