"use client";

import type { Story } from "../lib/types";
import type { FamilyInfo } from "../lib/storyFamilies";
import { CaretRight } from "@phosphor-icons/react";
import Sigil from "./Sigil";
import { hapticLight } from "../lib/haptics";
import { BASE_PATH } from "../lib/utils";
import { useInView } from "../lib/sharedObserver";

interface StoryCardProps {
  story: Story;
  index: number;
  onStoryClick?: (story: Story, rect: DOMRect) => void;
  /** Global story index for keyboard navigation — sets data-story-index attribute */
  globalIndex?: number;
  /** True when this card is focused via keyboard (J/K) navigation */
  kbdFocused?: boolean;
  /** Newspaper variant — drives type scale via layout-zones.css.
      digest = ranks 1-9 (22px Playfair); wire = ranks 10+ (14px Playfair).
      Omit for default StoryCard scale. */
  variant?: "digest" | "wire";
  /** Same-story family info — when present, the card is one of N angles
      on the same event. Renders a "Related: N angles" chip above the
      headline so readers see the connection rather than reading the
      duplicates as a clustering failure. */
  family?: FamilyInfo;
}

/* ---------------------------------------------------------------------------
   StoryCard — Newspaper-style article card
   Hover via CSS. Keyboard accessible.
   Scroll-driven stagger: IntersectionObserver triggers animation only when
   the card enters the viewport — below-fold cards don't waste their entrance.
   --------------------------------------------------------------------------- */

export default function StoryCard({ story, index, onStoryClick, globalIndex, kbdFocused, variant, family }: StoryCardProps) {
  const [cardRef, visible] = useInView<HTMLElement>();

  // Log-stagger only for the initial above-fold band (index < 10). Deep-feed
  // cards enter via IntersectionObserver as the user scrolls — an index-scaled
  // delay there (~230ms at card 50) made the feed visibly trail the thumb.
  const staggerDelay = index < 10 ? `${Math.round(40 * Math.log2(index + 2))}ms` : "0ms";

  return (
    <article
      ref={cardRef}
      data-story-index={globalIndex}
      data-story-id={story.id}
      data-variant={variant}
      data-family-id={family?.familyId}
      className={`story-card anim-stagger${visible ? " anim-stagger--visible" : ""}${kbdFocused ? " story-card--kbd-focus" : ""}${family ? " story-card--family-member" : ""}`}
      style={{ animationDelay: staggerDelay }}
    >
      {/* Stretched link — covers the entire article while preserving <article>
          semantics for screen readers. Progressive enhancement: when the story
          has been archived it renders a real <a href> (crawlable, middle-click,
          copy-link), but a plain left-click still opens the inline Deep Dive
          via preventDefault. An archive miss falls back to the button. */}
      {story.permalink ? (
        <a
          href={`${BASE_PATH}${story.permalink}`}
          className="story-card__stretch-link"
          aria-label={`Open deep dive for: ${story.title}`}
          onClick={(e) => {
            // Let modified clicks (new tab / window) fall through to the browser.
            if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
            e.preventDefault();
            hapticLight();
            onStoryClick?.(story, cardRef.current?.getBoundingClientRect() ?? new DOMRect());
          }}
          onKeyDown={(e) => {
            // Enter already fires click on an <a>; only intercept Space so it
            // opens in-app (parity with the button) instead of scrolling.
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
      {/* Family relationship chip — visible only when this card shares
          a stemmed-title-Jaccard family with another top-10 card. Tells
          the reader "this is one of N angles on the same event" rather
          than letting duplicates read as a clustering failure. */}
      {family && (
        <p className="story-card__family" aria-label={`Part of a family of ${family.size} angles on this event`}>
          <span className="story-card__family-dot" aria-hidden="true" />
          <span className="story-card__family-label">
            {family.size} angles · {family.label}
          </span>
        </p>
      )}

      {/* Headline + inline Sigil + caret */}
      <h3 className="story-card__headline">
        <span className="story-card__headline-text">{story.title}</span>
        <Sigil data={story.sigilData} size="lg" storyId={story.id} />
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

      {/* LeanCoverageBar removed from feed cards 2026-08-11 (CEO): the
          blue/green/red segmented strip appeared on only the both-wings
          stories, adding a second multicolor element to an otherwise quiet
          surface. The Sigil's divergence fan already flags contested
          coverage on every card; the full split lives in the Deep Dive
          BiasSnapshot + spectrum, where it has room to be understood. */}
    </article>
  );
}
