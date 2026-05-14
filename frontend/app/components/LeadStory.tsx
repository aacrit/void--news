"use client";

import { useRef } from "react";
import type { Story } from "../lib/types";
import { CaretRight } from "@phosphor-icons/react";
import Sigil from "./Sigil";
import { hapticLight } from "../lib/haptics";
import { classifyCoverage } from "../lib/coverageClass";

interface LeadStoryProps {
  story: Story;
  /** 0 = primary (first/most important), 1+ = secondary */
  rank?: number;
  onStoryClick?: (story: Story, rect: DOMRect) => void;
  /** True when this card is focused via keyboard (J/K) navigation */
  kbdFocused?: boolean;
  /** v3 (2026-05-14): when true, this lead is rendered in a side-by-side
      twin layout sharing the hero canvas with another lead. Headline scales
      down one notch (--type-twin-headline) and the card wears a modifier
      class so layout-zones.css can apply twin-only styles. */
  twin?: boolean;
}

/* ---------------------------------------------------------------------------
   LeadStory — Hero treatment for the most important story.
   Text-only newspaper-front-page composition: badge → headline → summary.
   Per CEO 2026-05-13: hero image removed. The visualization (Sigil) and
   typography carry the editorial moment; no photograph.
   --------------------------------------------------------------------------- */

export default function LeadStory({ story, rank = 0, onStoryClick, kbdFocused, twin = false }: LeadStoryProps) {
  const cardRef = useRef<HTMLElement>(null);

  // Twin and solo top-story rank-0 layouts both use the full-canvas .lead-split
  // text composition. Twin reduces the headline scale via .lead-story--twin.
  // For rank 1+ (legacy secondary leads — currently unused but kept for safety)
  // we fall back to the smaller .lead-story__headline scale.
  const useSplit = rank === 0 || twin;
  const verdict = classifyCoverage(story);

  // Twin leads are co-equal Top Stories: both wear the badge. Solo rank-0
  // also wears it. Secondary (rank 1+ in non-twin mode) does not.
  const showBadge = rank === 0 || twin;

  // Headline is <h1> for the primary lead (rank 0 OR first twin) to satisfy
  // SEO/a11y "one h1 per page." A second twin lead uses <h2>.
  const HeadingTag: "h1" | "h2" = rank === 0 ? "h1" : "h2";
  const textContent = (
    <div data-slot="text" className={useSplit ? "lead-split__text" : undefined}>
      <HeadingTag className={useSplit ? "lead-headline" : "lead-story__headline"}>
        <span className={useSplit ? undefined : "lead-story__headline-text"}>{story.title}</span>
        {/* Badge moved inline with the Sigil (v6.2, 2026-05-15) — sits in the
            same row as the source-count Sigil to reclaim the ~24px vertical
            real estate it used to occupy above the headline. Both leads in a
            twin layout wear it; solo rank-0 also wears it. */}
        {showBadge && <span className="lead-story__badge lead-story__badge--inline">Top Story</span>}
        <Sigil data={story.sigilData} size={twin ? "lg" : "xl"} storyId={story.id} />
        <CaretRight
          size={16}
          weight="bold"
          aria-hidden="true"
          className="story-card__headline-icon"
        />
      </HeadingTag>

      {story.summary?.trim() && (
        <p className={useSplit ? "lead-summary" : "lead-story__summary"}>{story.summary}</p>
      )}
      {!story.summary?.trim() && (
        <p className={`${useSplit ? "lead-summary" : "lead-story__summary"} lead-story__summary--pending`}>
          {story.source.count} source{story.source.count !== 1 ? 's' : ''} covering this story
        </p>
      )}

      {verdict && (
        <p className={`coverage-verdict coverage-verdict--${verdict.tone} coverage-verdict--lead`} aria-label={`Coverage: ${verdict.label}`}>
          {verdict.label}
        </p>
      )}
    </div>
  );

  return (
    <article
      ref={cardRef}
      data-story-id={story.id}
      className={`lead-story${useSplit ? " lead-split" : ""}${twin ? " lead-story--twin" : ""} ${rank === 0 ? "anim-lead-primary" : "anim-lead-secondary"}${kbdFocused ? " story-card--kbd-focus" : ""}`}
    >
      {/* Stretched link — invisible button covers the article for click + a11y */}
      <button
        type="button"
        className="story-card__stretch-link"
        aria-label={`Open deep dive for: ${story.title}`}
        onClick={() => {
          if (cardRef.current && onStoryClick) {
            hapticLight();
            onStoryClick(story, cardRef.current.getBoundingClientRect());
          }
        }}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            hapticLight();
            onStoryClick?.(story, new DOMRect());
          }
        }}
      />

      {textContent}
    </article>
  );
}
