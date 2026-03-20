"use client";

import type { Story } from "../lib/types";
import { timeAgo, whyThisStory } from "../lib/utils";
import Sigil from "./Sigil";

interface LeadStoryProps {
  story: Story;
  /** 0 = primary (first/most important), 1+ = secondary */
  rank?: number;
  onStoryClick?: (story: Story) => void;
}

/* ---------------------------------------------------------------------------
   LeadStory — Hero treatment for the most important story
   Larger typography, more prominent layout, bigger bias stamp.
   --------------------------------------------------------------------------- */

export default function LeadStory({ story, rank = 0, onStoryClick }: LeadStoryProps) {
  return (
    <article
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
      className={`lead-story ${rank === 0 ? "anim-lead-primary" : "anim-lead-secondary"}`}
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
