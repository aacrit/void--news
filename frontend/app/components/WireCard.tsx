"use client";

import { useRef } from "react";
import type { Story } from "../lib/types";
import { hapticLight } from "../lib/haptics";

/* Category → dot color mapping */
const CAT_DOT_COLORS: Record<string, string> = {
  Politics: "var(--bias-left)",
  Conflict: "#C0392B",
  Economy: "var(--accent-warm)",
  Science: "#2980B9",
  Health: "#27AE60",
  Environment: "#16A085",
  Culture: "#8E44AD",
};

interface WireCardProps {
  story: Story;
  onStoryClick?: (story: Story, rect: DOMRect) => void;
  globalIndex?: number;
  kbdFocused?: boolean;
}

/* ---------------------------------------------------------------------------
   WireCard — Zone 3: Ultra-compact headline (AP wire density)

   6px category dot + headline (Inter 600, --text-base). No summary, no Sigil.
   Hover: headline underline draws left→right.
   No individual stagger — parent does batch reveal.
   --------------------------------------------------------------------------- */

export default function WireCard({ story, onStoryClick, globalIndex, kbdFocused }: WireCardProps) {
  const cardRef = useRef<HTMLElement>(null);
  const dotColor = CAT_DOT_COLORS[story.category] || "var(--fg-muted)";

  return (
    <article
      ref={cardRef}
      data-story-index={globalIndex}
      className={`wire-card${kbdFocused ? " story-card--kbd-focus" : ""}`}
    >
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

      <span className="wire-card__dot" style={{ backgroundColor: dotColor }} aria-hidden="true" />
      <span className="wire-card__cat">{story.category}</span>
      <h3 className="wire-card__headline">{story.title}</h3>
    </article>
  );
}
