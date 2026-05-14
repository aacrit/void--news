"use client";

import type { Story, EditionMeta } from "../lib/types";
import type { DailyBriefState } from "./DailyBrief";
import MobileStoryCard from "./MobileStoryCard";
import MobileBriefPill from "./MobileBriefPill";

interface MobileFeedProps {
  stories: Story[];
  dailyBriefState: DailyBriefState;
  onStoryClick: (story: Story, rect: DOMRect) => void;
  filterKey: string;
  kbdFocusIndex: number;
  editionMeta: EditionMeta;
  /** CSS class for edition switch cross-fade animation */
  transitionClass?: string;
}

/* ---------------------------------------------------------------------------
   MobileFeed — Mobile-native news feed layout (30-story cap, no pagination)

   Order (CEO 2026-05-13): Brief (collapsed pill — TL;DR + Opinion with single
   chevron) → Hero (top story, text-only) → compact cards. The brief sits
   above the hero so TL;DR, Opinion, and Top Story all land above the fold
   on every mobile resolution.
   --------------------------------------------------------------------------- */

export default function MobileFeed({
  stories,
  dailyBriefState,
  onStoryClick,
  filterKey,
  kbdFocusIndex,
  editionMeta,
  transitionClass,
}: MobileFeedProps) {
  const hero = stories[0];
  const feedCards = stories.slice(1);

  return (
    <div className={["mf", transitionClass].filter(Boolean).join(" ")} key={filterKey}>
      {/* Brief on top — TL;DR + Opinion collapsed pill. Tap chevron to expand. */}
      <MobileBriefPill state={dailyBriefState} className="anim-cold-open-pill" />

      {/* Hero story — second slot, below brief but above the wire */}
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

      {/* Feed cards — identical compact treatment for all ranks 1-29 */}
      {feedCards.length > 0 && (
        <div className="mf__cards" aria-label="Stories">
          {feedCards.map((story, idx) => {
            const gi = idx + 1;
            return (
              <MobileStoryCard
                key={story.id}
                story={story}
                index={gi}
                variant="compact"
                onStoryClick={onStoryClick}
                globalIndex={gi}
                kbdFocused={kbdFocusIndex === gi}
              />
            );
          })}
        </div>
      )}

    </div>
  );
}
