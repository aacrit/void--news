"use client";

import type { Story } from "../lib/types";
import { CaretRight } from "@phosphor-icons/react";
import Sigil from "./Sigil";
import { hapticLight } from "../lib/haptics";
import { useInView } from "../lib/sharedObserver";
import { getLeanColor, tiltLabel } from "../lib/biasColors";

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
      data-story-id={story.id}
      className={`msc msc--${variant}${isHero ? " anim-cold-open-hero" : " anim-stagger"}${!isHero && visible ? " anim-stagger--visible" : ""}${kbdFocused ? " story-card--kbd-focus" : ""}`}
      style={{ animationDelay: isHero ? "0ms" : `${Math.min(index * 40, 200)}ms` }}
    >
      {/* Stretched link covers entire card */}
      <button
        type="button"
        className="story-card__stretch-link"
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

      {isHero && <span className="msc__badge">Top Story</span>}

      {isHero ? (
        /* Hero layout: headline + inline Sigil + caret */
        <>
          <h2 className="msc__headline msc__headline--hero">
            <span>{story.title}</span>
            <Sigil data={story.sigilData} size="lg" instant />
            <CaretRight size={14} weight="bold" aria-hidden="true" className="msc__caret" />
          </h2>
          {story.summary?.trim() && <p className="msc__summary">{story.summary}</p>}
          {!story.summary?.trim() && (
            <p className="msc__summary msc__summary--pending">
              {story.source.count} source{story.source.count !== 1 ? 's' : ''} covering this story
            </p>
          )}
        </>
      ) : (
        /* Compact layout: headline + lean dot row beneath */
        <>
          <h3 className="msc__headline msc__headline--compact">
            <span>{story.title}</span>
            <CaretRight size={12} weight="bold" aria-hidden="true" className="msc__caret" />
          </h3>
          <div className="msc__sigil-row">
            <span
              className="msc__lean-dot"
              style={{ "--lean-dot-color": story.sigilData.unscored ? undefined : getLeanColor(story.sigilData.politicalLean) } as React.CSSProperties}
              aria-hidden="true"
            />
            <span className="msc__lean-label">{story.sigilData.unscored ? "unscored" : tiltLabel(story.sigilData.politicalLean).toLowerCase().replace(" tilt", "")}</span>
            {story.category && <span className="msc__cat">{story.category}</span>}
            <span className="msc__cat">{story.source.count} sources</span>
          </div>
          {story.summary?.trim() && <p className="msc__summary msc__summary--compact">{story.summary}</p>}
        </>
      )}
    </article>
  );
}
