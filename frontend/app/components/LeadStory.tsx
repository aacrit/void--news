"use client";

import type { Story } from "../lib/types";
import { timeAgo } from "../lib/utils";
import Sigil from "./Sigil";

interface LeadStoryProps {
  story: Story;
  onStoryClick?: (story: Story) => void;
}

/* ---------------------------------------------------------------------------
   LeadStory — Hero treatment for the most important story
   Larger typography, more prominent layout, bigger bias stamp.
   --------------------------------------------------------------------------- */

export default function LeadStory({ story, onStoryClick }: LeadStoryProps) {
  return (
    <article
      className="lead-story anim-fade-in-up"
      role="button"
      tabIndex={0}
      aria-label={`Open deep dive for: ${story.title}`}
      onClick={() => onStoryClick?.(story)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onStoryClick?.(story);
        }
      }}
    >
      {/* Category tag + time */}
      <div className="lead-story__meta">
        <span className="category-tag category-tag--lead">{story.category}</span>
        <span className="dot-separator" aria-hidden="true" />
        <span className="time-tag">{timeAgo(story.publishedAt)}</span>
      </div>

      {/* Hero headline */}
      <h2 className="lead-story__headline">{story.title}</h2>

      {/* Extended summary */}
      <p className="lead-story__summary">{story.summary}</p>

      {/* Source count + large bias stamp */}
      <div className="lead-story__footer">
        <span className="source-count source-count--lead">
          {story.source.count} sources
        </span>
        <Sigil data={story.sigilData} size="lg" />
      </div>
    </article>
  );
}
