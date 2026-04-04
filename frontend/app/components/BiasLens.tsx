"use client";

import { useState, useRef, useEffect, useCallback, useId } from "react";
import { createPortal } from "react-dom";
import type { ThreeLensData, LeanRationale, CoverageRationale } from "../lib/types";
import {
  getColors,
  getLeanColor,
  getCoverageColor,
  lerpColor,
  tiltLabel as getLeanLabel,
  coverageLabel as getCoverageLabel,
} from "../lib/biasColors";

interface BiasLensProps {
  lensData: ThreeLensData;
  size?: "sm" | "lg";
}

/* ---------------------------------------------------------------------------
   BiasLens — "Three Lenses"

   Three distinctive visual elements replacing the 5-bar Bias Pulse:
     1. The Needle — tilting line showing political lean (left/right)
     2. The Signal Ring — SVG ring showing coverage/confidence (Harvey ball)
     3. The Prism — morphing square→circle showing opinion vs reporting

   Each lens has its own independent hover popup with rationale.
   --------------------------------------------------------------------------- */

/* ── Shared popup component ────────────────────────────────────────────── */

interface LensPopupProps {
  triggerRef: React.RefObject<HTMLElement | null>;
  isOpen: boolean;
  onClose: () => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  title: string;
  id: string;
  children: React.ReactNode;
}

function LensPopup({ triggerRef, isOpen, onClose, onMouseEnter, onMouseLeave, title, id, children }: LensPopupProps) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (!isOpen || !triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    const cardW = 260;
    const spaceRight = window.innerWidth - rect.right;
    const rawX = spaceRight > cardW + 12
      ? rect.right + 8
      : rect.left - cardW - 8;
    // Clamp x so the popup never overflows either edge of the viewport
    const x = Math.max(8, Math.min(rawX, window.innerWidth - cardW - 8));
    const y = Math.max(8, Math.min(rect.top - 20, window.innerHeight - 320));
    setPos({ x, y });
  }, [isOpen, triggerRef]);

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

  return createPortal(
    <div
      id={id}
      role="tooltip"
      className="bias-lens-popup"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{
        top: pos.y,
        left: pos.x,
      }}
    >
      <div className="bias-lens-popup__title">
        {title}
      </div>
      {children}
    </div>,
    document.body,
  );
}

/* ── Hook for lens interaction ─────────────────────────────────────────── */

function useLensInteraction() {
  const [open, setOpen] = useState(false);
  const [pressed, setPressed] = useState(false);
  const leaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tapDebounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback(() => {
    if (leaveTimer.current) clearTimeout(leaveTimer.current);
    setOpen(true);
  }, []);

  const hide = useCallback(() => {
    leaveTimer.current = setTimeout(() => setOpen(false), 200);
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

  /* Touch tap handler — debounced to prevent popup flicker on repeated taps.
     Spring press feedback (scale 0.95→1.0) plays via the `pressed` state.
     Only fires on touch devices (@media (hover: none)). */
  const onTouchTap = useCallback((e: React.TouchEvent) => {
    e.stopPropagation();
    // Trigger spring press visual
    setPressed(true);
    setTimeout(() => setPressed(false), 300);
    // Debounce toggle — ignore taps within 300ms of previous tap
    if (tapDebounceTimer.current) return;
    tapDebounceTimer.current = setTimeout(() => {
      tapDebounceTimer.current = null;
    }, 300);
    setOpen((v) => !v);
  }, []);

  useEffect(() => () => {
    if (leaveTimer.current) clearTimeout(leaveTimer.current);
    if (tapDebounceTimer.current) clearTimeout(tapDebounceTimer.current);
  }, []);

  return { open, pressed, show, hide, toggle, onKey, keepOpen, onTouchTap };
}

/* ── Lens 1: The Needle (Political Lean) ───────────────────────────────── */

function LeanNeedle({ value, rationale, size }: {
  value: number; rationale?: LeanRationale; size: "sm" | "lg";
}) {
  const ref = useRef<HTMLDivElement>(null);
  const { open, pressed, show, hide, toggle, onKey, keepOpen, onTouchTap } = useLensInteraction();
  const [animated, setAnimated] = useState(false);
  const tooltipId = `lean-${useId()}`;

  const h = size === "lg" ? 28 : 18;
  const w = size === "lg" ? 3 : 2;
  const pivotR = size === "lg" ? 3 : 2;
  const rotation = (value - 50) * 0.6; // -30 to +30 degrees
  const color = getLeanColor(value);
  const label = getLeanLabel(value);

  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 50);
    return () => clearTimeout(t);
  }, []);

  return (
    <div
      ref={ref}
      className="lens"
      onMouseEnter={show}
      onFocus={show}
      onMouseLeave={hide}
      onBlur={hide}
      onClick={toggle}
      onTouchEnd={onTouchTap}
      onKeyDown={onKey}
      tabIndex={0}
      role="button"
      aria-expanded={open}
      aria-label={`Political lean: ${label}, score ${value}. Press Enter or Space to ${open ? "close" : "open"} details.`}
      aria-controls={open ? tooltipId : undefined}
      style={{
        width: h,
        height: h + pivotR,
        cursor: "pointer",
        transform: pressed ? "scale(0.95)" : "scale(1)",
        transition: pressed ? "transform 150ms var(--spring)" : "transform 300ms var(--spring)",
      }}
    >
      <div className="lens__inner">
        {/* Tick mark at center (reference line) */}
        <div style={{
          position: "absolute",
          bottom: pivotR,
          left: "50%",
          transform: "translateX(-50%)",
          width: 1,
          height: h * 0.4,
          backgroundColor: "var(--border-subtle)",
          opacity: 0.4,
        }} />
        {/* The needle */}
        <div style={{
          position: "absolute",
          bottom: pivotR,
          left: "50%",
          width: w,
          height: h,
          backgroundColor: color,
          borderRadius: w,
          transformOrigin: "bottom center",
          transform: `translateX(-50%) rotate(${animated ? rotation : 0}deg)`,
          transition: "transform 400ms var(--ease-out), background-color 300ms var(--ease-out)",
          opacity: animated ? 1 : 0.3,
        }} />
        {/* Pivot dot */}
        <div style={{
          width: pivotR * 2,
          height: pivotR * 2,
          borderRadius: "50%",
          backgroundColor: color,
          flexShrink: 0,
          transition: "background-color 300ms var(--ease-out)",
        }} />
      </div>

      <LensPopup
        triggerRef={ref}
        isOpen={open}
        onClose={() => hide()}
        onMouseEnter={keepOpen}
        onMouseLeave={hide}
        title="Political Lean"
        id={tooltipId}
      >
        <div className="bias-lens-popup__header">
          <span className="bias-lens-popup__label">
            {label}
          </span>
          <span className="bias-lens-popup__value" style={{ color }}>
            {value}
          </span>
        </div>
        {/* Spectrum bar */}
        <div className="bias-lens-popup__spectrum">
          <div className="bias-lens-popup__spectrum-track" />
          <div className="bias-lens-popup__spectrum-dot" style={{
            left: `${value}%`,
            backgroundColor: color,
          }} />
        </div>
        {rationale ? (
          <div className="bias-lens-popup__rationale">
            {rationale.topLeftKeywords?.length > 0 && (
              <div className="bias-lens-popup__rationale-row">
                <span className="bias-lens-popup__signal--left">Left signals:</span>{" "}
                {rationale.topLeftKeywords.slice(0, 3).join(", ")}
              </div>
            )}
            {rationale.topRightKeywords?.length > 0 && (
              <div className="bias-lens-popup__rationale-row">
                <span className="bias-lens-popup__signal--right">Right signals:</span>{" "}
                {rationale.topRightKeywords.slice(0, 3).join(", ")}
              </div>
            )}
            {rationale.sourceBaseline !== 50 && (
              <div className="bias-lens-popup__baseline">
                Source baseline: {rationale.sourceBaseline} (15% weight)
              </div>
            )}
          </div>
        ) : (
          <div className="bias-lens-popup__pending">
            Detailed analysis pending
          </div>
        )}
      </LensPopup>
    </div>
  );
}

/* ── Lens 2: The Signal Ring (Coverage/Confidence) ─────────────────────── */

function SignalRing({ value, sourceCount, tierBreakdown, rationale, size }: {
  value: number; sourceCount: number; tierBreakdown?: Record<string, number>;
  rationale?: CoverageRationale; size: "sm" | "lg";
}) {
  const ref = useRef<HTMLDivElement>(null);
  const { open, pressed, show, hide, toggle, onKey, keepOpen, onTouchTap } = useLensInteraction();
  const [animated, setAnimated] = useState(false);
  const tooltipId = `coverage-${useId()}`;

  const diameter = size === "lg" ? 28 : 18;
  const stroke = size === "lg" ? 3 : 2;
  const r = (diameter - stroke) / 2;
  const circumference = 2 * Math.PI * r;
  const fillPct = Math.max(0, Math.min(100, value));
  const dashLen = (fillPct / 100) * circumference;
  const color = getCoverageColor(value);
  const label = getCoverageLabel(value);
  const fontSize = size === "lg" ? "var(--text-xs)" : "var(--text-xxs)";

  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 110);
    return () => clearTimeout(t);
  }, []);

  const TIER_LABELS: Record<string, string> = {
    us_major: "US Major",
    international: "International",
    independent: "Independent",
  };

  return (
    <div
      ref={ref}
      className="lens"
      onMouseEnter={show}
      onFocus={show}
      onMouseLeave={hide}
      onBlur={hide}
      onClick={toggle}
      onTouchEnd={onTouchTap}
      onKeyDown={onKey}
      tabIndex={0}
      role="button"
      aria-expanded={open}
      aria-label={`Coverage: ${label}, ${sourceCount} sources, score ${value}. Press Enter or Space to ${open ? "close" : "open"} details.`}
      aria-controls={open ? tooltipId : undefined}
      style={{
        width: diameter,
        height: diameter,
        cursor: "pointer",
        position: "relative",
        transform: pressed ? "scale(0.95)" : "scale(1)",
        transition: pressed ? "transform 150ms var(--spring)" : "transform 300ms var(--spring)",
      }}
    >
      <svg
        width={diameter}
        height={diameter}
        viewBox={`0 0 ${diameter} ${diameter}`}
        style={{ transform: "rotate(-90deg)" }}
      >
        {/* Background ring */}
        <circle
          cx={diameter / 2}
          cy={diameter / 2}
          r={r}
          fill="none"
          stroke="var(--border-subtle)"
          strokeWidth={stroke}
          opacity={0.3}
        />
        {/* Fill ring */}
        <circle
          cx={diameter / 2}
          cy={diameter / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${animated ? dashLen : 0} ${circumference}`}
          style={{ transition: "stroke-dasharray 500ms var(--ease-out), stroke 300ms var(--ease-out)" }}
        />
      </svg>
      {/* Source count — absolutely positioned over ring center.
          Parent div carries position: relative to anchor this correctly. */}
      <span className="lens__count" style={{ fontSize }}>
        {sourceCount}
      </span>

      <LensPopup
        triggerRef={ref}
        isOpen={open}
        onClose={() => hide()}
        onMouseEnter={keepOpen}
        onMouseLeave={hide}
        title="Coverage"
        id={tooltipId}
      >
        <div className="bias-lens-popup__header">
          <span className="bias-lens-popup__label">
            {label}
          </span>
          <span className="bias-lens-popup__value" style={{ color }}>
            {value}
          </span>
        </div>
        <div className="bias-lens-popup__content">
          <div className="bias-lens-popup__rationale-row">
            <span className="bias-lens-popup__count-highlight">{sourceCount}</span> source{sourceCount !== 1 ? "s" : ""} covering this story
          </div>
          {tierBreakdown && Object.values(tierBreakdown).some(v => v > 0) && (
            <div className="bias-lens-popup__tier-row">
              {Object.entries(tierBreakdown).map(([tier, count]) =>
                count > 0 ? (
                  <span key={tier} className="bias-lens-popup__tier-tag">
                    {TIER_LABELS[tier] || tier}: {count}
                  </span>
                ) : null
              )}
            </div>
          )}
          {rationale ? (
            <>
              {rationale.namedSourcesCount > 0 && (
                <div>{rationale.namedSourcesCount} named source{rationale.namedSourcesCount !== 1 ? "s" : ""} cited</div>
              )}
              {rationale.dataPointsCount > 0 && (
                <div>{rationale.dataPointsCount} data point{rationale.dataPointsCount !== 1 ? "s" : ""}</div>
              )}
              {rationale.directQuotesCount > 0 && (
                <div>{rationale.directQuotesCount} direct quote{rationale.directQuotesCount !== 1 ? "s" : ""}</div>
              )}
            </>
          ) : (
            <div className="bias-lens-popup__pending">
              Detailed analysis pending
            </div>
          )}
        </div>
      </LensPopup>
    </div>
  );
}

/* ── Main BiasLens component ───────────────────────────────────────────── */

export default function BiasLens({ lensData, size = "sm" }: BiasLensProps) {
  const pending = lensData.pending;
  const sizeClass = size === "lg" ? " bias-lens--lg" : "";

  return (
    <div
      className={`bias-lens${sizeClass}`}
      style={{
        opacity: pending ? 0.35 : 1,
        filter: pending ? "grayscale(1)" : "none",
      }}
      aria-label={pending ? "Bias analysis pending" : undefined}
    >
      <LeanNeedle
        value={lensData.lean}
        rationale={lensData.leanRationale}
        size={size}
      />
      <SignalRing
        value={lensData.coverage}
        sourceCount={lensData.sourceCount}
        tierBreakdown={lensData.tierBreakdown}
        rationale={lensData.coverageRationale}
        size={size}
      />
      {pending && (
        <span className="bias-lens__pending-label">
          Pending
        </span>
      )}
    </div>
  );
}
