"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import LogoWordmark from "./LogoWordmark";
import ThemeToggle from "./ThemeToggle";
import ScaleIcon from "./ScaleIcon";
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

   IA (one flat, icon-led list — no section labels):
     Header  — Void News wordmark + tagline "See through the void."
     Today's Feed (/)   — PRIMARY. Terracotta Sigil-O mark (--palette-news), the
                          same accent the bottom tab bar's Home anchor wears.
     On Air (/onair)    — PRIMARY. Teal broadcast glyph (--voice-accent), the
                          same accent the tab bar's On Air tab wears.
     Sources (/sources) — peer row, muted layers icon.
     Feedback (/ship)   — peer row, muted chat icon.
     About · Press · Privacy — quiet inline utility trio, subordinate.
     Info bar — "Edition as of {time}", "1,016 sources across 158 countries",
                ThemeToggle

   History + Weekly are intentionally omitted (hidden for launch). The four main
   rows share one layout: leading icon + command (editorial voice) + description
   (structural voice), full-width tap target, accent rail on the active route.

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

type NavIcon = "feed" | "onair" | "sources" | "feedback";

interface NavItem {
  href: string;
  label: string;
  desc: string;
  /** Drives --msp-accent (rail/wash) and --msp-icon (icon color) in CSS. */
  accent: "news" | "onair" | "neutral";
  icon: NavIcon;
}

// One flat list. Two navbar-accented primary rows (Feed terracotta, On Air
// teal — matching their MobileTabBar counterparts) then two muted peer rows.
const MAIN_ITEMS: NavItem[] = [
  { href: "/", label: "Today’s Feed", desc: "The front page, 50 stories.", accent: "news", icon: "feed" },
  { href: "/onair", label: "On Air", desc: "The broadcast.", accent: "onair", icon: "onair" },
  { href: "/sources", label: "Sources", desc: "1,016 sources, 158 countries.", accent: "neutral", icon: "sources" },
  { href: "/ship", label: "Feedback", desc: "Tell us what to build or fix.", accent: "neutral", icon: "feedback" },
];

// Leading row glyphs. The Feed mark is the ScaleIcon Sigil-O (same mark the tab
// bar anchor uses); the On Air glyph is the concentric radio-wave broadcast SVG
// (same as MobileTabBar). Color flows from currentColor / --sigil-brass, which
// the .msp__link-icon rule pins to the row's --msp-icon accent.
function NavGlyph({ icon }: { icon: NavIcon }) {
  if (icon === "feed") {
    // --sigil-brass follows currentColor via CSS so the mark wears the row accent.
    return <ScaleIcon size={24} animation="none" />;
  }
  if (icon === "onair") {
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" aria-hidden="true">
        <circle cx="12" cy="12" r="1.75" fill="currentColor" stroke="none" />
        <path d="M8.2 8.2 a5.4 5.4 0 0 0 0 7.6" />
        <path d="M5.1 5.1 a9.8 9.8 0 0 0 0 13.8" />
        <path d="M15.8 8.2 a5.4 5.4 0 0 1 0 7.6" />
        <path d="M18.9 5.1 a9.8 9.8 0 0 1 0 13.8" />
      </svg>
    );
  }
  if (icon === "sources") {
    // Stacked layers — the layered source corpus.
    return (
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M12 3 4 7.5l8 4.5 8-4.5-8-4.5Z" />
        <path d="M4 12l8 4.5 8-4.5" />
        <path d="M4 16.5l8 4.5 8-4.5" />
      </svg>
    );
  }
  // feedback — chat bubble.
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 11.5a8.38 8.38 0 0 1-8.5 8.5 8.5 8.5 0 0 1-3.8-.9L3 21l1.9-5.7a8.5 8.5 0 0 1-.9-3.8 8.38 8.38 0 0 1 8.5-8.5A8.5 8.5 0 0 1 21 11.5Z" />
    </svg>
  );
}

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
    // Link navigation MUST proceed. Do NOT call requestClose()/history.back()
    // here: unwinding our throwaway pushState entry races the <Link>'s own
    // pushState, bouncing the route so only the drawer closes and navigation is
    // lost. Instead release ownership of the entry and close the drawer visually;
    // the <Link> then navigates normally. A redundant history entry left under
    // the new route is harmless; a dead link is not.
    historyPushedRef.current = false;
    onCloseRef.current();
  }, []);

  const renderItem = (item: NavItem, cascade: number) => {
    const active = isActive(item.href);
    return (
      <Link
        key={item.href}
        href={item.href}
        className={`msp__link${active ? " msp__link--active" : ""}`}
        data-accent={item.accent}
        data-msp-cascade={cascade}
        aria-current={active ? "page" : undefined}
        onClick={handleLinkClick}
      >
        <span className="msp__link-icon" aria-hidden="true">
          <NavGlyph icon={item.icon} />
        </span>
        <span className="msp__link-text">
          <span className="msp__link-cmd">{item.label}</span>
          <span className="msp__link-desc">{item.desc}</span>
        </span>
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

        {/* One flat, icon-led list. Two accented primary rows (Feed, On Air)
            then two muted peer rows (Sources, Feedback), then a quiet utility
            trio subordinated below an organic ink divider. */}
        <nav className="msp__links" aria-label="Site navigation">
          {renderItem(MAIN_ITEMS[0], 2)}
          {renderItem(MAIN_ITEMS[1], 2)}
          {renderItem(MAIN_ITEMS[2], 3)}
          {renderItem(MAIN_ITEMS[3], 3)}

          <svg className="msp__divider" data-msp-cascade="4" viewBox="0 0 200 4" preserveAspectRatio="none" aria-hidden="true">
            <path d="M0,2 C25,0.5 50,3.5 75,2 C100,0.5 125,3 150,2 C175,1 200,3 200,2" />
          </svg>

          {/* About Void News — quieter utility trio, subordinate to the rows above */}
          <div className="msp__util" data-msp-cascade="4">
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
