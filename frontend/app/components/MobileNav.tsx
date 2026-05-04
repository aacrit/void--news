"use client";

import { useState, useCallback } from "react";
import dynamic from "next/dynamic";
import MobileTabBar from "./MobileTabBar";
import MobileMiniPlayer from "./MobileMiniPlayer";

const MobileSidePanel = dynamic(() => import("./MobileSidePanel"), { ssr: false });

/* ---------------------------------------------------------------------------
   MobileNav — Client wrapper that orchestrates MobileTabBar, MobileSidePanel,
   and MobileMiniPlayer. Placed in layout.tsx so it appears on every page.
   Desktop: hidden via CSS on .mtb, .msp, .mmp.
   --------------------------------------------------------------------------- */

export default function MobileNav() {
  const [sidePanelOpen, setSidePanelOpen] = useState(false);

  const handleMoreTap = useCallback(() => {
    setSidePanelOpen((v) => !v);
  }, []);

  const handleSidePanelClose = useCallback(() => {
    setSidePanelOpen(false);
  }, []);

  return (
    <>
      <MobileMiniPlayer />
      <MobileTabBar onMoreTap={handleMoreTap} moreOpen={sidePanelOpen} />
      <MobileSidePanel open={sidePanelOpen} onClose={handleSidePanelClose} />
    </>
  );
}
