"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import MobileTabBar from "./MobileTabBar";
import { useAudio } from "./AudioProvider";
import { AUDIO_ENABLED } from "../lib/audioGate";
import { BASE_PATH } from "../lib/utils";

// The MobileMoreSheet replaces the retired right-edge MobileSidePanel as the
// secondary-destination surface. The bottom tab bar is now the only primary nav;
// MobileSidePanel.tsx is kept in the repo (unused) for reversibility.
const MobileMoreSheet = dynamic(() => import("./MobileMoreSheet"), { ssr: false });
// Global desktop audio player. Mounted here (a layout-level client module) so it
// renders on EVERY route — including /weekly — not just the homepage. It hides
// itself on mobile via CSS, so it is safe alongside the mobile UI below.
const FloatingPlayer = dynamic(() => import("./FloatingPlayer"), { ssr: false });

/* ---------------------------------------------------------------------------
   MobileNav — Client wrapper that orchestrates MobileTabBar and MobileMoreSheet.
   Placed in layout.tsx so it appears on every page. Desktop: hidden via CSS on
   .mtb, .mms.

   The horizontal MobileMiniPlayer strip (that used to sit above the tab bar) was
   retired 2026-08-06 as redundant with the /onair destination page. Its file
   (MobileMiniPlayer.tsx) is kept in the repo (unused) for reversibility, mirroring
   how MobileSidePanel was retired.
   --------------------------------------------------------------------------- */

export default function MobileNav() {
  const [moreSheetOpen, setMoreSheetOpen] = useState(false);
  const pathname = usePathname();
  const { contentType } = useAudio();
  const route = pathname.replace(BASE_PATH, "") || "/";
  // The /ship "Mission Control" dashboard owns the viewport and has no place for
  // the On Air player chrome — suppress both audio players there. The global
  // MobileTabBar / side panel (site navigation, not audio) stay.
  const onShip = route.startsWith("/ship");
  // On a void --history event route the daily news brief must NOT show — its
  // pill physically overlaps the hero/scrubber. Suppress the shared player
  // UNLESS the reader has loaded the event's own audio via playHistory (which
  // flips contentType to "history"), in which case the same shared player is
  // now showing HISTORY audio and should stay. Same per-route gate as /ship.
  const suppressNewsChrome = route.startsWith("/history") && contentType !== "history";

  const handleMoreTap = useCallback(() => {
    setMoreSheetOpen((v) => !v);
  }, []);

  const handleMoreSheetClose = useCallback(() => {
    setMoreSheetOpen(false);
  }, []);

  return (
    <>
      {/* Desktop floating player — global across all routes (incl. /weekly),
          hidden on mobile via CSS. Suppressed on /ship and on /history when the
          daily brief (not history audio) would otherwise be shown. */}
      {AUDIO_ENABLED && !onShip && !suppressNewsChrome && <FloatingPlayer />}
      <MobileTabBar onMoreTap={handleMoreTap} moreOpen={moreSheetOpen} />
      <MobileMoreSheet open={moreSheetOpen} onClose={handleMoreSheetClose} />
    </>
  );
}
