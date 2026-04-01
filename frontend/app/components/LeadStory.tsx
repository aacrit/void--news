"use client";

import { useRef } from "react";
import type { Story } from "../lib/types";
import { timeAgo } from "../lib/utils";
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
      {/* Badge (lead only) */}
      {rank === 0 && (
        <div className="lead-story__meta">
          <span className="lead-story__badge">Top Story</span>
        </div>
      )}

      {/* Hero headline */}
      <h2 className="lead-story__headline">{story.title}</h2>

      {/* Extended summary */}
      <p className="lead-story__summary">{story.summary}</p>

      {/* X-Ray teaser — surfaces when cluster framing is above neutral */}
      {story.biasScores.framing > 40 && (
        <p className="story-card__xray-teaser" aria-label="Framing analysis available">
          <svg className="story-card__xray-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="16" y1="16" x2="21" y2="21"/></svg>
          {story.biasScores.framing > 65 ? "High" : "Moderate"} framing
          {story.source.count > 1 ? ` · ${story.source.count} sources` : ""}
        </p>
      )}

      {/* Footer: category · time (left) | Sigil (right) */}
      <div className="lead-story__footer">
        <div className="lead-story__byline">
          <span className="category-tag">{story.category}</span>
          <span className="dot-separator" aria-hidden="true" />
          <span className="time-tag">{timeAgo(story.publishedAt)}</span>
        </div>
        <Sigil data={story.sigilData} size="lg" />
      </div>
    </article>
  );
}
