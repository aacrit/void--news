"use client";

import { useCallback } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { hapticMicro } from "../lib/haptics";
import { BASE_PATH } from "../lib/utils";
import { AUDIO_ENABLED } from "../lib/audioGate";
import { useAudio } from "./AudioProvider";

/* ---------------------------------------------------------------------------
   MobileTabBar — Persistent bottom tab bar (mobile only, <768px).

   Five TEXT-label slots (no icons), typography mirrors the desktop masthead
   spinoffs: Playfair italic with per-product accent colors.

     Home · Weekly · History · On Air · Menu

   - Weekly / History / On Air carry their product accent (same values as the
     desktop NavBar: History burnt umber, Weekly magazine red, On Air the
     broadcast red). Home + Menu use the neutral nav color.
   - On Air reveals the collapsed mini-player when a brief with audio is loaded;
     otherwise it routes to the dedicated /onair page. It never auto-plays and
     never opens the full in-page sheet (that IS /onair on mobile).
   - Menu toggles the MobileSidePanel.
   - Active route shown via a top accent rule (not an icon).
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
        aria-current={isActive("home") ? "page" : undefined}
        onClick={() => hapticMicro()}
      >
        <span className="mtb__label">Home</span>
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
        <span className="mtb__label">On Air</span>
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
        <span className="mtb__label">Menu</span>
      </button>
    </nav>
  );
}
