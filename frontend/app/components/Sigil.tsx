"use client";

import { useState, useRef, useEffect, useCallback, useId } from "react";
import { createPortal } from "react-dom";
import type { SigilData } from "../lib/types";

/* ==========================================================================
   Sigil — Lean-First Bias Indicator

   Hero: Political lean spectrum bar with animated marker
   Second: Source count badge
   Third: Binary Fact/Opinion badge
   On hover: Full detail popup with secondary scores

   Premium micro-interactions throughout. $100B product feel.
   ========================================================================== */

interface SigilProps {
  data: SigilData;
  size?: "sm" | "lg";
}

/* ── CSS variable cache (shared pattern) ──────────────────────────────── */

let cssVarCache: Record<string, string> | null = null;

const SSR_FALLBACK: Record<string, string> = {
  "--bias-left": "#3B82F6",
  "--bias-center-left": "#60A5FA",
  "--bias-center": "#9CA3AF",
  "--bias-center-right": "#F97316",
  "--bias-right": "#EF4444",
  "--sense-low": "#22C55E",
  "--sense-medium": "#EAB308",
  "--sense-high": "#EF4444",
  "--type-reporting": "#3B82F6",
  "--type-opinion": "#F97316",
  "--rigor-high": "#22C55E",
  "--rigor-medium": "#EAB308",
  "--rigor-low": "#EF4444",
};

function getColors(): Record<string, string> {
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
  const obs = new MutationObserver((muts) => {
    for (const m of muts) {
      if (m.type === "attributes" && m.attributeName === "data-mode") cssVarCache = null;
    }
  });
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-mode"] });
}

/* ── Color helpers ─────────────────────────────────────────────────────── */

function lerpColor(a: string, b: string, t: number): string {
  const ah = parseInt(a.slice(1), 16), bh = parseInt(b.slice(1), 16);
  const ar = (ah >> 16) & 0xff, ag = (ah >> 8) & 0xff, ab = ah & 0xff;
  const br = (bh >> 16) & 0xff, bg = (bh >> 8) & 0xff, bb = bh & 0xff;
  return `#${(
    ((Math.round(ar + (br - ar) * t) << 16) |
      (Math.round(ag + (bg - ag) * t) << 8) |
      Math.round(ab + (bb - ab) * t))
  ).toString(16).padStart(6, "0")}`;
}

function getLeanColor(v: number): string {
  const c = getColors();
  if (v <= 20) return c["--bias-left"];
  if (v <= 35) return lerpColor(c["--bias-left"], c["--bias-center-left"], (v - 20) / 15);
  if (v <= 45) return c["--bias-center-left"];
  if (v <= 55) return c["--bias-center"];
  if (v <= 65) return c["--bias-center-right"];
  if (v <= 80) return lerpColor(c["--bias-center-right"], c["--bias-right"], (v - 65) / 15);
  return c["--bias-right"];
}

function getLeanLabel(v: number): string {
  if (v <= 20) return "Far Left";
  if (v <= 35) return "Left";
  if (v <= 45) return "Center-Left";
  if (v <= 55) return "Center";
  if (v <= 65) return "Center-Right";
  if (v <= 80) return "Right";
  return "Far Right";
}

function getScoreColor(v: number, invert = false): string {
  const c = getColors();
  const s = invert ? 100 - v : v;
  if (s <= 30) return c["--sense-low"];
  if (s <= 60) return lerpColor(c["--sense-low"], c["--sense-medium"], (s - 30) / 30);
  if (s <= 80) return lerpColor(c["--sense-medium"], c["--sense-high"], (s - 60) / 20);
  return c["--sense-high"];
}

/* ── Interaction hook ──────────────────────────────────────────────────── */

function useSigilHover() {
  const [open, setOpen] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const show = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
    setOpen(true);
  }, []);

  const hide = useCallback(() => {
    timer.current = setTimeout(() => setOpen(false), 220);
  }, []);

  const toggle = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setOpen(v => !v);
  }, []);

  const onKey = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setOpen(v => !v); }
    if (e.key === "Escape") setOpen(false);
  }, []);

  const keepOpen = useCallback(() => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  useEffect(() => () => { if (timer.current) clearTimeout(timer.current); }, []);

  return { open, show, hide, toggle, onKey, keepOpen };
}

/* ── Animated count-up ─────────────────────────────────────────────────── */

function useCountUp(target: number, ms: number, active: boolean): number {
  const [v, setV] = useState(0);
  useEffect(() => {
    if (!active) { setV(0); return; }
    const t0 = performance.now();
    let raf: number;
    function tick(now: number) {
      const p = Math.min((now - t0) / ms, 1);
      const e = 1 - Math.pow(1 - p, 3);
      setV(Math.round(e * target));
      if (p < 1) raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, ms, active]);
  return v;
}

/* ── Detail popup ─────────────────────────────────────────────────────── */

function SigilPopup({
  triggerRef, isOpen, onClose, onMouseEnter, onMouseLeave, id, data,
}: {
  triggerRef: React.RefObject<HTMLElement | null>;
  isOpen: boolean;
  onClose: () => void;
  onMouseEnter: () => void;
  onMouseLeave: () => void;
  id: string;
  data: SigilData;
}) {
  const [pos, setPos] = useState<{ x: number; y: number } | null>(null);
  const [revealed, setRevealed] = useState(false);

  const lean = data.politicalLean;
  const leanColor = getLeanColor(lean);
  const leanLabel = getLeanLabel(lean);
  const isOpinion = data.opinionFact > 50;

  useEffect(() => {
    if (!isOpen || !triggerRef.current) { setRevealed(false); return; }
    const rect = triggerRef.current.getBoundingClientRect();
    const W = 300, H = 360;
    const spR = window.innerWidth - rect.right;
    const spL = rect.left;
    let x = spR > W + 16 ? rect.right + 10 : spL > W + 16 ? rect.left - W - 10 : Math.max(8, (window.innerWidth - W) / 2);
    const y = Math.max(8, Math.min(rect.top - 60, window.innerHeight - H - 16));
    setPos({ x, y });
    requestAnimationFrame(() => requestAnimationFrame(() => setRevealed(true)));
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

  const TIER_MAP: Record<string, string> = { us_major: "US Major", international: "Intl", independent: "Ind" };

  const secondaryAxes = [
    { label: "Sensationalism", value: data.sensationalism, desc: data.sensationalism <= 25 ? "Measured" : data.sensationalism <= 50 ? "Moderate" : data.sensationalism <= 75 ? "Elevated" : "Inflammatory" },
    { label: "Factual Rigor", value: data.factualRigor, desc: data.factualRigor >= 70 ? "High" : data.factualRigor >= 40 ? "Moderate" : "Low", invert: true },
    { label: "Framing", value: data.framing, desc: data.framing <= 25 ? "Neutral" : data.framing <= 55 ? "Some" : "Heavy" },
    { label: "Source Agreement", value: data.agreement, desc: data.agreement <= 25 ? "Agree" : data.agreement <= 55 ? "Mixed" : "Disagree" },
  ];

  return createPortal(
    <div
      id={id}
      role="tooltip"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      style={{
        position: "fixed", top: pos.y, left: pos.x, width: 300, zIndex: 9999,
        background: "var(--bg-card)", border: "1px solid var(--border-subtle)",
        boxShadow: "var(--shadow-e3)", pointerEvents: "auto",
        animation: "sigilPopupIn 280ms var(--spring) both",
      }}
    >
      {/* ── Header ── */}
      <div style={{
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "10px 14px 8px", borderBottom: "1px solid var(--border-subtle)",
      }}>
        <span style={{
          fontFamily: "var(--font-data)", fontSize: "var(--text-xs)", fontWeight: 500,
          letterSpacing: "0.08em", textTransform: "uppercase" as const, color: "var(--fg-tertiary)",
        }}>
          Bias Analysis
        </span>
        <span style={{
          fontFamily: "var(--font-editorial)", fontSize: 11, fontWeight: 600,
          color: isOpinion ? "var(--type-opinion)" : "var(--type-reporting)",
          padding: "1px 6px",
          border: `1px solid ${isOpinion ? "var(--type-opinion)" : "var(--type-reporting)"}`,
          opacity: 0.8,
        }}>
          {isOpinion ? "Opinion" : "Reporting"}
        </span>
      </div>

      {/* ── Hero: Lean Spectrum ── */}
      <div style={{ padding: "14px 14px 10px" }}>
        {/* Label */}
        <div style={{
          display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 8,
        }}>
          <span style={{
            fontFamily: "var(--font-structural)", fontSize: "var(--text-sm)",
            fontWeight: 600, color: leanColor,
            opacity: revealed ? 1 : 0,
            transition: "opacity 300ms var(--ease-out) 80ms",
          }}>
            {leanLabel}
          </span>
          <PopupCountScore target={lean} color={leanColor} revealed={revealed} delay={120} />
        </div>

        {/* Full spectrum bar */}
        <div style={{ position: "relative", height: 20, marginBottom: 6 }}>
          {/* Track */}
          <div style={{
            position: "absolute", left: 0, right: 0, top: 7, height: 6, borderRadius: 3,
            background: "linear-gradient(to right, var(--bias-left), var(--bias-center-left) 35%, var(--bias-center) 50%, var(--bias-center-right) 65%, var(--bias-right))",
            opacity: 0.35,
          }} />
          {/* Marker */}
          <div style={{
            position: "absolute", top: "50%", left: `${lean}%`,
            width: 12, height: 12, borderRadius: "50%",
            backgroundColor: leanColor,
            transform: revealed ? "translate(-50%, -50%) scale(1)" : "translate(-50%, -50%) scale(0)",
            transition: "transform 450ms var(--spring) 150ms, background-color 300ms var(--ease-out)",
            boxShadow: `0 0 0 3px var(--bg-card), 0 0 8px ${leanColor}44`,
          }} />
        </div>

        {/* Tick labels */}
        <div style={{
          display: "flex", justifyContent: "space-between",
          fontFamily: "var(--font-data)", fontSize: 8, letterSpacing: "0.04em",
          textTransform: "uppercase" as const, color: "var(--fg-muted)",
          opacity: revealed ? 1 : 0,
          transition: "opacity 300ms var(--ease-out) 200ms",
        }}>
          <span>Left</span>
          <span>Center</span>
          <span>Right</span>
        </div>
      </div>

      {/* ── Sources ── */}
      <div style={{
        padding: "8px 14px", borderTop: "1px solid var(--border-subtle)",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        opacity: revealed ? 1 : 0,
        transition: "opacity 300ms var(--ease-out) 250ms",
      }}>
        <span style={{
          fontFamily: "var(--font-data)", fontSize: "var(--text-xs)", color: "var(--fg-secondary)",
        }}>
          <strong>{data.sourceCount}</strong>{" "}
          <span style={{ color: "var(--fg-tertiary)" }}>source{data.sourceCount !== 1 ? "s" : ""}</span>
        </span>
        {data.tierBreakdown && (
          <div style={{ display: "flex", gap: 5 }}>
            {Object.entries(data.tierBreakdown).map(([tier, count]) =>
              (count as number) > 0 ? (
                <span key={tier} style={{
                  fontFamily: "var(--font-data)", fontSize: 9, padding: "1px 5px",
                  border: "1px solid var(--border-subtle)", borderRadius: 2,
                  color: "var(--fg-tertiary)",
                }}>
                  {TIER_MAP[tier] || tier}: {count as number}
                </span>
              ) : null
            )}
          </div>
        )}
      </div>

      {/* ── Secondary Scores ── */}
      <div style={{
        padding: "8px 14px 12px", borderTop: "1px solid var(--border-subtle)",
      }}>
        {secondaryAxes.map((axis, i) => (
          <SecondaryRow
            key={axis.label}
            label={axis.label}
            value={axis.value}
            desc={axis.desc}
            invert={axis.invert}
            revealed={revealed}
            delay={300 + i * 60}
          />
        ))}
      </div>
    </div>,
    document.body,
  );
}

/* ── Popup count-up score ──────────────────────────────────────────────── */

function PopupCountScore({ target, color, revealed, delay }: {
  target: number; color: string; revealed: boolean; delay: number;
}) {
  const v = useCountUp(target, 500, revealed);
  return (
    <span style={{
      fontFamily: "var(--font-data)", fontSize: 13, fontWeight: 700, color,
      opacity: revealed ? 1 : 0,
      transition: `opacity 250ms var(--ease-out) ${delay}ms`,
    }}>
      {v}
    </span>
  );
}

/* ── Secondary score row with animated bar ─────────────────────────────── */

function SecondaryRow({ label, value, desc, invert, revealed, delay }: {
  label: string; value: number; desc: string; invert?: boolean; revealed: boolean; delay: number;
}) {
  const color = getScoreColor(value, invert);
  const barPct = invert ? value : value; // always show magnitude

  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8, marginBottom: 5,
      opacity: revealed ? 1 : 0,
      transition: `opacity 280ms var(--ease-out) ${delay}ms`,
    }}>
      <span style={{
        fontFamily: "var(--font-data)", fontSize: 9, color: "var(--fg-tertiary)",
        width: 78, flexShrink: 0, letterSpacing: "0.02em",
      }}>
        {label}
      </span>
      <div style={{
        flex: 1, height: 4, backgroundColor: "var(--border-subtle)",
        borderRadius: 2, overflow: "hidden",
      }}>
        <div style={{
          width: revealed ? `${barPct}%` : "0%", height: "100%",
          backgroundColor: color, borderRadius: 2,
          transition: `width 500ms var(--ease-out) ${delay + 80}ms`,
        }} />
      </div>
      <span style={{
        fontFamily: "var(--font-data)", fontSize: 9, fontWeight: 500,
        color: "var(--fg-tertiary)", width: 42, textAlign: "right" as const,
        flexShrink: 0,
      }}>
        {desc}
      </span>
    </div>
  );
}

/* ── Lean spectrum bar (inline, compact) ──────────────────────────────── */

function LeanBar({ lean, size, mounted }: {
  lean: number; size: "sm" | "lg"; mounted: boolean;
}) {
  const color = getLeanColor(lean);
  const w = size === "lg" ? 140 : 80;
  const h = size === "lg" ? 6 : 4;
  const dot = size === "lg" ? 10 : 7;

  return (
    <div style={{
      position: "relative", width: w, height: dot + 4,
      display: "flex", alignItems: "center",
    }}>
      {/* Gradient track */}
      <div style={{
        position: "absolute", left: 0, right: 0,
        top: "50%", transform: "translateY(-50%)",
        height: h, borderRadius: h / 2,
        background: "linear-gradient(to right, var(--bias-left), var(--bias-center-left) 35%, var(--bias-center) 50%, var(--bias-center-right) 65%, var(--bias-right))",
        opacity: mounted ? 0.3 : 0.1,
        transition: "opacity 400ms var(--ease-out)",
      }} />

      {/* Active fill — from center to marker position */}
      <div style={{
        position: "absolute",
        top: "50%", transform: "translateY(-50%)",
        height: h, borderRadius: h / 2,
        left: lean < 50 ? `${lean}%` : "50%",
        width: mounted ? `${Math.abs(lean - 50)}%` : "0%",
        backgroundColor: color,
        opacity: 0.5,
        transition: "width 500ms var(--spring) 100ms, left 500ms var(--spring) 100ms, opacity 300ms var(--ease-out)",
      }} />

      {/* Marker dot */}
      <div style={{
        position: "absolute",
        top: "50%",
        left: mounted ? `${lean}%` : "50%",
        width: dot, height: dot,
        borderRadius: "50%",
        backgroundColor: color,
        transform: "translate(-50%, -50%)",
        transition: "left 600ms var(--spring) 80ms, background-color 300ms var(--ease-out), box-shadow 200ms var(--ease-out)",
        boxShadow: `0 0 0 2px var(--bg-card), 0 1px 4px ${color}55`,
      }} />
    </div>
  );
}

/* ── Source count badge ─────────────────────────────────────────────────── */

function SourceBadge({ count, size, mounted }: {
  count: number; size: "sm" | "lg"; mounted: boolean;
}) {
  const fontSize = size === "lg" ? 11 : 9;
  const dim = size === "lg" ? 22 : 16;
  const good = count >= 5;
  const great = count >= 10;

  return (
    <div style={{
      width: dim, height: dim, borderRadius: "50%",
      display: "flex", alignItems: "center", justifyContent: "center",
      backgroundColor: great ? "var(--sense-low)" : good ? "var(--sense-medium)" : "var(--border-subtle)",
      opacity: mounted ? (great ? 0.18 : good ? 0.15 : 0.12) : 0,
      transition: "opacity 350ms var(--ease-out) 200ms",
      position: "relative",
    }}>
      <span style={{
        fontFamily: "var(--font-data)", fontSize, fontWeight: 700,
        color: "var(--fg-secondary)", lineHeight: 1,
        opacity: mounted ? 1 : 0,
        transition: "opacity 300ms var(--ease-out) 250ms",
      }}>
        {count}
      </span>
    </div>
  );
}

/* ── Fact / Opinion binary badge ───────────────────────────────────────── */

function TypeBadge({ isOpinion, size, mounted }: {
  isOpinion: boolean; size: "sm" | "lg"; mounted: boolean;
}) {
  const fontSize = size === "lg" ? 9 : 7;
  const label = size === "lg"
    ? (isOpinion ? "OPINION" : "REPORT")
    : (isOpinion ? "OPN" : "RPT");

  return (
    <span style={{
      fontFamily: "var(--font-data)", fontSize, fontWeight: 600,
      letterSpacing: "0.06em",
      color: isOpinion ? "var(--type-opinion)" : "var(--type-reporting)",
      opacity: mounted ? 0.75 : 0,
      transition: "opacity 300ms var(--ease-out) 300ms",
      lineHeight: 1,
      padding: size === "lg" ? "2px 5px" : "1px 3px",
      border: `1px solid ${isOpinion ? "var(--type-opinion)" : "var(--type-reporting)"}`,
      borderRadius: 1,
      borderColor: isOpinion ? "var(--type-opinion)" : "var(--type-reporting)",
      // Subtle tinted background
      backgroundColor: isOpinion
        ? "color-mix(in srgb, var(--type-opinion) 6%, transparent)"
        : "color-mix(in srgb, var(--type-reporting) 6%, transparent)",
    }}>
      {label}
    </span>
  );
}

/* ── Main Sigil export ─────────────────────────────────────────────────── */

export default function Sigil({ data, size = "sm" }: SigilProps) {
  const ref = useRef<HTMLDivElement>(null);
  const { open, show, hide, toggle, onKey, keepOpen } = useSigilHover();
  const [mounted, setMounted] = useState(false);
  const tooltipId = `sigil-${useId()}`;

  const isOpinion = data.opinionFact > 50;
  const leanLabel = getLeanLabel(data.politicalLean);

  useEffect(() => {
    const t = setTimeout(() => setMounted(true), 60);
    return () => clearTimeout(t);
  }, []);

  const gap = size === "lg" ? 10 : 6;

  const ariaLabel = `Political lean: ${leanLabel} (${data.politicalLean}). ${data.sourceCount} sources. ${isOpinion ? "Opinion" : "Reporting"}. Press Enter for full bias analysis.`;

  return (
    <div
      ref={ref}
      className="sigil"
      onMouseEnter={show}
      onFocus={show}
      onMouseLeave={hide}
      onBlur={hide}
      onClick={toggle}
      onKeyDown={onKey}
      tabIndex={0}
      role="button"
      aria-expanded={open}
      aria-label={ariaLabel}
      aria-controls={open ? tooltipId : undefined}
      style={{
        display: "inline-flex", alignItems: "center", gap,
        cursor: "pointer", position: "relative",
        // Touch target minimum 44px height
        minHeight: 44, paddingTop: 4, paddingBottom: 4,
        opacity: data.pending ? 0.3 : 1,
        filter: data.pending ? "grayscale(1)" : "none",
        transition: "opacity 300ms var(--ease-out), filter 300ms var(--ease-out)",
      }}
    >
      {/* Source count */}
      <SourceBadge count={data.sourceCount} size={size} mounted={mounted} />

      {/* HERO: Lean spectrum bar */}
      <LeanBar lean={data.politicalLean} size={size} mounted={mounted} />

      {/* Fact / Opinion badge */}
      <TypeBadge isOpinion={isOpinion} size={size} mounted={mounted} />

      {/* Pending label */}
      {data.pending && (
        <span style={{
          fontFamily: "var(--font-data)", fontSize: 7, fontWeight: 500,
          letterSpacing: "0.04em", textTransform: "uppercase" as const,
          color: "var(--fg-tertiary)", whiteSpace: "nowrap",
        }}>
          Pending
        </span>
      )}

      {/* Detail popup */}
      <SigilPopup
        triggerRef={ref}
        isOpen={open}
        onClose={() => hide()}
        onMouseEnter={keepOpen}
        onMouseLeave={hide}
        id={tooltipId}
        data={data}
      />
    </div>
  );
}
