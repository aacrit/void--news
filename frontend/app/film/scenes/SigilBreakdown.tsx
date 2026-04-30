"use client";

import { useState, useEffect, useRef } from "react";
import {
  VOID_CIRCLE, BEAM_CURVE, BASE_CURVE,
  VOID_CIRC_LEN, BEAM_LEN, TICK_LEN, POST_LEN, BASE_LEN,
  LEFT_TICK, RIGHT_TICK, POST,
  PIVOT, SPRING, SPRING_BOUNCY, SPRING_GENTLE,
  DRAW_TIMING, BREAKDOWN_TIMING, EXPLODE_TRANSFORMS,
} from "../constants";
import { SIGIL_PARTS, SWEEP_POSITIONS } from "../data";
import { useReducedMotion } from "../useReducedMotion";

/* ==========================================================================
   SigilBreakdown — The centerpiece teaching moment

   6-stage animation that explodes the Sigil into labeled components,
   then reassembles and activates it with live data encoding.

   Stages:
     0. draw     — Stroke-dashoffset reveals Sigil part by part
     1. separate — Components translate apart from center
     2. label    — Labels fade in beside each component
     3. reassemble — Spring back to center
     4. activate — Beam sweeps spectrum, ring fills
     5. hold     — Settled state

   In "prologue" mode: auto-advance through stages via setTimeout.
   In "manifesto" mode: IO-triggered, with six-axis accordion below.
   ========================================================================== */

type Stage = 0 | 1 | 2 | 3 | 4 | 5;

interface Props {
  mode: "prologue" | "manifesto";
  active: boolean;
}

export default function SigilBreakdown({ mode, active }: Props) {
  const [stage, setStage] = useState<Stage>(0);
  const [sweepStep, setSweepStep] = useState(0);
  const reducedMotion = useReducedMotion();
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);
  const sweepInterval = useRef<ReturnType<typeof setInterval> | null>(null);

  // Clean up timers
  useEffect(() => {
    return () => {
      timers.current.forEach(clearTimeout);
      if (sweepInterval.current) clearInterval(sweepInterval.current);
    };
  }, []);

  // Stage progression — auto-advance when active
  useEffect(() => {
    if (!active) {
      setStage(0);
      setSweepStep(0);
      if (sweepInterval.current) { clearInterval(sweepInterval.current); sweepInterval.current = null; }
      return;
    }

    // Clear any stale sweep from previous activation
    if (sweepInterval.current) { clearInterval(sweepInterval.current); sweepInterval.current = null; }

    // Reduced motion: skip to final state
    if (reducedMotion.current) {
      setStage(5);
      setSweepStep(SWEEP_POSITIONS.length - 1);
      return;
    }

    // Clear previous timers
    timers.current.forEach(clearTimeout);
    timers.current = [];

    // Stage 0: draw (starts immediately)
    setStage(0);

    // Stage 1: separate
    timers.current.push(setTimeout(() => setStage(1), BREAKDOWN_TIMING.drawEnd));

    // Stage 2: label
    timers.current.push(setTimeout(() => setStage(2), BREAKDOWN_TIMING.separateEnd));

    // Stage 3: reassemble
    timers.current.push(setTimeout(() => setStage(3), BREAKDOWN_TIMING.labelEnd));

    // Stage 4: activate (start beam sweep)
    timers.current.push(setTimeout(() => {
      setStage(4);
      let i = 0;
      sweepInterval.current = setInterval(() => {
        i++;
        if (i >= SWEEP_POSITIONS.length) {
          if (sweepInterval.current) clearInterval(sweepInterval.current);
          return;
        }
        setSweepStep(i);
      }, 600);
    }, BREAKDOWN_TIMING.reassembleEnd));

    // Stage 5: hold
    timers.current.push(setTimeout(() => setStage(5), BREAKDOWN_TIMING.activateEnd));

  }, [active, reducedMotion]);

  const isDrawn = stage >= 1 || reducedMotion.current;
  const isSeparated = stage === 1 || stage === 2;
  const isLabeled = stage === 2;
  const isActivating = stage >= 4;

  const { lean, color } = SWEEP_POSITIONS[sweepStep];
  const beamAngle = isActivating ? (lean - 50) * 0.30 : 0;
  const coverage = isActivating ? Math.min(sweepStep + 1, 5) / 6 : 0;
  const ringFill = coverage * VOID_CIRC_LEN;

  // Transition style helper
  const sep = (partKey: keyof typeof EXPLODE_TRANSFORMS) => ({
    transform: isSeparated ? EXPLODE_TRANSFORMS[partKey] : "translate(0, 0)",
    transition: `transform 800ms var(--ease-cinematic, cubic-bezier(0.22, 1, 0.36, 1))`,
    transformOrigin: PIVOT,
  });

  return (
    <div className="film-sigil" aria-hidden="true">
      <div className="film-sigil__canvas">
        <svg
          viewBox="-10 -24 52 80"
          className="film-sigil__svg"
          fill="none"
          strokeLinecap="round"
          strokeLinejoin="round"
          style={{ overflow: "visible" }}
        >
          {/* ── Void Circle ── */}
          <g style={sep("circle")}>
            {/* Background ring */}
            <path
              d={VOID_CIRCLE}
              stroke="var(--border-subtle)"
              strokeWidth="1.8"
              opacity={0.3}
            />
            {/* Coverage ring fill (activating stage) */}
            <path
              d={VOID_CIRCLE}
              stroke={isActivating ? color : "var(--fg-tertiary)"}
              strokeWidth="1.8"
              strokeDasharray={isDrawn
                ? `${isActivating ? ringFill : 0} ${VOID_CIRC_LEN}`
                : `0 ${VOID_CIRC_LEN}`}
              style={{
                transform: "rotate(-90deg)",
                transformOrigin: PIVOT,
                transition: `stroke-dasharray 700ms ${SPRING} 120ms, stroke 400ms ease`,
              }}
              opacity={0.9}
            />
            {/* Draw animation overlay */}
            {!isDrawn && (
              <path
                d={VOID_CIRCLE}
                stroke="currentColor"
                strokeWidth="1.8"
                strokeDasharray={VOID_CIRC_LEN.toString()}
                strokeDashoffset={VOID_CIRC_LEN.toString()}
                style={{
                  animation: active
                    ? `filmDraw ${DRAW_TIMING.void.duration}ms var(--ease-cinematic) ${DRAW_TIMING.void.delay}ms forwards`
                    : "none",
                }}
              />
            )}
            {/* Source count (activate stage) */}
            {isActivating && (
              <text
                x="16" y="13.5"
                textAnchor="middle" dominantBaseline="central"
                style={{
                  fontFamily: "var(--font-data)", fontSize: 8, fontWeight: 700,
                  fill: "var(--fg-secondary)", opacity: 0.85,
                }}
              >
                {Math.min(sweepStep + 1, 5) * 3}
              </text>
            )}
          </g>

          {/* ── Beam Group ── */}
          <g style={{
            ...sep("beam"),
            transform: isSeparated
              ? EXPLODE_TRANSFORMS.beam
              : `rotate(${beamAngle}deg)`,
            transformOrigin: PIVOT,
            transition: isActivating
              ? `transform 500ms ${SPRING}`
              : `transform 800ms var(--ease-cinematic)`,
          }}>
            {/* Beam line */}
            <path
              d={BEAM_CURVE}
              stroke={isActivating ? color : "currentColor"}
              strokeWidth="1.8"
              strokeDasharray={isDrawn ? "none" : BEAM_LEN.toString()}
              strokeDashoffset={isDrawn ? "0" : BEAM_LEN.toString()}
              style={{
                animation: !isDrawn && active
                  ? `filmDraw ${DRAW_TIMING.beam.duration}ms var(--ease-cinematic) ${DRAW_TIMING.beam.delay}ms forwards`
                  : "none",
                transition: "stroke 400ms ease",
              }}
            />
          </g>

          {/* ── Left Tick ── */}
          <g style={sep("tickL")}>
            <line
              x1={LEFT_TICK.x1} y1={LEFT_TICK.y1}
              x2={LEFT_TICK.x2} y2={LEFT_TICK.y2}
              stroke={isActivating ? color : "currentColor"}
              strokeWidth="1.4"
              strokeDasharray={isDrawn ? "none" : TICK_LEN.toString()}
              strokeDashoffset={isDrawn ? "0" : TICK_LEN.toString()}
              style={{
                animation: !isDrawn && active
                  ? `filmDraw ${DRAW_TIMING.tickL.duration}ms var(--ease-cinematic) ${DRAW_TIMING.tickL.delay}ms forwards`
                  : "none",
                transition: "stroke 400ms ease",
              }}
              opacity={0.85}
            />
          </g>

          {/* ── Right Tick ── */}
          <g style={sep("tickR")}>
            <line
              x1={RIGHT_TICK.x1} y1={RIGHT_TICK.y1}
              x2={RIGHT_TICK.x2} y2={RIGHT_TICK.y2}
              stroke={isActivating ? color : "currentColor"}
              strokeWidth="1.4"
              strokeDasharray={isDrawn ? "none" : TICK_LEN.toString()}
              strokeDashoffset={isDrawn ? "0" : TICK_LEN.toString()}
              style={{
                animation: !isDrawn && active
                  ? `filmDraw ${DRAW_TIMING.tickR.duration}ms var(--ease-cinematic) ${DRAW_TIMING.tickR.delay}ms forwards`
                  : "none",
                transition: "stroke 400ms ease",
              }}
              opacity={0.85}
            />
          </g>

          {/* ── Post ── */}
          <g style={sep("post")}>
            <line
              x1={POST.x1} y1={POST.y1} x2={POST.x2} y2={POST.y2}
              stroke="var(--fg-tertiary)"
              strokeWidth="1.4"
              strokeDasharray={isDrawn ? "none" : POST_LEN.toString()}
              strokeDashoffset={isDrawn ? "0" : POST_LEN.toString()}
              style={{
                animation: !isDrawn && active
                  ? `filmDraw ${DRAW_TIMING.post.duration}ms var(--ease-cinematic) ${DRAW_TIMING.post.delay}ms forwards`
                  : "none",
              }}
              opacity={0.4}
            />
          </g>

          {/* ── Base ── */}
          <g style={sep("base")}>
            <path
              d={BASE_CURVE}
              stroke="var(--fg-tertiary)"
              strokeWidth="1.8"
              strokeDasharray={isDrawn ? "none" : BASE_LEN.toString()}
              strokeDashoffset={isDrawn ? "0" : BASE_LEN.toString()}
              style={{
                animation: !isDrawn && active
                  ? `filmDraw ${DRAW_TIMING.base.duration}ms var(--ease-cinematic) ${DRAW_TIMING.base.delay}ms forwards`
                  : "none",
              }}
              opacity={0.3}
            />
          </g>
        </svg>

        {/* ── Labels (HTML overlays for better typography) ── */}
        <div className="film-sigil__labels" aria-hidden="true">
          {SIGIL_PARTS.map((part, i) => (
            <div
              key={part.id}
              className={`film-sigil__label film-sigil__label--${part.id}`}
              style={{
                opacity: isLabeled ? 1 : 0,
                transform: isLabeled ? "translateY(0)" : "translateY(8px)",
                transition: `opacity 300ms ${SPRING_GENTLE} ${200 + i * 150}ms, transform 400ms ${SPRING_GENTLE} ${200 + i * 150}ms`,
              }}
            >
              <span className="film-sigil__label-name">{part.name}</span>
              <span className="film-sigil__label-desc">{part.desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── Spectrum bar (activate stage) ── */}
      {stage >= 4 && (
        <div className="film-sigil__spectrum">
          <div className="film-sigil__spectrum-fill" />
          <div
            className="film-sigil__spectrum-dot"
            style={{
              left: `${lean}%`,
              backgroundColor: color,
              transition: `left 500ms ${SPRING}, background-color 400ms ease`,
            }}
          />
        </div>
      )}

      {/* ── Spectrum labels ── */}
      {stage >= 4 && (
        <div className="film-sigil__spectrum-labels">
          <span style={{ color: "var(--bias-left)" }}>Left</span>
          <span style={{ color: "var(--fg-muted)" }}>Center</span>
          <span style={{ color: "var(--bias-right)" }}>Right</span>
        </div>
      )}
    </div>
  );
}
