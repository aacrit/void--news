"use client";

import type { Story } from "../lib/types";
import { timeAgo } from "../lib/utils";
import { CaretRight } from "@phosphor-icons/react";
import Sigil from "./Sigil";
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
      className={`story-card anim-stagger${visible ? " anim-stagger--visible" : ""}${kbdFocused ? " story-card--kbd-focus" : ""}`}
      style={{ animationDelay: `${Math.round(40 * Math.log2(index + 2))}ms` }}
    >
      {/* Stretched link — invisible button covers the entire article
          while preserving <article> semantics for screen readers */}
      <button
        type="button"
        className="story-card__stretch-link"
        tabIndex={0}
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
      {/* Headline */}
      <h3 className="story-card__headline">
        <span className="story-card__headline-text">{story.title}</span>
        <CaretRight
          size={14}
          weight="bold"
          aria-hidden="true"
          className="story-card__headline-icon"
        />
      </h3>

      {/* Summary */}
      <p className="story-card__summary">{story.summary}</p>

      {/* Divergence badge — surfaces when sources actively disagree */}
      {story.sigilData.divergenceFlag === "divergent" && story.deepDive?.divergence?.[0] && (
        <p className="story-card__divergence">
          <span className="story-card__divergence-icon" aria-hidden="true" />
          {story.deepDive.divergence[0]}
        </p>
      )}

      {/* Footer: category · time · sources (left) | Sigil (right) */}
      <div className="story-card__footer">
        <div className="story-card__byline">
          <span className="category-tag">{story.category}</span>
          <span className="dot-separator" aria-hidden="true" />
          <span className="time-tag">{timeAgo(story.publishedAt)}</span>
          <span className="dot-separator" aria-hidden="true" />
          <span className="time-tag">{story.source.count} source{story.source.count !== 1 ? "s" : ""}</span>
        </div>
        <Sigil data={story.sigilData} size="lg" />
      </div>
    </article>
  );
}
