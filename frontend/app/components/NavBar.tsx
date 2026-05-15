"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { MagnifyingGlass } from "@phosphor-icons/react";
import type { Edition } from "../lib/types";
import { EDITIONS } from "../lib/types";
import ThemeToggle from "./ThemeToggle";
import PageToggle from "./PageToggle";
import LogoFull from "./LogoFull";
import { getEditionTimestamp } from "../lib/utils";
import { hapticConfirm } from "../lib/haptics";

/** When only one edition exists, edition UI is hidden. World becomes an inline
 *  section of the homepage instead of a switchable edition. */
const MULTI_EDITION = EDITIONS.length > 1;

interface NavBarProps {
  activeEdition: Edition;
  onEditionChange?: (edition: Edition) => void;
  onSearchClick?: () => void;
  hasAudio?: boolean;
  isAudioPlaying?: boolean;
  onOnairClick?: () => void;
}

/* ---------------------------------------------------------------------------
   NavBar — Single-row masthead

   Row 1 (Chrome — structural, about the app):
     Logo | dateline · timestamp | Spinoffs | Pages | Theme | Search

   Filters (lean chips + topic dropdown) and the inline Row 2 lens were removed
   in 2026-05-15 redesign — pure curation, no client-side filtering. The
   server-side ranker enforces topic diversity and source-count quality floor.
   --------------------------------------------------------------------------- */

function formatDateCompact(): string {
  return new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function NavBar({
  activeEdition,
  onEditionChange,
  onSearchClick,
}: NavBarProps) {
  const [mounted, setMounted] = useState(false);
  // SSR-safe hydration pattern — defer dateline/timestamp render until after
  // mount so server HTML matches client HTML on first paint (avoids React #418).
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setMounted(true); }, []);
  const dateline = mounted ? formatDateCompact() : "            ";
  const timestamp = mounted ? getEditionTimestamp(activeEdition) : "     ";

  /* ── Scroll-compact masthead (NYT-style): wires --scroll-nav-compact-* tokens.
     Adds data-scroll-compact="true" past 80px, removes at ≤40px (hysteresis
     prevents jitter at threshold). rAF-throttled, passive listener.
     Desktop-only behavior — mobile nav is a separate component (MobileNav).   */
  const [scrollCompact, setScrollCompact] = useState(false);
  useEffect(() => {
    let ticking = false;
    let compact = false;

    const update = () => {
      ticking = false;
      const y = window.scrollY;
      if (!compact && y > 80) {
        compact = true;
        setScrollCompact(true);
      } else if (compact && y <= 40) {
        compact = false;
        setScrollCompact(false);
      }
    };

    const onScroll = () => {
      if (!ticking) {
        ticking = true;
        window.requestAnimationFrame(update);
      }
    };

    // Prime initial state (e.g., page reload mid-scroll)
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleEditionTap = (edition: Edition) => {
    hapticConfirm();
    onEditionChange?.(edition);
  };

  return (
    <header
      className="nav-header anim-cold-open-nav"
      data-scroll-compact={scrollCompact ? "true" : undefined}
    >
      {/* ── Row 1: Chrome — structural, about the app ── */}
      <nav className="nav-inner" aria-label="Main navigation">
        <div className="nav-left">
          <Link href="/" aria-label="void --news — home" className="nav-logo si-hoverable">
            <span className="nav-logo-desktop">
              <LogoFull height={32} />
            </span>
            <span className="nav-logo-mobile">
              <LogoFull height={22} />
            </span>
          </Link>
        </div>

        <span className="nav-dateline-inline" aria-hidden="true" suppressHydrationWarning>
          {dateline}
          <span className="nav-dateline-inline__sep">&middot;</span>
          <span className="nav-dateline-inline__time">{timestamp}</span>
        </span>
        <span className="nav-dateline-mobile" aria-hidden="true" suppressHydrationWarning>
          {dateline}
        </span>

        {/* Spinoff product links — Weekly + History are standalone products
            under the void --news umbrella, treated with italic accents
            (warm rule + label) regardless of edition mode. Per CEO 2026-05-15:
            their dedicated styling must persist; they are NOT generic nav-pages. */}
        <nav className="nav-spinoffs" aria-label="Spinoff editions">
          <Link href="/weekly" className="nav-weekly" aria-label="Go to Weekly digest" title="void --weekly">
            <span className="nav-weekly__rule" aria-hidden="true" />
            <span className="nav-weekly__label">Weekly</span>
          </Link>
          <Link href="/history" className="nav-history" aria-label="Go to History archive" title="void --history">
            <span className="nav-history__rule" aria-hidden="true" />
            <span className="nav-history__label">History</span>
          </Link>
        </nav>

        <div className="nav-right">
          {/* Page navigation — destinations.
              Games + Paper hidden from production nav (not ready). Routes
              still resolve at /games and /paper for direct URL access. */}
          <nav className="nav-pages" aria-label="Pages">
            <PageToggle activePage="feed" />
            <Link href="/ship" className="nav-page" aria-label="void --ship" title="void --ship">
              Ship
            </Link>
            <Link href="/about" className="nav-page" aria-label="About void --news" title="void --about">
              About
            </Link>
          </nav>

          {/* Search — single icon button. Cmd+K opens overlay. */}
          {onSearchClick && (
            <button
              type="button"
              className="nav-search-btn"
              onClick={onSearchClick}
              aria-label="Search stories (Ctrl+K)"
              title="Search (Ctrl+K)"
            >
              <MagnifyingGlass size={18} weight="regular" aria-hidden="true" />
            </button>
          )}

          {/* Utility: Theme (hidden on mobile — ThemeToggle is in MobileSidePanel) */}
          <ThemeToggle />
        </div>
      </nav>

      {/* ── Mobile edition tabs — only when multi-edition ── */}
      {MULTI_EDITION && onEditionChange && (
        <nav className="nav-mob-editions" aria-label="Edition">
          {EDITIONS.map((ed) => (
            <button
              key={ed.slug}
              type="button"
              aria-current={activeEdition === ed.slug ? "page" : undefined}
              className={`nav-mob-ed${activeEdition === ed.slug ? " nav-mob-ed--active" : ""}`}
              onClick={() => handleEditionTap(ed.slug)}
            >
              {ed.label}
            </button>
          ))}
        </nav>
      )}
    </header>
  );
}
