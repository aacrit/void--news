"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import dynamic from "next/dynamic";

/* ---------------------------------------------------------------------------
   UnifiedOnboarding — Orchestrator for two-act onboarding flow

   Act 1: OnboardingCarousel (modal) — teaches concepts (beam, ring, products)
   Act 2: OnboardingSpotlight (spotlight tour) — grounds concepts in real UI

   State machine: idle → carousel → transitioning → spotlight → complete
   Single localStorage key with migration from old keys.
   --------------------------------------------------------------------------- */

const OnboardingCarousel = dynamic(() => import("./OnboardingCarousel"), { ssr: false });
const OnboardingSpotlight = dynamic(() => import("./OnboardingSpotlight"), { ssr: false });

const STORAGE_KEY = "void-news-onboarding";
const OLD_CAROUSEL_KEY = "void-news-intro-seen";
const OLD_VISITS_KEY = "void-news-visit-count";
const OLD_TOUR_KEY = "void-tour-complete";
const TRIGGER_DELAY = 1500;
const TRANSITION_DELAY = 600; // 500ms exit animation + 100ms breath

type State = "idle" | "carousel" | "transitioning" | "spotlight" | "complete";

interface UnifiedOnboardingProps {
  active: boolean;
}

export default function UnifiedOnboarding({ active }: UnifiedOnboardingProps) {
  const [state, setState] = useState<State>("idle");
  const triggerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const transitionRef = useRef<ReturnType<typeof setTimeout> | null>(null);
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
        // Clean up old keys
        localStorage.removeItem(OLD_CAROUSEL_KEY);
        localStorage.removeItem(OLD_VISITS_KEY);
        try { sessionStorage.removeItem(OLD_TOUR_KEY); } catch { /* ignore */ }
        setState("complete");
        return;
      }
    } catch {
      // Storage blocked — skip onboarding entirely
      setState("complete");
    }
  }, []);

  // Trigger carousel when content is ready
  useEffect(() => {
    if (state !== "idle" || !active) return;

    triggerRef.current = setTimeout(() => {
      setState("carousel");
    }, TRIGGER_DELAY);

    return () => {
      if (triggerRef.current) clearTimeout(triggerRef.current);
    };
  }, [state, active]);

  const handleCarouselDone = useCallback(() => {
    setState("transitioning");
    const delay = reducedMotion.current ? 0 : TRANSITION_DELAY;
    transitionRef.current = setTimeout(() => {
      setState("spotlight");
    }, delay);
  }, []);

  // Skip carousel but still show spotlight
  const handleCarouselSkip = useCallback(() => {
    setState("transitioning");
    const delay = reducedMotion.current ? 0 : TRANSITION_DELAY;
    transitionRef.current = setTimeout(() => {
      setState("spotlight");
    }, delay);
  }, []);

  const markComplete = useCallback(() => {
    try { localStorage.setItem(STORAGE_KEY, "complete"); } catch { /* ignore */ }
    setState("complete");
  }, []);

  const handleSpotlightDone = useCallback(() => {
    markComplete();
  }, [markComplete]);

  const handleSpotlightSkip = useCallback(() => {
    markComplete();
  }, [markComplete]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (triggerRef.current) clearTimeout(triggerRef.current);
      if (transitionRef.current) clearTimeout(transitionRef.current);
    };
  }, []);

  if (state === "complete" || state === "idle") return null;

  return (
    <>
      <OnboardingCarousel
        visible={state === "carousel"}
        onComplete={handleCarouselDone}
        onSkip={handleCarouselSkip}
      />
      <OnboardingSpotlight
        visible={state === "spotlight"}
        onComplete={handleSpotlightDone}
        onSkip={handleSpotlightSkip}
      />
    </>
  );
}
