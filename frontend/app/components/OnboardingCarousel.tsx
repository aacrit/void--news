"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import { CHAPTERS } from "../film/data";
import { useReducedMotion } from "../film/useReducedMotion";
import DivergentHeadlines from "../film/scenes/DivergentHeadlines";
import SigilBreakdown from "../film/scenes/SigilBreakdown";
import SourceEngine from "../film/scenes/SourceEngine";
import ArticleDifference from "../film/scenes/ArticleDifference";
import ProductWorlds from "../film/scenes/ProductWorlds";
import TheVerdict from "../film/scenes/TheVerdict";

/* ==========================================================================
   OnboardingCarousel — "The Film: Prologue"

   Thin wrapper that renders shared film/scenes in prologue mode.
   6-chapter cinematic product introduction (~90s).

   All content and visuals are in film/scenes/*.tsx and film/data.ts.
   This file handles: modal overlay, auto-advance, keyboard nav,
   body scroll lock, focus trap, progress dots.
   ========================================================================== */

const MODE = "prologue" as const;

/* ── Scene Visual Router ── */

function SceneVisual({ chapterId, active }: { chapterId: string; active: boolean }) {
  switch (chapterId) {
    case "the-void":       return <DivergentHeadlines mode={MODE} active={active} />;
    case "the-instrument": return <SigilBreakdown mode={MODE} active={active} />;
    case "the-engine":     return <SourceEngine mode={MODE} active={active} />;
    case "the-difference": return <ArticleDifference mode={MODE} active={active} />;
    case "the-worlds":     return <ProductWorlds mode={MODE} active={active} />;
    case "the-verdict":    return <TheVerdict mode={MODE} active={active} />;
    default: return null;
  }
}

/* ── Main Component ── */

interface Props {
  visible: boolean;
  onComplete: () => void;
  onSkip: () => void;
}

export default function OnboardingCarousel({ visible, onComplete, onSkip }: Props) {
  const [mounted, setMounted] = useState(false);
  const [phase, setPhase] = useState(-1);
  const [exiting, setExiting] = useState(false);
  const [paused, setPaused] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reducedMotion = useReducedMotion();
  const exitCallbackRef = useRef<(() => void) | null>(null);

  useEffect(() => { setMounted(true); }, []);

  // Body scroll lock
  useEffect(() => {
    if (!visible || !mounted) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => { document.body.style.overflow = prev; };
  }, [visible, mounted]);

  // Start phase 0
  useEffect(() => {
    if (!mounted || !visible) return;
    const delay = reducedMotion.current ? 0 : 600;
    const timer = setTimeout(() => setPhase(0), delay);
    return () => clearTimeout(timer);
  }, [mounted, visible, reducedMotion]);

  // Auto-advance — gated by exiting
  useEffect(() => {
    if (phase < 0 || phase >= CHAPTERS.length - 1) return;
    if (reducedMotion.current || exiting) return;
    if (paused) {
      if (timerRef.current) clearTimeout(timerRef.current);
      return;
    }
    timerRef.current = setTimeout(() => {
      setPhase((p) => p + 1);
    }, CHAPTERS[phase].duration);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [phase, paused, exiting, reducedMotion]);

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
  }, [exiting, reducedMotion]);

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
      if (e.key === "ArrowRight" || (e.key === " " && !(e.target instanceof HTMLButtonElement))) {
        e.preventDefault();
        if (phase < CHAPTERS.length - 1) {
          if (timerRef.current) clearTimeout(timerRef.current);
          setPhase((p) => Math.min(CHAPTERS.length - 1, p + 1));
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

  const chapter = phase >= 0 ? CHAPTERS[phase] : null;
  const isLast = phase === CHAPTERS.length - 1;
  const progress = phase >= 0 ? ((phase + 1) / CHAPTERS.length) * 100 : 0;

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
            if (!dialogRef.current?.contains(e.relatedTarget as Node)) resumeAutoAdvance();
          }}
        >
          {/* Visual */}
          <div className="intro__visual">
            {chapter && <SceneVisual chapterId={chapter.id} active />}
          </div>

          {/* Text — aria-live for screen readers */}
          {chapter && (
            <div key={chapter.id} className="intro__text" aria-live="polite" aria-atomic="true">
              <span className="intro__chapter">{chapter.roman}</span>
              <h2 className="intro__headline">{chapter.headline}</h2>
              {chapter.subtitle && (
                <p className="intro__subtitle">{chapter.subtitle}</p>
              )}
              <p className="intro__body">{chapter.prologueBody}</p>
            </div>
          )}
        </div>

        {/* Chapter dots */}
        <div className="intro__dots" aria-label="Guide sections">
          {CHAPTERS.map((ch, i) => (
            <button
              key={ch.id}
              aria-label={`Go to chapter ${i + 1}: ${ch.headline}`}
              aria-current={i === phase ? "step" : undefined}
              className={`intro__dot${i === phase ? " intro__dot--active" : ""}${i < phase ? " intro__dot--done" : ""}`}
              onClick={() => {
                if (timerRef.current) clearTimeout(timerRef.current);
                setPhase(i);
              }}
            />
          ))}
        </div>

        {/* Actions */}
        <div className="intro__actions">
          {!isLast ? (
            <button className="intro__btn intro__btn--next" onClick={() => {
              if (timerRef.current) clearTimeout(timerRef.current);
              setPhase((p) => Math.min(CHAPTERS.length - 1, p + 1));
            }}>
              Next
            </button>
          ) : (
            <>
              <button className="intro__btn intro__btn--primary" onClick={handleComplete} autoFocus>
                Start reading
              </button>
              <a href="/void--news/about" className="intro__manifesto-link" onClick={() => dismiss(onComplete)}>
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
