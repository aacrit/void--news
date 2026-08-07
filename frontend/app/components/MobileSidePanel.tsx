"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import LogoWordmark from "./LogoWordmark";
import ThemeToggle from "./ThemeToggle";
import { hapticLight } from "../lib/haptics";
import { BASE_PATH, getEditionTimestamp } from "../lib/utils";
import { fetchLastPipelineRun } from "../lib/supabase";

/* ---------------------------------------------------------------------------
   MobileSidePanel — the mobile secondary-navigation drawer.

   Opened by the hamburger "Menu" tab in MobileTabBar. Slides in from the right
   edge over a scrim. It is navigation-COMPLETE for the launch surface (every
   destination not on the bottom bar is one tap away here) AND it carries the
   masthead info the mobile top chrome drops: the edition build time, the source
   count, and the light/dark theme control.

   IA (grouped with small section labels):
     Header  — Void News wordmark + tagline "See through the void."
     Read    — Today's Feed (/), On Air (/onair)
     Explore — Sources (/sources)
     Participate — Feedback (/ship)
     About Void News — About (/about) · Press (/press) · Privacy (/privacy)
     Info bar — "Edition as of {time}", "1,016 sources across 158 countries",
                ThemeToggle

   History + Weekly are intentionally omitted (hidden for launch).

   Accessibility / interaction:
   - role="dialog" aria-modal; focus moves into the drawer on open, Tab/Shift+Tab
     cycle within it, and focus returns to the hamburger on close.
   - Dismiss on backdrop tap, Escape, browser back, swipe-right, or link tap.
   - Body scroll locked while open; safe-area insets respected.
   - The active route is marked (aria-current + a filled accent rail).
   - prefers-reduced-motion disables the slide (handled in mobile-nav.css).
   Hidden on desktop via CSS.
   --------------------------------------------------------------------------- */

interface MobileSidePanelProps {
  open: boolean;
  onClose: () => void;
}

interface NavItem {
  href: string;
  label: string;
  desc: string;
  accent?: string;
}

const READ_ITEMS: NavItem[] = [
  { href: "/", label: "Today’s Feed", desc: "The front page, 50 stories", accent: "neutral" },
  { href: "/onair", label: "On Air", desc: "The broadcast", accent: "onair" },
];
const EXPLORE_ITEMS: NavItem[] = [
  { href: "/sources", label: "Sources", desc: "1,016 sources, 158 countries", accent: "neutral" },
];
const PARTICIPATE_ITEMS: NavItem[] = [
  { href: "/ship", label: "Feedback", desc: "Tell us what to build or fix", accent: "neutral" },
];

export default function MobileSidePanel({ open, onClose }: MobileSidePanelProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const touchStartRef = useRef<{ x: number } | null>(null);
  // Element that had focus before the drawer opened (the hamburger) — focus
  // returns here on close.
  const openerRef = useRef<HTMLElement | null>(null);
  // True while we own a pushed history entry (for browser-back-to-close).
  const historyPushedRef = useRef(false);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  const pathname = usePathname();
  const route = pathname.replace(BASE_PATH, "") || "/";
  const isActive = useCallback(
    (href: string) => (href === "/" ? route === "/" : route === href || route.startsWith(href + "/")),
    [route]
  );

  const [mounted, setMounted] = useState(false);
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setMounted(true); }, []);

  // Edition build time (pipeline completed_at) for the info bar, formatted in
  // the reader's local zone and rounded to the hour like the desktop masthead.
  const [editionBuiltAt, setEditionBuiltAt] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    fetchLastPipelineRun()
      .then((run) => {
        if (!cancelled && run?.completed_at) setEditionBuiltAt(run.completed_at as string);
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  // Close on Escape.
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onCloseRef.current();
      }
    };
    document.addEventListener("keydown", handleKey);
    return () => document.removeEventListener("keydown", handleKey);
  }, [open]);

  // Browser back closes the drawer: push a throwaway history entry on open and
  // close when it is popped. requestClose() consumes the entry so history stays
  // clean; a genuine back gesture pops it directly.
  useEffect(() => {
    if (!open) return;
    window.history.pushState({ mspDrawer: true }, "");
    historyPushedRef.current = true;
    const onPop = () => {
      historyPushedRef.current = false;
      onCloseRef.current();
    };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
  }, [open]);

  // Close initiated from inside the drawer (backdrop / Esc-via-button / swipe).
  // If we still own the pushed history entry, unwind it so the back button does
  // not leave a dead state; the popstate handler then fires the single close.
  const requestClose = useCallback(() => {
    if (historyPushedRef.current) {
      historyPushedRef.current = false;
      window.history.back();
    } else {
      onCloseRef.current();
    }
  }, []);

  // Focus management — move focus into the drawer on open, restore to the
  // opener (the hamburger) on close.
  useEffect(() => {
    if (open) {
      openerRef.current = (document.activeElement as HTMLElement) ?? null;
      const first = panelRef.current?.querySelector<HTMLElement>(
        "a, button, [tabindex]:not([tabindex='-1'])"
      );
      first?.focus();
    } else if (openerRef.current) {
      openerRef.current.focus();
      openerRef.current = null;
    }
  }, [open]);

  // Trap Tab focus within the drawer while open.
  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key !== "Tab" || !panelRef.current) return;
    const focusables = Array.from(
      panelRef.current.querySelectorAll<HTMLElement>(
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

  // Prevent body scroll when drawer is open.
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

  // Swipe right to close with visual drag feedback.
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
          const newOpacity = Math.max(0, 1 - dx / panelWidth);
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
      // Reset any inline drag styles so the CSS state class takes over again.
      if (panelRef.current) {
        panelRef.current.style.transition = "transform 300ms var(--spring-snappy)";
        panelRef.current.style.transform = "";
      }
      if (backdropRef.current) {
        backdropRef.current.style.transition = "opacity 300ms var(--ease-cinematic)";
        backdropRef.current.style.opacity = "";
      }
      if (dx > 60) {
        hapticLight();
        requestClose();
      }
      touchStartRef.current = null;
    },
    [requestClose]
  );

  const handleLinkClick = useCallback(() => {
    hapticLight();
    // Link navigation proceeds; just drop the visual drawer + our history entry.
    requestClose();
  }, [requestClose]);

  const renderItem = (item: NavItem, cascade: number) => {
    const active = isActive(item.href);
    return (
      <Link
        key={item.href}
        href={item.href}
        className={`msp__link${active ? " msp__link--active" : ""}`}
        data-accent={item.accent ?? "neutral"}
        data-msp-cascade={cascade}
        aria-current={active ? "page" : undefined}
        onClick={handleLinkClick}
      >
        <span className="msp__link-cmd">{item.label}</span>
        <span className="msp__link-desc">{item.desc}</span>
      </Link>
    );
  };

  return (
    <>
      {/* Backdrop overlay */}
      <div
        ref={backdropRef}
        className={`msp__backdrop${open ? " msp__backdrop--open" : ""}`}
        onClick={requestClose}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        ref={panelRef}
        className={`msp${open ? " msp--open" : ""}`}
        role="dialog"
        aria-modal={open}
        aria-label="Menu"
        onKeyDown={handleKeyDown}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
      >
        {/* Header — Void News wordmark + tagline */}
        <div className="msp__header" data-msp-cascade="1">
          <LogoWordmark height={22} className="msp__wordmark" />
          <span className="msp__header-tagline">See through the void.</span>
        </div>

        {/* Grouped navigation — Read / Explore / Participate + a quieter
            About Void News utility group. */}
        <nav className="msp__links" aria-label="Site navigation">
          <span className="msp__section-label" data-msp-cascade="2">Read</span>
          {READ_ITEMS.map((item) => renderItem(item, 2))}

          <svg className="msp__divider" data-msp-cascade="3" viewBox="0 0 200 4" preserveAspectRatio="none" aria-hidden="true">
            <path d="M0,2 C25,0.5 50,3.5 75,2 C100,0.5 125,3 150,2 C175,1 200,3 200,2" />
          </svg>

          <span className="msp__section-label" data-msp-cascade="3">Explore</span>
          {EXPLORE_ITEMS.map((item) => renderItem(item, 3))}

          <svg className="msp__divider" data-msp-cascade="4" viewBox="0 0 200 4" preserveAspectRatio="none" aria-hidden="true">
            <path d="M0,2 C30,3.2 55,0.8 80,2 C105,3.2 130,0.8 160,2 C180,3 200,1.5 200,2" />
          </svg>

          <span className="msp__section-label" data-msp-cascade="4">Participate</span>
          {PARTICIPATE_ITEMS.map((item) => renderItem(item, 4))}

          {/* About Void News — quieter utility group */}
          <span className="msp__section-label" data-msp-cascade="5">About Void News</span>
          <div className="msp__util" data-msp-cascade="5">
            <Link
              href="/about"
              className={`msp__util-link${isActive("/about") ? " msp__util-link--active" : ""}`}
              aria-current={isActive("/about") ? "page" : undefined}
              onClick={handleLinkClick}
            >
              About
            </Link>
            <span className="msp__util-sep" aria-hidden="true">&middot;</span>
            <Link
              href="/press"
              className={`msp__util-link${isActive("/press") ? " msp__util-link--active" : ""}`}
              aria-current={isActive("/press") ? "page" : undefined}
              onClick={handleLinkClick}
            >
              Press
            </Link>
            <span className="msp__util-sep" aria-hidden="true">&middot;</span>
            <Link
              href="/privacy"
              className={`msp__util-link${isActive("/privacy") ? " msp__util-link--active" : ""}`}
              aria-current={isActive("/privacy") ? "page" : undefined}
              onClick={handleLinkClick}
            >
              Privacy
            </Link>
          </div>
        </nav>

        {/* Info bar — the masthead facts the mobile top chrome drops: edition
            build time, source count, and the theme control. */}
        <div className="msp__infobar" data-msp-cascade="5">
          <div className="msp__info-lines">
            <span className="msp__info-line" suppressHydrationWarning>
              {mounted ? `Edition as of ${getEditionTimestamp(editionBuiltAt)}` : " "}
            </span>
            <span className="msp__info-line msp__info-line--muted">
              1,016 sources across 158 countries
            </span>
          </div>
          <div className="msp__theme-row">
            <span className="msp__theme-label">Appearance</span>
            <ThemeToggle />
          </div>
        </div>
      </div>
    </>
  );
}
