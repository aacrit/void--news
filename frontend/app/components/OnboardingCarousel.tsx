"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";

/* ---------------------------------------------------------------------------
   OnboardingCarousel — Act 1 of unified onboarding

   5-phase modal carousel: origin story, beam & ring, product family,
   audio broadcast, verdict. Teaches concepts abstractly before the
   spotlight tour (Act 2) grounds them in real UI.

   Controlled by UnifiedOnboarding orchestrator via visible/onComplete/onSkip.
   --------------------------------------------------------------------------- */

/* ── Phase definitions ─────────────────────────────────────────────────── */

interface Phase {
  id: string;
  duration: number;
  headline: string;
  body: string;
  subtitle?: string;
  visual: "story" | "beam-ring" | "verdict";
}

const PHASES: Phase[] = [
  {
    id: "origin",
    duration: 10000,
    headline: "void --news",
    subtitle: "See through the void.",
    body: "The same event. Five outlets. Five different realities. One calls it a crackdown. Another calls it restoring order. A third buries it on page six. void --news scores every article across six axes, so the framing becomes visible.",
    visual: "story",
  },
  {
    id: "beam-ring",
    duration: 10000,
    headline: "Beam & Ring",
    subtitle: "Every story, measured",
    body: "The beam tilts toward the lean. The ring fills as more sources cover the story. Together: where does the weight fall, and how many newsrooms have pressure-tested it?",
    visual: "beam-ring",
  },
  {
    id: "verdict",
    duration: 10000,
    headline: "Read with clarity",
    body: "Broad coverage from across the spectrum, grounded in named sources. That\u2019s where confidence lives. Thin coverage from one corner? Scrutinize more.",
    visual: "verdict",
  },
];

/* ── Spring easing (CSS linear() approximation of damped spring) ────── */
const SPRING = "linear(0, 0.009, 0.035 2.1%, 0.141 4.4%, 0.723 15.5%, 0.938 20.7%, 1.017 24.3%, 1.061 27.7%, 1.085 32%, 1.078 36.3%, 1.042 44.4%, 1.014 53.3%, 0.996 64.4%, 1.001 78.8%, 1)";

/* ── Animated Beam SVG ─────────────────────────────────────────────────── */

function AnimatedBeam({ active }: { active: boolean }) {
  const [step, setStep] = useState(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

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
  const beamAngle = (value - 50) * 0.30;

  return (
    <div className="intro-beam" aria-hidden="true">
      <svg width="200" height="160" viewBox="0 0 32 32" fill="none"
        strokeLinecap="round" strokeLinejoin="round"
        className="intro-beam__svg"
      >
        <circle cx="16" cy="13" r="9"
          stroke="var(--border-subtle)" strokeWidth="1.8" opacity={0.3}
        />
        <circle cx="16" cy="13" r="9"
          stroke={color} strokeWidth="1.8" strokeLinecap="round"
          strokeDasharray={`${active ? 0.7 * 2 * Math.PI * 9 : 0} ${2 * Math.PI * 9}`}
          style={{
            transform: "rotate(-90deg)", transformOrigin: "16px 13px",
            transition: `stroke-dasharray 700ms ${SPRING} 120ms, stroke 400ms ease`,
          }}
          opacity={0.9}
        />
        <g style={{
          transformOrigin: "16px 13px",
          transform: `rotate(${active ? beamAngle : 0}deg)`,
          transition: `transform 500ms ${SPRING}`,
        }}>
          <line x1="4" y1="13" x2="28" y2="13"
            stroke={color} strokeWidth="1.8"
            style={{ transition: "stroke 400ms ease" }}
          />
          <line x1="6" y1="11.5" x2="6" y2="14.5"
            stroke={color} strokeWidth="1.4"
            style={{ transition: "stroke 400ms ease" }}
            opacity={0.85}
          />
          <line x1="26" y1="11.5" x2="26" y2="14.5"
            stroke={color} strokeWidth="1.4"
            style={{ transition: "stroke 400ms ease" }}
            opacity={0.85}
          />
        </g>
        <line x1="16" y1="22" x2="16" y2="28"
          stroke="var(--fg-tertiary)" strokeWidth="1.4" opacity={0.4}
        />
        <line x1="12" y1="28.5" x2="20" y2="28.5"
          stroke="var(--fg-tertiary)" strokeWidth="1.8" opacity={0.3}
        />
      </svg>
      <div className="intro-beam__spectrum">
        <div className="intro-beam__spectrum-fill" />
      </div>
      <div className="intro-beam__labels">
        <span className="intro-beam__label" style={{ color: "var(--bias-left)" }}>Left</span>
        <span className="intro-beam__label" style={{ color: "var(--fg-muted)" }}>Center</span>
        <span className="intro-beam__label" style={{ color: "var(--bias-right)" }}>Right</span>
      </div>
      <div className="intro-beam__readout text-data" style={{ color }}>
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
      const spring = t < 0.6
        ? t / 0.6 * 1.12
        : 1.12 - 0.12 * ((t - 0.6) / 0.4);
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
        <circle cx="70" cy="70" r={r} fill="none" stroke="var(--border-subtle)" strokeWidth="5" opacity="0.3" />
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
      <div className="intro-ring__center">
        <span className="intro-ring__count text-data">{count}</span>
        <span className="intro-ring__label text-data">sources</span>
      </div>
      <div className={`intro-ring__tiers${active ? " intro-ring__tiers--visible" : ""}`}>
        <span className="intro-ring__tier" style={{ transitionDelay: "200ms" }}>US Major: 5</span>
        <span className="intro-ring__tier" style={{ transitionDelay: "300ms" }}>International: 4</span>
        <span className="intro-ring__tier" style={{ transitionDelay: "400ms" }}>Independent: 3</span>
      </div>
    </div>
  );
}

/* ── Story Visual — abstract "five tabs" illustration ──────────────────── */

function StoryVisual({ active }: { active: boolean }) {
  return (
    <div className={`intro-story-visual${active ? " intro-story-visual--active" : ""}`} aria-hidden="true">
      <div className="intro-story-visual__tabs">
        {["var(--bias-far-left)", "var(--bias-left)", "var(--bias-center)", "var(--bias-right)", "var(--bias-far-right)"].map((color, i) => (
          <div
            key={i}
            className="intro-story-visual__tab"
            style={{
              borderTopColor: color,
              transitionDelay: `${100 + i * 60}ms`,
            }}
          />
        ))}
      </div>
      <div className="intro-story-visual__void-line" />
    </div>
  );
}

/* ── Beam & Ring Combined Visual ──────────────────────────────────────── */

function BeamAndRing({ active }: { active: boolean }) {
  return (
    <div className="intro-beam-ring" aria-hidden="true">
      <AnimatedBeam active={active} />
      <AnimatedRing active={active} />
    </div>
  );
}

/* ── Product Family Visual ─────────────────────────────────────────────── */

function ProductFamilyVisual({ active }: { active: boolean }) {
  const products = [
    { cmd: "void --tl;dr", label: "Daily Brief", desc: "Top stories, editorially weighed" },
    { cmd: "void --onair", label: "Audio Broadcast", desc: "Two hosts, three minutes" },
    { cmd: "void --opinion", label: "The Board", desc: "Editorial lean rotates daily" },
    { cmd: "void --sources", label: "Source Spectrum", desc: "1,013 sources, one axis" },
    { cmd: "void --deep-dive", label: "Deep Dive", desc: "Every source, every score" },
    { cmd: "void --paper", label: "E-Paper", desc: "The broadsheet front page" },
  ];

  return (
    <div className={`intro-products${active ? " intro-products--active" : ""}`} aria-hidden="true">
      {products.map((p, i) => (
        <div
          key={p.cmd}
          className="intro-products__item"
          style={{ transitionDelay: `${120 + i * 60}ms` }}
        >
          <span className="intro-products__cmd text-data">{p.cmd}</span>
          <span className="intro-products__label">{p.label}</span>
          <span className="intro-products__desc">{p.desc}</span>
        </div>
      ))}
    </div>
  );
}

/* ── Audio Product Visual ──────────────────────────────────────────────── */

function AudioProductVisual({ active }: { active: boolean }) {
  return (
    <div className={`intro-audio${active ? " intro-audio--active" : ""}`} aria-hidden="true">
      <div className="intro-audio__card">
        <span className="intro-audio__cmd text-data">void --onair</span>
        <span className="intro-audio__label">Audio Broadcast</span>
        <div className="intro-audio__waveform">
          {Array.from({ length: 24 }).map((_, i) => (
            <div
              key={i}
              className="intro-audio__bar"
              style={{
                height: `${12 + Math.sin(i * 0.6) * 18 + Math.random() * 8}px`,
                animationDelay: `${i * 60}ms`,
              }}
            />
          ))}
        </div>
        <div className="intro-audio__voices">
          <span>Host A: the facts</span>
          <span>Host B: the questions</span>
        </div>
      </div>
    </div>
  );
}

/* ── Verdict Combined Display ──────────────────────────────────────────── */

function MiniSigil({ lean, leanColor: lc, coverage, coverageColor }: {
  lean: number; leanColor: string; coverage: number; coverageColor: string;
}) {
  const beamAngle = (lean - 50) * 0.30;
  const r = 9;
  const circ = 2 * Math.PI * r;
  return (
    <svg width="48" height="48" viewBox="0 0 32 32" fill="none" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="16" cy="13" r={r} stroke="var(--border-subtle)" strokeWidth="1.8" opacity={0.3} />
      <circle cx="16" cy="13" r={r} stroke={coverageColor} strokeWidth="1.8"
        strokeDasharray={`${coverage * circ} ${circ}`}
        transform="rotate(-90 16 13)" opacity={0.9} />
      <g style={{ transformOrigin: "16px 13px", transform: `rotate(${beamAngle}deg)` }}>
        <line x1="4" y1="13" x2="28" y2="13" stroke={lc} strokeWidth="1.8" />
        <line x1="6" y1="11.5" x2="6" y2="14.5" stroke={lc} strokeWidth="1.4" opacity={0.85} />
        <line x1="26" y1="11.5" x2="26" y2="14.5" stroke={lc} strokeWidth="1.4" opacity={0.85} />
      </g>
      <line x1="16" y1="22" x2="16" y2="28" stroke="var(--fg-tertiary)" strokeWidth="1.4" opacity={0.4} />
      <line x1="12" y1="28.5" x2="20" y2="28.5" stroke="var(--fg-tertiary)" strokeWidth="1.8" opacity={0.3} />
    </svg>
  );
}

function VerdictDisplay({ active }: { active: boolean }) {
  return (
    <div className={`intro-verdict${active ? " intro-verdict--active" : ""}`} aria-hidden="true">
      <div className="intro-verdict__row">
        <div className="intro-verdict__card intro-verdict__card--left" style={{ transitionDelay: "100ms" }}>
          <MiniSigil lean={25} leanColor="var(--bias-left)" coverage={0.8} coverageColor="var(--sense-low)" />
          <span className="intro-verdict__label text-data">Left, Broad</span>
          <span className="intro-verdict__sub text-data">Well sourced</span>
        </div>

        <div className="intro-verdict__card intro-verdict__card--center" style={{ transitionDelay: "200ms" }}>
          <MiniSigil lean={50} leanColor="var(--bias-center)" coverage={0.92} coverageColor="var(--sense-low)" />
          <span className="intro-verdict__label text-data">Center, Deep</span>
          <span className="intro-verdict__sub text-data">Most reliable</span>
        </div>

        <div className="intro-verdict__card intro-verdict__card--right" style={{ transitionDelay: "300ms" }}>
          <MiniSigil lean={78} leanColor="var(--bias-right)" coverage={0.25} coverageColor="var(--sense-high)" />
          <span className="intro-verdict__label text-data">Right, Thin</span>
          <span className="intro-verdict__sub text-data">Scrutinize more</span>
        </div>
      </div>
    </div>
  );
}

/* ── Phase Visual Router ───────────────────────────────────────────────── */

function PhaseVisual({ visual, active }: { visual: Phase["visual"]; active: boolean }) {
  switch (visual) {
    case "story": return <StoryVisual active={active} />;
    case "beam-ring": return <BeamAndRing active={active} />;
    case "verdict": return <VerdictDisplay active={active} />;
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

  // Start phase 0 when visible becomes true
  useEffect(() => {
    if (!mounted || !visible) return;
    const delay = reducedMotion.current ? 0 : 600;
    const timer = setTimeout(() => setPhase(0), delay);
    return () => clearTimeout(timer);
  }, [mounted, visible]);

  // Auto-advance phases
  useEffect(() => {
    if (phase < 0 || phase >= PHASES.length - 1) return;
    if (reducedMotion.current) return;
    if (paused) {
      if (timerRef.current) clearTimeout(timerRef.current);
      return;
    }
    timerRef.current = setTimeout(() => {
      setPhase((p) => p + 1);
    }, PHASES[phase].duration);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [phase, paused]);

  const pauseAutoAdvance = useCallback(() => setPaused(true), []);
  const resumeAutoAdvance = useCallback(() => setPaused(false), []);

  const dismiss = useCallback((callback: () => void) => {
    if (exiting) return;
    setExiting(true);
    exitCallbackRef.current = callback;
    setTimeout(() => {
      callback();
    }, reducedMotion.current ? 0 : 500);
  }, [exiting]);

  const handleSkip = useCallback(() => dismiss(onSkip), [dismiss, onSkip]);
  const handleComplete = useCallback(() => dismiss(onComplete), [dismiss, onComplete]);

  const skipToEnd = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    setPhase(PHASES.length - 1);
  }, []);

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

        {/* Skip */}
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
          {/* Illustration area */}
          <div className="intro__visual">
            {currentPhase && <PhaseVisual visual={currentPhase.visual} active />}
          </div>

          {/* Text area */}
          {currentPhase && (
            <div key={currentPhase.id} className="intro__text">
              <span className="intro__chapter">{["I", "II", "III"][phase]}</span>
              <h2 className="intro__headline">{currentPhase.headline}</h2>
              {currentPhase.subtitle && (
                <p className="intro__subtitle">{currentPhase.subtitle}</p>
              )}
              <p className="intro__body">{currentPhase.body}</p>
            </div>
          )}
        </div>

        {/* Phase dots */}
        <div className="intro__dots" role="tablist" aria-label="Guide sections">
          {PHASES.map((p, i) => (
            <button
              key={p.id}
              role="tab"
              aria-selected={i === phase}
              aria-label={`Section ${i + 1}: ${p.headline}`}
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
            <button className="intro__btn intro__btn--next" onClick={skipToEnd}>
              Skip to end
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
