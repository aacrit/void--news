"use client";

import type { CSSProperties } from "react";

/* ---------------------------------------------------------------------------
   SigilWordmark — the parent-brand lockup: "V[◎]ID  NEWS"

   The product's own Sigil (a coverage ring with a level balance beam) replaces
   the letter O in VOID. "VOID" is the parent brand; the second word is a
   swappable product slot (VOID NEWS today, VOID VISION later — pass `product`).

   Implementation: HTML inline-flex. The caps are real serif text (Playfair
   Display, Georgia fallback) so kerning stays correct and the mark survives
   when Playfair has not loaded; the O is an inline <svg> sized to cap height,
   baseline-aligned with a hair of round-letter overshoot.

   The letters render in currentColor (ink on light, cream on dark). The
   Sigil-O renders in BRASS (--sigil-brass) so the mark pops as the brand
   accent — a decorative mark, so the AA text-contrast rule does not bind.

   On :hover / :focus-visible of the lockup (or an enclosing link/button) the
   beam tilts and sweeps left<->right, its color crossing the lean spectrum
   (blue = left, brass = center, red = right) — the live product Sigil's
   metaphor. Honors prefers-reduced-motion (static level brass mark).

   Styling for color + the hover sweep lives in components.css
   (.sigil-word* + @keyframes sigil-word-sweep). Height/geometry are inline so
   the visual-height contract holds at any `height`.
   --------------------------------------------------------------------------- */

interface SigilWordmarkProps {
  /** Target rendered height in px. Everything scales from this. */
  height: number;
  className?: string;
  /** Swappable product word after VOID. Defaults to "NEWS". */
  product?: string;
}

export default function SigilWordmark({
  height,
  className,
  product = "NEWS",
}: SigilWordmarkProps) {
  const fontSize = height;
  // The ring's visible outer edge is inset ~5% inside the 100x100 viewBox, so
  // markSize is sized up from cap height (~0.72em for these serifs) to make the
  // ring read as a true cap-height O; overshoot then re-centers it on the cap
  // band with a ~1.5% round-letter overshoot past the baseline and cap line.
  const markSize = fontSize * 0.81;
  const overshoot = fontSize * 0.055;

  const letter: CSSProperties = { display: "inline-block" };

  return (
    <span
      className={className ? `sigil-word ${className}` : "sigil-word"}
      /* Decorative: consumers (NavBar link, Footer, error pages) supply the
         accessible name, and NavBar renders three responsive copies — a label
         here would announce three times. Matches the prior LogoFull behavior. */
      aria-hidden="true"
      style={{
        display: "inline-flex",
        alignItems: "baseline",
        flexShrink: 0,
        whiteSpace: "nowrap",
        fontFamily: "var(--font-editorial, 'Playfair Display', Georgia, serif)",
        fontWeight: 700,
        fontStyle: "normal",
        fontSize: `${fontSize}px`,
        lineHeight: 1,
        letterSpacing: "0.02em",
        color: "currentColor",
      }}
    >
      <span style={letter} aria-hidden="true">
        V
      </span>
      <svg
        className="sigil-word__mark"
        viewBox="0 0 100 100"
        aria-hidden="true"
        style={{
          height: `${markSize}px`,
          width: `${markSize}px`,
          display: "inline-block",
          margin: "0 0.035em",
          transform: `translateY(${overshoot}px)`,
          flexShrink: 0,
          overflow: "visible",
        }}
      >
        {/* Coverage ring */}
        <circle
          className="sigil-word__ring"
          cx="50"
          cy="50"
          r="41"
          fill="none"
          strokeWidth={8}
        />
        {/* Balance beam + weight ticks — level at rest, tilts/sweeps on hover.
            The beam flows OUT past the ring, capped by vertical end-ticks: the
            sigil's |-| scale-beam shape. */}
        <g className="sigil-word__beam">
          <line x1="4" y1="50" x2="96" y2="50" strokeWidth={6} strokeLinecap="round" />
          <line x1="4" y1="42" x2="4" y2="58" strokeWidth={5} strokeLinecap="round" />
          <line x1="96" y1="42" x2="96" y2="58" strokeWidth={5} strokeLinecap="round" />
        </g>
        {/* Scale foot — post + base, static brass. The ring's bottom rests on the
            text baseline with the other caps; the foot draws BELOW y=91 and, via
            the svg's overflow:visible, hangs beneath the letters like a descender
            (the full void lens + sigil). Outside the beam group so it never tilts. */}
        <line className="sigil-word__foot" x1="50" y1="91" x2="50" y2="112" strokeWidth={6} strokeLinecap="round" />
        <path className="sigil-word__foot" d="M35 118 C43 113 57 113 65 118" fill="none" strokeWidth={6} strokeLinecap="round" />
      </svg>
      <span style={letter} aria-hidden="true">
        ID
      </span>
      {/* Wider gap between the two words */}
      <span style={{ display: "inline-block", width: "0.34em" }} aria-hidden="true" />
      <span style={letter} aria-hidden="true">
        {product}
      </span>
    </span>
  );
}
