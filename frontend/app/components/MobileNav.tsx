"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import MobileTabBar from "./MobileTabBar";
import MobileMiniPlayer from "./MobileMiniPlayer";
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
  const route = pathname.replace(BASE_PATH, "") || "/";
  // The /onair page is itself the player — suppress the redundant mini-player.
  const onOnAir = route.startsWith("/onair");
  // The /ship "Mission Control" dashboard owns the viewport and has no place for
  // the On Air player chrome — suppress both audio players there. The global
  // MobileTabBar / side panel (site navigation, not audio) stay.
  const onShip = route.startsWith("/ship");

  const handleMoreTap = useCallback(() => {
    setSidePanelOpen((v) => !v);
  }, []);

  const handleSidePanelClose = useCallback(() => {
    setSidePanelOpen(false);
  }, []);

  return (
    <>
      {AUDIO_ENABLED && !onOnAir && !onShip && <MobileMiniPlayer />}
      {/* Desktop floating player — global across all routes (incl. /weekly),
          hidden on mobile via CSS. Suppressed on /ship. */}
      {AUDIO_ENABLED && !onShip && <FloatingPlayer />}
      <MobileTabBar onMoreTap={handleMoreTap} moreOpen={sidePanelOpen} />
      <MobileSidePanel open={sidePanelOpen} onClose={handleSidePanelClose} />
    </>
  );
}
