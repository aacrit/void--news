"use client";

import ScaleIcon from "./ScaleIcon";
import type { ScaleAnimation } from "./ScaleIcon";

/* ---------------------------------------------------------------------------
   LogoIcon — Icon-only brand mark (Void Circle + Scale Beam)
   Use this for compact contexts: mobile nav, loading indicators, refresh btn.
   For the full logo (icon + wordmark), use LogoFull instead.

   animation="none" renders only the void circle (pure favicon mark).
   animation="idle" and others show the full scale apparatus with tipping.
   --------------------------------------------------------------------------- */

interface LogoIconProps {
  size?: number;
  animation?: ScaleAnimation;
  className?: string;
}

export default function LogoIcon({
  size = 24,
  animation = "idle",
  className,
}: LogoIconProps) {
  return <ScaleIcon size={size} animation={animation} className={className} />;
}
