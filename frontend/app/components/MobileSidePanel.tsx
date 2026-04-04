"use client";

import { useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import LogoFull from "./LogoFull";
import ThemeToggle from "./ThemeToggle";
import { hapticLight } from "../lib/haptics";

/* ---------------------------------------------------------------------------
   MobileSidePanel — Slides from the right edge when "More" tab is tapped.
   Dark overlay backdrop. Links to About, Ship. ThemeToggle. Tagline.
   Accessible: Escape to close, backdrop tap to close, link click closes.
   Hidden on desktop via CSS.
   --------------------------------------------------------------------------- */

interface MobileSidePanelProps {
  open: boolean;
  onClose: () => void;
}

export default function MobileSidePanel({ open, onClose }: MobileSidePanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const touchStartRef = useRef<{ x: number } | null>(null);

  // Close on Escape
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

  // Trap focus inside panel when open
  useEffect(() => {
    if (!open || !panelRef.current) return;
    const first = panelRef.current.querySelector<HTMLElement>("a, button");
    first?.focus();
  }, [open]);

  // Prevent body scroll when panel is open
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

  // Swipe right to close
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartRef.current = { x: e.touches[0].clientX };
  }, []);

  const handleTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      if (!touchStartRef.current) return;
      const dx = e.changedTouches[0].clientX - touchStartRef.current.x;
      if (dx > 60) {
        hapticLight();
        onClose();
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
        className={`msp__backdrop${open ? " msp__backdrop--open" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        ref={panelRef}
        className={`msp${open ? " msp--open" : ""}`}
        role="dialog"
        aria-modal={open}
        aria-label="Navigation menu"
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        {/* Logo header */}
        <div className="msp__header">
          <LogoFull height={24} />
        </div>

        {/* Navigation links */}
        <nav className="msp__links" aria-label="Side navigation">
          <Link href="/about" className="msp__link" onClick={handleLinkClick}>
            About
          </Link>
          <Link href="/ship" className="msp__link" onClick={handleLinkClick}>
            Ship
          </Link>
        </nav>

        {/* Theme toggle row */}
        <div className="msp__theme-row">
          <span className="msp__theme-label">Theme</span>
          <ThemeToggle />
        </div>

        {/* Footer tagline */}
        <div className="msp__footer">
          <span className="msp__tagline">See through the void.</span>
        </div>
      </div>
    </>
  );
}
