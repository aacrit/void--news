"use client";

import { useState, useRef, useEffect, useCallback, useId } from "react";
import { createPortal } from "react-dom";
import type { SigilData } from "../lib/types";
import { getLeanColor as leanColor, leanLabel } from "../lib/biasColors";

/* ==========================================================================
   Sigil — The Dial

   The void scale silhouette is the brand mark. A single lean-colored dot
   on the circle's upper semicircle acts as a gauge needle. Source count
   sits centered inside the void.

     Dial dot position → political lean (9 o'clock = left, 3 o'clock = right)
     Dial dot color    → lean spectrum (blue → gray → red)
     Center number     → source count
     Scale shape       → always neutral, always level — pure brand element

   sm (feed): Non-interactive indicator. Click passes through to story card.
   lg/xl (cards, Deep Dive): Interactive — hover/tap reveals spectrum popup.
   ========================================================================== */

interface SigilProps {
  data: SigilData;
  size?: "sm" | "lg" | "xl";
  /** Skip mount animation (mobile) */
  instant?: boolean;
}

/* ── Hover hook (lg/xl only) ──────────────────────────────────────────── */

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

/* ── Dial dot position ────────────────────────────────────────────────── */

function dialXY(lean: number): { x: number; y: number } {
  // Upper semicircle: 0 (far left) → 9 o'clock, 50 → 12 o'clock, 100 → 3 o'clock
  const angle = Math.PI * (1 - lean / 100);
  return { x: 16 + 9 * Math.cos(angle), y: 13 - 9 * Math.sin(angle) };
}

/* ── Data-encoded brand mark ─────────────────────────────────────────── */

function DataMark({ data, size, mounted }: {
  data: SigilData; size: "sm" | "lg" | "xl"; mounted: boolean;
}) {
  const px = size === "xl" ? 56 : size === "lg" ? 42 : 28;
  const lc = leanColor(data.politicalLean);
  const dot = dialXY(data.politicalLean);
  const dotR = size === "sm" ? 2 : 2.5;

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
      {/* Void circle — neutral brand element */}
      <circle cx="16" cy="13" r="9"
        stroke="var(--fg-tertiary)" strokeWidth="1.8" opacity={0.35}
      />

      {/* Beam — always level, pure brand (no tilt) */}
      <line x1="4" y1="13" x2="28" y2="13"
        stroke="var(--fg-tertiary)" strokeWidth="1.8" opacity={0.3}
      />
      {/* Left weight tick */}
      <line x1="6" y1="11.5" x2="6" y2="14.5"
        stroke="var(--fg-tertiary)" strokeWidth="1.4" opacity={0.25}
      />
      {/* Right weight tick */}
      <line x1="26" y1="11.5" x2="26" y2="14.5"
        stroke="var(--fg-tertiary)" strokeWidth="1.4" opacity={0.25}
      />

      {/* Center post */}
      <line x1="16" y1="22" x2="16" y2="28"
        stroke="var(--fg-tertiary)" strokeWidth="1.4" opacity={0.2}
      />
      {/* Base */}
      <line x1="12" y1="28.5" x2="20" y2="28.5"
        stroke="var(--fg-tertiary)" strokeWidth="1.8" opacity={0.15}
      />

      {/* Dial dot — the only colored element, gauge needle on the void circle */}
      <circle
        cx={dot.x} cy={dot.y}
        r={dotR}
        fill={lc}
        stroke="var(--bg-card)" strokeWidth="1.2"
        style={{
          opacity: mounted ? 1 : 0,
          transition: "opacity 350ms var(--ease-out) 150ms, fill 400ms var(--ease-out)",
        }}
      />

      {/* Source count — centered in the void */}
      <text x="16" y="13.5" textAnchor="middle" dominantBaseline="central"
        style={{
          fontFamily: "var(--font-data)", fontSize: 8, fontWeight: 700,
          fill: "var(--fg-secondary)",
          opacity: mounted ? 0.8 : 0,
          transition: "opacity 400ms var(--ease-out) 200ms",
        }}
      >
        {data.sourceCount}
      </text>
    </svg>
  );
}

/* ── Popup (lg/xl only): spectrum + sources ──────────────────────────── */

function SigilPopup({ triggerRef, isOpen, onClose, onMouseEnter, onMouseLeave, id, data }: {
  triggerRef: React.RefObject<HTMLElement | null>;
  isOpen: boolean; onClose: () => void;
  onMouseEnter: () => void; onMouseLeave: () => void;
  id: string; data: SigilData;
}) {
  const [pos, setPos] = useState<{ x: number; y: number; mobile: boolean } | null>(null);
  const [visible, setVisible] = useState(false);

  const lean = data.politicalLean;
  const lc = leanColor(lean);
  const ll = leanLabel(lean);

  useEffect(() => {
    if (!isOpen || !triggerRef.current) { setVisible(false); return; }
    const mobile = window.innerWidth < 768;
    if (mobile) {
      setPos({ x: 0, y: 0, mobile: true });
    } else {
      const r = triggerRef.current.getBoundingClientRect();
      const W = 260, H = 200;
      const spR = window.innerWidth - r.right;
      const x = spR > W + 16 ? r.right + 10 : r.left > W + 16 ? r.left - W - 10 : Math.max(8, (window.innerWidth - W) / 2);
      const y = Math.max(8, Math.min(r.top - 40, window.innerHeight - H - 16));
      setPos({ x, y, mobile: false });
    }
    const t = setTimeout(() => setVisible(true), 20);
    return () => clearTimeout(t);
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
  const isMobile = pos.mobile;
  const RING_R = 16;
  const RING_CIRC = 2 * Math.PI * RING_R;

  return createPortal(
    <>
      {isMobile && (
        <div className="sigil-popup__backdrop" onClick={onClose} style={{
          opacity: visible ? 1 : 0,
        }} />
      )}
      <div id={id} role={isMobile ? "dialog" : "tooltip"}
        aria-modal={isMobile ? true : undefined}
        aria-label={isMobile ? "Bias analysis details" : undefined}
        onMouseEnter={onMouseEnter} onMouseLeave={onMouseLeave}
        className={isMobile ? "sigil-popup sigil-popup--mobile" : "sigil-popup sigil-popup--desktop"}
        style={isMobile ? {
          transform: visible ? "translateY(0)" : "translateY(100%)",
        } : {
          top: pos.y, left: pos.x,
          opacity: visible ? 1 : 0,
          transform: visible ? "scale(1) translateY(0)" : "scale(0.94) translateY(6px)",
        }}
      >
        {/* ═══ Lean spectrum ═══ */}
        <div className="sigil-popup__section" style={{
          opacity: visible ? 1 : 0,
          transition: "opacity 200ms var(--ease-out)",
        }}>
          <div className="sigil-popup__header">
            <span className="sigil-popup__label" style={{ color: lc }}>{ll}</span>
            <span className="sigil-popup__score" style={{ color: lc }}>{lean}</span>
          </div>
          <div className="sigil-popup__spectrum">
            <div className="sigil-popup__spectrum-tick sigil-popup__spectrum-tick--left" />
            <div className="sigil-popup__spectrum-tick sigil-popup__spectrum-tick--right" />
            <div className="sigil-popup__spectrum-track" />
            <div className="sigil-popup__spectrum-marker-area">
              <div className="sigil-popup__spectrum-dot" style={{
                left: `${lean}%`,
                backgroundColor: lc,
                transform: visible ? "translate(-50%, -50%) scale(1)" : "translate(-50%, -50%) scale(0)",
                boxShadow: `0 0 0 2.5px var(--bg-card)`,
              }} />
            </div>
          </div>
          <div className="sigil-popup__spectrum-labels">
            <span>Left</span><span>Center</span><span>Right</span>
          </div>
        </div>

        {/* ═══ Source coverage ═══ */}
        <div className="sigil-popup__section sigil-popup__scores" style={{
          alignItems: "center",
          opacity: visible ? 1 : 0,
          transition: "opacity 200ms var(--ease-out) 60ms",
        }}>
          <svg viewBox="0 0 40 40" width="40" height="40" fill="none" className="sigil-popup__ring-svg">
            <circle cx="20" cy="20" r={RING_R} stroke="var(--border-subtle)" strokeWidth="2.5" opacity={0.25} />
            <circle cx="20" cy="20" r={RING_R}
              stroke={lc} strokeWidth="2.5" strokeLinecap="round"
              strokeDasharray={`${visible ? Math.min(data.sourceCount / 10, 1) * RING_CIRC : 0} ${RING_CIRC}`}
              style={{ transform: "rotate(-90deg)", transformOrigin: "20px 20px", transition: "stroke-dasharray 600ms var(--spring)" }}
              opacity={0.6}
            />
            <text x="20" y="20" textAnchor="middle" dominantBaseline="central"
              className="sigil__popup-lean"
            >
              {data.sourceCount}
            </text>
          </svg>
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
      </div>
    </>,
    document.body,
  );
}

/* ── Main Sigil ────────────────────────────────────────────────────────── */

export default function Sigil({ data, size = "sm", instant = false }: SigilProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInteractive = size === "lg" || size === "xl";
  const { open, show, hide, toggle, onKey, keep } = useHover();
  const [mounted, setMounted] = useState(false);
  const tooltipId = `sigil-${useId()}`;

  const ll = leanLabel(data.politicalLean);
  const lc = leanColor(data.politicalLean);

  useEffect(() => {
    if (instant) { setMounted(true); return; }
    const t = setTimeout(() => setMounted(true), 60);
    return () => clearTimeout(t);
  }, [instant]);

  const aria = `Political lean: ${ll} (${data.politicalLean}). ${data.sourceCount} sources.${isInteractive ? " Press Enter for details." : ""}`;

  return (
    <div ref={ref} className={`sigil sigil--${size}`}
      aria-label={aria}
      {...(isInteractive ? {
        onMouseEnter: show, onFocus: show, onMouseLeave: hide, onBlur: hide,
        onClick: toggle, onKeyDown: onKey,
        tabIndex: 0, role: "button" as const, "aria-expanded": open,
        "aria-controls": open ? tooltipId : undefined,
      } : {})}
      style={{
        opacity: data.pending ? 0.3 : 1,
        filter: data.pending ? "grayscale(1)" : "none",
        ...(!isInteractive ? { pointerEvents: "none" as const } : {}),
      }}
    >
      <DataMark data={data} size={size} mounted={mounted} />

      <span className="sigil__lean-label" style={{
        fontSize: size === "sm" ? "var(--text-xs)" : "var(--text-sm)",
        color: lc,
        opacity: mounted ? 1 : 0,
      }}>
        {ll}
      </span>

      {isInteractive && (
        <SigilPopup
          triggerRef={ref} isOpen={open} onClose={() => hide()}
          onMouseEnter={keep} onMouseLeave={hide}
          id={tooltipId} data={data}
        />
      )}
    </div>
  );
}
