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
  // v3 (2026-05-14): twin top stories on mobile. Ranks 0 and 1 are both
  // rendered as hero cards, stacked vertically. Both wear the "Top Story"
  // badge — they're co-equal leads. Compact feed cards (ranks 2+) follow.
  const twinLeads = stories.slice(0, 2);
  const feedCards = stories.slice(2);

  return (
    <div className={["mf", transitionClass].filter(Boolean).join(" ")} key={filterKey}>
      {/* Brief on top — TL;DR + Opinion collapsed pill. Tap chevron to expand. */}
      <MobileBriefPill state={dailyBriefState} className="anim-cold-open-pill" />

      {/* Twin top stories — both labeled Top Story, stacked vertically.
          A hairline divider between them in mf__twin-divider styles. */}
      {twinLeads.length > 0 && (
        <div className="mf__twin-leads">
          {twinLeads.map((story, idx) => (
            <MobileStoryCard
              key={story.id}
              story={story}
              index={idx}
              variant="hero"
              twin={twinLeads.length === 2}
              onStoryClick={onStoryClick}
              globalIndex={idx}
              kbdFocused={kbdFocusIndex === idx}
            />
          ))}
        </div>
      )}

      {/* Feed cards — compact treatment for ranks 2+ */}
      {feedCards.length > 0 && (
        <div className="mf__cards" aria-label="Stories">
          {feedCards.map((story, idx) => {
            const gi = idx + 2;
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
