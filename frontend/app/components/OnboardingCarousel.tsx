"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { createPortal } from "react-dom";

/* ---------------------------------------------------------------------------
   OnboardingCarousel — "The Prologue"

   4-scene cinematic product introduction:
   Scene 1: "The Void" — divergent headlines reveal the problem
   Scene 2: "The Instrument" — organic Sigil draws itself, beam sweeps
   Scene 3: "The Worlds" — 6 product pages in native design language
   Scene 4: "The Verdict" — read with clarity

   All SVGs use organic bezier paths matching ScaleIcon/Sigil production marks.
   No perfect circles — hand-drawn ink aesthetic throughout.

   Controlled by UnifiedOnboarding via visible/onComplete/onSkip.
   --------------------------------------------------------------------------- */

/* ── Organic SVG path constants (matching ScaleIcon/Sigil production) ── */
const VOID_CIRCLE = "M16 4 C24 3.5 25.5 7.5 25 13 C24.5 18.5 22.5 22 16 22 C9.5 22 7.5 18.5 7 13 C6.5 7.5 8 3.5 16 4";
const BEAM_CURVE = "M3 13 C10 12.2 22 13.8 29 13";
const BASE_CURVE = "M12 29 C14 28.7 18 29.3 20 29";
const VOID_CIRC_LEN = 57;

/* ── Phase definitions ─────────────────────────────────────────────────── */

interface Phase {
  id: string;
  duration: number;
  headline: string;
  body: string;
  subtitle?: string;
  visual: "void" | "instrument" | "worlds" | "verdict";
}

const PHASES: Phase[] = [
  {
    id: "void",
    duration: 9000,
    headline: "The Void",
    body: "One event. Five outlets. Five different realities. One calls it a crackdown. Another calls it restoring order. A third buries it on page six.",
    visual: "void",
  },
  {
    id: "instrument",
    duration: 10000,
    headline: "The Instrument",
    subtitle: "Every story, measured",
    body: "Six axes. Zero black boxes. The beam tilts with coverage lean \u2014 per story, not per outlet. The ring fills as sources weigh in. Sparse signal? Honest uncertainty over false precision.",
    visual: "instrument",
  },
  {
    id: "worlds",
    duration: 14000,
    headline: "The Worlds",
    subtitle: "One platform, six experiences",
    body: "Each built for a different way of reading.",
    visual: "worlds",
  },
  {
    id: "verdict",
    duration: 8000,
    headline: "Read with clarity.",
    body: "Broad coverage from across the spectrum, grounded in named sources. That\u2019s where confidence lives. Thin coverage from one corner? Scrutinize more.",
    visual: "verdict",
  },
];

/* ── Spring easing (CSS linear() approximation of damped spring) ────── */
const SPRING = "linear(0, 0.009, 0.035 2.1%, 0.141 4.4%, 0.723 15.5%, 0.938 20.7%, 1.017 24.3%, 1.061 27.7%, 1.085 32%, 1.078 36.3%, 1.042 44.4%, 1.014 53.3%, 0.996 64.4%, 1.001 78.8%, 1)";

/* ── Divergent Headlines Data ─────────────────────────────────────────── */

const DIVERGENT = [
  { outlet: "Reuters", lean: 48, color: "var(--bias-center)", headline: "\u201CUS and China resume trade talks amid tariff tensions\u201D" },
  { outlet: "Fox News", lean: 72, color: "var(--bias-right)", headline: "\u201CTrump administration takes hard line as China talks restart\u201D" },
  { outlet: "The Guardian", lean: 38, color: "var(--bias-left)", headline: "\u201CTrade war uncertainty looms as negotiations resume\u201D" },
  { outlet: "Al Jazeera", lean: 35, color: "var(--bias-left)", headline: "\u201CGlobal markets brace as superpowers return to table\u201D" },
  { outlet: "New York Post", lean: 74, color: "var(--bias-right)", headline: "\u201CBiden caves to China pressure, agrees to new talks\u201D" },
];

/* ── Scene 1: "The Void" — Divergent headlines ─────────────────────── */

function VoidVisual({ active }: { active: boolean }) {
  return (
    <div className="pro-void" aria-hidden="true">
      <p className="pro-void__event">Same event: US-China trade talks resume</p>
      <div className="pro-void__headlines">
        {DIVERGENT.map((h, i) => (
          <div
            key={h.outlet}
            className={`pro-void__card${active ? " pro-void__card--in" : ""}`}
            style={{ transitionDelay: `${200 + i * 120}ms` }}
          >
            <div className="pro-void__source">
              <span className="pro-void__outlet">{h.outlet}</span>
              <span className="pro-void__lean-dot" style={{ backgroundColor: h.color }} />
            </div>
            <p className="pro-void__headline">{h.headline}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Scene 2: "The Instrument" — Organic Sigil draws + beam sweep ──── */

const SWEEP = [
  { lean: 10, color: "var(--bias-far-left)", label: "Far Left" },
  { lean: 30, color: "var(--bias-left)", label: "Left" },
  { lean: 50, color: "var(--bias-center)", label: "Center" },
  { lean: 70, color: "var(--bias-right)", label: "Right" },
  { lean: 90, color: "var(--bias-far-right)", label: "Far Right" },
  { lean: 50, color: "var(--bias-center)", label: "Center" },
];

function InstrumentVisual({ active }: { active: boolean }) {
  const [step, setStep] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const prefersReduced = useRef(false);

  useEffect(() => {
    prefersReduced.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }, []);

  useEffect(() => {
    if (!active) { setStep(0); return; }
    // Under reduced motion, jump to final state immediately
    if (prefersReduced.current) { setStep(SWEEP.length - 1); return; }
    let i = 0;
    intervalRef.current = setInterval(() => {
      i++;
      if (i >= SWEEP.length) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        return;
      }
      setStep(i);
    }, 600);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [active]);

  const { lean, color } = SWEEP[step];
  const beamAngle = (lean - 50) * 0.30;
  const coverage = active ? Math.min(step + 1, 5) / 6 : 0;
  const ringFill = coverage * VOID_CIRC_LEN;

  return (
    <div className="pro-instrument" aria-hidden="true">
      <div className="pro-instrument__sigil">
        <svg width="160" height="160" viewBox="0 0 32 32" fill="none"
          strokeLinecap="round" strokeLinejoin="round"
        >
          {/* Void circle — organic hand-drawn path (background ring) */}
          <path d={VOID_CIRCLE}
            stroke="var(--border-subtle)" strokeWidth="1.8" opacity={0.3}
          />
          {/* Coverage ring fill */}
          <path d={VOID_CIRCLE}
            stroke={color} strokeWidth="1.8"
            strokeDasharray={`${ringFill} ${VOID_CIRC_LEN}`}
            style={{
              transform: "rotate(-90deg)", transformOrigin: "16px 13px",
              transition: `stroke-dasharray 700ms ${SPRING} 120ms, stroke 400ms ease`,
            }}
            opacity={0.9}
          />
          {/* Source count */}
          <text x="16" y="13.5" textAnchor="middle" dominantBaseline="central"
            style={{
              fontFamily: "var(--font-data)", fontSize: 8, fontWeight: 700,
              fill: "var(--fg-secondary)",
              opacity: active ? 0.85 : 0,
              transition: "opacity 400ms ease 300ms",
            }}
          >
            {active ? Math.min(step + 1, 5) * 3 : 0}
          </text>
          {/* Beam group — tilts with lean */}
          <g style={{
            transformOrigin: "16px 13px",
            transform: `rotate(${active ? beamAngle : 0}deg)`,
            transition: `transform 500ms ${SPRING}`,
          }}>
            <path d={BEAM_CURVE}
              stroke={color} strokeWidth="1.8"
              style={{ transition: "stroke 400ms ease" }}
            />
            <line x1="5" y1="11" x2="5" y2="15"
              stroke={color} strokeWidth="1.4"
              style={{ transition: "stroke 400ms ease" }}
              opacity={0.85}
            />
            <line x1="27" y1="11" x2="27" y2="15"
              stroke={color} strokeWidth="1.4"
              style={{ transition: "stroke 400ms ease" }}
              opacity={0.85}
            />
          </g>
          {/* Center post */}
          <line x1="16" y1="22" x2="16" y2="29"
            stroke="var(--fg-tertiary)" strokeWidth="1.4" opacity={0.4}
          />
          {/* Base — organic curve */}
          <path d={BASE_CURVE}
            stroke="var(--fg-tertiary)" strokeWidth="1.8" opacity={0.3}
          />
        </svg>
      </div>
      {/* Spectrum bar */}
      <div className="pro-instrument__spectrum">
        <div className="pro-instrument__spectrum-fill" />
        <div className="pro-instrument__spectrum-dot" style={{
          left: `${lean}%`,
          backgroundColor: color,
          transition: `left 500ms ${SPRING}, background-color 400ms ease`,
        }} />
      </div>
      <div className="pro-instrument__labels">
        <span style={{ color: "var(--bias-left)" }}>Left</span>
        <span style={{ color: "var(--fg-muted)" }}>Center</span>
        <span style={{ color: "var(--bias-right)" }}>Right</span>
      </div>
    </div>
  );
}

/* ── Scene 3: "The Worlds" — 6 product pages in native design ──────── */

const WORLDS = [
  {
    cli: "void --news",
    name: "The Feed",
    desc: "Importance-ranked, bias-analyzed",
    palette: "feed",
  },
  {
    cli: "void --weekly",
    name: "The Magazine",
    desc: "Economist-style weekly digest",
    palette: "weekly",
  },
  {
    cli: "void --paper",
    name: "The Broadsheet",
    desc: "E-paper front page",
    palette: "paper",
  },
  {
    cli: "void --sources",
    name: "The Spectrum",
    desc: "1,013 sources on one axis",
    palette: "sources",
  },
  {
    cli: "void --onair",
    name: "The Studio",
    desc: "Two-host audio broadcast",
    palette: "onair",
  },
  {
    cli: "void --ship",
    name: "The Forge",
    desc: "Feature request board",
    palette: "ship",
  },
];

function WorldCard({ world, index, active }: { world: typeof WORLDS[0]; index: number; active: boolean }) {
  return (
    <div
      className={`pro-world pro-world--${world.palette}${active ? " pro-world--in" : ""}`}
      style={{ transitionDelay: `${300 + index * 180}ms` }}
    >
      <div className="pro-world__preview">
        {world.palette === "feed" && <FeedPreview />}
        {world.palette === "weekly" && <WeeklyPreview />}
        {world.palette === "paper" && <PaperPreview />}
        {world.palette === "sources" && <SourcesPreview />}
        {world.palette === "onair" && <OnairPreview />}
        {world.palette === "ship" && <ShipPreview />}
      </div>
      <div className="pro-world__text">
        <span className="pro-world__cli">{world.cli}</span>
        <span className="pro-world__name">{world.name}</span>
        <span className="pro-world__desc">{world.desc}</span>
      </div>
    </div>
  );
}

/* Mini preview components — CSS-rendered, no images */

function FeedPreview() {
  return (
    <div className="pro-preview pro-preview--feed">
      <div className="pro-preview__cols">
        <div className="pro-preview__col pro-preview__col--lead">
          <div className="pro-preview__headline-bar" />
          <div className="pro-preview__text-lines">
            <div /><div /><div />
          </div>
          {/* Tiny organic Sigil */}
          <svg viewBox="0 0 32 32" className="pro-preview__sigil" fill="none" strokeLinecap="round" strokeLinejoin="round">
            <path d={VOID_CIRCLE} stroke="currentColor" strokeWidth="2.5" opacity={0.5} />
            <path d={BEAM_CURVE} stroke="currentColor" strokeWidth="2.5" opacity={0.7} />
          </svg>
        </div>
        <div className="pro-preview__col pro-preview__col--side">
          <div className="pro-preview__card-mini" />
          <div className="pro-preview__card-mini" />
          <div className="pro-preview__card-mini" />
        </div>
      </div>
    </div>
  );
}

function WeeklyPreview() {
  return (
    <div className="pro-preview pro-preview--weekly">
      <div className="pro-preview__masthead" />
      <div className="pro-preview__cover-hl" />
      <div className="pro-preview__cover-sub" />
      <div className="pro-preview__mag-cols">
        <div /><div /><div />
      </div>
    </div>
  );
}

function PaperPreview() {
  return (
    <div className="pro-preview pro-preview--paper">
      <div className="pro-preview__broadsheet-hdr" />
      <div className="pro-preview__broadsheet-rule" />
      <div className="pro-preview__broadsheet-hl" />
      <div className="pro-preview__broadsheet-cols">
        <div /><div /><div /><div />
      </div>
    </div>
  );
}

/* Deterministic pseudo-random positions — stable across re-renders */
const SRC_DOTS = Array.from({ length: 12 }, (_, i) => ({
  left: `${8 + ((i * 37 + 13) % 84)}%`,
  top: `${20 + ((i * 23 + 7) % 40)}%`,
  opacity: 0.3 + ((i * 17 + 5) % 50) / 100,
}));

const WAVE_HEIGHTS = Array.from({ length: 16 }, (_, i) =>
  `${20 + Math.sin(i * 0.7) * 40 + ((i * 13 + 3) % 15)}%`
);

function SourcesPreview() {
  return (
    <div className="pro-preview pro-preview--sources">
      <div className="pro-preview__spectrum-bar" />
      <div className="pro-preview__dots">
        {SRC_DOTS.map((d, i) => (
          <div key={i} className="pro-preview__src-dot" style={d} />
        ))}
      </div>
    </div>
  );
}

function OnairPreview() {
  return (
    <div className="pro-preview pro-preview--onair">
      <div className="pro-preview__waveform">
        {WAVE_HEIGHTS.map((h, i) => (
          <div key={i} className="pro-preview__wave-bar" style={{ height: h }} />
        ))}
      </div>
      <div className="pro-preview__hosts">
        <span>A</span><span>B</span>
      </div>
    </div>
  );
}

function ShipPreview() {
  return (
    <div className="pro-preview pro-preview--ship">
      <div className="pro-preview__kanban">
        <div className="pro-preview__kanban-col">
          <div className="pro-preview__kanban-card" />
          <div className="pro-preview__kanban-card" />
        </div>
        <div className="pro-preview__kanban-col">
          <div className="pro-preview__kanban-card" />
        </div>
        <div className="pro-preview__kanban-col">
          <div className="pro-preview__kanban-card" />
          <div className="pro-preview__kanban-card" />
          <div className="pro-preview__kanban-card" />
        </div>
      </div>
    </div>
  );
}

function WorldsVisual({ active }: { active: boolean }) {
  return (
    <div className="pro-worlds" aria-hidden="true">
      <div className="pro-worlds__grid">
        {WORLDS.map((w, i) => (
          <WorldCard key={w.cli} world={w} index={i} active={active} />
        ))}
      </div>
    </div>
  );
}

/* ── Scene 4: "The Verdict" — Three organic Sigils ─────────────────── */

function MiniOrganicSigil({ lean, leanColor: lc, coverage, coverageColor }: {
  lean: number; leanColor: string; coverage: number; coverageColor: string;
}) {
  const beamAngle = (lean - 50) * 0.30;
  const ringFill = coverage * VOID_CIRC_LEN;
  return (
    <svg width="48" height="48" viewBox="0 0 32 32" fill="none" strokeLinecap="round" strokeLinejoin="round">
      {/* Organic void circle */}
      <path d={VOID_CIRCLE} stroke="var(--border-subtle)" strokeWidth="1.8" opacity={0.3} />
      <path d={VOID_CIRCLE} stroke={coverageColor} strokeWidth="1.8"
        strokeDasharray={`${ringFill} ${VOID_CIRC_LEN}`}
        style={{ transform: "rotate(-90deg)", transformOrigin: "16px 13px" }}
        opacity={0.9}
      />
      {/* Beam group */}
      <g style={{ transformOrigin: "16px 13px", transform: `rotate(${beamAngle}deg)` }}>
        <path d={BEAM_CURVE} stroke={lc} strokeWidth="1.8" />
        <line x1="5" y1="11" x2="5" y2="15" stroke={lc} strokeWidth="1.4" opacity={0.85} />
        <line x1="27" y1="11" x2="27" y2="15" stroke={lc} strokeWidth="1.4" opacity={0.85} />
      </g>
      {/* Post + base */}
      <line x1="16" y1="22" x2="16" y2="29" stroke="var(--fg-tertiary)" strokeWidth="1.4" opacity={0.4} />
      <path d={BASE_CURVE} stroke="var(--fg-tertiary)" strokeWidth="1.8" opacity={0.3} />
    </svg>
  );
}

function VerdictVisual({ active }: { active: boolean }) {
  return (
    <div className={`pro-verdict${active ? " pro-verdict--active" : ""}`} aria-hidden="true">
      <div className="pro-verdict__row">
        <div className="pro-verdict__card" style={{ transitionDelay: "200ms" }}>
          <MiniOrganicSigil lean={25} leanColor="var(--bias-left)" coverage={0.8} coverageColor="var(--sense-low)" />
          <span className="pro-verdict__label">Left, Broad</span>
          <span className="pro-verdict__sub">Well sourced</span>
        </div>
        <div className="pro-verdict__card" style={{ transitionDelay: "350ms" }}>
          <MiniOrganicSigil lean={50} leanColor="var(--bias-center)" coverage={0.92} coverageColor="var(--sense-low)" />
          <span className="pro-verdict__label">Center, Deep</span>
          <span className="pro-verdict__sub">Most reliable</span>
        </div>
        <div className="pro-verdict__card" style={{ transitionDelay: "500ms" }}>
          <MiniOrganicSigil lean={78} leanColor="var(--bias-right)" coverage={0.25} coverageColor="var(--sense-high)" />
          <span className="pro-verdict__label">Right, Thin</span>
          <span className="pro-verdict__sub">Scrutinize more</span>
        </div>
      </div>
    </div>
  );
}

/* ── Phase Visual Router ───────────────────────────────────────────────── */

function PhaseVisual({ visual, active }: { visual: Phase["visual"]; active: boolean }) {
  switch (visual) {
    case "void": return <VoidVisual active={active} />;
    case "instrument": return <InstrumentVisual active={active} />;
    case "worlds": return <WorldsVisual active={active} />;
    case "verdict": return <VerdictVisual active={active} />;
  }
}

/* ── Main Carousel Component ──────────────────────────────────────────── */

interface OnboardingCarouselProps {
  visible: boolean;
  onComplete: () => void;
  onSkip: () => void;
}

export default function OnboardingCarousel({ visible, onComplete, onSkip }: OnboardingCarouselProps) {
  const [mounted, setMounted] = useState(false);
  const [phase, setPhase] = useState(-1);
  const [exiting, setExiting] = useState(false);
  const [paused, setPaused] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reducedMotion = useRef(false);
  const exitCallbackRef = useRef<(() => void) | null>(null);

  useEffect(() => {
    setMounted(true);
    reducedMotion.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }, []);

  // Body scroll lock — prevent feed scrolling behind the modal
  useEffect(() => {
    if (!visible || !mounted) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, [visible, mounted]);

  useEffect(() => {
    if (!mounted || !visible) return;
    const delay = reducedMotion.current ? 0 : 600;
    const timer = setTimeout(() => setPhase(0), delay);
    return () => clearTimeout(timer);
  }, [mounted, visible]);

  // Auto-advance phases — gated by exiting to prevent race conditions
  useEffect(() => {
    if (phase < 0 || phase >= PHASES.length - 1) return;
    if (reducedMotion.current || exiting) return;
    if (paused) {
      if (timerRef.current) clearTimeout(timerRef.current);
      return;
    }
    timerRef.current = setTimeout(() => {
      setPhase((p) => p + 1);
    }, PHASES[phase].duration);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [phase, paused, exiting]);

  const pauseAutoAdvance = useCallback(() => setPaused(true), []);
  const resumeAutoAdvance = useCallback(() => setPaused(false), []);

  const dismiss = useCallback((callback: () => void) => {
    if (exiting) return;
    setExiting(true);
    exitCallbackRef.current = callback;
    setTimeout(() => {
      previousFocusRef.current?.focus();
      callback();
    }, reducedMotion.current ? 0 : 500);
  }, [exiting]);

  const handleSkip = useCallback(() => dismiss(onSkip), [dismiss, onSkip]);
  const handleComplete = useCallback(() => dismiss(onComplete), [dismiss, onComplete]);

  // Focus trap + keyboard
  useEffect(() => {
    if (!visible || !mounted) return;
    previousFocusRef.current = document.activeElement as HTMLElement;

    const timer = setTimeout(() => {
      dialogRef.current?.querySelector<HTMLElement>("button")?.focus();
    }, 100);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { handleSkip(); return; }
      if (e.key === "ArrowRight" || e.key === " ") {
        e.preventDefault();
        if (phase < PHASES.length - 1) {
          if (timerRef.current) clearTimeout(timerRef.current);
          setPhase((p) => Math.min(PHASES.length - 1, p + 1));
        } else {
          handleComplete();
        }
      }
      if (e.key === "ArrowLeft" && phase > 0) {
        e.preventDefault();
        if (timerRef.current) clearTimeout(timerRef.current);
        setPhase((p) => Math.max(0, p - 1));
      }
      if (e.key === "Tab" && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), a[href], [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault(); last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault(); first.focus();
        }
      }
    };
    document.addEventListener("keydown", onKey);
    return () => { clearTimeout(timer); document.removeEventListener("keydown", onKey); };
  }, [visible, mounted, phase, handleSkip, handleComplete]);

  if (!mounted || !visible) return null;

  const currentPhase = phase >= 0 ? PHASES[phase] : null;
  const isLastPhase = phase === PHASES.length - 1;
  const progress = phase >= 0 ? ((phase + 1) / PHASES.length) * 100 : 0;

  return createPortal(
    <div className={`intro${exiting ? " intro--exiting" : ""}`}>
      <div className="intro__backdrop" aria-hidden="true" onClick={handleSkip} />

      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Welcome to void news"
        className="intro__stage"
      >
        {/* Progress bar */}
        <div className="intro__progress" aria-hidden="true">
          <div className="intro__progress-fill" style={{ width: `${progress}%` }} />
        </div>

        {/* Skip — always visible */}
        <button className="intro__skip" onClick={handleSkip} aria-label="Skip introduction">
          Skip
        </button>

        {/* Content area */}
        {/* eslint-disable-next-line jsx-a11y/no-static-element-interactions */}
        <div
          onMouseEnter={pauseAutoAdvance}
          onMouseLeave={resumeAutoAdvance}
          onTouchStart={pauseAutoAdvance}
          onTouchEnd={resumeAutoAdvance}
          onFocus={pauseAutoAdvance}
          onBlur={(e) => {
            if (!dialogRef.current?.contains(e.relatedTarget as Node)) {
              resumeAutoAdvance();
            }
          }}
        >
          {/* Visual area */}
          <div className="intro__visual">
            {currentPhase && <PhaseVisual visual={currentPhase.visual} active />}
          </div>

          {/* Text area — aria-live announces phase changes to screen readers */}
          {currentPhase && (
            <div key={currentPhase.id} className="intro__text" aria-live="polite" aria-atomic="true">
              <span className="intro__chapter">{["I", "II", "III", "IV"][phase]}</span>
              <h2 className="intro__headline">{currentPhase.headline}</h2>
              {currentPhase.subtitle && (
                <p className="intro__subtitle">{currentPhase.subtitle}</p>
              )}
              <p className="intro__body">{currentPhase.body}</p>
            </div>
          )}
        </div>

        {/* Phase dots — stepper pattern, not tabs */}
        <div className="intro__dots" aria-label="Guide sections">
          {PHASES.map((p, i) => (
            <button
              key={p.id}
              aria-label={`Go to section ${i + 1}: ${p.headline}`}
              aria-current={i === phase ? "step" : undefined}
              className={`intro__dot${i === phase ? " intro__dot--active" : ""}${i < phase ? " intro__dot--done" : ""}`}
              onClick={() => {
                if (timerRef.current) clearTimeout(timerRef.current);
                setPhase(i);
              }}
            />
          ))}
        </div>

        {/* Action buttons */}
        <div className="intro__actions">
          {!isLastPhase ? (
            <button className="intro__btn intro__btn--next" onClick={() => {
              if (timerRef.current) clearTimeout(timerRef.current);
              setPhase((p) => Math.min(PHASES.length - 1, p + 1));
            }}>
              Next
            </button>
          ) : (
            <>
              <button className="intro__btn intro__btn--primary" onClick={handleComplete} autoFocus>
                Start reading
              </button>
              <a href="/about" className="intro__manifesto-link" onClick={() => dismiss(onComplete)}>
                Read the manifesto
              </a>
            </>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
