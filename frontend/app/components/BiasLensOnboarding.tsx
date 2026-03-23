"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";

/* ---------------------------------------------------------------------------
   BiasLensOnboarding — Cinematic intro with spring physics

   A premium onboarding experience that reveals the bias analysis system
   through orchestrated motion. Each phase builds on the previous:

   Phase 0: Void — dark field, the scale icon draws itself stroke-by-stroke
   Phase 1: Lean — needle swings through the spectrum, colors bloom
   Phase 2: Depth — ring fills with spring physics, sources count up
   Phase 3: Verdict — combined view crystallizes, "Got it" appears

   Motion principles:
   - Spring physics for all element entrances (no linear easing)
   - Staggered cascade reveals (40-80ms between siblings)
   - GPU-only: transform + opacity exclusively
   - Cinematic timing: each phase ~2.5s, total ~10s
   - Reduced-motion: instant reveal, no animation

   Shown once per browser (localStorage: void-news-intro-seen).
   --------------------------------------------------------------------------- */

const STORAGE_KEY = "void-news-intro-seen";

/* ── Phase definitions ─────────────────────────────────────────────────── */

interface Phase {
  id: string;
  /** Duration in ms before auto-advancing to next phase */
  duration: number;
  /** Headline text (Playfair) */
  headline: string;
  /** Body text (Inter) */
  body: string;
}

const PHASES: Phase[] = [
  {
    id: "void",
    duration: 3200,
    headline: "void --news",
    body: "Every story has more than one side.",
  },
  {
    id: "lean",
    duration: 3600,
    headline: "The Needle",
    body: "See where each source falls on the political spectrum — from far left to far right.",
  },
  {
    id: "depth",
    duration: 3200,
    headline: "The Ring",
    body: "Know how thoroughly a story is covered. More credible sources, fuller ring.",
  },
  {
    id: "verdict",
    duration: 4000,
    headline: "Read with clarity",
    body: "Lean and depth together tell you: is this story broadly reported and trustworthy?",
  },
];

/* ── Spring easing (CSS linear() approximation of damped spring) ────── */
// Stiffness ~300, damping ~22, mass ~1 — "smooth" preset
const SPRING = "linear(0, 0.009, 0.035 2.1%, 0.141 4.4%, 0.723 15.5%, 0.938 20.7%, 1.017 24.3%, 1.061 27.7%, 1.085 32%, 1.078 36.3%, 1.042 44.4%, 1.014 53.3%, 0.996 64.4%, 1.001 78.8%, 1)";

/* ── Animated Needle SVG ───────────────────────────────────────────────── */

function AnimatedNeedle({ active }: { active: boolean }) {
  const [step, setStep] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Sweep: far-left → left → center → right → far-right → center (settle)
  const SWEEP_VALUES = [10, 25, 50, 75, 90, 50];
  const SWEEP_COLORS = [
    "var(--bias-far-left)", "var(--bias-left)", "var(--bias-center)",
    "var(--bias-right)", "var(--bias-far-right)", "var(--bias-center)",
  ];

  useEffect(() => {
    if (!active) { setStep(0); return; }
    let i = 0;
    intervalRef.current = setInterval(() => {
      i++;
      if (i >= SWEEP_VALUES.length) {
        if (intervalRef.current) clearInterval(intervalRef.current);
        return;
      }
      setStep(i);
    }, 500);
    return () => { if (intervalRef.current) clearInterval(intervalRef.current); };
  }, [active]);

  const value = SWEEP_VALUES[step];
  const color = SWEEP_COLORS[step];
  const angle = ((value - 50) / 50) * 35;

  return (
    <div className="intro-needle" aria-hidden="true">
      {/* Spectrum bar behind needle */}
      <div className="intro-needle__spectrum">
        <div className="intro-needle__spectrum-fill" />
      </div>
      {/* Needle apparatus */}
      <svg width="200" height="100" viewBox="0 0 200 100" className="intro-needle__svg">
        {/* Tick marks */}
        <line x1="20" y1="45" x2="20" y2="55" stroke="var(--border-strong)" strokeWidth="1" opacity="0.4" />
        <line x1="100" y1="42" x2="100" y2="58" stroke="var(--border-strong)" strokeWidth="1.5" opacity="0.5" />
        <line x1="180" y1="45" x2="180" y2="55" stroke="var(--border-strong)" strokeWidth="1" opacity="0.4" />
        {/* Needle */}
        <line
          x1="100" y1="50" x2="100" y2="8"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          style={{
            transformOrigin: "100px 50px",
            transform: `rotate(${active ? angle : 0}deg)`,
            transition: `transform 500ms ${SPRING}, stroke 400ms ease`,
          }}
        />
        {/* Pivot */}
        <circle cx="100" cy="50" r="5" fill={color} style={{ transition: `fill 400ms ease` }} />
      </svg>
      {/* Labels */}
      <div className="intro-needle__labels">
        <span className="intro-needle__label" style={{ color: "var(--bias-left)" }}>Left</span>
        <span className="intro-needle__label" style={{ color: "var(--fg-muted)" }}>Center</span>
        <span className="intro-needle__label" style={{ color: "var(--bias-right)" }}>Right</span>
      </div>
      {/* Score readout */}
      <div className="intro-needle__readout text-data" style={{ color }}>
        {value}
      </div>
    </div>
  );
}

/* ── Animated Ring SVG ─────────────────────────────────────────────────── */

function AnimatedRing({ active }: { active: boolean }) {
  const [fill, setFill] = useState(0);
  const [count, setCount] = useState(0);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!active) { setFill(0); setCount(0); return; }
    const start = performance.now();
    const duration = 2400;
    const targetFill = 82;
    const targetCount = 12;

    function tick(now: number) {
      const elapsed = now - start;
      const t = Math.min(1, elapsed / duration);
      // Spring-like overshoot curve
      const spring = t < 0.6
        ? t / 0.6 * 1.12   // overshoot to 112%
        : 1.12 - 0.12 * ((t - 0.6) / 0.4); // settle back
      const clampedSpring = Math.max(0, Math.min(1.12, spring));

      setFill(Math.round(targetFill * Math.min(1, clampedSpring)));
      setCount(Math.min(targetCount, Math.round(targetCount * t)));

      if (t < 1) rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [active]);

  const r = 52;
  const circ = 2 * Math.PI * r;
  const dashLen = (fill / 100) * circ;
  const ringColor = fill >= 60 ? "var(--sense-low)" : fill >= 30 ? "var(--sense-medium)" : "var(--sense-high)";

  return (
    <div className="intro-ring" aria-hidden="true">
      <svg width="140" height="140" viewBox="0 0 140 140" className="intro-ring__svg">
        {/* Track */}
        <circle cx="70" cy="70" r={r} fill="none" stroke="var(--border-subtle)" strokeWidth="5" opacity="0.3" />
        {/* Fill */}
        <circle
          cx="70" cy="70" r={r}
          fill="none"
          stroke={ringColor}
          strokeWidth="5"
          strokeLinecap="round"
          strokeDasharray={`${dashLen} ${circ}`}
          transform="rotate(-90 70 70)"
          style={{ transition: "stroke 300ms ease" }}
        />
      </svg>
      {/* Center count */}
      <div className="intro-ring__center">
        <span className="intro-ring__count text-data">{count}</span>
        <span className="intro-ring__label text-data">sources</span>
      </div>
      {/* Tier badges cascade in */}
      <div className={`intro-ring__tiers${active ? " intro-ring__tiers--visible" : ""}`}>
        <span className="intro-ring__tier" style={{ transitionDelay: "800ms" }}>US Major: 5</span>
        <span className="intro-ring__tier" style={{ transitionDelay: "960ms" }}>International: 4</span>
        <span className="intro-ring__tier" style={{ transitionDelay: "1120ms" }}>Independent: 3</span>
      </div>
    </div>
  );
}

/* ── Scale Icon Draw Animation ─────────────────────────────────────────── */

function ScaleIconDraw({ active }: { active: boolean }) {
  return (
    <div className={`intro-scale${active ? " intro-scale--active" : ""}`} aria-hidden="true">
      <svg width="120" height="120" viewBox="0 0 32 32" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        {/* Void circle */}
        <circle cx="16" cy="13" r="9" className="intro-scale__void" />
        {/* Beam group */}
        <g className="intro-scale__beam">
          <line x1="3" y1="13" x2="29" y2="13" className="intro-scale__line intro-scale__line--beam" />
          <line x1="5" y1="11" x2="5" y2="15" className="intro-scale__line intro-scale__line--tick-l" />
          <line x1="27" y1="11" x2="27" y2="15" className="intro-scale__line intro-scale__line--tick-r" />
        </g>
        {/* Post */}
        <line x1="16" y1="22" x2="16" y2="29" className="intro-scale__line intro-scale__line--post" />
        {/* Base */}
        <line x1="12" y1="29" x2="20" y2="29" className="intro-scale__line intro-scale__line--base" />
      </svg>
    </div>
  );
}

/* ── Verdict Combined Display ──────────────────────────────────────────── */

function VerdictDisplay({ active }: { active: boolean }) {
  return (
    <div className={`intro-verdict${active ? " intro-verdict--active" : ""}`} aria-hidden="true">
      <div className="intro-verdict__row">
        {/* Left example */}
        <div className="intro-verdict__card intro-verdict__card--left" style={{ transitionDelay: "200ms" }}>
          <svg width="32" height="40" viewBox="0 0 32 40">
            <line x1="16" y1="32" x2="16" y2="4" stroke="var(--bias-left)" strokeWidth="3" strokeLinecap="round"
              style={{ transformOrigin: "16px 32px", transform: "rotate(-18deg)" }} />
            <circle cx="16" cy="32" r="3" fill="var(--bias-left)" />
          </svg>
          <svg width="32" height="32" viewBox="0 0 32 32">
            <circle cx="16" cy="16" r="10" fill="none" stroke="var(--border-subtle)" strokeWidth="3" opacity="0.3" />
            <circle cx="16" cy="16" r="10" fill="none" stroke="var(--sense-low)" strokeWidth="3" strokeLinecap="round"
              strokeDasharray={`${0.8 * 2 * Math.PI * 10} ${2 * Math.PI * 10}`} transform="rotate(-90 16 16)" />
          </svg>
          <span className="intro-verdict__label text-data">Left, Broad</span>
          <span className="intro-verdict__sub text-data">Well sourced</span>
        </div>

        {/* Center example */}
        <div className="intro-verdict__card intro-verdict__card--center" style={{ transitionDelay: "400ms" }}>
          <svg width="32" height="40" viewBox="0 0 32 40">
            <line x1="16" y1="32" x2="16" y2="4" stroke="var(--bias-center)" strokeWidth="3" strokeLinecap="round" />
            <circle cx="16" cy="32" r="3" fill="var(--bias-center)" />
          </svg>
          <svg width="32" height="32" viewBox="0 0 32 32">
            <circle cx="16" cy="16" r="10" fill="none" stroke="var(--border-subtle)" strokeWidth="3" opacity="0.3" />
            <circle cx="16" cy="16" r="10" fill="none" stroke="var(--sense-low)" strokeWidth="3" strokeLinecap="round"
              strokeDasharray={`${0.92 * 2 * Math.PI * 10} ${2 * Math.PI * 10}`} transform="rotate(-90 16 16)" />
          </svg>
          <span className="intro-verdict__label text-data">Center, Deep</span>
          <span className="intro-verdict__sub text-data">Most reliable</span>
        </div>

        {/* Right example */}
        <div className="intro-verdict__card intro-verdict__card--right" style={{ transitionDelay: "600ms" }}>
          <svg width="32" height="40" viewBox="0 0 32 40">
            <line x1="16" y1="32" x2="16" y2="4" stroke="var(--bias-right)" strokeWidth="3" strokeLinecap="round"
              style={{ transformOrigin: "16px 32px", transform: "rotate(22deg)" }} />
            <circle cx="16" cy="32" r="3" fill="var(--bias-right)" />
          </svg>
          <svg width="32" height="32" viewBox="0 0 32 32">
            <circle cx="16" cy="16" r="10" fill="none" stroke="var(--border-subtle)" strokeWidth="3" opacity="0.3" />
            <circle cx="16" cy="16" r="10" fill="none" stroke="var(--sense-high)" strokeWidth="3" strokeLinecap="round"
              strokeDasharray={`${0.25 * 2 * Math.PI * 10} ${2 * Math.PI * 10}`} transform="rotate(-90 16 16)" />
          </svg>
          <span className="intro-verdict__label text-data">Right, Thin</span>
          <span className="intro-verdict__sub text-data">Scrutinize more</span>
        </div>
      </div>
    </div>
  );
}

/* ── Main Onboarding Component ─────────────────────────────────────────── */

export default function BiasLensOnboarding() {
  const [mounted, setMounted] = useState(false);
  const [visible, setVisible] = useState(false);
  const [phase, setPhase] = useState(-1);    // -1 = not started
  const [exiting, setExiting] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reducedMotion = useRef(false);

  useEffect(() => {
    setMounted(true);
    reducedMotion.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    try {
      if (!localStorage.getItem(STORAGE_KEY)) {
        setVisible(true);
        // Start phase 0 after a brief moment
        setTimeout(() => setPhase(0), reducedMotion.current ? 0 : 600);
      }
    } catch { /* localStorage blocked — skip */ }
  }, []);

  // Auto-advance phases
  useEffect(() => {
    if (phase < 0 || phase >= PHASES.length - 1) return; // don't auto-advance past last
    if (reducedMotion.current) return; // manual navigation only in reduced motion
    timerRef.current = setTimeout(() => {
      setPhase((p) => p + 1);
    }, PHASES[phase].duration);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [phase]);

  const dismiss = useCallback(() => {
    if (exiting) return;
    setExiting(true);
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch { /* ignore */ }
    // Exit animation
    setTimeout(() => {
      setVisible(false);
      previousFocusRef.current?.focus();
    }, 500);
  }, [exiting]);

  const skipToEnd = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setPhase(PHASES.length - 1);
  }, []);

  // Focus trap + keyboard
  useEffect(() => {
    if (!visible) return;
    previousFocusRef.current = document.activeElement as HTMLElement;

    const timer = setTimeout(() => {
      dialogRef.current?.querySelector<HTMLElement>("button")?.focus();
    }, 100);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { dismiss(); return; }
      if (e.key === "ArrowRight" || e.key === " ") {
        e.preventDefault();
        if (phase < PHASES.length - 1) {
          if (timerRef.current) clearTimeout(timerRef.current);
          setPhase((p) => Math.min(PHASES.length - 1, p + 1));
        } else {
          dismiss();
        }
      }
      if (e.key === "ArrowLeft" && phase > 0) {
        e.preventDefault();
        if (timerRef.current) clearTimeout(timerRef.current);
        setPhase((p) => Math.max(0, p - 1));
      }
      if (e.key === "Tab" && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [tabindex]:not([tabindex="-1"])',
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
  }, [visible, phase, dismiss]);

  if (!mounted || !visible) return null;

  const currentPhase = phase >= 0 ? PHASES[phase] : null;
  const isLastPhase = phase === PHASES.length - 1;
  const progress = phase >= 0 ? ((phase + 1) / PHASES.length) * 100 : 0;

  return createPortal(
    <div className={`intro${exiting ? " intro--exiting" : ""}`}>
      {/* Cinematic backdrop — dark field with subtle grain */}
      <div className="intro__backdrop" aria-hidden="true" onClick={dismiss} />

      {/* Main stage */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="How void news works"
        className="intro__stage"
      >
        {/* Progress bar — thin line at top */}
        <div className="intro__progress" aria-hidden="true">
          <div className="intro__progress-fill" style={{ width: `${progress}%` }} />
        </div>

        {/* Skip button — top right */}
        <button className="intro__skip" onClick={dismiss} aria-label="Skip intro">
          Skip
        </button>

        {/* ── Illustration area ── */}
        <div className="intro__visual">
          {/* Phase 0: Scale icon draws itself */}
          {phase === 0 && <ScaleIconDraw active />}

          {/* Phase 1: Needle sweeps the spectrum */}
          {phase === 1 && <AnimatedNeedle active />}

          {/* Phase 2: Ring fills with spring physics */}
          {phase === 2 && <AnimatedRing active />}

          {/* Phase 3: Combined verdict */}
          {phase === 3 && <VerdictDisplay active />}
        </div>

        {/* ── Text area — fades/slides per phase ── */}
        {currentPhase && (
          <div key={currentPhase.id} className="intro__text">
            <h2 className="intro__headline">{currentPhase.headline}</h2>
            <p className="intro__body">{currentPhase.body}</p>
          </div>
        )}

        {/* ── Phase dots ── */}
        <div className="intro__dots" role="tablist" aria-label="Intro phases">
          {PHASES.map((p, i) => (
            <button
              key={p.id}
              role="tab"
              aria-selected={i === phase}
              aria-label={`Phase ${i + 1}: ${p.headline}`}
              className={`intro__dot${i === phase ? " intro__dot--active" : ""}${i < phase ? " intro__dot--done" : ""}`}
              onClick={() => {
                if (timerRef.current) clearTimeout(timerRef.current);
                setPhase(i);
              }}
            />
          ))}
        </div>

        {/* ── Action buttons ── */}
        <div className="intro__actions">
          {!isLastPhase ? (
            <button className="intro__btn intro__btn--next" onClick={skipToEnd}>
              Skip to end
            </button>
          ) : (
            <button className="intro__btn intro__btn--primary" onClick={dismiss} autoFocus>
              Start reading
            </button>
          )}
        </div>
      </div>
    </div>,
    document.body,
  );
}
