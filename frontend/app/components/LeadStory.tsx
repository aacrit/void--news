"use client";

import { useRef, useState } from "react";
import type { Story } from "../lib/types";
import { CaretRight } from "@phosphor-icons/react";
import Sigil from "./Sigil";
import { hapticLight } from "../lib/haptics";

interface LeadStoryProps {
  story: Story;
  /** 0 = primary (first/most important), 1+ = secondary */
  rank?: number;
  onStoryClick?: (story: Story, rect: DOMRect) => void;
  /** True when this card is focused via keyboard (J/K) navigation */
  kbdFocused?: boolean;
  /** og:image URL for the lead story — primary (rank 0) only */
  imageUrl?: string | null;
}

/* ---------------------------------------------------------------------------
   LeadStory — Hero treatment for the most important story
   Larger typography, more prominent layout, bigger bias stamp.
   Primary (rank 0) includes a cinematic front-page photograph.
   --------------------------------------------------------------------------- */

export default function LeadStory({ story, rank = 0, onStoryClick, kbdFocused, imageUrl }: LeadStoryProps) {
  const cardRef = useRef<HTMLElement>(null);
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgError, setImgError] = useState(false);

  const showImage = rank === 0 && imageUrl && !imgError;

  return (
    <article
      ref={cardRef}
      data-story-id={story.id}
      className={`lead-story ${rank === 0 ? "anim-lead-primary" : "anim-lead-secondary"}${kbdFocused ? " story-card--kbd-focus" : ""}${showImage ? " lead-story--has-image" : ""}`}
    >
      {/* Stretched link — the invisible button covers the entire article
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
      {rank === 0 && <span className="lead-story__badge">Top Story</span>}

      {/* Front-page photograph — primary lead story only */}
      {showImage && (
        <div className="lead-story__image-wrap">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageUrl!}
            alt=""
            className={`lead-story__image${imgLoaded ? " lead-story__image--loaded" : ""}`}
            loading="eager"
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgError(true)}
          />
          <div className="lead-story__image-grade" aria-hidden="true" />
        </div>
      )}

      {/* Hero headline + inline Sigil + caret */}
      <h2 className="lead-story__headline">
        <span className="lead-story__headline-text">{story.title}</span>
        <Sigil data={story.sigilData} size="xl" storyId={story.id} />
        <CaretRight
          size={16}
          weight="bold"
          aria-hidden="true"
          className="story-card__headline-icon"
        />
      </h2>

      {/* Extended summary — hidden when empty (Gemini pending or failed) */}
      {story.summary?.trim() && <p className="lead-story__summary">{story.summary}</p>}
      {!story.summary?.trim() && (
        <p className="lead-story__summary lead-story__summary--pending">
          {story.source.count} source{story.source.count !== 1 ? 's' : ''} covering this story
        </p>
      )}

      {/* Consensus ratio now embedded in Sigil */}
    </article>
  );
}
