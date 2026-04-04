"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";

/* ---------------------------------------------------------------------------
   OnboardingSpotlight — Act 2 of unified onboarding

   Spotlight tour that highlights real UI elements after the carousel
   (Act 1) has taught concepts. Walks through the key interactions:
   sigil, deep dive, on air, topics, lean filter, editions.

   Controlled by UnifiedOnboarding orchestrator via visible/onComplete/onSkip.
   --------------------------------------------------------------------------- */

interface TourStep {
  selector: string;
  title: string;
  body: string;
  /** Optional: action to perform when this step appears (e.g. scroll element into view) */
  action?: "click-first" | "scroll-into-view";
}

const STEPS: TourStep[] = [
  {
    selector: ".sigil",
    title: "The bias sigil",
    body: "Every story carries this hand-drawn mark. The beam tilts with political lean, the ring fills with source coverage. Tap it for the full breakdown.",
  },
  {
    selector: ".lead-section, .story-card",
    title: "Tap to open Deep Dive",
    body: "Tap any story to open its Deep Dive \u2014 the ink line shows where each source sits, six-axis scores reveal framing, and perspectives highlight where outlets agree or diverge.",
    action: "scroll-into-view",
  },
  {
    selector: ".skb, .mbp",
    title: "void --onair",
    body: "The daily brief lives here. Read the editorial take, or hit play for a two-host audio broadcast.",
    action: "scroll-into-view",
  },
  {
    selector: ".nav-lens__topics, .nav-lens__trigger",
    title: "Filter by topic",
    body: "Focus on what matters. Filter stories by category \u2014 Politics, Economy, Technology, and more.",
  },
  {
    selector: ".nav-lens__group, .lean-filter",
    title: "Filter by perspective",
    body: "See how the same stories look from left, center, or right-leaning sources.",
  },
  {
    selector: ".nav-lens__editions, .mob-nav__tabs",
    title: "Switch editions",
    body: "Four newsrooms, one page. World is the default. Switch to US, Europe, or South Asia for regional focus.",
  },
];

interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

const PADDING = 8;
const MAX_RETRIES = 3;
const RETRY_DELAY = 500;

function getTargetRect(selector: string): Rect | null {
  const parts = selector.split(",").map((s) => s.trim());
  for (const sel of parts) {
    const el = document.querySelector<HTMLElement>(sel);
    if (el) {
      const r = el.getBoundingClientRect();
      return {
        top: r.top + window.scrollY,
        left: r.left + window.scrollX,
        width: r.width,
        height: r.height,
      };
    }
  }
  return null;
}

interface TooltipPos {
  top: number;
  left: number;
  arrowDir: "up" | "down";
}

function computeTooltipPos(
  spotRect: Rect,
  tooltipWidth: number,
  tooltipHeight: number,
): TooltipPos {
  const GAP = 12;
  const viewH = window.innerHeight;
  const viewW = window.innerWidth;
  const scrollY = window.scrollY;

  const spotBottom = spotRect.top + spotRect.height + PADDING;
  const spotTop = spotRect.top - PADDING;
  const spaceBelow = viewH + scrollY - spotBottom;
  const spaceAbove = spotTop - scrollY;

  let top: number;
  let arrowDir: "up" | "down";

  if (spaceBelow >= tooltipHeight + GAP + 20) {
    top = spotBottom + GAP;
    arrowDir = "up";
  } else if (spaceAbove >= tooltipHeight + GAP + 20) {
    top = spotTop - GAP - tooltipHeight;
    arrowDir = "down";
  } else {
    top = spotBottom + GAP;
    arrowDir = "up";
  }

  let left = spotRect.left + spotRect.width / 2 - tooltipWidth / 2;
  left = Math.max(16 + window.scrollX, Math.min(left, viewW + window.scrollX - tooltipWidth - 16));

  return { top, left, arrowDir };
}

/* ── Main Component ─────────────────────────────────────────────────────── */

interface OnboardingSpotlightProps {
  visible: boolean;
  onComplete: () => void;
  onSkip: () => void;
}

export default function OnboardingSpotlight({ visible, onComplete, onSkip }: OnboardingSpotlightProps) {
  const [mounted, setMounted] = useState(false);
  const [ready, setReady] = useState(false);
  const [step, setStep] = useState(0);
  const [spotRect, setSpotRect] = useState<Rect | null>(null);
  const [tooltipPos, setTooltipPos] = useState<TooltipPos | null>(null);
  const [entering, setEntering] = useState(false);
  const [transitioning, setTransitioning] = useState(false);

  const tooltipRef = useRef<HTMLDivElement>(null);
  const reducedMotion = useRef(false);
  const retryRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const retryCountRef = useRef(0);

  useEffect(() => {
    setMounted(true);
    reducedMotion.current = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
  }, []);

  // Trigger entrance when visible
  useEffect(() => {
    if (!mounted || !visible) {
      setReady(false);
      setStep(0);
      retryCountRef.current = 0;
      return;
    }

    setReady(true);
    setEntering(true);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => setEntering(false));
    });

    return () => {
      if (retryRef.current) clearTimeout(retryRef.current);
    };
  }, [mounted, visible]);

  // Measure target and position tooltip
  const measure = useCallback(() => {
    if (!ready) return;
    const currentStep = STEPS[step];
    if (!currentStep) return;

    // Scroll target into view if the step requests it
    if (currentStep.action === "scroll-into-view") {
      const parts = currentStep.selector.split(",").map((s) => s.trim());
      for (const sel of parts) {
        const el = document.querySelector<HTMLElement>(sel);
        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          break;
        }
      }
    }

    const rect = getTargetRect(currentStep.selector);
    if (!rect) {
      // Retry up to MAX_RETRIES times before skipping
      if (retryCountRef.current < MAX_RETRIES) {
        retryCountRef.current++;
        retryRef.current = setTimeout(measure, RETRY_DELAY);
        return;
      }
      // Exhausted retries — skip to next step or finish
      retryCountRef.current = 0;
      if (step < STEPS.length - 1) {
        setStep((s) => s + 1);
      } else {
        onComplete();
      }
      return;
    }

    retryCountRef.current = 0;
    setSpotRect(rect);

    requestAnimationFrame(() => {
      const tooltipEl = tooltipRef.current;
      const tw = tooltipEl ? tooltipEl.offsetWidth : 320;
      const th = tooltipEl ? tooltipEl.offsetHeight : 200;
      setTooltipPos(computeTooltipPos(rect, tw, th));
    });
  }, [ready, step, onComplete]);

  useEffect(() => {
    measure();
  }, [measure]);

  useEffect(() => {
    if (!ready) return;
    const onResize = () => measure();
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onResize, { passive: true });
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onResize);
    };
  }, [ready, measure]);

  // Advance to next step
  const advance = useCallback(() => {
    if (step >= STEPS.length - 1) {
      onComplete();
      return;
    }
    setTransitioning(true);
    retryCountRef.current = 0;
    const dur = reducedMotion.current ? 0 : 180;
    setTimeout(() => {
      setStep((s) => s + 1);
      setTransitioning(false);
    }, dur);
  }, [step, onComplete]);

  // Keyboard handler
  useEffect(() => {
    if (!ready) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onSkip();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [ready, onSkip]);

  if (!mounted || !ready) return null;

  const currentStep = STEPS[step];
  if (!currentStep) return null;

  const spotStyle: React.CSSProperties = spotRect
    ? {
        top: spotRect.top - PADDING,
        left: spotRect.left - PADDING,
        width: spotRect.width + PADDING * 2,
        height: spotRect.height + PADDING * 2,
      }
    : { top: 0, left: 0, width: 0, height: 0, opacity: 0 };

  const tooltipStyle: React.CSSProperties = tooltipPos
    ? {
        top: tooltipPos.top,
        left: tooltipPos.left,
      }
    : { top: 0, left: 0, opacity: 0 };

  const isEnteringOrTransitioning = entering || transitioning;

  return createPortal(
    <div
      className={`tour${entering ? " tour--entering" : ""}${transitioning ? " tour--transitioning" : ""}`}
      role="dialog"
      aria-modal="true"
      aria-label={`Tour step ${step + 1} of ${STEPS.length}: ${currentStep.title}`}
    >
      <div
        className="tour__backdrop"
        onClick={advance}
        aria-hidden="true"
      />

      <div
        className="tour__spotlight"
        style={spotStyle}
        aria-hidden="true"
      />

      <div
        ref={tooltipRef}
        className={`tour__tooltip${tooltipPos?.arrowDir === "down" ? " tour__tooltip--above" : ""}${isEnteringOrTransitioning ? " tour__tooltip--animating" : ""}`}
        style={tooltipStyle}
      >
        <div
          className={`tour__tooltip-arrow tour__tooltip-arrow--${tooltipPos?.arrowDir || "up"}`}
          aria-hidden="true"
        />

        <div className="tour__dots" aria-hidden="true">
          {STEPS.map((_, i) => (
            <span
              key={i}
              className={`tour__dot${i === step ? " tour__dot--active" : ""}`}
            />
          ))}
        </div>

        <h3 className="tour__title">{currentStep.title}</h3>
        <p className="tour__body">{currentStep.body}</p>

        <div className="tour__actions">
          <button
            className="tour__skip"
            onClick={onSkip}
            type="button"
          >
            Skip tour
          </button>
          <button
            className="tour__next-btn"
            onClick={advance}
            type="button"
            autoFocus
          >
            {step < STEPS.length - 1 ? "Next" : "Done"}
          </button>
        </div>
      </div>
    </div>,
    document.body,
  );
}
