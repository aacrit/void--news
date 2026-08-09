"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { createPortal } from "react-dom";
import dynamic from "next/dynamic";
import { X } from "@phosphor-icons/react";
import type { Story } from "../lib/types";
import { hapticLight } from "../lib/haptics";
import "../styles/deep-dive-overlay.css";

// The Deep Dive content renderer. ssr:false because it does its own Supabase
// fetch on mount and touches window/matchMedia.
const InlineDeepDive = dynamic(() => import("./InlineDeepDive"), { ssr: false });

/* ---------------------------------------------------------------------------
   DeepDiveOverlay — focused Deep Dive presented over the feed.

   Desktop (>=768px): a centered card over a dimmed backdrop (max-width ~920px,
   max-height 88vh, internal scroll). The feed grid underneath does NOT reflow.
   Mobile (<768px): a full-screen sheet that slides up from the bottom, with its
   own scroll and a sticky top bar (grabber + close). Swipe the top bar down to
   dismiss.

   The overlay owns ALL dialog behaviour so InlineDeepDive can stay purely
   presentational: portal to <body>, role="dialog" aria-modal, aria-labelledby
   the story title, focus moved in on open + returned to the trigger on close,
   focus trap while open, body scroll-lock with exact scroll-position
   restoration, and dismissal via the close button, backdrop click, Escape, and
   the browser/hardware Back button. Motion respects prefers-reduced-motion.
   --------------------------------------------------------------------------- */

const TITLE_ID = "dd-overlay-title";
const EXIT_MS = 320; // must be >= the panel/backdrop CSS transition duration
const SWIPE_DISMISS_PX = 110; // drag distance past which a swipe-down dismisses

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), textarea, input, select, [tabindex]:not([tabindex="-1"])';

interface DeepDiveOverlayProps {
  story: Story;
  onClose: () => void;
}

export default function DeepDiveOverlay({ story, onClose }: DeepDiveOverlayProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const closeBtnRef = useRef<HTMLButtonElement>(null);
  // The element that had focus when the overlay opened (the triggering card).
  const triggerRef = useRef<HTMLElement | null>(null);
  // True once dismissal came from a Back-button popstate, so cleanup does not
  // try to pop the history entry a second time.
  const closedByPopRef = useRef(false);

  const [open, setOpen] = useState(false); // drives the enter transition
  const [closing, setClosing] = useState(false); // drives the exit transition

  const prefersReduced =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---- Dismiss: play the exit transition, then unmount via onClose. -------- */
  const requestClose = useCallback(() => {
    if (closing) return;
    hapticLight();
    if (prefersReduced) {
      onClose();
      return;
    }
    setClosing(true);
    window.setTimeout(onClose, EXIT_MS);
  }, [closing, prefersReduced, onClose]);

  /* ---- Body scroll-lock + focus capture/return (mount/unmount). -----------
     position:fixed pins the page so it cannot scroll behind the sheet; the
     exact scrollY is saved and restored on close so the reader lands on the
     same spot they opened from. Focus returns to the triggering card. */
  useEffect(() => {
    triggerRef.current =
      (document.activeElement as HTMLElement | null) ?? null;

    const scrollY = window.scrollY;
    const body = document.body;
    // Reserve the scrollbar's width so locking the page does not shift the feed
    // sideways behind the backdrop (desktop). No-op on overlay scrollbars.
    const scrollbarW = window.innerWidth - document.documentElement.clientWidth;
    const prev = {
      position: body.style.position,
      top: body.style.top,
      left: body.style.left,
      right: body.style.right,
      width: body.style.width,
      overflow: body.style.overflow,
      paddingRight: body.style.paddingRight,
    };
    body.style.position = "fixed";
    body.style.top = `-${scrollY}px`;
    body.style.left = "0";
    body.style.right = "0";
    body.style.width = "100%";
    body.style.overflow = "hidden";
    if (scrollbarW > 0) body.style.paddingRight = `${scrollbarW}px`;

    return () => {
      body.style.position = prev.position;
      body.style.top = prev.top;
      body.style.left = prev.left;
      body.style.right = prev.right;
      body.style.width = prev.width;
      body.style.overflow = prev.overflow;
      body.style.paddingRight = prev.paddingRight;
      // Restore the exact scroll position (place preservation).
      window.scrollTo(0, scrollY);
      // Return focus to the card that opened the overlay.
      const t = triggerRef.current;
      if (t && typeof t.focus === "function") {
        t.focus({ preventScroll: true });
      }
    };
  }, []);

  /* ---- Enter transition — flip `open` on the next frame after mount. ------- */
  useEffect(() => {
    const id = requestAnimationFrame(() => setOpen(true));
    return () => cancelAnimationFrame(id);
  }, []);

  /* ---- Move focus into the dialog on open. -------------------------------- */
  useEffect(() => {
    const id = window.setTimeout(() => {
      closeBtnRef.current?.focus({ preventScroll: true });
    }, 0);
    return () => window.clearTimeout(id);
  }, []);

  /* ---- Escape to close. --------------------------------------------------- */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        requestClose();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [requestClose]);

  /* ---- Hardware / browser Back button dismisses (mobile especially). ------
     Push one history entry on open; a Back press pops it and closes. If the
     overlay is instead closed from within (button / backdrop / Escape), the
     cleanup pops our pushed entry so the Back stack stays clean. */
  useEffect(() => {
    window.history.pushState({ ddOverlay: true }, "");
    const onPop = () => {
      closedByPopRef.current = true;
      onClose();
    };
    window.addEventListener("popstate", onPop);
    return () => {
      window.removeEventListener("popstate", onPop);
      if (!closedByPopRef.current) {
        window.history.back();
      }
    };
  }, [onClose]);

  /* ---- Focus trap — keep Tab focus inside the panel. ---------------------- */
  const handleKeyDownTrap = useCallback((e: React.KeyboardEvent) => {
    if (e.key !== "Tab") return;
    const panel = panelRef.current;
    if (!panel) return;
    const focusables = Array.from(
      panel.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR),
    ).filter((el) => el.offsetParent !== null || el === document.activeElement);
    if (focusables.length === 0) {
      e.preventDefault();
      return;
    }
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const active = document.activeElement;
    if (e.shiftKey && active === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && active === last) {
      e.preventDefault();
      first.focus();
    }
  }, []);

  /* ---- Swipe-down-to-dismiss (mobile) on the sheet top bar. ---------------
     Direct DOM writes during the drag keep it smooth (no per-frame React
     re-render). On release, past the threshold it dismisses; otherwise it
     springs back. Disabled under reduced motion and on desktop widths. */
  const dragState = useRef<{ startY: number; dy: number; active: boolean }>({
    startY: 0,
    dy: 0,
    active: false,
  });

  const isSheet = () =>
    typeof window !== "undefined" &&
    window.matchMedia("(max-width: 767px)").matches;

  const onBarTouchStart = useCallback(
    (e: React.TouchEvent) => {
      if (prefersReduced || !isSheet()) return;
      dragState.current = {
        startY: e.touches[0].clientY,
        dy: 0,
        active: true,
      };
      const panel = panelRef.current;
      if (panel) panel.style.transition = "none";
    },
    [prefersReduced],
  );

  const onBarTouchMove = useCallback((e: React.TouchEvent) => {
    const st = dragState.current;
    if (!st.active) return;
    const dy = e.touches[0].clientY - st.startY;
    st.dy = dy;
    const panel = panelRef.current;
    if (!panel) return;
    // Only track downward drags; a small upward pull resists (rubber-band).
    const applied = dy > 0 ? dy : dy * 0.25;
    panel.style.transform = `translateY(${applied}px)`;
  }, []);

  const onBarTouchEnd = useCallback(() => {
    const st = dragState.current;
    if (!st.active) return;
    st.active = false;
    const panel = panelRef.current;
    if (panel) {
      // Hand the transform back to CSS: on spring-back it animates to seated
      // (translateY 0); on dismiss the --closing class animates it off-screen.
      panel.style.transition = "";
      panel.style.transform = "";
    }
    if (st.dy >= SWIPE_DISMISS_PX) {
      requestClose();
    }
  }, [requestClose]);

  if (typeof document === "undefined") return null;

  const stateClass = closing
    ? "dd-overlay--closing"
    : open
    ? "dd-overlay--open"
    : "";

  return createPortal(
    <div className={`dd-overlay ${stateClass}`.trim()}>
      <div
        className="dd-overlay__backdrop"
        aria-hidden="true"
        onClick={requestClose}
      />
      <div
        ref={panelRef}
        className="dd-overlay__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={TITLE_ID}
        /* Fallback label for the brief window before the (async) content mounts
           and provides the #dd-overlay-title heading. */
        aria-label={story.title}
        onKeyDown={handleKeyDownTrap}
      >
        <div
          className="dd-overlay__bar"
          onTouchStart={onBarTouchStart}
          onTouchMove={onBarTouchMove}
          onTouchEnd={onBarTouchEnd}
          onTouchCancel={onBarTouchEnd}
        >
          <span className="dd-overlay__grabber" aria-hidden="true" />
          <button
            ref={closeBtnRef}
            type="button"
            className="dd-overlay__close"
            aria-label={`Close deep dive: ${story.title}`}
            onClick={requestClose}
          >
            <X size={18} weight="bold" aria-hidden="true" />
          </button>
        </div>

        <div className="dd-overlay__scroll">
          <InlineDeepDive story={story} titleId={TITLE_ID} />
        </div>
      </div>
    </div>,
    document.body,
  );
}
