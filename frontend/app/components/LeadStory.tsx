"use client";

import { useRef } from "react";
import type { Story } from "../lib/types";
import { timeAgo } from "../lib/utils";
import Sigil from "./Sigil";
import { hapticLight } from "../lib/haptics";
import LiveUpdatesInline from "./LiveUpdatesInline";

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
   Live updates embedded inline as timestamped bullets.
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
      {/* Live badge — visual indicator when memory engine is tracking */}
      {story.isTopStory && story.liveUpdateCount != null && story.liveUpdateCount > 0 && (
        <div className="lead-story__live-badge">
          <span className="live-badge__icon" aria-hidden="true">&#9679;</span>
          <span className="live-badge__text">Live</span>
          {story.lastLiveUpdateAt && (
            <time className="live-badge__time" dateTime={story.lastLiveUpdateAt}>
              Updated {timeAgo(story.lastLiveUpdateAt)}
            </time>
          )}
          <span className="live-badge__count" aria-label={`${story.liveUpdateCount} live updates`}>
            +{story.liveUpdateCount}
          </span>
        </div>
      )}

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

      {/* Inline live updates — story-specific timestamped bullets */}
      {story.storyMemoryId && (
        <LiveUpdatesInline storyMemoryId={story.storyMemoryId} />
      )}

      {/* Bias indicator */}
      <div className="lead-story__footer">
        <Sigil data={story.sigilData} size="lg" />
      </div>
    </article>
  );
}
