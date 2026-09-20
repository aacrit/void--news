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
  days,
}: {
  kicker: string;
  headline: string;
  deck?: string;
  dateline: string;
  /* Distinct outlets that carried this story across the WEEK, from the
     threading engine. The old figure summed the timeline's per-day source
     counts, which double-counts any outlet that covered the story twice. */
  sources?: number | null;
  /** Days the story ran. The one stat a weekly can print and a daily cannot. */
  days?: number | null;
}) {
  const [ref, visible] = useScrollReveal(0.05);
  return (
    <header
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-opening wk-reveal${visible ? " wk-reveal--visible" : ""}`}
    >
      <p className="wk-opening__kicker">{kicker}</p>
      {/* An h2, not an h1. This component is rendered once per cover feature,
          so hard-coding h1 gave the document two of them. The issue's h1 is the
          cover headline; a feature opening sits at the same level as the
          department plates. */}
      <h2 className="wk-opening__headline">{headline}</h2>
      {deck && <p className="wk-opening__deck">{deck}</p>}
      <div className="wk-opening__meta">
        <span className="wk-opening__dateline">{dateline}</span>
        {!!days && (
          <>
            <span className="wk-opening__sep" aria-hidden="true"> · </span>
            <span className="wk-opening__sources">
              {days} {days === 1 ? "day" : "days"}
            </span>
          </>
        )}
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
