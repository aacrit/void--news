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
  /** og:image URL for the rank-0 hero — null while loading or unavailable */
  leadImageUrl?: string | null;
  /** CSS class for edition switch cross-fade animation */
  transitionClass?: string;
}

/* ---------------------------------------------------------------------------
   MobileFeed — Mobile-native news feed layout (30-story cap, no pagination)

   Renders: Hero (story #1) → Brief → all remaining stories as compact cards
   All 30 stories render immediately. No infinite scroll, no sentinel.
   --------------------------------------------------------------------------- */

export default function MobileFeed({
  stories,
  dailyBriefState,
  onStoryClick,
  filterKey,
  kbdFocusIndex,
  editionMeta,
  leadImageUrl,
  transitionClass,
}: MobileFeedProps) {
  const hero = stories[0];
  const feedCards = stories.slice(1);

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
          imageUrl={leadImageUrl}
        />
      )}

      {/* Brief — below hero, first 2 sentences visible */}
      <MobileBriefPill state={dailyBriefState} className="anim-cold-open-pill" />

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
