"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import dynamic from "next/dynamic";

/* ---------------------------------------------------------------------------
   UnifiedOnboarding — Orchestrator for "The Prologue"

   Three-phase flow:
   1. Silent exploration: user browses freely for ~2 minutes
   2. Invitation card: subtle bottom card offers a 60-second tour
   3. Prologue: full cinematic introduction (if user opts in)

   Triggers: 120s elapsed OR 3+ story card interactions (whichever first).
   Skip always available. Never forced. Re-discoverable via /about.

   State machine: idle → invitation → prologue → complete
   Single localStorage key with migration from old keys.
   --------------------------------------------------------------------------- */

const OnboardingCarousel = dynamic(() => import("./OnboardingCarousel"), { ssr: false });

const STORAGE_KEY = "void-news-onboarding";
const OLD_CAROUSEL_KEY = "void-news-intro-seen";
const OLD_VISITS_KEY = "void-news-visit-count";
const OLD_TOUR_KEY = "void-tour-complete";

const EXPLORE_DELAY = 120_000;   // 2 minutes of exploration before invitation
const INTERACTION_THRESHOLD = 3;  // OR 3 story interactions
const INVITATION_LINGER = 15_000; // Auto-dismiss invitation after 15s if no action

type State = "idle" | "invitation" | "prologue" | "complete";

interface UnifiedOnboardingProps {
  active: boolean;
}

/* ── Invitation Card — subtle bottom CTA ──────────────────────────────── */

function InvitationCard({ onAccept, onDismiss }: { onAccept: () => void; onDismiss: () => void }) {
  const [show, setShow] = useState(false);
  const dismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const goRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    // Stagger entrance
    const t = setTimeout(() => {
      setShow(true);
      // Focus the CTA after entrance animation
      setTimeout(() => goRef.current?.focus(), 400);
    }, 50);
    // Auto-dismiss after linger period
    dismissTimer.current = setTimeout(() => {
      onDismiss();
    }, INVITATION_LINGER);
    return () => {
      clearTimeout(t);
      if (dismissTimer.current) clearTimeout(dismissTimer.current);
    };
  }, [onDismiss]);

  const handleAccept = useCallback(() => {
    if (dismissTimer.current) clearTimeout(dismissTimer.current);
    onAccept();
  }, [onAccept]);

  const handleDismiss = useCallback(() => {
    if (dismissTimer.current) clearTimeout(dismissTimer.current);
    setShow(false);
    setTimeout(onDismiss, 300);
  }, [onDismiss]);

  // Escape key dismisses
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") handleDismiss();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [handleDismiss]);

  if (typeof document === "undefined") return null;

  return createPortal(
    <div
      className={`onb-invite${show ? " onb-invite--visible" : ""}`}
      role="status"
      aria-live="polite"
      aria-label="Product tour invitation"
    >
      <div className="onb-invite__grain" aria-hidden="true" />
      <div className="onb-invite__content">
        <p className="onb-invite__text">
          There&rsquo;s more to every story.
        </p>
        <div className="onb-invite__actions">
          <button ref={goRef} className="onb-invite__btn onb-invite__btn--go" onClick={handleAccept}>
            60-second tour
          </button>
          <button className="onb-invite__btn onb-invite__btn--skip" onClick={handleDismiss}>
            Not now
          </button>
        </div>
      </div>
      <button className="onb-invite__close" onClick={handleDismiss} aria-label="Dismiss">
        &times;
      </button>
    </div>,
    document.body,
  );
}

export default function UnifiedOnboarding({ active }: UnifiedOnboardingProps) {
  const [state, setState] = useState<State>("idle");
  const exploreTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const interactionCountRef = useRef(0);
  const reducedMotion = useRef(false);

  // Check storage on mount — skip if already completed or migrated
  useEffect(() => {
    reducedMotion.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    try {
      if (localStorage.getItem(STORAGE_KEY)) {
        setState("complete");
        return;
      }

      // Migrate from old keys
      if (
        localStorage.getItem(OLD_CAROUSEL_KEY) ||
        sessionStorage.getItem(OLD_TOUR_KEY)
      ) {
        localStorage.setItem(STORAGE_KEY, "complete");
        localStorage.removeItem(OLD_CAROUSEL_KEY);
        localStorage.removeItem(OLD_VISITS_KEY);
        try { sessionStorage.removeItem(OLD_TOUR_KEY); } catch { /* ignore */ }
        setState("complete");
        return;
      }
    } catch {
      setState("complete");
    }
  }, []);

  // Track story card interactions (clicks on .story-card, .lead-section, .msc)
  useEffect(() => {
    if (state !== "idle" || !active) return;

    const handler = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.closest(".story-card") ||
        target.closest(".lead-section") ||
        target.closest(".msc")
      ) {
        interactionCountRef.current++;
        if (interactionCountRef.current >= INTERACTION_THRESHOLD) {
          showInvitation();
        }
      }
    };

    document.addEventListener("click", handler, { passive: true });
    return () => document.removeEventListener("click", handler);
  }, [state, active]);

  // Time-based trigger
  useEffect(() => {
    if (state !== "idle" || !active) return;

    exploreTimerRef.current = setTimeout(() => {
      showInvitation();
    }, EXPLORE_DELAY);

    return () => {
      if (exploreTimerRef.current) clearTimeout(exploreTimerRef.current);
    };
  }, [state, active]);

  const showInvitation = useCallback(() => {
    if (exploreTimerRef.current) clearTimeout(exploreTimerRef.current);
    setState((prev) => prev === "idle" ? "invitation" : prev);
  }, []);

  const markComplete = useCallback(() => {
    try { localStorage.setItem(STORAGE_KEY, "complete"); } catch { /* ignore */ }
    setState("complete");
  }, []);

  const handleAcceptInvitation = useCallback(() => {
    setState("prologue");
  }, []);

  const handleDismissInvitation = useCallback(() => {
    markComplete();
  }, [markComplete]);

  const handlePrologueComplete = useCallback(() => {
    markComplete();
  }, [markComplete]);

  const handlePrologueSkip = useCallback(() => {
    markComplete();
  }, [markComplete]);

  // Cleanup
  useEffect(() => {
    return () => {
      if (exploreTimerRef.current) clearTimeout(exploreTimerRef.current);
    };
  }, []);

  if (state === "complete" || state === "idle") return null;

  return (
    <>
      {state === "invitation" && (
        <InvitationCard
          onAccept={handleAcceptInvitation}
          onDismiss={handleDismissInvitation}
        />
      )}
      <OnboardingCarousel
        visible={state === "prologue"}
        onComplete={handlePrologueComplete}
        onSkip={handlePrologueSkip}
      />
    </>
  );
}
