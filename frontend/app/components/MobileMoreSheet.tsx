"use client";

import { useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import ThemeToggle from "./ThemeToggle";
import { hapticLight } from "../lib/haptics";

/* ---------------------------------------------------------------------------
   MobileMoreSheet — bottom sheet that slides UP from the "More" tab.

   Replaces the right-edge MobileSidePanel as the secondary-destination surface
   (the bottom tab bar is now the only primary nav). Holds the quieter routes
   that don't earn a bottom-bar slot: Sources, Feedback, About, plus a small
   utility footer (Press · Privacy) and the Theme toggle.

   Accessibility:
   - role="dialog" aria-modal; focus moves to the sheet on open and is trapped
     within it (Tab / Shift+Tab cycle); focus returns to the opener on close.
   - Dismiss on backdrop tap, Escape, swipe-down, or link activation.
   - Body scroll locked while open.
   Hidden on desktop via CSS (mobile-only, <768px).
   --------------------------------------------------------------------------- */

interface MobileMoreSheetProps {
  open: boolean;
  onClose: () => void;
}

export default function MobileMoreSheet({ open, onClose }: MobileMoreSheetProps) {
  const sheetRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const touchStartRef = useRef<{ y: number } | null>(null);
  // Remember what had focus before the sheet opened so we can restore it.
  const openerRef = useRef<HTMLElement | null>(null);

  // Close on Escape.
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open, onClose]);

  // Focus management — move focus into the sheet on open, restore on close.
  useEffect(() => {
    if (open) {
      openerRef.current = (document.activeElement as HTMLElement) ?? null;
      const first = sheetRef.current?.querySelector<HTMLElement>(
        "a, button, [tabindex]:not([tabindex='-1'])"
      );
      first?.focus();
    } else if (openerRef.current) {
      openerRef.current.focus();
      openerRef.current = null;
    }
  }, [open]);

  // Trap Tab focus within the sheet while open.
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key !== "Tab" || !sheetRef.current) return;
    const focusables = Array.from(
      sheetRef.current.querySelectorAll<HTMLElement>(
        "a, button, [tabindex]:not([tabindex='-1'])"
      )
    ).filter((el) => !el.hasAttribute("disabled"));
    if (focusables.length === 0) return;
    const first = focusables[0];
    const last = focusables[focusables.length - 1];
    const active = document.activeElement as HTMLElement;
    if (e.shiftKey && active === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && active === last) {
      e.preventDefault();
      first.focus();
    }
  }, []);

  // Lock body scroll while open.
  useEffect(() => {
    if (open) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);

  // Swipe-down to dismiss, with live drag feedback on the sheet + backdrop.
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartRef.current = { y: e.touches[0].clientY };
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!touchStartRef.current) return;
    const dy = e.touches[0].clientY - touchStartRef.current.y;
    if (dy > 0) {
      requestAnimationFrame(() => {
        if (sheetRef.current) {
          sheetRef.current.style.transform = `translateY(${dy}px)`;
          sheetRef.current.style.transition = "none";
        }
        if (backdropRef.current) {
          const h = sheetRef.current?.offsetHeight ?? 400;
          backdropRef.current.style.opacity = String(Math.max(0, 1 - dy / h));
          backdropRef.current.style.transition = "none";
        }
      });
    }
  }, []);

  const handleTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      if (!touchStartRef.current) return;
      const dy = e.changedTouches[0].clientY - touchStartRef.current.y;
      if (dy > 80) {
        hapticLight();
        onClose();
      } else {
        if (sheetRef.current) {
          sheetRef.current.style.transition = "transform 300ms var(--spring-snappy)";
          sheetRef.current.style.transform = "";
        }
        if (backdropRef.current) {
          backdropRef.current.style.transition = "opacity 300ms var(--ease-cinematic)";
          backdropRef.current.style.opacity = "";
        }
      }
      touchStartRef.current = null;
    },
    [onClose]
  );

  const handleLinkClick = useCallback(() => {
    hapticLight();
    onClose();
  }, [onClose]);

  return (
    <>
      {/* Backdrop overlay */}
      <div
        ref={backdropRef}
        className={`mms__backdrop${open ? " mms__backdrop--open" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sheet */}
      <div
        ref={sheetRef}
        className={`mms${open ? " mms--open" : ""}`}
        role="dialog"
        aria-modal={open}
        aria-label="More menu"
        onKeyDown={handleKeyDown}
      >
        {/* Grabber — swipe target */}
        <div
          className="mms__grabber-zone"
          onTouchStart={handleTouchStart}
          onTouchMove={handleTouchMove}
          onTouchEnd={handleTouchEnd}
        >
          <span className="mms__grabber" aria-hidden="true" />
        </div>

        {/* Primary destinations — editorial serif links (mirror the masthead) */}
        <nav className="mms__links" aria-label="More destinations">
          <Link href="/sources" className="mms__link" onClick={handleLinkClick}>
            <span className="mms__link-cmd">Sources</span>
            <span className="mms__link-desc">1,016 curated sources</span>
          </Link>
          <Link href="/ship" className="mms__link" onClick={handleLinkClick}>
            <span className="mms__link-cmd">Feedback</span>
            <span className="mms__link-desc">Tell us what to build or fix</span>
          </Link>
          <Link href="/about" className="mms__link" onClick={handleLinkClick}>
            <span className="mms__link-cmd">About</span>
            <span className="mms__link-desc">What Void News is</span>
          </Link>
        </nav>

        {/* Footer — utility links + theme toggle */}
        <div className="mms__footer">
          <div className="mms__util">
            <Link href="/press" className="mms__util-link" onClick={handleLinkClick}>
              Press
            </Link>
            <span className="mms__util-sep" aria-hidden="true">&middot;</span>
            <Link href="/privacy" className="mms__util-link" onClick={handleLinkClick}>
              Privacy
            </Link>
          </div>
          <div className="mms__theme">
            <span className="mms__theme-label">Appearance</span>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </>
  );
}
