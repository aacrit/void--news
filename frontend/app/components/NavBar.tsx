"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { MagnifyingGlass } from "@phosphor-icons/react";
import ThemeToggle from "./ThemeToggle";
import PageToggle from "./PageToggle";
import LogoFull from "./LogoFull";
import ExperimentalBadge from "./ExperimentalBadge";
import { getEditionTimestampLocal, getEditionDatelineUTC } from "../lib/utils";

interface NavBarProps {
  onSearchClick?: () => void;
  /** Edition build time (pipeline completed_at, ISO). Drives the masthead
      dateline + timestamp so they reflect when THIS edition was built, not the
      reader's current clock. Falls back to now when absent. */
  editionBuiltAt?: string | null;
  /** Deterministic, preformatted edition DATE, computed once at build time in
      UTC (prerendered front page). When supplied it renders directly on first
      paint (server + client match exactly, no #418), bypassing the client-local
      mounted gate below. Absent on client-only routes. The TIME is NEVER passed
      this way: local time is machine-dependent, so it is always computed after
      mount from editionBuiltAt (see below). */
  editionDateline?: string;
  /** Explicit literal override for the "as of" TIME node. Normally left
      undefined so the time is computed in the viewer's local zone after mount.
      Pass "" to SUPPRESS the time entirely (e.g. an archived StandaloneDeepDive
      snapshot shows its edition DATE only, no live "as of" clock). */
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
}: NavBarProps) {
  const [mounted, setMounted] = useState(false);
  // SSR-safe hydration pattern — defer dateline/timestamp render until after
  // mount so server HTML matches client HTML on first paint (avoids React #418).
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { setMounted(true); }, []);
  // DATE: the preformatted build-time UTC string wins when supplied (front-page
  // prerender) so it renders immediately and byte-identically on server +
  // client. Otherwise fall back to the client-fetched build time formatted UTC,
  // mount-gated so an absent build time (which falls back to "now") can't
  // mismatch on first paint. The date stays UTC across every surface.
  const dateline = editionDateline ?? (mounted ? getEditionDatelineUTC(editionBuiltAt) : "");
  // TIME: rendered in the VIEWER'S LOCAL zone (e.g. "4:00 PM CDT") so it is
  // relevant to each reader. Local time is machine-dependent and MUST NOT be
  // baked into the prerendered HTML, so it is ALWAYS computed after mount from
  // the raw ISO editionBuiltAt. Server HTML and the first client render both
  // resolve to "" (mounted === false), so there is no hydration mismatch; the
  // local time paints in only after the mount effect fires. An explicit
  // editionTimestamp prop (e.g. "" from an archived snapshot) overrides the
  // local computation, letting a permalink page suppress the live clock.
  const timestamp =
    editionTimestamp !== undefined
      ? editionTimestamp
      : mounted
        ? getEditionTimestampLocal(editionBuiltAt)
        : "";

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
            {/* On Air reaches the daily broadcast from the docked/floating
                player and the footer On Air pill on desktop, so the duplicate
                top-nav On Air button was removed 2026-08-10 (nav-onair-dedup). */}
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
