"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import MobileTabBar from "./MobileTabBar";
import MobileMiniPlayer from "./MobileMiniPlayer";
import { useAudio } from "./AudioProvider";
import { AUDIO_ENABLED } from "../lib/audioGate";
import { BASE_PATH } from "../lib/utils";

const MobileSidePanel = dynamic(() => import("./MobileSidePanel"), { ssr: false });
// Global desktop audio player. Mounted here (a layout-level client module) so it
// renders on EVERY route — including /weekly — not just the homepage. It hides
// itself on mobile via CSS, so it is safe alongside the mobile UI below.
const FloatingPlayer = dynamic(() => import("./FloatingPlayer"), { ssr: false });

/* ---------------------------------------------------------------------------
   MobileNav — Client wrapper that orchestrates MobileTabBar, MobileSidePanel,
   and MobileMiniPlayer. Placed in layout.tsx so it appears on every page.
   Desktop: hidden via CSS on .mtb, .msp, .mmp.
   --------------------------------------------------------------------------- */

export default function MobileNav() {
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const pathname = usePathname();
  const { contentType } = useAudio();
  const route = pathname.replace(BASE_PATH, "") || "/";
  // The /onair page is itself the player — suppress the redundant mini-player.
  const onOnAir = route.startsWith("/onair");
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
    setSidePanelOpen((v) => !v);
  }, []);

  const handleSidePanelClose = useCallback(() => {
    setSidePanelOpen(false);
  }, []);

  return (
    <>
      {AUDIO_ENABLED && !onOnAir && !onShip && !suppressNewsChrome && <MobileMiniPlayer />}
      {/* Desktop floating player — global across all routes (incl. /weekly),
          hidden on mobile via CSS. Suppressed on /ship and on /history when the
          daily brief (not history audio) would otherwise be shown. */}
      {AUDIO_ENABLED && !onShip && !suppressNewsChrome && <FloatingPlayer />}
      <MobileTabBar onMoreTap={handleMoreTap} moreOpen={sidePanelOpen} />
      <MobileSidePanel open={sidePanelOpen} onClose={handleSidePanelClose} />
    </>
  );
}
