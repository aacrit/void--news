"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { createPortal } from "react-dom";
import dynamic from "next/dynamic";
import "../styles/onboarding.css";

/* ---------------------------------------------------------------------------
   UnifiedOnboarding — Orchestrator for "The Prologue"

   Two-phase flow:
   1. Invitation card: a bottom card offers a 60-second tour, on arrival
   2. Prologue: full cinematic introduction (if the reader opts in)

   Offered ONCE (P1-14, 2026-10-02). It used to wait 120 s or three card
   clicks, so the reader who most needed it, the one who did not know how to
   read a card, had usually left first (audit 2 F6). It now offers shortly
   after arrival, and the offer is recorded the moment it is shown: accept,
   "Not now", the close button, Escape or the card timing out all end it for
   good. It never takes focus from the page; it announces itself politely.
   Never forced. Re-discoverable via /about.

   State machine: idle → invitation → prologue → complete
   Single localStorage key with migration from old keys.
   --------------------------------------------------------------------------- */

const AboutExperience = dynamic(() => import("./about/AboutExperience"), { ssr: false });

const STORAGE_KEY = "void-news-onboarding";
const OLD_CAROUSEL_KEY = "void-news-intro-seen";
const OLD_VISITS_KEY = "void-news-visit-count";
const OLD_TOUR_KEY = "void-tour-complete";

const ARRIVAL_DELAY = 1_200;      // let the page settle before the card slides in
const INVITATION_LINGER = 20_000; // the card withdraws after 20s if left alone

type State = "idle" | "invitation" | "prologue" | "complete";

interface UnifiedOnboardingProps {
  active: boolean;
}

/* ── Invitation Card — subtle bottom CTA ──────────────────────────────── */

function InvitationCard({ onAccept, onDismiss }: { onAccept: () => void; onDismiss: () => void }) {
  const [show, setShow] = useState(false);
  const dismissTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    // Stagger entrance. No focus move: on arrival the reader's focus belongs
    // to the page (the skip link first), and the card announces itself.
    const t = setTimeout(() => setShow(true), 50);
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
          <button className="onb-invite__btn onb-invite__btn--go" onClick={handleAccept}>
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
  const reducedMotion = useRef(false);

  // Declared before the effects that call it (lint: no use-before-declare).
  const showInvitation = useCallback(() => {
    if (exploreTimerRef.current) clearTimeout(exploreTimerRef.current);
    // Offered once: recorded as it is shown, so no answer brings it back.
    try { localStorage.setItem(STORAGE_KEY, "offered"); } catch { /* storage blocked */ }
    setState((prev) => prev === "idle" ? "invitation" : prev);
  }, []);

  // Check storage on mount — skip if already completed or migrated
  useEffect(() => {
    reducedMotion.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    try {
      if (localStorage.getItem(STORAGE_KEY)) {
        setState("complete");
        return;
      }

      // Deferred this session — skip but allow next visit
      if (sessionStorage.getItem(STORAGE_KEY + "-deferred")) {
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

  // On arrival
  useEffect(() => {
    if (state !== "idle" || !active) return;

    exploreTimerRef.current = setTimeout(() => {
      showInvitation();
    }, ARRIVAL_DELAY);

    return () => {
      if (exploreTimerRef.current) clearTimeout(exploreTimerRef.current);
    };
  }, [state, active, showInvitation]);

  const markComplete = useCallback(() => {
    try { localStorage.setItem(STORAGE_KEY, "complete"); } catch { /* ignore */ }
    setState("complete");
  }, []);

  const handleAcceptInvitation = useCallback(() => {
    setState("prologue");
  }, []);

  // Invitation dismissed ("Not now", close, Escape, or left to time out):
  // complete for good. The offer is made once.
  const handleDismissInvitation = useCallback(() => {
    markComplete();
  }, [markComplete]);

  // Prologue finished or explicitly skipped — permanently complete
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
      {state === "prologue" && (
        <AboutExperience
          presentation="overlay"
          onComplete={handlePrologueComplete}
          onClose={handlePrologueSkip}
        />
      )}
    </>
  );
}
