"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";
import MobileTabBar from "./MobileTabBar";
import MobileMiniPlayer from "./MobileMiniPlayer";
import { AUDIO_ENABLED } from "../lib/audioGate";
import { BASE_PATH } from "../lib/utils";

const MobileSidePanel = dynamic(() => import("./MobileSidePanel"), { ssr: false });

/* ---------------------------------------------------------------------------
   MobileNav — Client wrapper that orchestrates MobileTabBar, MobileSidePanel,
   and MobileMiniPlayer. Placed in layout.tsx so it appears on every page.
   Desktop: hidden via CSS on .mtb, .msp, .mmp.
   --------------------------------------------------------------------------- */

export default function MobileNav() {
  const [sidePanelOpen, setSidePanelOpen] = useState(false);
  const pathname = usePathname();
  // The /onair page is itself the player — suppress the redundant mini-player.
  const onOnAir = (pathname.replace(BASE_PATH, "") || "/").startsWith("/onair");

  const handleMoreTap = useCallback(() => {
    setSidePanelOpen((v) => !v);
  }, []);

  const handleSidePanelClose = useCallback(() => {
    setSidePanelOpen(false);
  }, []);

  return (
    <>
      {AUDIO_ENABLED && !onOnAir && <MobileMiniPlayer />}
      <MobileTabBar onMoreTap={handleMoreTap} moreOpen={sidePanelOpen} />
      <MobileSidePanel open={sidePanelOpen} onClose={handleSidePanelClose} />
    </>
  );
}
