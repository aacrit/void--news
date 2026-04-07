"use client";

import { useState, useRef, useEffect, useCallback, useId } from "react";
import { createPortal } from "react-dom";
import type { SigilData } from "../lib/types";
import {
  getColors as gc,
  getLeanColor as leanColor,
  tiltLabel,
  tiltDescriptor,
  sigilLabelInfo,
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

/** Feed-level sizes (sm) get simplified popup + no InkUnderline.
 *  Deep Dive sizes (lg, xl) get the full analysis view. */
function isFullDetail(size: "sm" | "lg" | "xl"): boolean {
  return size === "lg" || size === "xl";
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

const CIRC_ORGANIC = 57;   // organic hand-drawn void circle path length (~57)
const CIRC_GEOMETRIC = 56.5; // 2π × 9 ≈ 56.5 (true circle r=9, cx=16, cy=13)

/* ── Compact data-mark: the logo encoding live data ───────────────────── */

function DataMark({ data, size, mounted }: {
  data: SigilData; size: "sm" | "lg" | "xl"; mounted: boolean; mode?: "facts";
}) {
  const lean = data.politicalLean;
  const isUnscored = !!data.unscored;
  const beamAngle = isUnscored ? 0 : (lean - 50) * 0.30; // ±15° range, level when unscored
  const beamCol = isUnscored ? "var(--fg-tertiary)" : leanColor(lean);

  const px = size === "xl" ? 56 : size === "lg" ? 42 : 28;
  const isSmall = size === "sm";

  // Source coverage Harvey ball — ring fill proportional to source count
  const coverage = Math.min(data.sourceCount / 15, 1);
  const circ = isSmall ? CIRC_GEOMETRIC : CIRC_ORGANIC;
  const ringFill = coverage * circ;
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
      {/* Coverage ring — geometric circle at sm for instant readability,
          organic hand-drawn path at lg/xl where the wobble is perceptible */}
      {isSmall ? (
        <>
          {/* Background ring (geometric) */}
          <circle cx="16" cy="13" r="9"
            stroke="var(--border-subtle)" strokeWidth="1.8" opacity={0.3} fill="none"
          />
          {/* Fill ring (geometric Harvey ball) */}
          <circle cx="16" cy="13" r="9"
            stroke={ringCol} strokeWidth="1.8" fill="none"
            strokeDasharray={`${mounted ? ringFill : 0} ${CIRC_GEOMETRIC}`}
            style={{
              transform: "rotate(-90deg)", transformOrigin: "16px 13px",
              transition: "stroke-dasharray 700ms var(--spring) 120ms, stroke 400ms var(--ease-out)",
            }}
            opacity={0.9}
          />
        </>
      ) : (
        <>
          {/* Background ring (organic) */}
          <path d="M16 4 C24 3.5 25.5 7.5 25 13 C24.5 18.5 22.5 22 16 22 C9.5 22 7.5 18.5 7 13 C6.5 7.5 8 3.5 16 4"
            stroke="var(--border-subtle)" strokeWidth="1.8" opacity={0.3}
          />
          {/* Fill ring (organic) */}
          <path d="M16 4 C24 3.5 25.5 7.5 25 13 C24.5 18.5 22.5 22 16 22 C9.5 22 7.5 18.5 7 13 C6.5 7.5 8 3.5 16 4"
            stroke={ringCol} strokeWidth="1.8"
            strokeDasharray={`${mounted ? ringFill : 0} ${CIRC_ORGANIC}`}
            style={{
              transform: "rotate(-90deg)", transformOrigin: "16px 13px",
              transition: "stroke-dasharray 700ms var(--spring) 120ms, stroke 400ms var(--ease-out)",
            }}
            opacity={0.9}
          />
        </>
      )}

      {/* Beam group — pivots around circle center, tilts by lean */}
      <g className="sigil__beam-group" style={{
        transformOrigin: "16px 13px",
        transform: `rotate(${mounted ? beamAngle : 0}deg)`,
        transition: "transform var(--beam-tilt-dur, 800ms) var(--spring-beam, var(--spring)) var(--beam-tilt-delay, 60ms)",
      }}>
        {/* Beam — straight line at sm (tilt readable at 28px), organic S-curve at lg/xl */}
        {isSmall ? (
          <line x1="4" y1="13" x2="28" y2="13"
            stroke={beamCol} strokeWidth="1.8"
            style={{ transition: "stroke 500ms var(--ease-rack) 200ms" }}
            opacity={mounted ? 1 : 0.3}
          />
        ) : (
          <path d="M4 13 C10 12.3 22 13.7 28 13"
            stroke={beamCol} strokeWidth="1.8"
            style={{ transition: "stroke 500ms var(--ease-rack) 200ms" }}
            opacity={mounted ? 1 : 0.3}
          />
        )}
        {/* Weight ticks — only at lg/xl where they're visible (3px at 28px = noise) */}
        {!isSmall && (
          <>
            <line x1="5.8" y1="11.5" x2="6.2" y2="14.5"
              stroke={beamCol} strokeWidth="1.4"
              style={{ transition: "stroke 500ms var(--ease-rack) 200ms" }}
              opacity={mounted ? 0.85 : 0.2}
            />
            <line x1="26.2" y1="11.5" x2="25.8" y2="14.5"
              stroke={beamCol} strokeWidth="1.4"
              style={{ transition: "stroke 500ms var(--ease-rack) 200ms" }}
              opacity={mounted ? 0.85 : 0.2}
            />
          </>
        )}
      </g>

      {/* Source count — below beam, in lower half of circle */}
      <text x="16" y="18" textAnchor="middle" dominantBaseline="central"
        style={{
          fontFamily: "var(--font-data)", fontSize: px > 32 ? 8 : 7, fontWeight: 700,
          fill: "var(--fg-secondary)",
          opacity: mounted ? 0.8 : 0,
          transition: "opacity 400ms var(--ease-out) 300ms",
        }}
      >
        {data.sourceCount}
      </text>

      {/* Center post */}
      <line x1="16" y1="22" x2="16" y2="28"
        stroke="var(--fg-tertiary)" strokeWidth="1.4"
        opacity={mounted ? 0.4 : 0.15}
        style={{ transition: "opacity 300ms var(--ease-out) 200ms" }}
      />

      {/* Base — organic subtle curve */}
      <path d="M12 28.5 C14 28.2 18 28.8 20 28.5"
        stroke="var(--fg-tertiary)" strokeWidth="1.8"
        opacity={mounted ? 0.3 : 0.1}
        style={{ transition: "opacity 400ms var(--ease-out) 250ms" }}
      />
    </svg>
  );
}

/* ── Popup: the mark unfolds ──────────────────────────────────────────── */

function SigilPopup({ triggerRef, isOpen, onClose, onMouseEnter, onMouseLeave, id, data, instant = false, size = "sm" }: {
  triggerRef: React.RefObject<HTMLElement | null>;
  isOpen: boolean; onClose: () => void;
  onMouseEnter: () => void; onMouseLeave: () => void;
  id: string; data: SigilData; instant?: boolean; size?: "sm" | "lg" | "xl";
}) {
  const [pos, setPos] = useState<{ x: number; y: number; mobile: boolean } | null>(null);
  const [stage, setStage] = useState(0); // 0=hidden, 1=mark, 2=beam, 3=circle, 4=details

  const lean = data.politicalLean;
  const popupUnscored = !!data.unscored;
  const lc = popupUnscored ? "var(--fg-tertiary)" : leanColor(lean);
  const ll = popupUnscored ? "Unscored" : tiltLabel(lean);
  const full = isFullDetail(size);

  useEffect(() => {
    if (!isOpen || !triggerRef.current) { setStage(0); return; }
    const mobile = window.innerWidth < 768;
    if (mobile) {
      // Bottom sheet positioning on mobile
      setPos({ x: 0, y: 0, mobile: true });
    } else {
      const r = triggerRef.current.getBoundingClientRect();
      const W = 280, H = full ? 320 : 200;
      const spR = window.innerWidth - r.right;
      const x = spR > W + 16 ? r.right + 10 : r.left > W + 16 ? r.left - W - 10 : Math.max(8, (window.innerWidth - W) / 2);
      const y = Math.max(8, Math.min(r.top - 60, window.innerHeight - H - 16));
      setPos({ x, y, mobile: false });
    }
    // Compressed 2-stage reveal: mark+beam → circle+details
    // instant mode: skip stagger, show all in one frame
    if (instant) {
      const t = setTimeout(() => setStage(4), 10);
      return () => clearTimeout(t);
    }
    const t1 = setTimeout(() => setStage(2), 20);
    const t2 = setTimeout(() => setStage(4), 120);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [isOpen, triggerRef, full, instant]);

  // Outside-click handler: capture-phase listener that closes the popup AND
  // stops propagation so the click doesn't reach the underlying story card
  // (which would open Deep Dive — bug F03).
  const popupRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!isOpen) return;
    const h = (e: MouseEvent) => {
      const target = e.target as Node;
      const insideTrigger = triggerRef.current?.contains(target);
      const insidePopup = popupRef.current?.contains(target);
      if (!insideTrigger && !insidePopup) {
        e.stopPropagation();
        onClose();
      }
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
        <div className="sigil-popup__backdrop" onClick={onClose} style={{
          opacity: stage >= 1 ? 1 : 0,
        }} />
      )}
      <div ref={popupRef} id={id} role={isMobile ? "dialog" : "tooltip"} aria-modal={isMobile ? true : undefined} aria-label={isMobile ? "Bias analysis details" : undefined} onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave}
        className={isMobile ? "sigil-popup sigil-popup--mobile" : "sigil-popup sigil-popup--desktop"}
        style={isMobile ? {
          transform: stage >= 1 ? "translateY(0)" : "translateY(100%)",
        } : {
          top: pos.y, left: pos.x,
          opacity: stage >= 1 ? 1 : 0, transform: stage >= 1 ? "scale(1) translateY(0)" : "scale(0.94) translateY(6px)",
        }}
      >
      {/* ═══ SECTION 1: Beam → Coverage Tilt ═══ */}
      <div className="sigil-popup__section" style={{
        opacity: stage >= 2 ? 1 : 0, transform: stage >= 2 ? "translateY(0)" : "translateY(-8px)",
        transition: "opacity 300ms var(--ease-out), transform 350ms var(--spring)",
      }}>
        {/* Label row */}
        <div className="sigil-popup__header">
          <span className="sigil-popup__label" style={{ color: lc }}>{ll}</span>
          <CountScore target={lean} color={lc} active={stage >= 2} />
        </div>
        {/* Contextual descriptor — explains what the score means */}
        {stage >= 2 && (
          <p className="sigil-popup__descriptor">
            {popupUnscored ? "Not enough analytical signal to determine lean" : tiltDescriptor(lean)}
          </p>
        )}
        {/* Spectrum bar — echoes the beam */}
        <div className="sigil-popup__spectrum">
          {/* Ticks at ends (echoing beam weight ticks) */}
          <div className="sigil-popup__spectrum-tick sigil-popup__spectrum-tick--left" />
          <div className="sigil-popup__spectrum-tick sigil-popup__spectrum-tick--right" />
          {/* Track */}
          <div className="sigil-popup__spectrum-track" />
          {/* Marker dot — positioned within the track (6px inset each side) */}
          <div className="sigil-popup__spectrum-marker-area">
            <div className="sigil-popup__spectrum-dot" style={{
              left: `${lean}%`,
              backgroundColor: lc,
              transform: stage >= 2 ? "translate(-50%, -50%) scale(1)" : "translate(-50%, -50%) scale(0)",
              boxShadow: `0 0 0 2.5px var(--bg-card)`,
            }} />
          </div>
        </div>
        {/* Tick labels */}
        <div className="sigil-popup__spectrum-labels">
          <span>Left</span><span>Center</span><span>Right</span>
        </div>
      </div>

      {full ? (
        <>
          {/* ═══ SECTION 2: Circle → Source Coverage (full detail) ═══ */}
          <div className="sigil-popup__section sigil-popup__scores" style={{
            alignItems: "center",
            opacity: stage >= 3 ? 1 : 0, transform: stage >= 3 ? "translateY(0)" : "translateY(-6px)",
            transition: "opacity 280ms var(--ease-out), transform 320ms var(--spring)",
          }}>
            {/* Mini coverage ring (echoing the void circle) */}
            <svg viewBox="0 0 40 40" width="40" height="40" fill="none" className="sigil-popup__ring-svg">
              <circle cx="20" cy="20" r="16" stroke="var(--border-subtle)" strokeWidth="2.5" opacity={0.25} />
              <circle cx="20" cy="20" r="16"
                stroke={lc} strokeWidth="2.5" strokeLinecap="round"
                strokeDasharray={`${stage >= 3 ? Math.min(data.sourceCount / 15, 1) * (2 * Math.PI * 16) : 0} ${2 * Math.PI * 16}`}
                style={{ transform: "rotate(-90deg)", transformOrigin: "20px 20px", transition: "stroke-dasharray 600ms var(--spring)" }}
                opacity={0.6}
              />
              <text x="20" y="20" textAnchor="middle" dominantBaseline="central"
                className="sigil__popup-lean"
              >
                <CountText target={data.sourceCount} active={stage >= 3} />
              </text>
            </svg>
            {/* Source details */}
            <div>
              <div className="sigil-popup__source-label">
                {data.sourceCount} source{data.sourceCount !== 1 ? "s" : ""}
              </div>
              {data.tierBreakdown && (
                <div className="sigil-popup__tier-list">
                  {Object.entries(data.tierBreakdown).map(([tier, count]) =>
                    (count as number) > 0 ? (
                      <span key={tier} className="sigil-popup__tier-tag">
                        {TM[tier] || tier}: {count as number}
                      </span>
                    ) : null
                  )}
                </div>
              )}
            </div>
          </div>

          {/* ═══ SECTION 3: Secondary Scores — dot scale (matches BiasInspector) ═══ */}
          <div className="sigil-popup__section">
            {secondary.map((ax, i) => (
              <div key={ax.label} className="sigil-popup__axis-row" style={{
                opacity: stage >= 4 ? 1 : 0,
                transition: `opacity 250ms var(--ease-out) ${i * 55}ms`,
              }}>
                <span className="sigil-popup__axis-label">
                  {ax.label}
                </span>
                {/* 5-dot scale — consistent with BiasInspector subfactors */}
                <span className="sigil-popup__dots">
                  {Array.from({ length: 5 }, (_, di) => {
                    const filled = Math.max(0, Math.min(5, Math.round((ax.v / 100) * 5)));
                    return (
                      <span key={di} className="sigil-popup__dot" style={{
                        backgroundColor: di < filled ? "var(--fg-secondary)" : "var(--border-subtle)",
                        transition: `background-color 250ms var(--ease-out) ${(150 + i * 55 + di * 30)}ms`,
                      }} />
                    );
                  })}
                </span>
                <span className="sigil-popup__axis-desc">
                  {ax.d}
                </span>
              </div>
            ))}
          </div>
        </>
      ) : (
        /* ═══ SIMPLIFIED: Compact summary for feed-level Sigil (sm) ═══ */
        <div className="sigil-popup__section sigil-popup__compact" style={{
          opacity: stage >= 3 ? 1 : 0,
          transition: "opacity 280ms var(--ease-out)",
        }}>
          <div className="sigil-popup__compact-row">
            <span className="sigil-popup__compact-count">{data.sourceCount}</span>
            <span className="sigil-popup__compact-sources">
              source{data.sourceCount !== 1 ? "s" : ""} reporting
            </span>
          </div>
          <span className="sigil-popup__hint">
            Tap story for full analysis
          </span>
        </div>
      )}
    </div>
    </>,
    document.body,
  );
}

/* ── Count-up helpers for popup ────────────────────────────────────────── */

function CountScore({ target, color, active }: { target: number; color: string; active: boolean }) {
  const v = useCountUp(target, 500, active);
  return <span className="sigil-popup__score" style={{ color }}>{v}</span>;
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

  const unscored = !!data.unscored;
  const labelInfo = sigilLabelInfo(data.politicalLean, data.agreement, data.divergenceFlag, unscored);
  const lc = unscored ? "var(--fg-tertiary)" : leanColor(data.politicalLean);
  const full = isFullDetail(size);

  useEffect(() => { const t = setTimeout(() => setMounted(true), 60); return () => clearTimeout(t); }, []);

  const aria = unscored
    ? `Coverage tilt: Unscored (insufficient signal). ${data.sourceCount} sources. Press Enter for details.`
    : `Coverage tilt: ${labelInfo.text} (${data.politicalLean}). ${data.sourceCount} sources. Press Enter for details.`;

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

  const sizeClass = ` sigil--${size}`;

  return (
    <div ref={ref} className={`sigil${ringClass}${sizeClass}${unscored ? " sigil--unscored" : ""}`} title={ringTitle}
      onMouseEnter={show} onFocus={show} onMouseLeave={hide} onBlur={hide}
      onClick={toggle} onKeyDown={onKey}
      tabIndex={0} role="button" aria-expanded={open} aria-label={aria}
      aria-controls={open ? tooltipId : undefined}
      aria-describedby={open ? tooltipId : undefined}
      style={{
        opacity: data.pending ? 0.3 : 1,
        filter: data.pending ? "grayscale(1)" : "none",
      }}
    >
      {/* The data-encoded brand mark */}
      <DataMark data={data} size={size} mounted={mounted} mode={mode} />

      {/* Combined lean + divergence label — InkUnderline on all sizes */}
      <span className="sigil__lean-label" style={{
        color: labelInfo.color,
        opacity: mounted ? 1 : 0,
      }}>
        {labelInfo.text}
        {data.divergenceFlag === "divergent" && (
          <InkUnderline variant={data.politicalLean % 3} color="var(--sense-high)" />
        )}
        {data.divergenceFlag === "consensus" && (
          <InkUnderline variant={(data.politicalLean + 1) % 3} color="var(--sense-low)" />
        )}
      </span>

      {/* Consensus X/Y stays in deep dive (void --verify) where it has context */}

      <SigilPopup
        triggerRef={ref} isOpen={open} onClose={() => hide()}
        onMouseEnter={keep} onMouseLeave={hide}
        id={tooltipId} data={data} instant={instant} size={size}
      />
    </div>
  );
}
