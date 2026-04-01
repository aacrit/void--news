"use client";

import type { Story } from "../lib/types";
import { timeAgo } from "../lib/utils";
import { CaretRight } from "@phosphor-icons/react";
import Sigil from "./Sigil";
import { hapticLight } from "../lib/haptics";
import { useInView } from "../lib/sharedObserver";

interface MobileStoryCardProps {
  story: Story;
  index: number;
  onStoryClick?: (story: Story, rect: DOMRect) => void;
  globalIndex?: number;
  kbdFocused?: boolean;
  /** "hero" = lead story with summary; "compact" = headline + inline Sigil only */
  variant?: "hero" | "compact";
}

/* ---------------------------------------------------------------------------
   MobileStoryCard — Space-efficient mobile card

   Hero: meta + headline (Playfair) + 2-line summary + Sigil footer (~140px)
   Compact: meta row + headline with inline Sigil (~72px)
   Saves ~60px per card vs desktop StoryCard by eliminating summary + footer.
   --------------------------------------------------------------------------- */

export default function MobileStoryCard({
  story, index, onStoryClick, globalIndex, kbdFocused, variant = "compact",
}: MobileStoryCardProps) {
  const [cardRef, visible] = useInView<HTMLElement>();

  const isHero = variant === "hero";

  return (
    <article
      ref={cardRef}
      data-story-index={globalIndex}
      className={`msc msc--${variant} anim-stagger${visible ? " anim-stagger--visible" : ""}${kbdFocused ? " story-card--kbd-focus" : ""}`}
      style={{ animationDelay: `${Math.round(30 * Math.log2(index + 2))}ms` }}
    >
      {/* Stretched link covers entire card */}
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

      {/* Meta row */}
      <div className="msc__meta">
        {isHero && <span className="msc__badge">Top Story</span>}
        <span className="category-tag">{story.category}</span>
        <span className="dot-separator" aria-hidden="true" />
        <span className="time-tag">{timeAgo(story.publishedAt)}</span>
      </div>

      {isHero ? (
        /* Hero layout: headline + summary + Sigil footer */
        <>
          <h2 className="msc__headline msc__headline--hero">{story.title}</h2>
          <p className="msc__summary">{story.summary}</p>
          {story.biasScores.framing > 40 && (
            <p className="story-card__xray-teaser" aria-label="Framing analysis available">
              <svg className="story-card__xray-icon" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><circle cx="11" cy="11" r="7"/><line x1="16" y1="16" x2="21" y2="21"/></svg>
              {story.biasScores.framing > 65 ? "High" : "Moderate"} framing
              {story.source.count > 1 ? ` · ${story.source.count} sources` : ""}
            </p>
          )}
          <div className="msc__footer">
            <Sigil data={story.sigilData} size="lg" instant />
          </div>
        </>
      ) : (
        /* Compact layout: headline with inline Sigil */
        <div className="msc__row">
          <h3 className="msc__headline msc__headline--compact">
            <span>{story.title}</span>
            <CaretRight size={12} weight="bold" aria-hidden="true" className="msc__caret" />
          </h3>
          <div className="msc__sigil">
            <Sigil data={story.sigilData} size="sm" instant />
          </div>
        </div>
      )}
    </article>
  );
}
