"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import type { HistoricalEvent } from "../types";
import EventDetail from "./EventDetail";

/* ===========================================================================
   HistoryOverlay — Full-screen story overlay with FLIP morph
   Opens when user clicks "Read all N perspectives" on a landing tile.
   The tile photo FLIP-morphs into EventDetail's hero image. URL updates
   via pushState (no router.push). Browser back closes overlay.
   =========================================================================== */

interface HistoryOverlayProps {
  event: HistoricalEvent;
  allEvents: HistoricalEvent[];
  sourceRect: DOMRect | null; // tile photo position for FLIP
  onClose: () => void;
}

export default function HistoryOverlay({
  event,
  allEvents,
  sourceRect,
  onClose,
}: HistoryOverlayProps) {
  const overlayRef = useRef<HTMLDivElement>(null);
  const [contentVisible, setContentVisible] = useState(false);
  const closingRef = useRef(false);

  /* ── Reduced motion check ── */
  const reducedMotion = typeof window !== "undefined"
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false;

  /* ── FLIP morph on mount ── */
  useEffect(() => {
    if (reducedMotion || !sourceRect) {
      setContentVisible(true);
      return;
    }

    /* Find EventDetail's hero image inside the overlay */
    const heroEl = overlayRef.current?.querySelector<HTMLImageElement>(".hist-hero__image");

    if (!heroEl) {
      setContentVisible(true);
      return;
    }

    /* Double rAF: first commits the snap frame, second starts transition */
    requestAnimationFrame(() => {
      const targetRect = heroEl.getBoundingClientRect();

      if (targetRect.width === 0 || targetRect.height === 0) {
        setContentVisible(true);
        return;
      }

      /* Snap to source position */
      const dx = sourceRect.left - targetRect.left;
      const dy = sourceRect.top - targetRect.top;
      const sx = sourceRect.width / targetRect.width;
      const sy = sourceRect.height / targetRect.height;

      heroEl.style.transform = `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`;
      heroEl.style.transformOrigin = "top left";
      heroEl.style.transition = "none";

      /* Force reflow */
      heroEl.offsetHeight; // eslint-disable-line @typescript-eslint/no-unused-expressions

      requestAnimationFrame(() => {
        /* Animate to final position */
        heroEl.style.transition = "transform 500ms cubic-bezier(0.4, 0, 0.2, 1)";
        heroEl.style.transform = "none";

        /* L-cut: content cascades in while morph settles */
        setTimeout(() => setContentVisible(true), 250);
      });
    });
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  /* ── pushState for URL + popstate listener ── */
  useEffect(() => {
    /* Push history state so browser back closes overlay */
    window.history.pushState(
      { historyOverlay: true, slug: event.slug },
      "",
      `/history/${event.slug}`
    );

    const handlePopState = () => {
      if (!closingRef.current) {
        closingRef.current = true;
        onClose();
      }
    };

    window.addEventListener("popstate", handlePopState);

    /* Lock body scroll */
    document.body.style.overflow = "hidden";

    return () => {
      window.removeEventListener("popstate", handlePopState);
      document.body.style.overflow = "";
    };
  }, [event.slug, onClose]);

  /* ── Close handler ── */
  const handleClose = useCallback(() => {
    if (closingRef.current) return;
    closingRef.current = true;

    /* Go back in history to restore the /history URL */
    window.history.back();
  }, []);

  /* ── Keyboard: Escape to close ── */
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        handleClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleClose]);

  return (
    <div
      ref={overlayRef}
      className={`hist-overlay ${reducedMotion ? "hist-overlay--instant" : ""}`}
      role="dialog"
      aria-modal="true"
      aria-label={`${event.title} — full story`}
    >
      {/* Close button */}
      <button
        className="hist-overlay__close"
        onClick={handleClose}
        aria-label="Close story overlay"
        type="button"
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          aria-hidden="true"
        >
          <path d="M18 6L6 18" />
          <path d="M6 6l12 12" />
        </svg>
      </button>

      {/* EventDetail — rendered as complete unit.
          FLIP morph targets its .hist-hero__image element. */}
      <div
        className={`hist-overlay__content ${contentVisible ? "hist-overlay__content--visible" : ""}`}
      >
        <EventDetail event={event} allEvents={allEvents} />
      </div>
    </div>
  );
}
