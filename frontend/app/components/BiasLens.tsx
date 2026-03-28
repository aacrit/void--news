"use client";

import { useState, useRef, useEffect, useCallback, useId } from "react";
import { createPortal } from "react-dom";
import type { ThreeLensData, LeanRationale, CoverageRationale } from "../lib/types";
import {
  getColors,
  getLeanColor,
  getCoverageColor,
  lerpColor,
  leanLabel as getLeanLabel,
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
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{
        position: "fixed",
        top: pos.y,
        left: pos.x,
        width: 260,
        background: "var(--bg-card)",
        border: "1px solid var(--border-subtle)",
        boxShadow: "var(--shadow-e3)",
        zIndex: 9999,
        padding: "var(--space-3) var(--space-4)",
        animation: "fadeIn 150ms var(--ease-out)",
        pointerEvents: "auto",
      }}
    >
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
      <div style={{
        position: "relative",
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "flex-end",
      }}>
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
          <span style={{ fontFamily: "var(--font-structural)", fontSize: "var(--text-sm)", color: "var(--fg-primary)", fontWeight: 600 }}>
            {label}
          </span>
          <span style={{ fontFamily: "var(--font-data)", fontSize: "var(--text-xs)", color, fontWeight: 600 }}>
            {value}
          </span>
        </div>
        {/* Spectrum bar */}
        <div style={{ position: "relative", height: 14, marginBottom: 10 }}>
          <div style={{
            position: "absolute", left: 0, right: 0, top: 3, height: 3,
            background: "linear-gradient(to right, var(--bias-left), var(--bias-center) 50%, var(--bias-right))",
            borderRadius: 2, opacity: 0.4,
          }} />
          <div style={{
            position: "absolute", left: `${value}%`, top: "50%",
            width: 8, height: 8, borderRadius: "50%", backgroundColor: color,
            transform: "translate(-50%, -50%)", boxShadow: "0 0 0 2px var(--bg-card)",
          }} />
        </div>
        {rationale ? (
          <div style={{ fontSize: "var(--text-xs)", color: "var(--fg-tertiary)", lineHeight: 1.5 }}>
            {rationale.topLeftKeywords?.length > 0 && (
              <div style={{ marginBottom: 4 }}>
                <span style={{ color: "var(--bias-left)" }}>Left signals:</span>{" "}
                {rationale.topLeftKeywords.slice(0, 3).join(", ")}
              </div>
            )}
            {rationale.topRightKeywords?.length > 0 && (
              <div style={{ marginBottom: 4 }}>
                <span style={{ color: "var(--bias-right)" }}>Right signals:</span>{" "}
                {rationale.topRightKeywords.slice(0, 3).join(", ")}
              </div>
            )}
            {rationale.sourceBaseline !== 50 && (
              <div style={{ opacity: 0.7 }}>
                Source baseline: {rationale.sourceBaseline} (15% weight)
              </div>
            )}
          </div>
        ) : (
          <div className="rationale-pending" style={{ fontSize: "var(--text-xs)", color: "var(--fg-muted)", fontStyle: "italic", lineHeight: 1.5 }}>
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
  const fontSize = size === "lg" ? 10 : 7;

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
      <span style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        fontFamily: "var(--font-data)",
        fontSize,
        fontWeight: 700,
        color: "var(--fg-secondary)",
        lineHeight: 1,
      }}>
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
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
          <span style={{ fontFamily: "var(--font-structural)", fontSize: "var(--text-sm)", color: "var(--fg-primary)", fontWeight: 600 }}>
            {label}
          </span>
          <span style={{ fontFamily: "var(--font-data)", fontSize: "var(--text-xs)", color, fontWeight: 600 }}>
            {value}
          </span>
        </div>
        <div style={{ fontSize: "var(--text-xs)", color: "var(--fg-tertiary)", lineHeight: 1.6 }}>
          <div style={{ marginBottom: 4 }}>
            <span style={{ fontWeight: 500, color: "var(--fg-secondary)" }}>{sourceCount}</span> source{sourceCount !== 1 ? "s" : ""} covering this story
          </div>
          {tierBreakdown && Object.values(tierBreakdown).some(v => v > 0) && (
            <div style={{ marginBottom: 6 }}>
              {Object.entries(tierBreakdown).map(([tier, count]) =>
                count > 0 ? (
                  <span key={tier} style={{
                    display: "inline-block",
                    marginRight: 8,
                    padding: "1px 5px",
                    fontSize: "var(--text-xs)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: 2,
                    fontFamily: "var(--font-data)",
                  }}>
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
            <div className="rationale-pending" style={{ marginTop: 4, fontSize: "var(--text-xs)", color: "var(--fg-muted)", fontStyle: "italic" }}>
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
  const gap = size === "lg" ? 10 : 6;
  const pending = lensData.pending;

  return (
    <div
      className="bias-lens"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap,
        position: "relative",
        opacity: pending ? 0.35 : 1,
        filter: pending ? "grayscale(1)" : "none",
        transition: "opacity 300ms var(--ease-out), filter 300ms var(--ease-out)",
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
        <span style={{
          fontFamily: "var(--font-data)",
          fontSize: size === "lg" ? "var(--text-xs)" : 9,
          fontWeight: 500,
          letterSpacing: "0.04em",
          textTransform: "uppercase" as const,
          color: "var(--fg-tertiary)",
          marginLeft: 2,
          whiteSpace: "nowrap",
        }}>
          Pending
        </span>
      )}
    </div>
  );
}
