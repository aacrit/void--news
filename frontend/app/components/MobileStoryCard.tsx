"use client";

import type { Story } from "../lib/types";
import { CaretRight } from "@phosphor-icons/react";
import Sigil from "./Sigil";
import ConsensusBadge from "./ConsensusBadge";
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
      data-story-id={story.id}
      className={`msc msc--${variant}${isHero ? " anim-cold-open-hero" : " anim-stagger"}${!isHero && visible ? " anim-stagger--visible" : ""}${kbdFocused ? " story-card--kbd-focus" : ""}`}
      style={{ animationDelay: isHero ? "0ms" : `${Math.min(index * 40, 200)}ms` }}
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

      {isHero && <span className="msc__badge">Top Story</span>}

      {isHero ? (
        /* Hero layout: headline + inline Sigil + caret */
        <>
          <h2 className="msc__headline msc__headline--hero">
            <span>{story.title}</span>
            <Sigil data={story.sigilData} size="sm" instant />
            {story.deepDive?.claimConsensus && (
              <ConsensusBadge
                ratio={story.deepDive.claimConsensus.consensus_ratio}
                disputed={story.deepDive.claimConsensus.disputed}
                total={story.deepDive.claimConsensus.total_claims}
                corroborated={story.deepDive.claimConsensus.corroborated}
              />
            )}
            <CaretRight size={14} weight="bold" aria-hidden="true" className="msc__caret" />
          </h2>
          <p className="msc__summary">{story.summary}</p>
          {/* [V05] ConsensusBadge in data row, hero variant only */}
          {story.deepDive?.claimConsensus && (
            <ConsensusBadge
              ratio={story.deepDive.claimConsensus.consensus_ratio}
              disputed={story.deepDive.claimConsensus.disputed}
              total={story.deepDive.claimConsensus.total_claims}
              corroborated={story.deepDive.claimConsensus.corroborated}
            />
          )}
        </>
      ) : (
        /* Compact layout: headline + inline Sigil + caret — badge hidden */
        <>
          <h3 className="msc__headline msc__headline--compact">
            <span>{story.title}</span>
            <Sigil data={story.sigilData} size="sm" instant />
            {story.deepDive?.claimConsensus && (
              <ConsensusBadge
                ratio={story.deepDive.claimConsensus.consensus_ratio}
                disputed={story.deepDive.claimConsensus.disputed}
                total={story.deepDive.claimConsensus.total_claims}
                corroborated={story.deepDive.claimConsensus.corroborated}
              />
            )}
            <CaretRight size={12} weight="bold" aria-hidden="true" className="msc__caret" />
          </h3>
          {story.summary && <p className="msc__summary msc__summary--compact">{story.summary}</p>}
        </>
      )}
    </article>
  );
}
