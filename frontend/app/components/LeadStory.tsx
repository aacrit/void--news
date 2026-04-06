"use client";

import { useRef } from "react";
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
}

/* ---------------------------------------------------------------------------
   LeadStory — Hero treatment for the most important story
   Larger typography, more prominent layout, bigger bias stamp.
   --------------------------------------------------------------------------- */

export default function LeadStory({ story, rank = 0, onStoryClick, kbdFocused }: LeadStoryProps) {
  const cardRef = useRef<HTMLElement>(null);

  return (
    <article
      ref={cardRef}
      data-story-id={story.id}
      className={`lead-story ${rank === 0 ? "anim-lead-primary" : "anim-lead-secondary"}${kbdFocused ? " story-card--kbd-focus" : ""}`}
    >
      {/* Stretched link — the invisible button covers the entire article
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
      {rank === 0 && <span className="lead-story__badge">Top Story</span>}

      {/* Hero headline + inline Sigil + caret */}
      <h2 className="lead-story__headline">
        <span className="lead-story__headline-text">{story.title}</span>
        <Sigil data={story.sigilData} size="lg" />
        <CaretRight
          size={16}
          weight="bold"
          aria-hidden="true"
          className="story-card__headline-icon"
        />
      </h2>

      {/* Extended summary */}
      <p className="lead-story__summary">{story.summary}</p>

      {/* Consensus ratio now embedded in Sigil */}
    </article>
  );
}
