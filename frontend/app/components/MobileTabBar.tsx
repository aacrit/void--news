"use client";

import { useCallback } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { hapticMicro } from "../lib/haptics";
import { BASE_PATH } from "../lib/utils";
import { AUDIO_ENABLED } from "../lib/audioGate";
import { useAudio } from "./AudioProvider";
import ScaleIcon from "./ScaleIcon";

/* ---------------------------------------------------------------------------
   MobileTabBar — Persistent bottom tab bar (mobile only, <768px).

   A MIX of a brand mark, editorial text, and icons — evenly spaced, each a
   >=44px tap target:

     [Sigil-O]  ·  Weekly  ·  History  ·  [broadcast]  ·  [hamburger]

   - Home is the standalone Sigil-O brand mark, recolored to the News terracotta
     (--palette-news) so it matches the masthead. Links to "/".
   - Weekly / History keep their Playfair-italic labels + product accents
     (Weekly magazine red, History burnt umber).
   - On Air is a teal broadcast glyph (--voice-accent, the On Air brand color).
     It reveals the collapsed mini-player when a brief with audio is loaded;
     otherwise it routes to the dedicated /onair page. Never auto-plays and never
     opens the full in-page sheet (that IS /onair on mobile).
   - Menu is a neutral hamburger glyph; toggles the MobileSidePanel.
   - Active route shown via a top accent rule (not an icon swap).
   Hidden on desktop via CSS.
   --------------------------------------------------------------------------- */

interface MobileTabBarProps {
  onMoreTap: () => void;
  moreOpen: boolean;
}

export default function MobileTabBar({ onMoreTap, moreOpen }: MobileTabBarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { brief, setPlayerVisible, setExpanded } = useAudio();

  const path = pathname.replace(BASE_PATH, "") || "/";

  const isActive = useCallback(
    (key: string): boolean => {
      switch (key) {
        case "home":
          return path === "/" || path === "" || /^\/(world)\/?$/.test(path);
        case "weekly":
          return path.startsWith("/weekly");
        case "history":
          return path.startsWith("/history") || path.startsWith("/revolt");
        case "onair":
          return path.startsWith("/onair");
        case "menu":
          return moreOpen;
        default:
          return false;
      }
    },
    [path, moreOpen]
  );

  // On Air tap: reveal the collapsed mini-player strip when a brief with audio
  // is loaded; otherwise take the reader to /onair. Never auto-plays, never
  // opens the expanded sheet (setExpanded(false) keeps it collapsed).
  const handleOnAir = useCallback(() => {
    hapticMicro();
    if (AUDIO_ENABLED && brief?.audio_url) {
      setExpanded(false);
      setPlayerVisible(true);
    } else {
      router.push("/onair");
    }
  }, [brief?.audio_url, setExpanded, setPlayerVisible, router]);

  const tabClass = (key: string) =>
    `mtb__tab${isActive(key) ? " mtb__tab--active" : ""}`;

  return (
    <nav className="mtb" aria-label="Mobile navigation">
      <Link
        href="/"
        className={tabClass("home")}
        data-accent="neutral"
        aria-label="Home"
        aria-current={isActive("home") ? "page" : undefined}
        onClick={() => hapticMicro()}
      >
        {/* Sigil-O brand mark, recolored to the News terracotta */}
        <ScaleIcon
          size={26}
          animation="none"
          className="mtb__mark"
          style={{ ["--sigil-brass" as string]: "var(--palette-news)" }}
        />
      </Link>

      <Link
        href="/weekly"
        className={tabClass("weekly")}
        data-accent="weekly"
        aria-current={isActive("weekly") ? "page" : undefined}
        onClick={() => hapticMicro()}
      >
        <span className="mtb__label">Weekly</span>
      </Link>

      <Link
        href="/history"
        className={tabClass("history")}
        data-accent="history"
        aria-current={isActive("history") ? "page" : undefined}
        onClick={() => hapticMicro()}
      >
        <span className="mtb__label">History</span>
      </Link>

      <button
        type="button"
        className={tabClass("onair")}
        data-accent="onair"
        aria-current={isActive("onair") ? "page" : undefined}
        aria-label="On Air"
        onClick={handleOnAir}
      >
        {/* Broadcast glyph — center dot with concentric radio-wave arcs (teal) */}
        <svg
          className="mtb__icon"
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
      </button>

      <button
        type="button"
        className={tabClass("menu")}
        data-accent="neutral"
        aria-expanded={moreOpen}
        aria-label="Menu"
        onClick={() => {
          hapticMicro();
          onMoreTap();
        }}
      >
        {/* Hamburger glyph — three horizontal bars (neutral) */}
        <svg
          className="mtb__icon"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          aria-hidden="true"
        >
          <line x1="4" y1="7" x2="20" y2="7" />
          <line x1="4" y1="12" x2="20" y2="12" />
          <line x1="4" y1="17" x2="20" y2="17" />
        </svg>
      </button>
    </nav>
  );
}
