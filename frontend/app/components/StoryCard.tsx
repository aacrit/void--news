"use client";

import { useRef, useEffect, useState } from "react";
import type { Story } from "../lib/types";
import { timeAgo, whyThisStory } from "../lib/utils";
import { CaretRight } from "@phosphor-icons/react";
import Sigil from "./Sigil";

interface StoryCardProps {
  story: Story;
  index: number;
  onStoryClick?: (story: Story, rect: DOMRect) => void;
}

/* ---------------------------------------------------------------------------
   StoryCard — Newspaper-style article card
   Hover via CSS. Keyboard accessible.
   Scroll-driven stagger: IntersectionObserver triggers animation only when
   the card enters the viewport — below-fold cards don't waste their entrance.
   --------------------------------------------------------------------------- */

export default function StoryCard({ story, index, onStoryClick }: StoryCardProps) {
  const cardRef = useRef<HTMLElement>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setVisible(true); observer.disconnect(); } },
      { threshold: 0.1 }
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <article
      ref={cardRef}
      role="button"
      tabIndex={0}
      aria-label={`Open deep dive for: ${story.title}`}
      onClick={() => {
        if (cardRef.current && onStoryClick) {
          onStoryClick(story, cardRef.current.getBoundingClientRect());
        }
      }}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          // Keyboard nav: no origin rect (panel will slide in normally)
          onStoryClick?.(story, new DOMRect());
        }
      }}
      className={`story-card anim-stagger${visible ? " anim-stagger--visible" : ""}`}
      style={{ animationDelay: `${Math.round(40 * Math.log2(index + 2))}ms` }}
    >
      {/* Category tag + time */}
      <div className="story-card__meta">
        <span className="category-tag">{story.category}</span>
        <span className="time-tag">{timeAgo(story.publishedAt)}</span>
      </div>

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

      {/* Bias indicator — lean bar + source count + type badge */}
      <div className="story-card__footer">
        <Sigil data={story.sigilData} />
        {(() => {
          const reasons = whyThisStory({
            sourceCount: story.source.count,
            coverageVelocity: story.coverageVelocity,
            divergenceScore: story.divergenceScore,
            leanSpread: story.biasSpread?.leanSpread,
            headlineRank: story.headlineRank,
          });
          return reasons.length > 0 ? (
            <span className="story-card__why" title={reasons.join(" / ")}>
              {reasons[0]}
            </span>
          ) : null;
        })()}
      </div>
    </article>
  );
}
