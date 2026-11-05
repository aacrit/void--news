"use client";

import SigilWordmark from "./SigilWordmark";

/* ---------------------------------------------------------------------------
   LogoWordmark — the brand lockup "V[Sigil-O]ID  NEWS".

   Same lockup as LogoFull (the Sigil-O is the mark, so there is no icon-less
   variant to distinguish anymore). Kept as its own export with its original
   API for the ~half-dozen consumers that import it directly (Footer,
   ErrorBoundary, HomeContent, LoadingSkeleton).

   Public API preserved: LogoWordmark({ height = 20, className }).
   --------------------------------------------------------------------------- */

interface LogoWordmarkProps {
  /** Height in px. Width scales proportionally. Default 20. */
  height?: number;
  className?: string;
  /** Swappable product word after VOID (e.g. "VISION"). Default "NEWS". */
  product?: string;
}

export default function LogoWordmark({ height = 20, className, product = "NEWS" }: LogoWordmarkProps) {
  return <SigilWordmark height={height} className={className} product={product} accent={"var(--palette-news)"} />;
}
