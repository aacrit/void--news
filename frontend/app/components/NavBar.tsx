"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { MagnifyingGlass } from "@phosphor-icons/react";
import ThemeToggle from "./ThemeToggle";
import PageToggle from "./PageToggle";
import LogoFull from "./LogoFull";
import ExperimentalBadge from "./ExperimentalBadge";
import { getEditionTimestamp, getEditionDatelineUTC } from "../lib/utils";

interface NavBarProps {
  onSearchClick?: () => void;
  hasAudio?: boolean;
  isAudioPlaying?: boolean;
  onOnairClick?: () => void;
  /** Edition build time (pipeline completed_at, ISO). Drives the masthead
      dateline + timestamp so they reflect when THIS edition was built, not the
      reader's current clock. Falls back to now when absent. */
  editionBuiltAt?: string | null;
  /** Deterministic, preformatted masthead strings computed once at build time
      (prerendered front page). When BOTH are provided they render directly on
      first paint (server + client match exactly, no #418), bypassing the
      client-local mounted gate below. Absent on client-only routes. */
  editionDateline?: string;
  editionTimestamp?: string;
}

/* ---------------------------------------------------------------------------
   NavBar — Single-row masthead

   Row 1 (Chrome — structural, about the app):
     Logo | dateline · timestamp | Spinoffs | Pages | Theme | Search

   Filters (lean chips + topic dropdown) and the inline Row 2 lens were removed
   in 2026-05-15 redesign — pure curation, no client-side filtering. The
   server-side ranker enforces topic diversity and source-count quality floor.
   --------------------------------------------------------------------------- */

export default function NavBar({
  onSearchClick,
  editionBuiltAt,
  editionDateline,
  editionTimestamp,
  hasAudio,
  isAudioPlaying,
  onOnairClick,
}: NavBarProps) {
  const [mounted, setMounted] = useState(false);
  // SSR-safe hydration pattern — defer dateline/timestamp render until after
  // mount so server HTML matches client HTML on first paint (avoids React #418).
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setMounted(true); }, []);
  // Preformatted build-time strings win when supplied (front-page prerender):
  // they are deterministic UTC, so server and client first paint are identical
  // and the "as of" block renders immediately. Otherwise fall back to the
  // client-fetched build time, formatted through the SAME UTC formatters the
  // front page uses (getEditionDatelineUTC / getEditionTimestamp), so every
  // detail surface shows the identical UTC "as of" value and never the reader's
  // local zone. The mounted gate only defers the client-fetched path so an
  // absent build time (which falls back to "now") can't mismatch on first paint.
  // Before mount (and when no build value is available) BOTH resolve to empty
  // and the time block below is omitted entirely, never a doubled placeholder.
  const dateline = editionDateline ?? (mounted ? getEditionDatelineUTC(editionBuiltAt) : "");
  const timestamp = editionTimestamp ?? (mounted ? getEditionTimestamp(editionBuiltAt) : "");

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

  return (
    <header
      className="nav-header anim-cold-open-nav"
      data-scroll-compact={scrollCompact ? "true" : undefined}
    >
      {/* ── Row 1: Chrome — structural, about the app ── */}
      <nav className="nav-inner" aria-label="Main navigation">
        <div className="nav-left">
          <Link href="/" aria-label="Void News home" className="nav-logo si-hoverable">
            <span className="nav-logo-desktop">
              <LogoFull height={30} />
            </span>
            {/* Tablet / landscape-phone band (768-1023): a compact wordmark so the
                masthead reads as a masthead, not a stray icon. Full mark won't fit
                once History + Weekly join the row; the phone mark (18px) is too
                small for this width. See components.css tablet-band block. */}
            <span className="nav-logo-tablet">
              <LogoFull height={22} />
            </span>
            <span className="nav-logo-mobile">
              <LogoFull height={18} />
            </span>
          </Link>
          <ExperimentalBadge />
          {/* Masthead tagline — lives inline in the top bar (desktop only). The
              standalone full-width ".home-flag" strip was retired 2026-08-02 so
              the feed starts higher; this italic subline carries the tagline. */}
          <span className="nav-tagline" aria-hidden="true">See through the void.</span>
        </div>

        <span className="nav-dateline-inline" aria-hidden="true" suppressHydrationWarning>
          {dateline}
          {timestamp && (
            <>
              <span className="nav-dateline-inline__sep">&middot;</span>
              <span className="nav-dateline-inline__time"><span className="nav-asof">as of </span>{timestamp}</span>
            </>
          )}
        </span>
        {/* Mobile dateline — compact freshness signal. Time (with zone) is the
            priority in the tight row; the date shows only when the row is wide
            enough (>=400px, via CSS). */}
        <span className="nav-dateline-mobile" aria-hidden="true" suppressHydrationWarning>
          <span className="nav-dateline-mobile__date">{dateline}</span>
          {timestamp && (
            <span className="nav-dateline-mobile__time"><span className="nav-asof">as of </span>{timestamp}</span>
          )}
        </span>

        {/* Spinoff product family (Void History + Void Weekly) HIDDEN for launch
            2026-08-05 — restore the .nav-spinoffs block when History/Weekly ship
            as features. Links + SigilWordmark import removed, routes intact. */}

        <div className="nav-right">
          {/* Page navigation — destinations.
              Games + Paper hidden from production nav (not ready). Routes
              still resolve at /games and /paper for direct URL access. */}
          <nav className="nav-pages" aria-label="Pages">
            <PageToggle activePage="feed" />
            {/* On Air — desktop affordance for the daily broadcast. Only shown
                when a brief with audio is available (hasAudio); tapping opens the
                player and starts playback via onOnairClick. */}
            {onOnairClick && hasAudio && (
              <button
                type="button"
                className={`nav-page nav-page--onair${isAudioPlaying ? " nav-page--onair-live" : ""}`}
                onClick={onOnairClick}
                aria-label={isAudioPlaying ? "On Air, playing" : "On Air"}
                title="On Air"
              >
                On Air
              </button>
            )}
            <Link href="/ship" className="nav-page" aria-label="Feedback: tell us what to build or fix" title="Feedback">
              Feedback
            </Link>
            <Link href="/about" className="nav-page" aria-label="About Void News" title="About">
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

      {/* Mobile edition tabs removed 2026-06-02 single-feed. */}
    </header>
  );
}
