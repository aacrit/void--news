"use client";

import ScaleIcon from "./ScaleIcon";
import type { ScaleAnimation } from "./ScaleIcon";

/* ---------------------------------------------------------------------------
   LogoIcon — Icon-only brand mark (The Void Scale)
   Use this for compact contexts: mobile nav, loading indicators, refresh btn.
   For the full logo (icon + wordmark), use LogoFull instead.
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
