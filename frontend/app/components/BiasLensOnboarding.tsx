"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";

/* ---------------------------------------------------------------------------
   BiasLensOnboarding — 3-slide carousel explaining bias lenses on first visit.

   Slide 1: The Needle — political lean
   Slide 2: The Ring — coverage depth
   Slide 3: Combined — together they tell the story

   Shown once per browser (localStorage key: void-news-bias-onboarding-seen).
   --------------------------------------------------------------------------- */

const STORAGE_KEY = "void-news-bias-onboarding-seen";

/* ---- Static SVG examples ---- */

/** Needle SVG: tilting horizontal bar showing lean. value 0–100. */
function NeedleExample({ value, label, color }: { value: number; label: string; color: string }) {
  // Map 0–100 to -30deg (far left) to +30deg (far right). 50 = 0deg.
  const angle = ((value - 50) / 50) * 30;
  return (
    <div className="onboard-example onboard-example--needle" aria-label={`${label} lean needle`}>
      <svg width="48" height="28" viewBox="0 0 48 28" aria-hidden="true">
        <line
          x1="6" y1="14" x2="42" y2="14"
          stroke={color}
          strokeWidth="3"
          strokeLinecap="round"
          style={{ transform: `rotate(${angle}deg)`, transformOrigin: "24px 14px" }}
        />
        <circle cx="24" cy="14" r="3" fill={color} />
      </svg>
      <span className="onboard-example__label text-data">{label}</span>
    </div>
  );
}

/** Ring SVG: Harvey-ball style fill ring. pct 0–100. */
function RingExample({ pct, label }: { pct: number; label: string }) {
  const r = 10;
  const circ = 2 * Math.PI * r;
  const dash = (pct / 100) * circ;
  const color = pct >= 70 ? "var(--sense-low)" : pct >= 40 ? "var(--sense-medium)" : "var(--sense-high)";
  return (
    <div className="onboard-example onboard-example--ring" aria-label={`${pct}% coverage ring: ${label}`}>
      <svg width="32" height="32" viewBox="0 0 32 32" aria-hidden="true">
        {/* Track */}
        <circle cx="16" cy="16" r={r} fill="none" stroke="var(--border-subtle)" strokeWidth="3" />
        {/* Fill */}
        <circle
          cx="16" cy="16" r={r}
          fill="none"
          stroke={color}
          strokeWidth="3"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          transform="rotate(-90 16 16)"
        />
      </svg>
      <span className="onboard-example__label text-data">{label}</span>
    </div>
  );
}

/** Combined example — needle + ring side by side. */
function CombinedExample() {
  return (
    <div className="onboard-combined">
      <div className="onboard-combined__group">
        <NeedleExample value={25} label="Left" color="var(--bias-left)" />
        <RingExample pct={80} label="Broad" />
        <span className="onboard-combined__verdict text-data">Well covered, left-leaning</span>
      </div>
      <div className="onboard-combined__group">
        <NeedleExample value={50} label="Center" color="var(--bias-center)" />
        <RingExample pct={45} label="Moderate" />
        <span className="onboard-combined__verdict text-data">Center, moderate coverage</span>
      </div>
    </div>
  );
}

const SLIDES = [
  {
    id: "needle",
    title: "The Needle shows political lean",
    description:
      "The tilting bar indicates where sources fall on the political spectrum — left, center, or right. The color reinforces the direction.",
    illustration: (
      <div className="onboard-illustrations">
        <NeedleExample value={15} label="Left" color="var(--bias-left)" />
        <NeedleExample value={50} label="Center" color="var(--bias-center)" />
        <NeedleExample value={85} label="Right" color="var(--bias-right)" />
      </div>
    ),
  },
  {
    id: "ring",
    title: "The Ring shows coverage depth",
    description:
      "The signal ring fills based on how many credible sources cover this story and their factual rigor — think of it as a confidence meter.",
    illustration: (
      <div className="onboard-illustrations">
        <RingExample pct={25} label="Few sources" />
        <RingExample pct={60} label="Moderate" />
        <RingExample pct={90} label="Broad coverage" />
      </div>
    ),
  },
  {
    id: "combined",
    title: "Together: lean + depth",
    description:
      "Read both at once: a broadly covered, centered story is likely the most reliable take. A single-source, far-lean story warrants more scrutiny.",
    illustration: <CombinedExample />,
  },
];

export default function BiasLensOnboarding() {
  const [mounted, setMounted] = useState(false);
  const [visible, setVisible] = useState(false);
  const [slide, setSlide] = useState(0);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    setMounted(true);
    try {
      if (!localStorage.getItem(STORAGE_KEY)) {
        setVisible(true);
      }
    } catch {
      // localStorage blocked — skip onboarding silently
    }
  }, []);

  const dismiss = useCallback(() => {
    setVisible(false);
    try { localStorage.setItem(STORAGE_KEY, "1"); } catch { /* ignore */ }
    previousFocusRef.current?.focus();
  }, []);

  // Focus trap
  useEffect(() => {
    if (!visible) return;
    previousFocusRef.current = document.activeElement as HTMLElement;

    // Focus first interactive element
    const timer = setTimeout(() => {
      const el = dialogRef.current?.querySelector<HTMLElement>(
        'button, [tabindex]:not([tabindex="-1"])',
      );
      el?.focus();
    }, 50);

    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") { dismiss(); return; }
      if (e.key === "Tab" && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [tabindex]:not([tabindex="-1"])',
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener("keydown", onKey);
    return () => { clearTimeout(timer); document.removeEventListener("keydown", onKey); };
  }, [visible, dismiss]);

  if (!mounted || !visible) return null;

  const current = SLIDES[slide];
  const isLast = slide === SLIDES.length - 1;

  return createPortal(
    <>
      {/* Frosted backdrop */}
      <div
        className="onboard-backdrop"
        aria-hidden="true"
        onClick={dismiss}
      />

      {/* Dialog */}
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Bias lens guide"
        aria-describedby="onboard-description"
        className="onboard-dialog"
      >
        {/* Close button */}
        <button
          className="onboard-close"
          onClick={dismiss}
          aria-label="Close guide"
        >
          &#x2715;
        </button>

        {/* Slide counter */}
        <div className="onboard-counter text-data" aria-live="polite" aria-atomic="true">
          {slide + 1} / {SLIDES.length}
        </div>

        {/* Illustration */}
        <div className="onboard-illustration" aria-hidden="true">
          {current.illustration}
        </div>

        {/* Content */}
        <h2 className="onboard-title">{current.title}</h2>
        <p id="onboard-description" className="onboard-description">
          {current.description}
        </p>

        {/* Dot navigation */}
        <div className="onboard-dots" role="tablist" aria-label="Slide navigation">
          {SLIDES.map((s, i) => (
            <button
              key={s.id}
              role="tab"
              aria-selected={i === slide}
              aria-label={`Go to slide ${i + 1}: ${s.title}`}
              className={`onboard-dot${i === slide ? " onboard-dot--active" : ""}`}
              onClick={() => setSlide(i)}
            />
          ))}
        </div>

        {/* Navigation buttons */}
        <div className="onboard-nav">
          {slide > 0 && (
            <button
              className="onboard-btn onboard-btn--prev"
              onClick={() => setSlide((s) => s - 1)}
              aria-label="Previous slide"
            >
              &#8592; Back
            </button>
          )}
          <div style={{ flex: 1 }} />
          {isLast ? (
            <button
              className="onboard-btn onboard-btn--primary"
              onClick={dismiss}
              autoFocus={isLast}
            >
              Got it
            </button>
          ) : (
            <button
              className="onboard-btn onboard-btn--next"
              onClick={() => setSlide((s) => s + 1)}
              aria-label="Next slide"
            >
              Next &#8594;
            </button>
          )}
        </div>

        {/* Skip */}
        <button className="onboard-skip" onClick={dismiss}>
          Skip intro
        </button>
      </div>
    </>,
    document.body,
  );
}
