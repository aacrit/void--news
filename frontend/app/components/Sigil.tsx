"use client";

import { useState, useRef, useEffect, useCallback, useId } from "react";
import { createPortal } from "react-dom";
import type { SigilData } from "../lib/types";
import {
  getColors as gc,
  getLeanColor as leanColor,
  leanLabel,
  lerpColor as lerp,
} from "../lib/biasColors";

/* ==========================================================================
   Sigil — The Brand Mark AS the Bias Indicator

   The void --news scale icon encodes live bias data:
     Beam tilt  → political lean (left/right)
     Beam color → lean spectrum (blue → gray → red)
     Circle     → source coverage (stroke fill = Harvey ball)
     Base       → Reporting (blue) vs Opinion (orange)

   On hover: the mark gracefully unfolds — beam lifts into a lean spectrum,
   circle reveals source count, base morphs into type label. Then secondary
   scores stagger in. The brand literally opens up to show its analysis.
   ========================================================================== */

interface SigilProps {
  data: SigilData;
  size?: "sm" | "lg" | "xl";
  /** "facts" = standard cluster mode (coverage ring + source count) */
  mode?: "facts";
  /** Skip 4-stage stagger reveal on mobile — single 150ms transition */
  instant?: boolean;
}


/* ── Hover hook ────────────────────────────────────────────────────────── */

function useHover() {
  const [open, setOpen] = useState(false);
  const t = useRef<ReturnType<typeof setTimeout> | null>(null);
  const show = useCallback(() => { if (t.current) clearTimeout(t.current); setOpen(true); }, []);
  const hide = useCallback(() => { t.current = setTimeout(() => setOpen(false), 240); }, []);
  const toggle = useCallback((e: React.MouseEvent) => { e.stopPropagation(); setOpen(v => !v); }, []);
  const onKey = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setOpen(v => !v); }
    if (e.key === "Escape") setOpen(false);
  }, []);
  const keep = useCallback(() => { if (t.current) clearTimeout(t.current); }, []);
  useEffect(() => () => { if (t.current) clearTimeout(t.current); }, []);
  return { open, show, hide, toggle, onKey, keep };
}

/* ── Count-up hook ─────────────────────────────────────────────────────── */

function useCountUp(target: number, ms: number, active: boolean): number {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!active) { setV(0); return; }
    const t0 = performance.now();
    let raf: number;
    const tick = (now: number) => {
      const p = Math.min((now - t0) / ms, 1);
      setV(Math.round((1 - Math.pow(1 - p, 3)) * target));
      if (p < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms, active]);
  return v;
}

/* ── Constants ─────────────────────────────────────────────────────────── */

const CIRC = 2 * Math.PI * 9; // ~56.55, circle circumference (r=9)

/* ── Compact data-mark: the logo encoding live data ───────────────────── */

function DataMark({ data, size, mounted }: {
  data: SigilData; size: "sm" | "lg" | "xl"; mounted: boolean; mode?: "facts";
}) {
  const lean = data.politicalLean;
  const beamAngle = (lean - 50) * 0.30; // ±15° range
  const beamCol = leanColor(lean);

  const px = size === "xl" ? 56 : size === "lg" ? 42 : 28;

  // Source coverage Harvey ball — ring fill proportional to source count
  const coverage = Math.min(data.sourceCount / 10, 1);
  const ringFill = coverage * CIRC;
  const ringCol = beamCol;

  return (
    <svg
      viewBox="0 0 32 32"
      width={px} height={px}
      fill="none"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      style={{ display: "block", flexShrink: 0 }}
    >
      {/* Void circle — coverage ring (facts) or tone arc (oped) */}
      {/* Background ring (faint) */}
      <circle cx="16" cy="13" r="9"
        stroke="var(--border-subtle)" strokeWidth="1.8" opacity={0.3}
      />
      {/* Fill ring */}
      <circle cx="16" cy="13" r="9"
        stroke={ringCol} strokeWidth="1.8"
        strokeDasharray={`${mounted ? ringFill : 0} ${CIRC}`}
        style={{
          transform: "rotate(-90deg)", transformOrigin: "16px 13px",
          transition: "stroke-dasharray 700ms var(--spring) 120ms, stroke 400ms var(--ease-out)",
        }}
        opacity={0.9}
      />
      {/* Source count inside ring */}
      <text x="16" y="13.5" textAnchor="middle" dominantBaseline="central"
        style={{
          fontFamily: "var(--font-data)", fontSize: px > 32 ? 8 : 7, fontWeight: 700,
          fill: "var(--fg-secondary)",
          opacity: mounted ? 0.85 : 0,
          transition: "opacity 400ms var(--ease-out) 300ms",
        }}
      >
        {data.sourceCount}
      </text>

      {/* Beam group — pivots around circle center, tilts by lean */}
      <g style={{
        transformOrigin: "16px 13px",
        transform: `rotate(${mounted ? beamAngle : 0}deg)`,
        transition: "transform 700ms var(--spring) 60ms",
      }}>
        {/* Beam line */}
        <line x1="4" y1="13" x2="28" y2="13"
          stroke={beamCol} strokeWidth="1.8"
          style={{ transition: "stroke 400ms var(--ease-out)" }}
          opacity={mounted ? 1 : 0.3}
        />
        {/* Left weight tick */}
        <line x1="6" y1="11.5" x2="6" y2="14.5"
          stroke={beamCol} strokeWidth="1.4"
          style={{ transition: "stroke 400ms var(--ease-out)" }}
          opacity={mounted ? 0.85 : 0.2}
        />
        {/* Right weight tick */}
        <line x1="26" y1="11.5" x2="26" y2="14.5"
          stroke={beamCol} strokeWidth="1.4"
          style={{ transition: "stroke 400ms var(--ease-out)" }}
          opacity={mounted ? 0.85 : 0.2}
        />
      </g>

      {/* Center post */}
      <line x1="16" y1="22" x2="16" y2="28"
        stroke="var(--fg-tertiary)" strokeWidth="1.4"
        opacity={mounted ? 0.4 : 0.15}
        style={{ transition: "opacity 300ms var(--ease-out) 200ms" }}
      />

      {/* Base — neutral stand */}
      <line x1="12" y1="28.5" x2="20" y2="28.5"
        stroke="var(--fg-tertiary)" strokeWidth="1.8"
        opacity={mounted ? 0.3 : 0.1}
        style={{ transition: "opacity 400ms var(--ease-out) 250ms" }}
      />
    </svg>
  );
}

/* ── Popup: the mark unfolds ──────────────────────────────────────────── */

function SigilPopup({ triggerRef, isOpen, onClose, onMouseEnter, onMouseLeave, id, data, instant = false }: {
  triggerRef: React.RefObject<HTMLElement | null>;
  isOpen: boolean; onClose: () => void;
  onMouseEnter: () => void; onMouseLeave: () => void;
  id: string; data: SigilData; instant?: boolean;
}) {
  const [pos, setPos] = useState<{ x: number; y: number; mobile: boolean } | null>(null);
  const [stage, setStage] = useState(0); // 0=hidden, 1=mark, 2=beam, 3=circle, 4=details

  const lean = data.politicalLean;
  const lc = leanColor(lean);
  const ll = leanLabel(lean);

  useEffect(() => {
    if (!isOpen || !triggerRef.current) { setStage(0); return; }
    const mobile = window.innerWidth < 768;
    if (mobile) {
      // Bottom sheet positioning on mobile
      setPos({ x: 0, y: 0, mobile: true });
    } else {
      const r = triggerRef.current.getBoundingClientRect();
      const W = 280, H = 320;
      const spR = window.innerWidth - r.right;
      const x = spR > W + 16 ? r.right + 10 : r.left > W + 16 ? r.left - W - 10 : Math.max(8, (window.innerWidth - W) / 2);
      const y = Math.max(8, Math.min(r.top - 60, window.innerHeight - H - 16));
      setPos({ x, y, mobile: false });
    }
    // Staggered reveal: mark → beam → circle → details
    // instant mode: skip stagger, show all in one 150ms transition
    if (instant) {
      const t = setTimeout(() => setStage(4), 10);
      return () => clearTimeout(t);
    }
    const t1 = setTimeout(() => setStage(1), 30);
    const t2 = setTimeout(() => setStage(2), 180);
    const t3 = setTimeout(() => setStage(3), 320);
    const t4 = setTimeout(() => setStage(4), 480);
    return () => { clearTimeout(t1); clearTimeout(t2); clearTimeout(t3); clearTimeout(t4); };
  }, [isOpen, triggerRef]);

  useEffect(() => {
    if (!isOpen) return;
    const h = (e: MouseEvent) => {
      if (triggerRef.current && !triggerRef.current.contains(e.target as Node)) onClose();
    };
    document.addEventListener("click", h, true);
    return () => document.removeEventListener("click", h, true);
  }, [isOpen, onClose, triggerRef]);

  if (!isOpen || !pos || typeof document === "undefined") return null;

  const TM: Record<string, string> = { us_major: "US Major", international: "Intl", independent: "Ind" };
  const secondary = [
    { label: "Sensationalism", v: data.sensationalism, d: data.sensationalism <= 25 ? "Measured" : data.sensationalism <= 50 ? "Moderate" : data.sensationalism <= 75 ? "Elevated" : "Inflammatory" },
    { label: "Factual Rigor", v: data.factualRigor, d: data.factualRigor >= 70 ? "High" : data.factualRigor >= 40 ? "Moderate" : "Low", inv: true },
    { label: "Framing", v: data.framing, d: data.framing <= 25 ? "Neutral" : data.framing <= 55 ? "Some" : "Heavy" },
    { label: "Agreement", v: data.agreement, d: data.agreement <= 25 ? "Agree" : data.agreement <= 55 ? "Mixed" : "Disagree" },
  ];

  const isMobile = pos.mobile;

  return createPortal(
    <>
      {/* Backdrop overlay on mobile */}
      {isMobile && (
        <div onClick={onClose} style={{
          position: "fixed", inset: 0, zIndex: 150,
          backgroundColor: "var(--overlay-backdrop)",
          opacity: stage >= 1 ? 1 : 0,
          transition: "opacity 200ms var(--ease-out)",
        }} />
      )}
      <div id={id} role={isMobile ? "dialog" : "tooltip"} aria-modal={isMobile ? true : undefined} aria-label={isMobile ? "Bias analysis details" : undefined} onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave}
        style={isMobile ? {
          // Mobile: bottom sheet
          position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 151,
          background: "var(--bg-card)", borderTop: "1px solid var(--border-subtle)",
          boxShadow: "var(--shadow-e3)", pointerEvents: "auto",
          borderRadius: "12px 12px 0 0",
          maxHeight: "80vh", overflowY: "auto" as const,
          transform: stage >= 1 ? "translateY(0)" : "translateY(100%)",
          transition: "transform 350ms var(--spring)",
        } : {
          // Desktop: floating popup
          position: "fixed", top: pos.y, left: pos.x, width: 280, zIndex: 151,
          background: "var(--bg-card)", border: "1px solid var(--border-subtle)",
          boxShadow: "var(--shadow-e3)", pointerEvents: "auto",
          opacity: stage >= 1 ? 1 : 0, transform: stage >= 1 ? "scale(1) translateY(0)" : "scale(0.94) translateY(6px)",
          transition: "opacity 250ms var(--ease-out), transform 300ms var(--spring)",
        }}
      >
      {/* ═══ SECTION 1: Beam → Lean Spectrum ═══ */}
      <div style={{
        padding: "14px 16px 10px", borderBottom: "1px solid var(--border-subtle)",
        opacity: stage >= 2 ? 1 : 0, transform: stage >= 2 ? "translateY(0)" : "translateY(-8px)",
        transition: "opacity 300ms var(--ease-out), transform 350ms var(--spring)",
      }}>
        {/* Label row */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8 }}>
          <span style={{
            fontFamily: "var(--font-structural)", fontSize: "var(--text-sm)", fontWeight: 600, color: lc,
          }}>{ll}</span>
          <CountScore target={lean} color={lc} active={stage >= 2} />
        </div>
        {/* Spectrum bar — echoes the beam */}
        <div style={{ position: "relative", height: 18, marginBottom: 4 }}>
          {/* Ticks at ends (echoing beam weight ticks) */}
          <div style={{ position: "absolute", left: 0, top: 3, width: 2, height: 12, borderRadius: 1, backgroundColor: "var(--bias-left)", opacity: 0.4 }} />
          <div style={{ position: "absolute", right: 0, top: 3, width: 2, height: 12, borderRadius: 1, backgroundColor: "var(--bias-right)", opacity: 0.4 }} />
          {/* Track */}
          <div style={{
            position: "absolute", left: 6, right: 6, top: 7, height: 4, borderRadius: 2,
            background: "linear-gradient(to right, var(--bias-left), var(--bias-center-left) 35%, var(--bias-center) 50%, var(--bias-center-right) 65%, var(--bias-right))",
            opacity: 0.3,
          }} />
          {/* Marker dot — positioned within the track (6px inset each side) */}
          <div style={{
            position: "absolute", top: "50%", left: 6, right: 6,
            height: 0, pointerEvents: "none" as const,
          }}>
            <div style={{
              position: "absolute", top: 0,
              left: `${lean}%`,
              width: 11, height: 11, borderRadius: "50%", backgroundColor: lc,
              transform: stage >= 2 ? "translate(-50%, -50%) scale(1)" : "translate(-50%, -50%) scale(0)",
              transition: "transform 450ms var(--spring) 100ms, left 450ms var(--spring) 100ms, background-color 300ms var(--ease-out)",
              boxShadow: `0 0 0 2.5px var(--bg-card)`,
            }} />
          </div>
        </div>
        {/* Tick labels */}
        <div style={{
          display: "flex", justifyContent: "space-between", padding: "0 2px",
          fontFamily: "var(--font-data)", fontSize: 8, letterSpacing: "0.05em",
          textTransform: "uppercase" as const, color: "var(--fg-muted)",
        }}>
          <span>Left</span><span>Center</span><span>Right</span>
        </div>
      </div>

      {/* ═══ SECTION 2: Circle → Source Coverage ═══ */}
      <div style={{
        padding: "12px 16px", borderBottom: "1px solid var(--border-subtle)",
        display: "flex", alignItems: "center", gap: 14,
        opacity: stage >= 3 ? 1 : 0, transform: stage >= 3 ? "translateY(0)" : "translateY(-6px)",
        transition: "opacity 280ms var(--ease-out), transform 320ms var(--spring)",
      }}>
        {/* Mini coverage ring (echoing the void circle) */}
        <svg viewBox="0 0 40 40" width="40" height="40" fill="none" style={{ flexShrink: 0 }}>
          <circle cx="20" cy="20" r="16" stroke="var(--border-subtle)" strokeWidth="2.5" opacity={0.25} />
          <circle cx="20" cy="20" r="16"
            stroke={lc} strokeWidth="2.5" strokeLinecap="round"
            strokeDasharray={`${stage >= 3 ? Math.min(data.sourceCount / 10, 1) * (2 * Math.PI * 16) : 0} ${2 * Math.PI * 16}`}
            style={{ transform: "rotate(-90deg)", transformOrigin: "20px 20px", transition: "stroke-dasharray 600ms var(--spring)" }}
            opacity={0.6}
          />
          <text x="20" y="20" textAnchor="middle" dominantBaseline="central"
            style={{ fontFamily: "var(--font-data)", fontSize: 13, fontWeight: 700, fill: "var(--fg-secondary)" }}
          >
            <CountText target={data.sourceCount} active={stage >= 3} />
          </text>
        </svg>
        {/* Source details */}
        <div>
          <div style={{
            fontFamily: "var(--font-structural)", fontSize: "var(--text-sm)", fontWeight: 500, color: "var(--fg-secondary)", marginBottom: 4,
          }}>
            {data.sourceCount} source{data.sourceCount !== 1 ? "s" : ""}
          </div>
          {data.tierBreakdown && (
            <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
              {Object.entries(data.tierBreakdown).map(([tier, count]) =>
                (count as number) > 0 ? (
                  <span key={tier} style={{
                    fontFamily: "var(--font-data)", fontSize: 9, padding: "1px 5px",
                    border: "1px solid var(--border-subtle)", borderRadius: 2, color: "var(--fg-tertiary)",
                  }}>{TM[tier] || tier}: {count as number}</span>
                ) : null
              )}
            </div>
          )}
        </div>
      </div>

      {/* ═══ SECTION 3: Secondary Scores — dot scale (matches BiasInspector) ═══ */}
      <div style={{ padding: "10px 16px 14px" }}>
        {secondary.map((ax, i) => (
          <div key={ax.label} style={{
            display: "flex", alignItems: "center", gap: 8, marginBottom: 5,
            opacity: stage >= 4 ? 1 : 0,
            transition: `opacity 250ms var(--ease-out) ${i * 55}ms`,
          }}>
            <span style={{ fontFamily: "var(--font-data)", fontSize: 9, color: "var(--fg-tertiary)", width: 74, flexShrink: 0 }}>
              {ax.label}
            </span>
            {/* 5-dot scale — consistent with BiasInspector subfactors */}
            <span style={{ display: "inline-flex", gap: 3 }}>
              {Array.from({ length: 5 }, (_, di) => {
                const filled = Math.max(0, Math.min(5, Math.round((ax.v / 100) * 5)));
                return (
                  <span key={di} style={{
                    width: 6, height: 6, borderRadius: "50%",
                    backgroundColor: di < filled ? "var(--fg-secondary)" : "var(--border-subtle)",
                    transition: `background-color 250ms var(--ease-out) ${(150 + i * 55 + di * 30)}ms`,
                  }} />
                );
              })}
            </span>
            <span style={{ fontFamily: "var(--font-data)", fontSize: 9, fontWeight: 500, color: "var(--fg-tertiary)", flexShrink: 0 }}>
              {ax.d}
            </span>
          </div>
        ))}
      </div>
    </div>
    </>,
    document.body,
  );
}

/* ── Count-up helpers for popup ────────────────────────────────────────── */

function CountScore({ target, color, active }: { target: number; color: string; active: boolean }) {
  const v = useCountUp(target, 500, active);
  return <span style={{ fontFamily: "var(--font-data)", fontSize: 13, fontWeight: 700, color }}>{v}</span>;
}

function CountText({ target, active }: { target: number; active: boolean }) {
  const v = useCountUp(target, 400, active);
  return <>{v}</>;
}

/* ── Hand-drawn ink underline — editor's pen stroke ──────────────────── */

/**
 * Organic underline strokes as if an editor dragged a pen beneath a word.
 * Multiple variants for visual variety. Slightly wavy with pressure
 * variation — thick at the press, thin at the trail.
 *
 * viewBox 100x12 — wide and short, sits below the lean label.
 * Red = divergent (sources disagree), green = consensus (sources agree).
 * Stroke-dasharray length stored in --ink-len for the draw animation.
 */
const INK_UNDERLINES = [
  // Variant A: gentle wave, thick start tapering
  { d: "M 4 6 C 15 4, 28 8, 42 5 C 56 2, 70 9, 96 5", len: 95 },
  // Variant B: slight downward arc, confident stroke
  { d: "M 3 4 C 20 6, 45 8, 60 7 C 75 6, 88 4, 97 6", len: 96 },
  // Variant C: wobbly, quick editorial scribble
  { d: "M 5 7 C 18 3, 30 9, 48 5 C 62 2, 78 8, 95 4", len: 94 },
];

function InkUnderline({ variant, color }: { variant: number; color: string }) {
  const path = INK_UNDERLINES[variant % INK_UNDERLINES.length];
  return (
    <div className="sigil__ink-underline" aria-hidden="true">
      <svg viewBox="0 0 100 12" preserveAspectRatio="none" fill="none">
        {/* Faint bleed — ink feathering into paper */}
        <path
          d={path.d}
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.10"
          style={{ filter: "blur(1px)" } as React.CSSProperties}
        />
        {/* Main pen stroke — organic pressure variation */}
        <path
          d={path.d}
          stroke={color}
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          opacity="0.7"
          style={{ ["--ink-len" as string]: path.len } as React.CSSProperties}
        />
      </svg>
    </div>
  );
}

/* ── Main Sigil ────────────────────────────────────────────────────────── */

export default function Sigil({ data, size = "sm", mode = "facts", instant = false }: SigilProps) {
  const ref = useRef<HTMLDivElement>(null);
  const { open, show, hide, toggle, onKey, keep } = useHover();
  const [mounted, setMounted] = useState(false);
  const tooltipId = `sigil-${useId()}`;

  const ll = leanLabel(data.politicalLean);
  const lc = leanColor(data.politicalLean);

  useEffect(() => { const t = setTimeout(() => setMounted(true), 60); return () => clearTimeout(t); }, []);

  const aria = `Political lean: ${ll} (${data.politicalLean}). ${data.sourceCount} sources. Press Enter for details.`;

  const ringClass = data.divergenceFlag === "divergent"
    ? " sigil--divergent"
    : data.divergenceFlag === "consensus"
      ? " sigil--consensus"
      : "";

  const ringTitle = data.divergenceFlag === "divergent"
    ? "Sources disagree significantly on this story"
    : data.divergenceFlag === "consensus"
      ? "Sources largely agree on this story"
      : undefined;

  return (
    <div ref={ref} className={`sigil${ringClass}`} title={ringTitle}
      onMouseEnter={show} onFocus={show} onMouseLeave={hide} onBlur={hide}
      onClick={toggle} onKeyDown={onKey}
      tabIndex={0} role="button" aria-expanded={open} aria-label={aria}
      aria-controls={open ? tooltipId : undefined}
      style={{
        display: "inline-flex", alignItems: "center",
        gap: size === "xl" ? 12 : size === "lg" ? 8 : 5,
        cursor: "pointer", position: "relative",
        minHeight: 44,
        opacity: data.pending ? 0.3 : 1,
        filter: data.pending ? "grayscale(1)" : "none",
        transition: "opacity 300ms var(--ease-out), filter 300ms var(--ease-out)",
      }}
    >
      {/* The data-encoded brand mark */}
      <DataMark data={data} size={size} mounted={mounted} mode={mode} />

      {/* Lean label — with optional hand-drawn ink circle for divergence/consensus */}
      <span style={{
        fontFamily: "var(--font-data)", fontWeight: 600,
        fontSize: size === "xl" ? 14 : size === "lg" ? 11 : 10,
        color: lc,
        lineHeight: 1,
        letterSpacing: "0.02em",
        opacity: mounted ? 1 : 0,
        transition: "opacity 350ms var(--ease-out) 350ms",
        position: "relative",
      }}>
        {ll}
        {data.divergenceFlag === "divergent" && (
          <InkUnderline variant={data.politicalLean % 3} color="var(--sense-high)" />
        )}
        {data.divergenceFlag === "consensus" && (
          <InkUnderline variant={(data.politicalLean + 1) % 3} color="var(--sense-low)" />
        )}
      </span>

      <SigilPopup
        triggerRef={ref} isOpen={open} onClose={() => hide()}
        onMouseEnter={keep} onMouseLeave={hide}
        id={tooltipId} data={data} instant={instant}
      />
    </div>
  );
}
