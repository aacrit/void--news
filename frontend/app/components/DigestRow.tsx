"use client";

import type { Story } from "../lib/types";
import { timeAgo } from "../lib/utils";
import Sigil from "./Sigil";
import { hapticLight } from "../lib/haptics";
import { useInView } from "../lib/sharedObserver";

/* Category → left-border color mapping (CSS custom properties from tokens.css) */
const CAT_COLORS: Record<string, string> = {
  Politics: "var(--cat-politics)",
  Conflict: "var(--cat-conflict)",
  Economy: "var(--accent-warm)",
  Science: "var(--cat-science)",
  Health: "var(--cat-health)",
  Environment: "var(--cat-environment)",
  Culture: "var(--cat-culture)",
};

interface DigestRowProps {
  story: Story;
  index: number;
  onStoryClick?: (story: Story, rect: DOMRect) => void;
  globalIndex?: number;
  kbdFocused?: boolean;
}

/* ---------------------------------------------------------------------------
   DigestRow — Zone 2: Headline-only row (FT/Bloomberg density)

   Colored left-border + category tag + headline (Playfair) + Sigil sm
   No summary. One horizontal line per story. ~40px per row.
   Hover: background tint only, no paper lift.
   --------------------------------------------------------------------------- */

export default function DigestRow({ story, index, onStoryClick, globalIndex, kbdFocused }: DigestRowProps) {
  const [rowRef, visible] = useInView<HTMLElement>();

  const borderColor = CAT_COLORS[story.category] || "var(--fg-muted)";

  return (
    <article
      ref={rowRef}
      data-story-index={globalIndex}
      data-story-id={story.id}
      className={`dg-row anim-typewriter${visible ? " anim-typewriter--visible" : ""}${kbdFocused ? " story-card--kbd-focus" : ""}`}
      style={{
        borderLeftColor: borderColor,
        animationDelay: `${Math.round(30 * index)}ms`,
      }}
    >
      <button
        type="button"
        className="story-card__stretch-link"
        tabIndex={0}
        aria-label={`Open deep dive for: ${story.title}`}
        onClick={() => {
          if (rowRef.current && onStoryClick) {
            hapticLight();
            onStoryClick(story, rowRef.current.getBoundingClientRect());
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

      <span className="dg-row__cat">{story.category}</span>
      <span className="dg-row__time">{timeAgo(story.publishedAt)}</span>
      <h3 className="dg-row__headline">{story.title}</h3>
      <div className="dg-row__sigil">
        <Sigil data={story.sigilData} size="sm" />
      </div>
    </article>
  );
}
