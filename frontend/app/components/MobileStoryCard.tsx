"use client";

import { useState } from "react";
import type { Story } from "../lib/types";
import Sigil from "./Sigil";
import { hapticLight } from "../lib/haptics";
import { useInView } from "../lib/sharedObserver";
import { getLeanColor } from "../lib/biasColors";

interface MobileStoryCardProps {
  story: Story;
  index: number;
  onStoryClick?: (story: Story, rect: DOMRect) => void;
  globalIndex?: number;
  kbdFocused?: boolean;
  /** "hero" = lead story with summary; "compact" = headline + inline Sigil only */
  variant?: "hero" | "compact";
  /** og:image for the rank-0 hero — full-bleed 4:5 above headline. Hero only. */
  imageUrl?: string | null;
}

/* ---------------------------------------------------------------------------
   MobileStoryCard — Space-efficient mobile card

   Hero: meta + headline (Playfair) + 2-line summary + Sigil footer (~140px)
   Compact: meta row + headline with inline Sigil (~72px)
   Saves ~60px per card vs desktop StoryCard by eliminating summary + footer.
   --------------------------------------------------------------------------- */

export default function MobileStoryCard({
  story, index, onStoryClick, globalIndex, kbdFocused, variant = "compact", imageUrl,
}: MobileStoryCardProps) {
  const [cardRef, visible] = useInView<HTMLElement>();
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgError, setImgError] = useState(false);

  const isHero = variant === "hero";
  const showImage = isHero && imageUrl && !imgError;

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

      {isHero ? (
        /* Hero layout: full-bleed 4:5 image + headline + Sigil + summary.
           Image is the cinematic anchor that flips perception from
           "RSS feed" to "premium newspaper". Per CEO scope lock 2026-04-29:
           lead-only imagery on mobile (ranks 1+ stay text-only). */
        <>
          {showImage && (
            <div className={`msc__hero-image${imgLoaded ? " msc__hero-image--loaded" : ""}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={imageUrl!}
                alt=""
                className="msc__hero-image__img"
                loading="eager"
                fetchPriority="high"
                decoding="async"
                onLoad={() => setImgLoaded(true)}
                onError={() => setImgError(true)}
              />
            </div>
          )}
          <h2 className="msc__headline msc__headline--hero">
            <span>{story.title}</span>
            <Sigil data={story.sigilData} size="lg" instant />
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
          </h3>
          {/* Skip the entire row when it would render as just an orphaned
              8px dot (scored cluster with no category). With no companion
              text/pill, the dot looks like a CSS bug. */}
          {(story.sigilData.unscored || story.category) && (
            <div className="msc__sigil-row">
              <span
                className="msc__lean-dot"
                style={{ "--lean-dot-color": story.sigilData.unscored ? undefined : getLeanColor(story.sigilData.politicalLean) } as React.CSSProperties}
                aria-hidden="true"
              />
              {/* Lean text removed when scored — the dot color already encodes lean.
                  Only render the explicit label when unscored, where the absence
                  of color carries no signal. Per feedback_bias_indicator_priorities. */}
              {story.sigilData.unscored && (
                <span className="msc__lean-label">unscored</span>
              )}
              {story.category && <span className="msc__cat">{story.category}</span>}
            </div>
          )}
          {story.summary?.trim() && <p className="msc__summary msc__summary--compact">{story.summary}</p>}
        </>
      )}
    </article>
  );
}
