"use client";

import { useRef } from "react";
import type { Story } from "../lib/types";
import { CaretRight } from "@phosphor-icons/react";
import Sigil from "./Sigil";
import { hapticLight } from "../lib/haptics";
import { BASE_PATH } from "../lib/utils";

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

  // Top-story signal now lives in the accented "Today's Top Stories" divider
  // above the feed plus position #1, so the per-card "Top Story" badge was
  // removed (2026-08-06) — it was a third redundant marker that pushed the
  // headline down. `isTop` drives only a screen-reader-only label now.
  const isTop = rank === 0 || twin;

  // Headline is <h1> for the primary lead (rank 0 OR first twin) to satisfy
  // SEO/a11y "one h1 per page." A second twin lead uses <h2>.
  const HeadingTag: "h1" | "h2" = rank === 0 ? "h1" : "h2";
  const textContent = (
    <div data-slot="text" className={useSplit ? "lead-split__text" : undefined}>
      <HeadingTag className={useSplit ? "lead-headline" : "lead-story__headline"}>
        {/* Screen-reader-only "Top story" — the visual badge was removed
            2026-08-06 (the accented divider + position #1 carry the signal),
            but the semantic cue is preserved for assistive tech. */}
        {isTop && <span className="sr-only">Top story. </span>}
        <span className={useSplit ? undefined : "lead-story__headline-text"}>{story.title}</span>
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

    </div>
  );

  return (
    <article
      ref={cardRef}
      data-story-id={story.id}
      className={`lead-story${useSplit ? " lead-split" : ""}${twin ? " lead-story--twin" : ""} ${rank === 0 ? "anim-lead-primary" : "anim-lead-secondary"}${kbdFocused ? " story-card--kbd-focus" : ""}`}
    >
      {/* Stretched link — covers the article for click + a11y. Progressive
          enhancement: a real <a href> when the story is archived (crawlable,
          middle-click, copy-link); plain left-click still opens the inline Deep
          Dive via preventDefault. Archive miss falls back to the button. */}
      {story.permalink ? (
        <a
          href={`${BASE_PATH}${story.permalink}`}
          className="story-card__stretch-link"
          aria-label={`Open deep dive for: ${story.title}`}
          onClick={(e) => {
            if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
            e.preventDefault();
            hapticLight();
            onStoryClick?.(story, cardRef.current?.getBoundingClientRect() ?? new DOMRect());
          }}
          onKeyDown={(e) => {
            if (e.key === " ") {
              e.preventDefault();
              hapticLight();
              onStoryClick?.(story, cardRef.current?.getBoundingClientRect() ?? new DOMRect());
            }
          }}
        />
      ) : (
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
      )}

      {textContent}
    </article>
  );
}
