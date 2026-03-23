"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";

/* ---------------------------------------------------------------------------
   BiasLensOnboarding — Origin story + product guide

   Redesigned flow: 7 phases that tell the void --news story, explain the
   product family (--tl;dr, --onair, --opinion, --sources, --deep-dive),
   and teach the visualization system (Needle, Ring).

   Trigger: 2nd visit OR 90s idle on 1st visit — content comes first.
   Always dismissible: Skip button, Esc, backdrop click.
   localStorage tracks: visit count + dismissed state.
   --------------------------------------------------------------------------- */

const STORAGE_KEY = "void-news-intro-seen";
const VISITS_KEY = "void-news-visit-count";
const IDLE_TRIGGER_MS = 90_000; // 90 seconds idle before showing on 1st visit

/* ── Phase definitions ─────────────────────────────────────────────────── */

interface Phase {
  id: string;
  duration: number;
  headline: string;
  body: string;
  /** Optional subtitle below headline — used for product branding education */
  subtitle?: string;
  /** Visual type for the illustration area */
  visual: "scale-draw" | "story" | "needle" | "ring" | "product" | "product-audio" | "verdict";
}

const PHASES: Phase[] = [
  {
    id: "origin",
    duration: 4000,
    headline: "void --news",
    subtitle: "See every side of the story",
    body: "You open five tabs. Five outlets, five versions of the same event. One says crisis. Another says routine. A third buries it on page six. The truth isn't in any single tab — it's in the space between them.",
    visual: "scale-draw",
  },
  {
    id: "why",
    duration: 4000,
    headline: "The space between",
    body: "We built void to live in that space. No editorial staff picking winners. No algorithm optimizing for outrage. Just 370 sources, scored on six axes, so you can see what every outlet chose to show you — and what they left out.",
    visual: "story",
  },
  {
    id: "lean",
    duration: 3600,
    headline: "The Needle",
    subtitle: "Political lean at a glance",
    body: "Each source lands somewhere on the spectrum. The needle shows you where — not to judge, but so you know which direction the wind is blowing.",
    visual: "needle",
  },
  {
    id: "depth",
    duration: 3200,
    headline: "The Ring",
    subtitle: "Coverage depth and breadth",
    body: "A thin ring means one outlet is talking. A full ring means the world noticed. The fuller it gets, the more you can trust that the story has been pressure-tested by competing newsrooms.",
    visual: "ring",
  },
  {
    id: "products",
    duration: 4000,
    headline: "Your daily toolkit",
    body: "Everything in void is a command you run — transparent, no mystery behind the curtain.",
    visual: "product",
  },
  {
    id: "audio",
    duration: 3600,
    headline: "Listen, don\u2019t scroll",
    body: "Two voices. One delivers the facts, the other asks the questions you\u2019d ask. Three minutes, no filler, no \u201Cthat\u2019s interesting.\u201D Just the story and why it matters.",
    visual: "product-audio",
  },
  {
    id: "verdict",
    duration: 4000,
    headline: "Read with clarity",
    body: "Lean and depth together. A story reported broadly across the spectrum, from many credible sources — that\u2019s where confidence lives.",
    visual: "verdict",
  },
];

/* ── Spring easing (CSS linear() approximation of damped spring) ────── */
const SPRING = "linear(0, 0.009, 0.035 2.1%, 0.141 4.4%, 0.723 15.5%, 0.938 20.7%, 1.017 24.3%, 1.061 27.7%, 1.085 32%, 1.078 36.3%, 1.042 44.4%, 1.014 53.3%, 0.996 64.4%, 1.001 78.8%, 1)";

/* ── Animated Needle SVG ───────────────────────────────────────────────── */

function AnimatedNeedle({ active }: { active: boolean }) {
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
  const angle = ((value - 50) / 50) * 35;

  return (
    <div className="intro-needle" aria-hidden="true">
      <div className="intro-needle__spectrum">
        <div className="intro-needle__spectrum-fill" />
      </div>
      <svg width="200" height="100" viewBox="0 0 200 100" className="intro-needle__svg">
        <line x1="20" y1="45" x2="20" y2="55" stroke="var(--border-strong)" strokeWidth="1" opacity="0.4" />
        <line x1="100" y1="42" x2="100" y2="58" stroke="var(--border-strong)" strokeWidth="1.5" opacity="0.5" />
        <line x1="180" y1="45" x2="180" y2="55" stroke="var(--border-strong)" strokeWidth="1" opacity="0.4" />
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
        <circle cx="100" cy="50" r="5" fill={color} style={{ transition: `fill 400ms ease` }} />
      </svg>
      <div className="intro-needle__labels">
        <span className="intro-needle__label" style={{ color: "var(--bias-left)" }}>Left</span>
        <span className="intro-needle__label" style={{ color: "var(--fg-muted)" }}>Center</span>
        <span className="intro-needle__label" style={{ color: "var(--bias-right)" }}>Right</span>
      </div>
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
        <circle cx="16" cy="13" r="9" className="intro-scale__void" />
        <g className="intro-scale__beam">
          <line x1="3" y1="13" x2="29" y2="13" className="intro-scale__line intro-scale__line--beam" />
          <line x1="5" y1="11" x2="5" y2="15" className="intro-scale__line intro-scale__line--tick-l" />
          <line x1="27" y1="11" x2="27" y2="15" className="intro-scale__line intro-scale__line--tick-r" />
        </g>
        <line x1="16" y1="22" x2="16" y2="29" className="intro-scale__line intro-scale__line--post" />
        <line x1="12" y1="29" x2="20" y2="29" className="intro-scale__line intro-scale__line--base" />
      </svg>
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
              transitionDelay: `${200 + i * 120}ms`,
            }}
          />
        ))}
      </div>
      <div className="intro-story-visual__void-line" />
    </div>
  );
}

/* ── Product Family Visual ─────────────────────────────────────────────── */

function ProductFamilyVisual({ active }: { active: boolean }) {
  const products = [
    { cmd: "void --tl;dr", label: "The Daily Brief", desc: "Top stories, editorially weighed" },
    { cmd: "void --opinion", label: "The Board", desc: "What the pattern reveals" },
    { cmd: "void --sources", label: "Source Spectrum", desc: "370 outlets on one axis" },
    { cmd: "void --deep-dive", label: "Story Analysis", desc: "Every source, every score" },
  ];

  return (
    <div className={`intro-products${active ? " intro-products--active" : ""}`} aria-hidden="true">
      {products.map((p, i) => (
        <div
          key={p.cmd}
          className="intro-products__item"
          style={{ transitionDelay: `${300 + i * 150}ms` }}
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
          <span>Voice A: the facts</span>
          <span>Voice B: the questions</span>
        </div>
      </div>
    </div>
  );
}

/* ── Verdict Combined Display ──────────────────────────────────────────── */

function VerdictDisplay({ active }: { active: boolean }) {
  return (
    <div className={`intro-verdict${active ? " intro-verdict--active" : ""}`} aria-hidden="true">
      <div className="intro-verdict__row">
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

/* ── Phase Visual Router ───────────────────────────────────────────────── */

function PhaseVisual({ visual, active }: { visual: Phase["visual"]; active: boolean }) {
  switch (visual) {
    case "scale-draw": return <ScaleIconDraw active={active} />;
    case "story": return <StoryVisual active={active} />;
    case "needle": return <AnimatedNeedle active={active} />;
    case "ring": return <AnimatedRing active={active} />;
    case "product": return <ProductFamilyVisual active={active} />;
    case "product-audio": return <AudioProductVisual active={active} />;
    case "verdict": return <VerdictDisplay active={active} />;
  }
}

/* ── Main Onboarding Component ─────────────────────────────────────────── */

export default function BiasLensOnboarding() {
  const [mounted, setMounted] = useState(false);
  const [visible, setVisible] = useState(false);
  const [phase, setPhase] = useState(-1);
  const [exiting, setExiting] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const idleTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reducedMotion = useRef(false);

  useEffect(() => {
    setMounted(true);
    reducedMotion.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    try {
      // Already dismissed — never show again
      if (localStorage.getItem(STORAGE_KEY)) return;

      // Track visit count
      const visits = parseInt(localStorage.getItem(VISITS_KEY) || "0", 10) + 1;
      localStorage.setItem(VISITS_KEY, String(visits));

      if (visits >= 2) {
        // 2nd+ visit: show after short delay (let content render first)
        setTimeout(() => {
          setVisible(true);
          setTimeout(() => setPhase(0), reducedMotion.current ? 0 : 600);
        }, 1500);
      } else {
        // 1st visit: show after 90s idle (content first)
        idleTimerRef.current = setTimeout(() => {
          // Re-check — user might have navigated away
          if (!localStorage.getItem(STORAGE_KEY)) {
            setVisible(true);
            setTimeout(() => setPhase(0), reducedMotion.current ? 0 : 600);
          }
        }, IDLE_TRIGGER_MS);
      }
    } catch { /* localStorage blocked — skip */ }

    return () => {
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    };
  }, []);

  // Auto-advance phases
  useEffect(() => {
    if (phase < 0 || phase >= PHASES.length - 1) return;
    if (reducedMotion.current) return;
    timerRef.current = setTimeout(() => {
      setPhase((p) => p + 1);
    }, PHASES[phase].duration);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [phase]);

  const dismiss = useCallback(() => {
    if (exiting) return;
    setExiting(true);
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch { /* ignore */ }
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
      <div className="intro__backdrop" aria-hidden="true" onClick={dismiss} />

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

        {/* Skip — always visible, easy to reach */}
        <button className="intro__skip" onClick={dismiss} aria-label="Skip introduction">
          Skip
        </button>

        {/* Illustration area */}
        <div className="intro__visual">
          {currentPhase && <PhaseVisual visual={currentPhase.visual} active />}
        </div>

        {/* Text area */}
        {currentPhase && (
          <div key={currentPhase.id} className="intro__text">
            <h2 className="intro__headline">{currentPhase.headline}</h2>
            {currentPhase.subtitle && (
              <p className="intro__subtitle">{currentPhase.subtitle}</p>
            )}
            <p className="intro__body">{currentPhase.body}</p>
          </div>
        )}

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
