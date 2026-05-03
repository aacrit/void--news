"use client";

import { useState } from "react";
import type { Story } from "../lib/types";
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
  /** og:image for the rank-0 hero — full-bleed 4:5 above headline. Hero only. */
  imageUrl?: string | null;
}

/* ---------------------------------------------------------------------------
   MobileStoryCard — Space-efficient mobile card

   Hero: full-bleed 4:5 image + headline (Playfair) + xl Sigil (72px) + summary
   Compact: headline + inline sm Sigil (40px) + (optional) category row
   Phase 3 redesign: Sigil promoted as primary bias indicator (mixed hierarchy).
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
        /* Hero layout: full-bleed 4:5 image + headline + xl Sigil (72px, Phase 3) + summary.
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
            <Sigil data={story.sigilData} size="xl" instant />
          </h2>
          {story.summary?.trim() && <p className="msc__summary">{story.summary}</p>}
          {!story.summary?.trim() && (
            <p className="msc__summary msc__summary--pending">
              {story.source.count} source{story.source.count !== 1 ? 's' : ''} covering this story
            </p>
          )}
        </>
      ) : (
        /* Compact layout: headline + inline sm Sigil (40px) + (optional) category row.
           Phase 3: Sigil now sits inline with the headline as the primary
           bias signal. The lean-dot row only renders when needed:
             - story.sigilData.unscored (need explicit "unscored" label since
               the Sigil renders gray and the absence of color carries no signal)
             - story.category present (so the row has companion content) */
        <>
          <h3 className="msc__headline msc__headline--compact">
            <span>{story.title}</span>
            <Sigil data={story.sigilData} size="sm" instant />
          </h3>
          {(story.sigilData.unscored || story.category) && (
            <div className="msc__sigil-row">
              {story.sigilData.unscored && (
                <>
                  <span
                    className="msc__lean-dot"
                    style={{ "--lean-dot-color": undefined } as React.CSSProperties}
                    aria-hidden="true"
                  />
                  <span className="msc__lean-label">unscored</span>
                </>
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
