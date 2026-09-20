"use client";

/* ---------------------------------------------------------------------------
   The opening spread — what a reader lands on after the cover.

   This is the half of the "cover, then a spread" decision that fixes the
   duplication. The old CoverHero rendered the SAME headline over the SAME
   photograph the full-screen cover had just shown, so the first two screens of
   the issue were identical. It takes no image and no repeated headline now.

   What it carries instead is the furniture a feature opening actually needs:
   the department kicker, the headline as the page's <h1>, a deck in italic
   serif, and the dateline. The art belongs to the feature below it.
   --------------------------------------------------------------------------- */

import type React from "react";
import { useScrollReveal } from "../hooks";

export default function CoverOpening({
  kicker,
  headline,
  deck,
  dateline,
  sources,
}: {
  kicker: string;
  headline: string;
  deck?: string;
  dateline: string;
  sources?: number | null;
}) {
  const [ref, visible] = useScrollReveal(0.05);
  return (
    <header
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-opening wk-reveal${visible ? " wk-reveal--visible" : ""}`}
    >
      <p className="wk-opening__kicker">{kicker}</p>
      {/* The page's primary heading. UAT 2026-05-13 P0-5 found /weekly had no
          <h1> at all; it now sits on the opening spread, where a magazine puts
          the feature's title, rather than on a repeated cover. */}
      <h1 className="wk-opening__headline">{headline}</h1>
      {deck && <p className="wk-opening__deck">{deck}</p>}
      <div className="wk-opening__meta">
        <span className="wk-opening__dateline">{dateline}</span>
        {!!sources && (
          <>
            <span className="wk-opening__sep" aria-hidden="true"> · </span>
            <span className="wk-opening__sources">{sources} sources</span>
          </>
        )}
      </div>
      <div className="wk-opening__rule" aria-hidden="true">
        <svg viewBox="0 0 80 4" preserveAspectRatio="none">
          <path
            d="M0 2 C10 0.5, 20 3.5, 40 2 S60 0.5, 80 2"
            stroke="currentColor"
            strokeWidth="1.5"
            fill="none"
          />
        </svg>
      </div>
    </header>
  );
}
