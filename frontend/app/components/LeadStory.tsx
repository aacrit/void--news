"use client";

import { useRef } from "react";
import type { Story } from "../lib/types";
import { timeAgo, whyThisStory } from "../lib/utils";
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
      role="button"
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
      className={`lead-story ${rank === 0 ? "anim-lead-primary" : "anim-lead-secondary"}${kbdFocused ? " story-card--kbd-focus" : ""}`}
    >
      {/* Category tag + time */}
      <div className="lead-story__meta">
        {rank === 0 && <span className="lead-story__badge">Top Story</span>}
        <span className="category-tag category-tag--lead">{story.category}</span>
        <span className="dot-separator" aria-hidden="true" />
        <span className="time-tag">{timeAgo(story.publishedAt)}</span>
      </div>

      {/* Hero headline */}
      <h2 className="lead-story__headline">{story.title}</h2>

      {/* Extended summary */}
      <p className="lead-story__summary">{story.summary}</p>

      {/* Bias indicator — lean-first with source count + type badge */}
      <div className="lead-story__footer">
        <Sigil data={story.sigilData} size="lg" />
        {(() => {
          const reasons = whyThisStory({
            sourceCount: story.source.count,
            coverageVelocity: story.coverageVelocity,
            divergenceScore: story.divergenceScore,
            leanSpread: story.biasSpread?.leanSpread,
            headlineRank: story.headlineRank,
          });
          return reasons.length > 0 ? (
            <span className="lead-story__why" title={reasons.join(" / ")}>
              {reasons.join(" / ")}
            </span>
          ) : null;
        })()}
      </div>
    </article>
  );
}
