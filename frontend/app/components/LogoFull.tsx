"use client";

import SigilWordmark from "./SigilWordmark";

/* ---------------------------------------------------------------------------
   LogoFull — the primary brand lockup: "V[Sigil-O]ID  NEWS".

   The product's own Sigil (coverage ring + level balance beam) IS the letter O
   in VOID; there is no separate left-hand icon anymore. "VOID" is the parent
   brand, the second word a swappable product slot (pass `product`, default
   "NEWS"). Rendered by the shared SigilWordmark.

   Public API preserved: LogoFull({ height = 28, className }). At a given
   `height` the lockup renders ~that many px tall so consumers (NavBar tiers,
   Footer, topbars, about, error pages) do not shift.
   --------------------------------------------------------------------------- */

interface LogoFullProps {
  /** Height in px. Width scales proportionally. Default 28. */
  height?: number;
  className?: string;
  /** Swappable product word after VOID (e.g. "VISION"). Default "NEWS". */
  product?: string;
  /** Responsive sizing: let CSS font-size on `className` drive the size (one
   *  instance can scale across breakpoints instead of rendering copies). */
  responsive?: boolean;
}

export default function LogoFull({ height = 28, className, product = "NEWS", responsive }: LogoFullProps) {
  return <SigilWordmark height={height} className={className} product={product} responsive={responsive} accent={"var(--palette-news)"} />;
}
