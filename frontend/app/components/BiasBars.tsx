"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { BiasScores } from "../lib/types";

interface BiasBarsProps {
  scores: BiasScores;
  size?: "sm" | "lg";
}

/* ---------------------------------------------------------------------------
   Bias Bars — Mini bar chart / equalizer visualization
   5 thin vertical bars, one per bias axis: L S O R F
   Heights represent intensity. Colors represent the axis.
   Replaces the old DotMatrix component.
   --------------------------------------------------------------------------- */

function getLeanColor(value: number): string {
  if (value < 20) return "var(--bias-left)";
  if (value < 40) return "var(--bias-center-left)";
  if (value < 60) return "var(--bias-center)";
  if (value < 80) return "var(--bias-center-right)";
  return "var(--bias-right)";
}

function getLeanLabel(value: number): string {
  if (value < 20) return "far left";
  if (value < 40) return "center-left";
  if (value < 60) return "center";
  if (value < 80) return "center-right";
  return "far right";
}

function getSenseColor(value: number): string {
  if (value < 33) return "var(--sense-low)";
  if (value < 66) return "var(--sense-medium)";
  return "var(--sense-high)";
}

function getSenseLabel(value: number): string {
  if (value < 33) return "low";
  if (value < 66) return "medium";
  return "high";
}

function getOpinionColor(value: number): string {
  if (value < 33) return "var(--type-reporting)";
  if (value < 66) return "var(--type-analysis)";
  return "var(--type-opinion)";
}

function getOpinionLabel(value: number): string {
  if (value < 33) return "factual reporting";
  if (value < 66) return "analysis";
  return "opinion";
}

function getRigorColor(value: number): string {
  if (value > 66) return "var(--rigor-high)";
  if (value > 33) return "var(--rigor-medium)";
  return "var(--rigor-low)";
}

function getRigorLabel(value: number): string {
  if (value > 66) return "high";
  if (value > 33) return "medium";
  return "low";
}

function getFramingColor(value: number): string {
  if (value < 25) return "var(--sense-low)";
  if (value < 60) return "var(--sense-medium)";
  return "var(--sense-high)";
}

function getFramingLabel(value: number): string {
  if (value < 25) return "neutral";
  if (value < 60) return "moderate";
  return "heavy";
}

/** Map a 0-100 score to a pixel height in the 4-20px range */
function scoreToHeight(score: number): number {
  return Math.round(4 + (score / 100) * 16);
}

interface BarInfo {
  key: string;
  axisLabel: string;
  valueLabel: string;
  color: string;
  height: number;
  fullLabel: string;
}

function buildBars(scores: BiasScores): BarInfo[] {
  return [
    {
      key: "L",
      axisLabel: "Political Lean",
      valueLabel: getLeanLabel(scores.politicalLean),
      color: getLeanColor(scores.politicalLean),
      height: scoreToHeight(
        Math.abs(scores.politicalLean - 50) * 2
      ),
      fullLabel: `Political Lean: ${getLeanLabel(scores.politicalLean)}`,
    },
    {
      key: "S",
      axisLabel: "Sensationalism",
      valueLabel: getSenseLabel(scores.sensationalism),
      color: getSenseColor(scores.sensationalism),
      height: scoreToHeight(scores.sensationalism),
      fullLabel: `Sensationalism: ${getSenseLabel(scores.sensationalism)}`,
    },
    {
      key: "O",
      axisLabel: "Type",
      valueLabel: getOpinionLabel(scores.opinionFact),
      color: getOpinionColor(scores.opinionFact),
      height: scoreToHeight(scores.opinionFact),
      fullLabel: `Type: ${getOpinionLabel(scores.opinionFact)}`,
    },
    {
      key: "R",
      axisLabel: "Factual Rigor",
      valueLabel: getRigorLabel(scores.factualRigor),
      color: getRigorColor(scores.factualRigor),
      height: scoreToHeight(scores.factualRigor),
      fullLabel: `Factual Rigor: ${getRigorLabel(scores.factualRigor)}`,
    },
    {
      key: "F",
      axisLabel: "Framing",
      valueLabel: getFramingLabel(scores.framing),
      color: getFramingColor(scores.framing),
      height: scoreToHeight(scores.framing),
      fullLabel: `Framing: ${getFramingLabel(scores.framing)}`,
    },
  ];
}

export default function BiasBars({ scores, size = "sm" }: BiasBarsProps) {
  const [showTooltip, setShowTooltip] = useState(false);
  const [animated, setAnimated] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const tooltipTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const bars = buildBars(scores);

  const barWidth = size === "lg" ? 4 : 3;
  const barGap = 2;
  const containerHeight = size === "lg" ? 28 : 24;

  // Animate bars on mount (with small delay to trigger CSS transition)
  useEffect(() => {
    const timer = setTimeout(() => setAnimated(true), 50);
    return () => clearTimeout(timer);
  }, []);

  // Cleanup tooltip timer
  useEffect(() => {
    return () => {
      if (tooltipTimerRef.current) clearTimeout(tooltipTimerRef.current);
    };
  }, []);

  const handleMouseEnter = useCallback(() => {
    if (tooltipTimerRef.current) clearTimeout(tooltipTimerRef.current);
    setShowTooltip(true);
  }, []);

  const handleMouseLeave = useCallback(() => {
    tooltipTimerRef.current = setTimeout(() => setShowTooltip(false), 150);
  }, []);

  const handleClick = useCallback(() => {
    setShowTooltip((prev) => !prev);
  }, []);

  const ariaLabel = `Bias analysis: ${getLeanLabel(scores.politicalLean)} lean, ${getSenseLabel(scores.sensationalism)} sensationalism, ${getOpinionLabel(scores.opinionFact)}, ${getRigorLabel(scores.factualRigor)} rigor, ${getFramingLabel(scores.framing)} framing`;

  return (
    <div
      ref={containerRef}
      role="img"
      aria-label={ariaLabel}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
      style={{
        display: "inline-flex",
        alignItems: "flex-end",
        gap: `${barGap}px`,
        height: `${containerHeight}px`,
        position: "relative",
        cursor: "pointer",
        padding: "2px 0",
      }}
    >
      {/* Bars */}
      {bars.map((bar, idx) => (
        <div
          key={bar.key}
          title={`${bar.axisLabel}: ${bar.valueLabel}`}
          style={{
            width: `${barWidth}px`,
            height: animated ? `${bar.height}px` : "0px",
            backgroundColor: bar.color,
            borderRadius: "1px 1px 0 0",
            flexShrink: 0,
            transition: `height 300ms var(--ease-out)`,
            transitionDelay: `${idx * 30}ms`,
          }}
        />
      ))}

      {/* Tooltip — full breakdown on hover/tap */}
      {showTooltip && (
        <div
          role="tooltip"
          onMouseEnter={handleMouseEnter}
          onMouseLeave={handleMouseLeave}
          style={{
            position: "absolute",
            bottom: `${containerHeight + 6}px`,
            left: "50%",
            transform: "translateX(-50%)",
            background: "var(--bg-elevated)",
            border: "1px solid var(--border-strong)",
            padding: "8px 12px",
            fontFamily: "var(--font-data)",
            fontSize: "var(--text-xs)",
            color: "var(--fg-primary)",
            whiteSpace: "nowrap",
            zIndex: "var(--z-tooltip)",
            boxShadow: "var(--shadow-e2)",
            animation: "fadeIn var(--dur-fast) var(--ease-out)",
            lineHeight: 1.6,
            pointerEvents: "auto",
          }}
        >
          {bars.map((bar) => (
            <div
              key={bar.key}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <span
                style={{
                  width: "6px",
                  height: "6px",
                  borderRadius: "1px",
                  backgroundColor: bar.color,
                  flexShrink: 0,
                }}
              />
              <span style={{ color: "var(--fg-tertiary)" }}>
                {bar.axisLabel}:
              </span>
              <span style={{ fontWeight: 500 }}>{bar.valueLabel}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
