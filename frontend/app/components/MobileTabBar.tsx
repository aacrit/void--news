"use client";

import { useCallback } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { hapticMicro, hapticMedium } from "../lib/haptics";
import { BASE_PATH } from "../lib/utils";
import { useAudio } from "./AudioProvider";
import ScaleIcon from "./ScaleIcon";

/* ---------------------------------------------------------------------------
   MobileTabBar — the single primary nav surface (mobile only, <768px).

   Three zones, "raised center brand anchor between two side tabs":

       [ On Air ]        (( Home ))        [ Menu ]

   - Home (center) — the PROMINENT raised brand anchor: the Sigil-O mark in the
     News terracotta, larger than the side tabs, punching through the bar. Links
     to "/". This is the center logo/anchor.
   - On Air (left) — a standard side tab (icon + label), demoted from the old
     raised disc but keeping a teal accent on its broadcast glyph + label.
     Tapping it always navigates to the dedicated /onair broadcast page (On Air
     is a first-class destination, not a floating overlay). A small teal dot
     marks the live/playing state.
   - Menu (right) — a hamburger (three horizontal lines) that slides the
     MobileSidePanel drawer in from the right with the complete secondary nav
     + info surface.

   Active route shown via a top accent rule on the side tabs / a ring on the
   center anchor. Sits above the iOS home indicator (safe-area-inset-bottom).
   Hidden on desktop via CSS.
   --------------------------------------------------------------------------- */

interface MobileTabBarProps {
  onMoreTap: () => void;
  moreOpen: boolean;
}

export default function MobileTabBar({ onMoreTap, moreOpen }: MobileTabBarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { isPlaying } = useAudio();

  const path = pathname.replace(BASE_PATH, "") || "/";
  const homeActive =
    path === "/" || path === "" || /^\/(world)\/?$/.test(path);

  // On Air: always navigate to the dedicated /onair broadcast page. On Air is a
  // destination page (its own masthead, transport, show notes, archive), not a
  // floating overlay — playback state persists there via the global AudioProvider.
  const handleOnAir = useCallback(() => {
    hapticMedium();
    router.push("/onair");
  }, [router]);

  return (
    <nav className="mtb" aria-label="Primary navigation">
      {/* ── On Air (left, demoted side tab with a teal accent) ── */}
      <button
        type="button"
        className={`mtb__tab mtb__tab--onair${isPlaying ? " mtb__tab--onair-live" : ""}`}
        aria-label={isPlaying ? "On Air, playing" : "On Air"}
        onClick={handleOnAir}
      >
        <span className="mtb__onair-glyph">
          {/* Broadcast glyph — center dot with concentric radio-wave arcs */}
          <svg
            className="mtb__icon mtb__onair-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="1.75" fill="currentColor" stroke="none" />
            <path d="M8.2 8.2 a5.4 5.4 0 0 0 0 7.6" />
            <path d="M5.1 5.1 a9.8 9.8 0 0 0 0 13.8" />
            <path d="M15.8 8.2 a5.4 5.4 0 0 1 0 7.6" />
            <path d="M18.9 5.1 a9.8 9.8 0 0 1 0 13.8" />
          </svg>
          {/* Live dot — small teal pip when audio is playing. */}
          {isPlaying && <span className="mtb__onair-live-dot" aria-hidden="true" />}
        </span>
        <span className="mtb__label mtb__label--onair">On Air</span>
      </button>

      {/* ── Home (center, raised brand anchor) ── */}
      <Link
        href="/"
        className={`mtb__home${homeActive ? " mtb__home--active" : ""}`}
        aria-label="Home"
        aria-current={homeActive ? "page" : undefined}
        onClick={() => hapticMicro()}
      >
        <span className="mtb__home-disc">
          <ScaleIcon
            size={32}
            animation="none"
            className="mtb__mark"
            /* White mark on the terracotta disc — brand-on-brand anchor. */
            style={{ ["--sigil-brass" as string]: "#fff" }}
          />
        </span>
        <span className="mtb__label mtb__label--home">Home</span>
      </Link>

      {/* ── Menu (right, hamburger drawer trigger) ── */}
      <button
        type="button"
        className={`mtb__tab${moreOpen ? " mtb__tab--active" : ""}`}
        aria-expanded={moreOpen}
        aria-haspopup="dialog"
        aria-label="Menu"
        onClick={() => {
          hapticMicro();
          onMoreTap();
        }}
      >
        {/* Hamburger — three horizontal lines, signals the side drawer of
            secondary navigation + info. */}
        <svg
          className="mtb__icon mtb__hamburger"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M4 7h16" />
          <path d="M4 12h16" />
          <path d="M4 17h16" />
        </svg>
        <span className="mtb__label">Menu</span>
      </button>
    </nav>
  );
}
