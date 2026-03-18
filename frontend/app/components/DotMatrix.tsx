"use client";

import { useState, useRef, useEffect } from "react";
import type { BiasScores } from "../lib/types";

interface DotMatrixProps {
  scores: BiasScores;
  size?: "sm" | "lg";
}

/* ---------------------------------------------------------------------------
   Bias Dot Matrix — The Core Visual Language
   5 dots, one per bias axis: L S O R F
   Color + shape (filled/half/hollow) = double encoding for accessibility.
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

/**
 * Returns fill style: "filled" (strong signal), "half" (moderate), "hollow" (neutral/weak).
 * Based on how far from neutral center the value is.
 */
function getFramingFill(value: number): "filled" | "half" | "hollow" {
  if (value < 25) return "hollow";
  if (value < 60) return "half";
  return "filled";
}

function getFramingLabel(value: number): string {
  if (value < 25) return "neutral";
  if (value < 60) return "moderate";
  return "heavy";
}

/**
 * For non-framing dots, determine fill based on confidence/distance from center.
 */
function getConfidenceFill(value: number, center: number): "filled" | "half" | "hollow" {
  const dist = Math.abs(value - center);
  if (dist > 30) return "filled";
  if (dist > 15) return "half";
  return "hollow";
}

interface DotInfo {
  key: string;
  label: string;
  axisLabel: string;
  color: string;
  fill: "filled" | "half" | "hollow";
  fullLabel: string;
}

function buildDots(scores: BiasScores): DotInfo[] {
  return [
    {
      key: "L",
      label: "L",
      axisLabel: "Political lean",
      color: getLeanColor(scores.politicalLean),
      fill: getConfidenceFill(scores.politicalLean, 50),
      fullLabel: `Political lean: ${getLeanLabel(scores.politicalLean)}`,
    },
    {
      key: "S",
      label: "S",
      axisLabel: "Sensationalism",
      color: getSenseColor(scores.sensationalism),
      fill: getConfidenceFill(scores.sensationalism, 0),
      fullLabel: `Sensationalism: ${getSenseLabel(scores.sensationalism)}`,
    },
    {
      key: "O",
      label: "O",
      axisLabel: "Type",
      color: getOpinionColor(scores.opinionFact),
      fill: getConfidenceFill(scores.opinionFact, 0),
      fullLabel: `Type: ${getOpinionLabel(scores.opinionFact)}`,
    },
    {
      key: "R",
      label: "R",
      axisLabel: "Factual rigor",
      color: getRigorColor(scores.factualRigor),
      fill: getConfidenceFill(scores.factualRigor, 100),
      fullLabel: `Factual rigor: ${getRigorLabel(scores.factualRigor)}`,
    },
    {
      key: "F",
      label: "F",
      axisLabel: "Framing",
      color: getFramingFill(scores.framing) === "hollow"
        ? "var(--fg-tertiary)"
        : getFramingFill(scores.framing) === "half"
          ? "var(--fg-secondary)"
          : "var(--fg-primary)",
      fill: getFramingFill(scores.framing),
      fullLabel: `Framing: ${getFramingLabel(scores.framing)}`,
    },
  ];
}

export default function DotMatrix({ scores, size = "sm" }: DotMatrixProps) {
  const [activeDot, setActiveDot] = useState<number | null>(null);
  const tooltipTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const dots = buildDots(scores);
  const dotSize = size === "lg" ? 12 : 8;
  const gap = 6;

  useEffect(() => {
    return () => {
      if (tooltipTimerRef.current) clearTimeout(tooltipTimerRef.current);
    };
  }, []);

  const handleDotEnter = (idx: number) => {
    if (tooltipTimerRef.current) clearTimeout(tooltipTimerRef.current);
    setActiveDot(idx);
  };

  const handleDotLeave = () => {
    tooltipTimerRef.current = setTimeout(() => setActiveDot(null), 100);
  };

  const handleDotClick = (idx: number) => {
    setActiveDot((prev) => (prev === idx ? null : idx));
  };

  const screenReaderText = dots.map((d) => d.fullLabel).join(". ") + ".";

  return (
    <div
      ref={containerRef}
      role="group"
      aria-label="Bias analysis for this article"
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "flex-start",
        gap: "2px",
        position: "relative",
      }}
    >
      {/* Screen reader text */}
      <span
        style={{
          position: "absolute",
          width: 1,
          height: 1,
          padding: 0,
          margin: -1,
          overflow: "hidden",
          clip: "rect(0, 0, 0, 0)",
          whiteSpace: "nowrap",
          border: 0,
        }}
      >
        {screenReaderText}
      </span>

      {/* Dots row */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: `${gap}px`,
          position: "relative",
        }}
        aria-hidden="true"
      >
        {dots.map((dot, idx) => (
          <button
            key={dot.key}
            onMouseEnter={() => handleDotEnter(idx)}
            onMouseLeave={handleDotLeave}
            onClick={() => handleDotClick(idx)}
            aria-label={dot.fullLabel}
            style={{
              width: dotSize,
              height: dotSize,
              borderRadius: "50%",
              border:
                dot.fill === "hollow"
                  ? `1.5px solid ${dot.color}`
                  : dot.fill === "half"
                    ? `1.5px solid ${dot.color}`
                    : "none",
              background:
                dot.fill === "filled"
                  ? dot.color
                  : dot.fill === "half"
                    ? `linear-gradient(to right, ${dot.color} 50%, transparent 50%)`
                    : "transparent",
              cursor: "pointer",
              padding: 0,
              flexShrink: 0,
              animation: `dotReveal var(--dur-fast) var(--ease-out) both`,
              animationDelay: `${idx * 30}ms`,
              transition: "transform var(--dur-fast) var(--ease-out)",
              transform: activeDot === idx ? "scale(1.4)" : "scale(1)",
            }}
          />
        ))}

        {/* Tooltip */}
        {activeDot !== null && (
          <div
            role="tooltip"
            style={{
              position: "absolute",
              bottom: `${dotSize + 8}px`,
              left: `${activeDot * (dotSize + gap)}px`,
              transform: "translateX(-30%)",
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-strong)",
              padding: "6px 10px",
              fontFamily: "var(--font-data)",
              fontSize: "var(--text-xs)",
              color: "var(--fg-primary)",
              whiteSpace: "nowrap",
              zIndex: "var(--z-tooltip)",
              boxShadow: "var(--shadow-e2)",
              animation: "fadeIn var(--dur-fast) var(--ease-out)",
              lineHeight: 1.4,
              pointerEvents: "none",
            }}
          >
            <div style={{ fontWeight: 500, marginBottom: 2 }}>
              {dots[activeDot].axisLabel}
            </div>
            <div style={{ color: dots[activeDot].color }}>
              {dots[activeDot].fullLabel.split(": ")[1]}
            </div>
          </div>
        )}
      </div>

      {/* Axis labels */}
      <div
        style={{
          display: "flex",
          gap: `${gap}px`,
        }}
        aria-hidden="true"
      >
        {dots.map((dot) => (
          <span
            key={`label-${dot.key}`}
            style={{
              width: dotSize,
              textAlign: "center",
              fontFamily: "var(--font-data)",
              fontSize: "7px",
              fontWeight: 400,
              color: "var(--fg-muted)",
              letterSpacing: "0.02em",
              lineHeight: 1,
            }}
          >
            {dot.label}
          </span>
        ))}
      </div>
    </div>
  );
}
