"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import ScaleIcon from "./ScaleIcon";
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
  const backdropRef = useRef<HTMLDivElement>(null);
  const touchStartRef = useRef<{ x: number } | null>(null);
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

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

  // Swipe right to close with visual drag feedback
  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    touchStartRef.current = { x: e.touches[0].clientX };
  }, []);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (!touchStartRef.current || !panelRef.current) return;
    const dx = e.touches[0].clientX - touchStartRef.current.x;
    if (dx > 0) {
      requestAnimationFrame(() => {
        if (panelRef.current) {
          panelRef.current.style.transform = `translateX(${dx}px)`;
          panelRef.current.style.transition = "none";
        }
        if (backdropRef.current) {
          const panelWidth = panelRef.current?.offsetWidth ?? 280;
          const newOpacity = Math.max(0, 1 - (dx / panelWidth));
          backdropRef.current.style.opacity = String(newOpacity);
          backdropRef.current.style.transition = "none";
        }
      });
    }
  }, []);

  const handleTouchEnd = useCallback(
    (e: React.TouchEvent) => {
      if (!touchStartRef.current) return;
      const dx = e.changedTouches[0].clientX - touchStartRef.current.x;
      if (dx > 60) {
        hapticLight();
        onClose();
      } else {
        if (panelRef.current) {
          panelRef.current.style.transition = "transform 300ms var(--spring-snappy)";
          panelRef.current.style.transform = "";
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
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Header — ScaleIcon brand mark with ink underline */}
        <div className="msp__header" data-msp-cascade="1">
          <ScaleIcon size={28} animation="idle" />
        </div>

        {/* Content destinations */}
        <nav className="msp__links" aria-label="Side navigation">
          <span className="msp__section-label" data-msp-cascade="2">Read</span>
          <Link href="/history" className="msp__link" data-msp-cascade="2" onClick={handleLinkClick}>
            <span className="msp__link-cmd">void --history</span>
            <span className="msp__link-desc">The archive</span>
          </Link>
          <Link href="/weekly" className="msp__link" data-msp-cascade="2" onClick={handleLinkClick}>
            <span className="msp__link-cmd">void --weekly</span>
            <span className="msp__link-desc">Weekly digest</span>
          </Link>
          <Link href="/paper" className="msp__link" data-msp-cascade="2" onClick={handleLinkClick}>
            <span className="msp__link-cmd">void --paper</span>
            <span className="msp__link-desc">E-paper broadsheet</span>
          </Link>

          {/* Organic ink divider */}
          <svg className="msp__divider" data-msp-cascade="3" viewBox="0 0 200 4" preserveAspectRatio="none" aria-hidden="true">
            <path d="M0,2 C25,0.5 50,3.5 75,2 C100,0.5 125,3 150,2 C175,1 200,3 200,2" />
          </svg>

          <span className="msp__section-label" data-msp-cascade="3">Explore</span>
          <Link href="/sources" className="msp__link" data-msp-cascade="3" onClick={handleLinkClick}>
            <span className="msp__link-cmd">void --sources</span>
            <span className="msp__link-desc">1,013 curated sources</span>
          </Link>
          <Link href="/about" className="msp__link" data-msp-cascade="3" onClick={handleLinkClick}>
            <span className="msp__link-cmd">void --about</span>
            <span className="msp__link-desc">See through the void</span>
          </Link>

          {/* Organic ink divider */}
          <svg className="msp__divider" data-msp-cascade="4" viewBox="0 0 200 4" preserveAspectRatio="none" aria-hidden="true">
            <path d="M0,2 C30,3.2 55,0.8 80,2 C105,3.2 130,0.8 160,2 C180,3 200,1.5 200,2" />
          </svg>

          <span className="msp__section-label" data-msp-cascade="4">Participate</span>
          <Link href="/ship" className="msp__link" data-msp-cascade="4" onClick={handleLinkClick}>
            <span className="msp__link-cmd">void --ship</span>
            <span className="msp__link-desc">Request features, report bugs</span>
          </Link>
        </nav>

        {/* Theme toggle row */}
        <div className="msp__theme-row" data-msp-cascade="5">
          <span className="msp__theme-label">Theme</span>
          <ThemeToggle />
        </div>

        {/* Footer — dateline, tagline, colophon mark */}
        <div className="msp__footer" data-msp-cascade="6">
          <time className="msp__dateline" suppressHydrationWarning>
            {mounted
              ? new Date().toLocaleDateString("en-US", {
                  weekday: "long",
                  month: "long",
                  day: "numeric",
                  year: "numeric",
                })
              : "\u00A0"}
          </time>
          <span className="msp__tagline">See through the void.</span>
          <div className="msp__colophon" aria-hidden="true">
            <ScaleIcon size={16} animation="none" />
          </div>
        </div>
      </div>
    </>
  );
}
