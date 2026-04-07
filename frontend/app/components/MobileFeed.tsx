"use client";

import type { RefObject } from "react";
import type { Story, EditionMeta } from "../lib/types";
import type { DailyBriefState } from "./DailyBrief";
import MobileStoryCard from "./MobileStoryCard";
import MobileBriefPill from "./MobileBriefPill";
import LogoWordmark from "./LogoWordmark";

interface MobileFeedProps {
  stories: Story[];
  dailyBriefState: DailyBriefState;
  onStoryClick: (story: Story, rect: DOMRect) => void;
  filterKey: string;
  visibleCount: number;
  hasMore: boolean;
  sentinelRef: RefObject<HTMLDivElement | null>;
  kbdFocusIndex: number;
  editionMeta: EditionMeta;
  /** CSS class for edition switch cross-fade animation */
  transitionClass?: string;
}

/* ---------------------------------------------------------------------------
   MobileFeed — Mobile-native news feed layout

   Renders: Brief (skybox) → Hero (story #1) → Compact cards (story #2+)
   Brief promoted above hero like desktop SkyboxBanner.
   Shows 5+ stories above the fold on iPhone 15 (390×844).
   Infinite scroll via sentinel. Pull-to-refresh handled by parent.
   --------------------------------------------------------------------------- */

export default function MobileFeed({
  stories,
  dailyBriefState,
  onStoryClick,
  filterKey,
  visibleCount,
  hasMore,
  sentinelRef,
  kbdFocusIndex,
  editionMeta,
  transitionClass,
}: MobileFeedProps) {
  const hero = stories[0];
  const rest = stories.slice(1);
  const visibleRest = rest.slice(0, visibleCount);

  return (
    <div className={["mf", transitionClass].filter(Boolean).join(" ")} key={filterKey}>
      {/* Hero story — Scanner sees headlines first */}
      {hero && (
        <MobileStoryCard
          story={hero}
          index={0}
          variant="hero"
          onStoryClick={onStoryClick}
          globalIndex={0}
          kbdFocused={kbdFocusIndex === 0}
        />
      )}

      {/* Brief — below hero, first 2 sentences visible */}
      <MobileBriefPill state={dailyBriefState} className="anim-cold-open-pill" />

      {/* Compact story cards */}
      <div className="mf__cards" aria-label="Stories">
        {visibleRest.map((story, idx) => (
          <MobileStoryCard
            key={story.id}
            story={story}
            index={idx + 1}
            variant="compact"
            onStoryClick={onStoryClick}
            globalIndex={idx + 1}
            kbdFocused={kbdFocusIndex === idx + 1}
          />
        ))}
      </div>

      {/* Infinite scroll sentinel */}
      {hasMore && (
        <div className="mf__sentinel" ref={sentinelRef}>
          <div className="mf__sentinel-fade" aria-hidden="true" />
        </div>
      )}

      {/* Edition footer */}
      {stories.length > 0 && (
        <div className="mf__footer">
          <span className="edition-meta">
            {stories.length} stories
          </span>
          <LogoWordmark height={12} />
        </div>
      )}
    </div>
  );
}
