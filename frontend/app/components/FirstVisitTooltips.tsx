"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";

/* ---------------------------------------------------------------------------
   FirstVisitTooltips — 3-step spotlight tour for first-time visitors

   Fires once on first visit (after 1500ms delay when `active` becomes true).
   Teaches the three core concepts: Sigil, Lean filters, Deep Dive.

   sessionStorage key `void-tour-complete` gates re-display.
   Overlay uses box-shadow spotlight trick (no clip-path).
   Tooltip repositions on window resize.
   Escape / Skip / backdrop click all dismiss.
   --------------------------------------------------------------------------- */

const STORAGE_KEY = "void-tour-complete";

interface TourStep {
  selector: string;
  title: string;
  body: string;
}

const STEPS: TourStep[] = [
  {
    selector: ".sigil",
    title: "Your bias compass",
    body: "The tilted scale shows political lean. The ring shows how many sources covered this story. Tap any story for the full picture.",
  },
  {
    selector: ".nav-filters__group",
    title: "Filter by perspective",
    body: "See how the same stories look from left, center, or right-leaning sources.",
  },
  {
    selector: ".lead-section, .story-card",
    title: "Tap for deep analysis",
    body: "Every story has a detailed breakdown: source spectrum, bias scores, and where outlets agree or diverge.",
  },
];

interface Rect {
  top: number;
  left: number;
  width: number;
  height: number;
}

const PADDING = 8;

function getTargetRect(selector: string): Rect | null {
  // Support comma-separated selectors — take first match
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

  // Prefer below the spotlight
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
    // Fallback: position below anyway
    top = spotBottom + GAP;
    arrowDir = "up";
  }

  // Center horizontally on the spotlight
  let left = spotRect.left + spotRect.width / 2 - tooltipWidth / 2;
  // Clamp to viewport
  left = Math.max(16 + window.scrollX, Math.min(left, viewW + window.scrollX - tooltipWidth - 16));

  return { top, left, arrowDir };
}

/* ── Main Component ─────────────────────────────────────────────────────── */

interface FirstVisitTooltipsProps {
  active: boolean;
}

export default function FirstVisitTooltips({ active }: FirstVisitTooltipsProps) {
  const [mounted, setMounted] = useState(false);
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(0);
  const [spotRect, setSpotRect] = useState<Rect | null>(null);
  const [tooltipPos, setTooltipPos] = useState<TooltipPos | null>(null);
  const [entering, setEntering] = useState(false);
  const [transitioning, setTransitioning] = useState(false);

  const tooltipRef = useRef<HTMLDivElement>(null);
  const dismissedRef = useRef(false);
  const delayRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reducedMotion = useRef(false);

  // Mount check
  useEffect(() => {
    setMounted(true);
    reducedMotion.current = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches;
  }, []);

  // Check sessionStorage and trigger tour
  useEffect(() => {
    if (!mounted || !active || dismissedRef.current) return;
    try {
      if (sessionStorage.getItem(STORAGE_KEY)) {
        dismissedRef.current = true;
        return;
      }
    } catch {
      /* sessionStorage blocked */
    }

    delayRef.current = setTimeout(() => {
      setVisible(true);
      setEntering(true);
      // Allow enter animation to paint
      requestAnimationFrame(() => {
        requestAnimationFrame(() => setEntering(false));
      });
    }, 1500);

    return () => {
      if (delayRef.current) clearTimeout(delayRef.current);
    };
  }, [mounted, active]);

  // Measure target and position tooltip whenever step changes or window resizes
  const measure = useCallback(() => {
    if (!visible || dismissedRef.current) return;
    const currentStep = STEPS[step];
    if (!currentStep) return;

    const rect = getTargetRect(currentStep.selector);
    if (!rect) {
      // Target not found — try to skip to next step
      if (step < STEPS.length - 1) {
        setStep((s) => s + 1);
      } else {
        dismiss();
      }
      return;
    }

    setSpotRect(rect);

    // Defer tooltip positioning to after render so we can measure tooltip size
    requestAnimationFrame(() => {
      const tooltipEl = tooltipRef.current;
      const tw = tooltipEl ? tooltipEl.offsetWidth : 320;
      const th = tooltipEl ? tooltipEl.offsetHeight : 200;
      setTooltipPos(computeTooltipPos(rect, tw, th));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, step]);

  useEffect(() => {
    measure();
  }, [measure]);

  useEffect(() => {
    if (!visible) return;
    const onResize = () => measure();
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onResize, { passive: true });
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onResize);
    };
  }, [visible, measure]);

  // Dismiss helper
  const dismiss = useCallback(() => {
    if (dismissedRef.current) return;
    dismissedRef.current = true;
    try {
      sessionStorage.setItem(STORAGE_KEY, "1");
    } catch {
      /* ignore */
    }
    setVisible(false);
  }, []);

  // Advance to next step
  const advance = useCallback(() => {
    if (step >= STEPS.length - 1) {
      dismiss();
      return;
    }
    setTransitioning(true);
    const dur = reducedMotion.current ? 0 : 180;
    setTimeout(() => {
      setStep((s) => s + 1);
      setTransitioning(false);
    }, dur);
  }, [step, dismiss]);

  // Keyboard handler
  useEffect(() => {
    if (!visible) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        dismiss();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [visible, dismiss]);

  if (!mounted || !visible) return null;

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
      {/* Backdrop — click to advance */}
      <div
        className="tour__backdrop"
        onClick={advance}
        aria-hidden="true"
      />

      {/* Spotlight cutout */}
      <div
        className="tour__spotlight"
        style={spotStyle}
        aria-hidden="true"
      />

      {/* Tooltip card */}
      <div
        ref={tooltipRef}
        className={`tour__tooltip${tooltipPos?.arrowDir === "down" ? " tour__tooltip--above" : ""}${isEnteringOrTransitioning ? " tour__tooltip--animating" : ""}`}
        style={tooltipStyle}
      >
        {/* Arrow */}
        <div
          className={`tour__tooltip-arrow tour__tooltip-arrow--${tooltipPos?.arrowDir || "up"}`}
          aria-hidden="true"
        />

        {/* Step dots */}
        <div className="tour__dots" aria-hidden="true">
          {STEPS.map((_, i) => (
            <span
              key={i}
              className={`tour__dot${i === step ? " tour__dot--active" : ""}`}
            />
          ))}
        </div>

        {/* Content */}
        <h3 className="tour__title">{currentStep.title}</h3>
        <p className="tour__body">{currentStep.body}</p>

        {/* Actions */}
        <div className="tour__actions">
          <button
            className="tour__skip"
            onClick={dismiss}
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
