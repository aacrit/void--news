"use client";

import { useRef } from "react";
import type { Story } from "../lib/types";
import { hapticLight } from "../lib/haptics";

/* Category → dot color mapping (CSS custom properties from tokens.css) */
const CAT_DOT_COLORS: Record<string, string> = {
  Politics: "var(--cat-politics)",
  Conflict: "var(--cat-conflict)",
  Economy: "var(--accent-warm)",
  Science: "var(--cat-science)",
  Health: "var(--cat-health)",
  Environment: "var(--cat-environment)",
  Culture: "var(--cat-culture)",
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
      {story.sigilData?.sourceCount > 0 && (
        <span className="wire-card__sources">{story.sigilData.sourceCount}</span>
      )}
      <h3 className="wire-card__headline">{story.title}</h3>
    </article>
  );
}
