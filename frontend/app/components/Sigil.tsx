"use client";

import { useState, useRef, useEffect, useCallback, useId } from "react";
import { createPortal } from "react-dom";
import type { SigilData } from "../lib/types";
import {
  getColors as gc,
  getLeanColor as leanColor,
  getSigilLeanColor,
  DIVERGENT_SPREAD_MIN,
  storyShapeLabel,
  leanShapeDescriptor,
  leanShapeDirection,
  leanShape,
  leanToDisplayPos,
  lerpColor as lerp,
} from "../lib/biasColors";
import MicroSpectrum from "./MicroSpectrum";
import RosterStrip from "./RosterStrip";
import { fetchSourceLeans } from "../lib/supabase";

/** Session-level cache: storyId → lean values. Avoids re-fetching on re-hover. */
const leanCache = new Map<string, number[]>();

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
  /** Story cluster ID — enables real KDE in the popup spectrum (matches DeepDive shape) */
  storyId?: string;
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
const CIRC_GEOMETRIC = 69.1; // 2π × 11 ≈ 69.1 (true circle r=11, cx=16, cy=14)

/* ── Compact data-mark: the logo encoding live data ───────────────────── */

function DataMark({ data, size, mounted }: {
  data: SigilData; size: "sm" | "lg" | "xl"; mounted: boolean; mode?: "facts";
}) {
  const lean = data.politicalLean;
  const isUnscored = !!data.unscored;
  // Beam tilt AND color both use the shared perceptual-expansion curve
  // (biasColors leanToDisplayPos) so subtle center-left/center-right tilt
  // registers — both in angle and in hue — the way saturated extremes do.
  // Coloring the RAW lean left the solid green band (46-55) swallowing every
  // near-center story; coloring the expanded position shrinks green to ~±1.4
  // of true center, so a 47/53 reads blue/red. Confidence-damped (thin
  // clusters near 50 don't swing on noise); angle saturates near ±24°.
  const conf = data.biasSpread?.aggregateConfidence ?? 1;
  const leanSpread = data.biasSpread?.leanSpread ?? 0;
  const displayLean = leanToDisplayPos(lean, conf);
  // The mark obeys the same gate as the caption. Only a confident read tilts
  // the beam; a balanced or contested story sits level; an unmeasured one
  // sits level in the muted ink. (A beam that tilted under a "Flat" caption
  // was the mark disagreeing with its own label.)
  /* THE MARK READS THE ROSTER (2026-09-21).
     It obeyed a confidence gate on the mean before, which tilted the beam on
     1 story in 35 and left it level and mute on the rest: the brand's most
     distinctive asset doing nothing on the whole front page. The roster's
     shape is available on every story that has coverage, so the mark has four
     states instead of one, and each is a thing the geometry can already say.

       leans      beam tilts, as it always did, now earned by the wings
       split      the beam PARTS: two arms at the real wing positions, the
                  centre left hollow. A scale pulled both ways, which is what
                  a split story is
       consensus  dead level and crisp, centre marked: everyone framed it alike
       thin       level and dashed: not a reading, and it does not pretend

     The two arms are not new geometry. The divergence fan below has always
     drawn them; it was driven by a standard deviation, so it read as
     decoration. Driven by the real left and right mass it becomes the
     measurement. */
  const shape = isUnscored ? "thin" : leanShape(data.biasSpread);
  const gate = shape === "thin" ? "unmeasured"
    : shape === "leans" ? "confident"
    : shape === "split" ? "contested" : "balanced";
  const measured = shape !== "thin";
  /* The beam tilts the way the WORD says. Its magnitude still comes from the
     mean, but its sign comes from the roster: a "Leans left" roster whose mean
     sat a point right of 50 used to draw a beam tipped right under the word
     "left". A minimum of 6 degrees keeps an earned lean visible. */
  const beamAngle = shape === "leans"
    ? leanShapeDirection(data.biasSpread) * Math.max(6, Math.abs(((displayLean - 50) / 50) * 24))
    : 0;
  /* Split draws its own arms from the wing counts, so the stdev-driven fan
     stands down there and the two cannot contradict each other. */
  const wingL = data.biasSpread?.leanLeftCount ?? 0;
  const wingR = data.biasSpread?.leanRightCount ?? 0;
  const wingTotal = wingL + wingR;
  const splitArms = shape === "split" && wingTotal > 0
    ? {
        left: -Math.min(24, 8 + 16 * (wingL / wingTotal)),
        right: Math.min(24, 8 + 16 * (wingR / wingTotal)),
      }
    : null;
  // Color = lean (expanded), EXCEPT a balanced-but-divergent standoff drops the
  // green for a neutral slate — green is reserved for genuine consensus
  // (balanced AND agreed). See getSigilLeanColor.
  // Colour follows the gate too: a balanced or contested story takes the
  // centre colour (green when agreed, slate when split), never a hue that
  // hints at a direction the caption withholds.
  const beamCol = !measured
    ? "var(--fg-muted)"
    : gate === "confident"
      /* Clamped to the side the roster names, so the beam's hue cannot
         contradict its tilt or the word under it. */
      ? getSigilLeanColor(
          leanShapeDirection(data.biasSpread) > 0 ? Math.max(lean, 56) : Math.min(lean, 44),
          leanSpread, conf)
      : getSigilLeanColor(50, leanSpread, conf);

  // Divergence fan — agreed vs divergent, shown in the mark itself. The beam
  // half-angle scales with how spread the source leans are (leanSpread): a
  // thin/absent fan = sources agree; a wide fan = they diverge. Each arm is
  // colored by its OWN fanned position, so a balanced-but-divergent story
  // shows a neutral slate center beam flanked by a blue (left) and a red
  // (right) arm — visibly contested even though the mean sits at center.
  // Only open the fan once the lean spread is genuinely divergent (stddev ≥ 10):
  // agreed stories keep a single crisp beam, divergent ones fan wider with more
  // spread (10→40 maps to a 5°→22° half-angle).
  const showFan = measured && !splitArms && leanSpread >= DIVERGENT_SPREAD_MIN;
  const coneHalf = showFan
    ? 5 + ((Math.min(leanSpread, 40) - 10) / 30) * 17
    : 0;
  const fanColor = (deg: number) =>
    leanColor(Math.max(0, Math.min(100, 50 + (deg / 24) * 50)));

  // Circle r=11 (was r=9) — larger mark, more room in lower semi-circle.
  // px sizes: sm=40, lg=56, xl=72 — The Moat, no horizontal saving.
  const px = size === "xl" ? 72 : size === "lg" ? 56 : 40;
  // All sizes now use geometric precision — circle + straight beam
  const isOrganic = false;

  // Source coverage Harvey ball — ring fill proportional to source count
  const coverage = Math.min(data.sourceCount / 15, 1);
  const circ = isOrganic ? CIRC_ORGANIC : CIRC_GEOMETRIC;
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
      {/* Coverage ring — geometric at sm/lg (precision), organic at xl (Deep Dive texture) */}
      {isOrganic ? (
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
      ) : (
        <>
          {/* Background ring (geometric) */}
          <circle cx="16" cy="14" r="11"
            stroke="var(--border-subtle)" strokeWidth="1.8" opacity={0.3} fill="none"
          />
          {/* Fill ring (geometric Harvey ball) */}
          <circle cx="16" cy="14" r="11"
            stroke={ringCol} strokeWidth="1.8" fill="none"
            strokeDasharray={`${mounted ? ringFill : 0} ${CIRC_GEOMETRIC}`}
            style={{
              transform: "rotate(-90deg)", transformOrigin: "16px 14px",
              transition: "stroke-dasharray 700ms var(--spring) 120ms, stroke 400ms var(--ease-out)",
            }}
            opacity={0.9}
          />
        </>
      )}

      {/* Divergence fan — faded arms behind the main beam. Width = leanSpread
          (agreement when thin/absent, divergent when wide). Arms colored by
          their own fanned position so a contested story spans blue → red. */}
      {showFan && (
        <>
          <g style={{
            transformOrigin: "16px 14px",
            transform: `rotate(${mounted ? beamAngle - coneHalf : 0}deg)`,
            transition: "transform var(--beam-tilt-dur, 800ms) var(--spring-beam, var(--spring)) var(--beam-tilt-delay, 60ms)",
          }}>
            <line x1="4" y1="14" x2="28" y2="14"
              stroke={fanColor(beamAngle - coneHalf)} strokeWidth="1.3"
              style={{ transition: "stroke 500ms var(--ease-rack) 200ms, opacity 500ms" }}
              opacity={mounted ? 0.4 : 0}
            />
          </g>
          <g style={{
            transformOrigin: "16px 14px",
            transform: `rotate(${mounted ? beamAngle + coneHalf : 0}deg)`,
            transition: "transform var(--beam-tilt-dur, 800ms) var(--spring-beam, var(--spring)) var(--beam-tilt-delay, 60ms)",
          }}>
            <line x1="4" y1="14" x2="28" y2="14"
              stroke={fanColor(beamAngle + coneHalf)} strokeWidth="1.3"
              style={{ transition: "stroke 500ms var(--ease-rack) 200ms, opacity 500ms" }}
              opacity={mounted ? 0.4 : 0}
            />
          </g>
        </>
      )}

      {/* SPLIT: the beam parts. Two arms at the real wing positions with a
          hollow centre, drawn instead of the single beam. The angles come
          from the left and right counts, so a 7-to-8 story opens nearly
          symmetrically and a 12-to-5 one leans as it parts. */}
      {splitArms && (
        <g className="sigil__split">
          <g style={{
            transformOrigin: "16px 14px",
            transform: `rotate(${mounted ? splitArms.left : 0}deg)`,
            transition: "transform var(--beam-tilt-dur, 800ms) var(--spring-beam, var(--spring)) var(--beam-tilt-delay, 60ms)",
          }}>
            <line x1="4" y1="14" x2="14" y2="14"
              stroke="var(--bias-left)" strokeWidth="1.8"
              opacity={mounted ? 1 : 0.3}
              style={{ transition: "stroke 500ms var(--ease-rack) 200ms, opacity 500ms" }} />
          </g>
          <g style={{
            transformOrigin: "16px 14px",
            transform: `rotate(${mounted ? splitArms.right : 0}deg)`,
            transition: "transform var(--beam-tilt-dur, 800ms) var(--spring-beam, var(--spring)) var(--beam-tilt-delay, 60ms)",
          }}>
            <line x1="18" y1="14" x2="28" y2="14"
              stroke="var(--bias-right)" strokeWidth="1.8"
              opacity={mounted ? 1 : 0.3}
              style={{ transition: "stroke 500ms var(--ease-rack) 200ms, opacity 500ms" }} />
          </g>
          {/* The hollow itself, stated rather than left blank. */}
          <line x1="14.6" y1="14" x2="17.4" y2="14"
            stroke="var(--divider)" strokeWidth="1" opacity={mounted ? 0.55 : 0} />
        </g>
      )}

      {/* Beam group — pivots around circle center, tilts by lean */}
      {!splitArms && (
      <g className="sigil__beam-group" style={{
        transformOrigin: "16px 14px",
        transform: `rotate(${mounted ? beamAngle : 0}deg)`,
        transition: "transform var(--beam-tilt-dur, 800ms) var(--spring-beam, var(--spring)) var(--beam-tilt-delay, 60ms)",
      }}>
        {/* Beam — straight line from edge to edge of circle */}
        {isOrganic ? (
          <path d="M4 14 C10 13.3 22 14.7 28 14"
            stroke={beamCol} strokeWidth="1.8"
            style={{ transition: "stroke 500ms var(--ease-rack) 200ms" }}
            opacity={mounted ? 1 : 0.3}
          />
        ) : (
          <line x1="4" y1="14" x2="28" y2="14"
            stroke={beamCol} strokeWidth="1.8"
            style={{ transition: "stroke 500ms var(--ease-rack) 200ms" }}
            opacity={mounted ? 1 : 0.3}
          />
        )}
        {/* Weight ticks — outside the r=11 circle (circle edge at x=5/x=27) */}
        {size !== "sm" && (
          <>
            <line x1="4.2" y1="12.5" x2="3.8" y2="15.5"
              stroke={beamCol} strokeWidth="1.4"
              style={{ transition: "stroke 500ms var(--ease-rack) 200ms" }}
              opacity={mounted ? 0.85 : 0.2}
            />
            <line x1="27.8" y1="12.5" x2="28.2" y2="15.5"
              stroke={beamCol} strokeWidth="1.4"
              style={{ transition: "stroke 500ms var(--ease-rack) 200ms" }}
              opacity={mounted ? 0.85 : 0.2}
            />
          </>
        )}
      </g>
      )}

      {/* Source count — lower semi-circle.
          r=11, cy=14: chord at y=20 = 18.4 viewBox units, inner ≈ 14.8.
          font-size 6 × 3 digits × 0.60 aspect = 10.8 units — 4 units breathing room. */}
      <text x="16" y="20" textAnchor="middle" dominantBaseline="central"
        style={{
          fontFamily: "var(--font-data)", fontSize: 6, fontWeight: 700,
          fill: "var(--fg-secondary)",
          opacity: mounted ? 0.85 : 0,
          transition: "opacity 400ms var(--ease-out) 300ms",
        }}
      >
        {data.sourceCount}
      </text>

      {/* Center post — from circle bottom (y=25) to base */}
      <line x1="16" y1="25" x2="16" y2="29"
        stroke="var(--fg-tertiary)" strokeWidth="1.4"
        opacity={mounted ? 0.4 : 0.15}
        style={{ transition: "opacity 300ms var(--ease-out) 200ms" }}
      />

      {/* Base — wider to match larger circle */}
      <path d="M11 30.5 C13.5 30.2 18.5 30.8 21 30.5"
        stroke="var(--fg-tertiary)" strokeWidth="1.8"
        opacity={mounted ? 0.3 : 0.1}
        style={{ transition: "opacity 400ms var(--ease-out) 250ms" }}
      />
    </svg>
  );
}

/* ── Popup: the mark unfolds ──────────────────────────────────────────── */

function SigilPopup({ triggerRef, isOpen, onClose, onMouseEnter, onMouseLeave, id, data, instant = false, size = "sm", storyId }: {
  triggerRef: React.RefObject<HTMLElement | null>;
  isOpen: boolean; onClose: () => void;
  onMouseEnter: () => void; onMouseLeave: () => void;
  id: string; data: SigilData; instant?: boolean; size?: "sm" | "lg" | "xl";
  storyId?: string;
}) {
  const [pos, setPos] = useState<{ x: number; y: number; mobile: boolean } | null>(null);
  const [stage, setStage] = useState(0); // 0=hidden, 1=mark, 2=beam, 3=circle, 4=details

  const lean = data.politicalLean;
  const popupUnscored = !!data.unscored;
  /* The popup states the roster, so it needs the same shape the mark does. */
  const shape = popupUnscored ? "thin" : leanShape(data.biasSpread);
  // The popup heading is the card's own word, from the same rule (see
  // storyShapeLabel). The raw mean is not printed beside it: the card stopped
  // printing it because a mean over a bimodal roster reads as a position no
  // outlet holds, and a popup that printed it would disagree with the card.
  const popupInfo = storyShapeLabel(data.biasSpread, popupUnscored);
  const lc = popupInfo.color;
  const ll = popupInfo.text;
  const full = isFullDetail(size);

  // "Lean measured from 9 of 34 analyzed articles." Shown only when some
  // coverage was genuinely excluded, so the common fully-measured case stays
  // uncluttered. Hidden entirely when nothing was measured — the label is
  // already "Not measured"/"Unscored" there and a "0 of N" line would just be noise.
  const measured = data.biasSpread?.leanMeasuredCount;
  const measuredTotal = data.biasSpread?.leanTotalCount;
  const measuredNote =
    typeof measured === "number" &&
    typeof measuredTotal === "number" &&
    measured > 0 &&
    measured < measuredTotal
      ? `Lean measured from ${measured} of ${measuredTotal} analyzed articles`
      : null;

  /** Real per-source lean values — loaded on first popup open, cached by storyId */
  const [sourceLeans, setSourceLeans] = useState<number[] | null>(null);

  useEffect(() => {
    if (!isOpen || !storyId) return;
    // Serve from cache immediately if available
    if (leanCache.has(storyId)) {
      setSourceLeans(leanCache.get(storyId)!);
      return;
    }
    // Fetch lean values — lightweight query, only political_lean column
    fetchSourceLeans(storyId).then((leans) => {
      if (leans.length > 0) {
        leanCache.set(storyId, leans);
        setSourceLeans(leans);
      }
    });
  }, [isOpen, storyId]);

  useEffect(() => {
    if (!isOpen || !triggerRef.current) { setStage(0); return; }
    const mobile = window.innerWidth < 768;
    if (mobile) {
      // Bottom sheet positioning on mobile
      setPos({ x: 0, y: 0, mobile: true });
    } else {
      const r = triggerRef.current.getBoundingClientRect();
      const W = 280, H = 200;
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
        </div>
        {/* Contextual descriptor — explains what the score means */}
        {stage >= 2 && (
          <p className="sigil-popup__descriptor">
            {popupUnscored ? "Too few measured articles to read the coverage" : leanShapeDescriptor(data.biasSpread)}
          </p>
        )}
        {/* Measurement coverage. Most outlets in the roster are not placed on
            the left/right axis, and their calm copy carries no partisan signal,
            so they are real coverage but not a lean reading and are excluded
            from the mean (migration 078). Say so rather than implying the whole
            roster voted on this number. */}
        {stage >= 2 && measuredNote && (
          <p className="sigil-popup__measured">{measuredNote}</p>
        )}
        {/* KDE spectrum — real shape when source leans are loaded, Gaussian fallback */}
        <div className="sigil-popup__spectrum">
          <div className="sigil-popup__spectrum-tick sigil-popup__spectrum-tick--left" />
          <div className="sigil-popup__spectrum-tick sigil-popup__spectrum-tick--right" />
          <MicroSpectrum
            mean={lean}
            spread={data.biasSpread?.leanSpread ?? 12}
            leans={sourceLeans ?? undefined}
            height={40}
            showMarker={true}
            strokeWidth={1.4}
            className="sigil-popup__spectrum-curve"
          />
        </div>
        {/* Tick labels */}
        <div className="sigil-popup__spectrum-labels">
          <span>Left</span><span>Center</span><span>Right</span>
        </div>
      </div>

      {full ? (
        <>
          {/* ═══ SECTION 2: Source count — compact ═══ */}
          <div className="sigil-popup__section" style={{
            opacity: stage >= 3 ? 1 : 0,
            transition: "opacity 280ms var(--ease-out)",
          }}>
            <div className="sigil-popup__source-label">
              {data.sourceCount} source{data.sourceCount !== 1 ? "s" : ""}
            </div>
            {data.tierBreakdown && (
              <div className="sigil-popup__tier-list" style={{ marginTop: 4 }}>
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
        </>
      ) : (
        /* ═══ SIMPLIFIED: Compact summary for feed-level Sigil (sm) ═══ */
        <div className="sigil-popup__section sigil-popup__compact" style={{
          opacity: stage >= 3 ? 1 : 0,
          transition: "opacity 280ms var(--ease-out)",
        }}>
          {/* Human sentence: what the data actually says */}
          <p className="sigil-popup__compact-sentence">
            {(() => {
              /* The roster in a sentence. It names the counts rather than a
                 verdict, so the line is true at any sample size. */
              const L = data.biasSpread?.leanLeftCount ?? 0;
              const C = data.biasSpread?.leanCenterCount ?? 0;
              const R = data.biasSpread?.leanRightCount ?? 0;
              const n = L + C + R;
              const of = `${n} measured article${n !== 1 ? "s" : ""}`;
              if (shape === "thin") return `${of}, too few to read the coverage.`;
              if (shape === "consensus") return `${C} of ${of} sit in the centre.`;
              if (shape === "split") return `${L} left and ${R} right, of ${of}.`;
              if (shape === "balanced") return `${L} left and ${R} right, of ${of}, evenly matched.`;
              return `${of}: ${L} left, ${C} centre, ${R} right.`;
            })()}
          </p>
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
  const path = INK_UNDERLINES[(Math.round(Number(variant)) || 0) % INK_UNDERLINES.length];
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

export default function Sigil({ data, size = "sm", mode = "facts", instant = false, storyId }: SigilProps) {
  const ref = useRef<HTMLDivElement>(null);
  const { open, show, hide, toggle, onKey, keep } = useHover();
  const [mounted, setMounted] = useState(false);
  const tooltipId = `sigil-${useId()}`;

  const unscored = !!data.unscored;
  // One word, one rule. The printed line, the aria-label, the popup and the
  // Deep Dive chip all read storyShapeLabel. The aria-label used to read the
  // gated mean (storyLeanLabel) while the card printed the roster's word, so
  // "Leans left" was announced as "Not measured" (2026-09-25 edition).
  const info = storyShapeLabel(data.biasSpread, unscored);
  const full = isFullDetail(size);

  useEffect(() => { const t = setTimeout(() => setMounted(true), 60); return () => clearTimeout(t); }, []);

  const aria = `Coverage: ${info.text}. ${data.sourceCount} sources. Press Enter for details.`;

  const ringClass = data.divergenceFlag === "divergent"
    ? " sigil--divergent"
    : data.divergenceFlag === "consensus"
      ? " sigil--consensus"
      : "";

  const ringTitle = data.divergenceFlag === "divergent"
    ? "Sources split on this story"
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

      {/* The register: the roster's shape, under the mark. Seven strokes, one
          per bucket. It replaces the printed 0-100 score, which was a mean
          over a frequently bimodal distribution and was withheld on 20 of 35
          stories. See components/RosterStrip.tsx. */}
      <RosterStrip spread={data.biasSpread} className="sigil__roster" />

      {/* The one line under it. The roster's own word, not a gated mean. */}
      <span className="sigil__lean-label" style={{
        /* The register's word and the register's colour, one rule. See
           leanShapeColor: displayLabel.color is the old gated ramp, and it
           disagreed with the word printed over it. */
        color: info.color,
        opacity: mounted ? 1 : 0,
      }}>
        {info.text}
        {data.divergenceFlag === "divergent" && (
          <InkUnderline variant={(Math.round(Number(data.politicalLean)) || 0) % 3} color="var(--sense-high)" />
        )}
        {data.divergenceFlag === "consensus" && (
          <InkUnderline variant={((Math.round(Number(data.politicalLean)) || 0) + 1) % 3} color="var(--sense-low)" />
        )}
      </span>

      {/* Consensus X/Y stays in deep dive (void --verify) where it has context */}

      <SigilPopup
        triggerRef={ref} isOpen={open} onClose={() => hide()}
        onMouseEnter={keep} onMouseLeave={hide}
        id={tooltipId} data={data} instant={instant} size={size} storyId={storyId}
      />
    </div>
  );
}
