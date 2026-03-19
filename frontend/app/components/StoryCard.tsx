"use client";

import type { Story } from "../lib/types";
import { timeAgo } from "../lib/utils";
import { ArrowSquareOut } from "@phosphor-icons/react";
import Sigil from "./Sigil";

interface StoryCardProps {
  story: Story;
  index: number;
  onStoryClick?: (story: Story) => void;
}

/* ---------------------------------------------------------------------------
   StoryCard — Newspaper-style article card
   Hover via CSS. Keyboard accessible. Staggered entrance animation.
   --------------------------------------------------------------------------- */

export default function StoryCard({ story, index, onStoryClick }: StoryCardProps) {
  return (
    <article
      className="story-card anim-stagger"
      style={{ animationDelay: `${index * 40}ms` }}
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
      <div className="story-card__meta">
        <span className="category-tag">{story.category}</span>
        <span className="time-tag">{timeAgo(story.publishedAt)}</span>
      </div>

      {/* Headline */}
      <h3 className="story-card__headline">
        <span className="story-card__headline-text">{story.title}</span>
        <ArrowSquareOut
          size={14}
          weight="light"
          aria-hidden="true"
          className="story-card__headline-icon"
        />
      </h3>

      {/* Summary */}
      <p className="story-card__summary">{story.summary}</p>

      {/* Bias indicator — lean bar + source count + type badge */}
      <div className="story-card__footer">
        <Sigil data={story.sigilData} />
      </div>
    </article>
  );
}
