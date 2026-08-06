"use client";

import { useCallback } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { hapticMicro, hapticMedium } from "../lib/haptics";
import { BASE_PATH } from "../lib/utils";
import { AUDIO_ENABLED } from "../lib/audioGate";
import { useAudio } from "./AudioProvider";
import ScaleIcon from "./ScaleIcon";

/* ---------------------------------------------------------------------------
   MobileTabBar — the single primary nav surface (mobile only, <768px).

   Three zones, "lean bar + raised hero":

       [ Home ]        (( On Air ))        [ More ^ ]

   - Home (left) — the Sigil-O brand mark, recolored to the News terracotta.
     Links to "/".
   - On Air (center) — a PROMINENT raised teal disc (the broadcast hero). Tapping
     it opens the full teal broadcast portal (FloatingPlayer's broadcast view,
     the same markup/styling as the desktop On Air portal) as a full-height
     mobile sheet. It does this by revealing the player and flagging it expanded;
     FloatingPlayer maps that to its broadcast view on mobile. With no audio yet,
     it routes to /onair (which shows the "being prepared" state).
   - More (right) — an up-chevron (NOT a hamburger) that slides the
     MobileMoreSheet up with the secondary destinations.

   Active route shown via a top accent rule on the side tabs. Sits above the iOS
   home indicator (safe-area-inset-bottom). Hidden on desktop via CSS.
   --------------------------------------------------------------------------- */

interface MobileTabBarProps {
  onMoreTap: () => void;
  moreOpen: boolean;
}

export default function MobileTabBar({ onMoreTap, moreOpen }: MobileTabBarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { brief, isPlaying, setPlayerVisible, setExpanded } = useAudio();

  const path = pathname.replace(BASE_PATH, "") || "/";
  const homeActive =
    path === "/" || path === "" || /^\/(world)\/?$/.test(path);

  // On Air: open the full broadcast portal (teal, matching desktop) when a brief
  // with audio is loaded. setExpanded(true) makes FloatingPlayer render its
  // broadcast view as a full-height mobile sheet. With no audio, fall back to the
  // dedicated /onair route (empty-state screen).
  const handleOnAir = useCallback(() => {
    hapticMedium();
    if (AUDIO_ENABLED && brief?.audio_url) {
      setPlayerVisible(true);
      setExpanded(true);
    } else {
      router.push("/onair");
    }
  }, [brief?.audio_url, setPlayerVisible, setExpanded, router]);

  return (
    <nav className="mtb" aria-label="Primary navigation">
      {/* ── Home (left) ── */}
      <Link
        href="/"
        className={`mtb__tab${homeActive ? " mtb__tab--active" : ""}`}
        aria-label="Home"
        aria-current={homeActive ? "page" : undefined}
        onClick={() => hapticMicro()}
      >
        <ScaleIcon
          size={24}
          animation="none"
          className="mtb__mark"
          style={{ ["--sigil-brass" as string]: "var(--palette-news)" }}
        />
        <span className="mtb__label">Home</span>
      </Link>

      {/* ── On Air (center, raised hero) ── */}
      <button
        type="button"
        className={`mtb__onair${isPlaying ? " mtb__onair--live" : ""}`}
        aria-label={isPlaying ? "On Air — playing" : "On Air"}
        onClick={handleOnAir}
      >
        <span className="mtb__onair-disc">
          {/* Broadcast glyph — center dot with concentric radio-wave arcs */}
          <svg
            className="mtb__onair-icon"
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
        </span>
        <span className="mtb__label mtb__label--onair">On Air</span>
      </button>

      {/* ── More (right, up-chevron sheet trigger) ── */}
      <button
        type="button"
        className={`mtb__tab${moreOpen ? " mtb__tab--active" : ""}`}
        aria-expanded={moreOpen}
        aria-haspopup="dialog"
        aria-label="More"
        onClick={() => {
          hapticMicro();
          onMoreTap();
        }}
      >
        {/* Up-chevron — signals a sheet rising from the bottom (not a hamburger) */}
        <svg
          className={`mtb__icon mtb__chevron${moreOpen ? " mtb__chevron--open" : ""}`}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M6 15l6-6 6 6" />
        </svg>
        <span className="mtb__label">More</span>
      </button>
    </nav>
  );
}
