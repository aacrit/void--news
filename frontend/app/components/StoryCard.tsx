"use client";

import type { Story } from "../lib/types";
import { CaretRight } from "@phosphor-icons/react";
import Sigil from "./Sigil";
import MicroSpectrum from "./MicroSpectrum";
import { hapticLight } from "../lib/haptics";
import { useInView } from "../lib/sharedObserver";

interface StoryCardProps {
  story: Story;
  index: number;
  onStoryClick?: (story: Story, rect: DOMRect) => void;
  /** Global story index for keyboard navigation — sets data-story-index attribute */
  globalIndex?: number;
  /** True when this card is focused via keyboard (J/K) navigation */
  kbdFocused?: boolean;
}

/* ---------------------------------------------------------------------------
   StoryCard — Newspaper-style article card
   Hover via CSS. Keyboard accessible.
   Scroll-driven stagger: IntersectionObserver triggers animation only when
   the card enters the viewport — below-fold cards don't waste their entrance.
   --------------------------------------------------------------------------- */

export default function StoryCard({ story, index, onStoryClick, globalIndex, kbdFocused }: StoryCardProps) {
  const [cardRef, visible] = useInView<HTMLElement>();

  return (
    <article
      ref={cardRef}
      data-story-index={globalIndex}
      data-story-id={story.id}
      className={`story-card anim-stagger${visible ? " anim-stagger--visible" : ""}${kbdFocused ? " story-card--kbd-focus" : ""}`}
      style={{ animationDelay: `${Math.round(40 * Math.log2(index + 2))}ms` }}
    >
      {/* Stretched link — invisible button covers the entire article
          while preserving <article> semantics for screen readers */}
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
      {/* Headline + inline Sigil + caret */}
      <h3 className="story-card__headline">
        <span className="story-card__headline-text">{story.title}</span>
        <Sigil data={story.sigilData} size="lg" />
        <CaretRight
          size={14}
          weight="bold"
          aria-hidden="true"
          className="story-card__headline-icon"
        />
      </h3>

      {/* Summary — hidden when empty (Gemini pending or failed) */}
      {story.summary?.trim() && <p className="story-card__summary">{story.summary}</p>}
      {!story.summary?.trim() && (
        <p className="story-card__summary story-card__summary--pending">
          {story.source.count} source{story.source.count !== 1 ? 's' : ''} reporting
        </p>
      )}

      {/* MicroSpectrum — lean distribution bell-curve, 4+ sources only */}
      {story.sigilData.sourceCount >= 4 && (
        <div className="story-card__spectrum">
          <MicroSpectrum
            mean={story.sigilData.politicalLean}
            spread={story.sigilData.biasSpread?.leanSpread ?? 12}
            height={24}
            strokeWidth={1.3}
          />
        </div>
      )}

      {/* Consensus ratio now embedded in Sigil */}
    </article>
  );
}
