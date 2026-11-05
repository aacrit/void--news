"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import MobileTabBar from "./MobileTabBar";
import { useAudio } from "./AudioProvider";
import { AUDIO_ENABLED } from "../lib/audioGate";
import { BASE_PATH } from "../lib/utils";

// The hamburger "Menu" tab opens the MobileSidePanel — a right-edge side drawer
// that is the complete secondary nav + info surface (carries the masthead info
// the mobile top chrome drops: edition time, source count, theme control). The
// older bottom-sheet MobileMoreSheet.tsx is kept in the repo (unused) for
// reversibility.
const MobileSidePanel = dynamic(() => import("./MobileSidePanel"), { ssr: false });
// Global desktop audio player. Mounted here (a layout-level client module) so it
// renders on EVERY route — including /weekly — not just the homepage. It hides
// itself on mobile via CSS, so it is safe alongside the mobile UI below.
const FloatingPlayer = dynamic(() => import("./FloatingPlayer"), { ssr: false });
// The On Air console. A dialog opened from the tab bar, the pill or the
// wordmark, on every route. It is NOT suppressed with the pill below: the pill
// appears unasked and can cover a hero, while the panel only ever opens on a
// deliberate press, and a reader who presses On Air on a history event means it.
const OnAirPanel = dynamic(() => import("./OnAirPanel"), { ssr: false });

/* ---------------------------------------------------------------------------
   MobileNav — Client wrapper that orchestrates MobileTabBar and MobileSidePanel.
   Placed in layout.tsx so it appears on every page. Desktop: hidden via CSS on
   .mtb, .msp.

   The horizontal MobileMiniPlayer strip (that used to sit above the tab bar) was
   retired 2026-08-06 as redundant with the /onair destination page. Its file
   (MobileMiniPlayer.tsx) is kept in the repo (unused) for reversibility, mirroring
   how MobileSidePanel was retired.
   --------------------------------------------------------------------------- */

/** The edition build time (feed.builtAt), threaded from layout.tsx exactly as
 *  NavBar receives it, so the Menu drawer and the masthead format the SAME
 *  value. The drawer used to fetch it from a stub that always returned null
 *  and then print the reader's current hour as the edition time. */
export default function MobileNav({ editionBuiltAt = null }: { editionBuiltAt?: string | null } = {}) {
  const [moreSheetOpen, setMoreSheetOpen] = useState(false);
  const pathname = usePathname();
  const route = pathname.replace(BASE_PATH, "") || "/";
  // The /ship "Mission Control" dashboard owns the viewport and has no place for
  // the On Air player chrome — suppress both audio players there. The global
  // MobileTabBar / side panel (site navigation, not audio) stay.
  const onShip = route.startsWith("/ship");
  // The pill used to stand down on /history* unless History audio was loaded,
  // so On Air started on /audio kept playing on a History page with no control
  // in reach (WCAG 1.4.2, audit 2 F5). On History it now mounts whenever the
  // reader has started anything: playing, or paused part way (currentTime > 0),
  // or History's own audio loaded. What it still does not do on History is
  // advertise today's brief that nobody pressed: the daily edition is offered
  // to the element on every route, and an idle pill over the archive's
  // corner was the reason for the old gate. The documented stand downs remain
  // inside FloatingPlayer: /onair and an open panel.
  const { contentType, isPlaying, currentTime } = useAudio();
  const onHistory = route.startsWith("/history");
  const idleOnHistory = onHistory && contentType !== "history" && !isPlaying && !(currentTime > 0);

  const handleMoreTap = useCallback(() => {
    setMoreSheetOpen((v) => !v);
  }, []);

  const handleMoreSheetClose = useCallback(() => {
    setMoreSheetOpen(false);
  }, []);

  return (
    <>
      {/* Desktop floating player — global across all routes (incl. /weekly),
          hidden on mobile via CSS. Suppressed on /ship, and on /history only
          while nothing has been started, so whatever plays can be paused. */}
      {AUDIO_ENABLED && !onShip && !idleOnHistory && <FloatingPlayer />}
      {AUDIO_ENABLED && !onShip && <OnAirPanel />}
      <MobileTabBar onMoreTap={handleMoreTap} moreOpen={moreSheetOpen} />
      <MobileSidePanel open={moreSheetOpen} onClose={handleMoreSheetClose} editionBuiltAt={editionBuiltAt} />
    </>
  );
}
