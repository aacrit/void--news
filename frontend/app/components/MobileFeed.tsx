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
  /** "main" = full layout (Brief Pill + twin heroes + compact cards).
   *  "overflow" = compact-only (no Brief Pill duplicate, no hero treatment).
   *  Used by the inline World section so it doesn't re-render the daily-brief
   *  pill or treat the first two World stories as "Top Story" leads. */
  variant?: "main" | "overflow";
}

/* ---------------------------------------------------------------------------
   MobileFeed — Mobile-native news feed layout (30-story cap, no pagination)

   Order (CEO 2026-05-13): Brief (collapsed pill — TL;DR + Opinion with single
   chevron) → Hero (top story, text-only) → compact cards. The brief sits
   above the hero so TL;DR, Opinion, and Top Story all land above the fold
   on every mobile resolution.

   variant="overflow" (CEO 2026-05-15): when MobileFeed is reused below the
   World divider, skip Brief Pill + skip hero treatment. World stories are
   compact cards only — they're overflow, not leads.
   --------------------------------------------------------------------------- */

export default function MobileFeed({
  stories,
  dailyBriefState,
  onStoryClick,
  filterKey,
  kbdFocusIndex,
  editionMeta,
  transitionClass,
  variant = "main",
}: MobileFeedProps) {
  const isOverflow = variant === "overflow";
  // v3 (2026-05-14): twin top stories on mobile (main only). Overflow renders
  // ALL stories as compact cards — no leads, no hero scale.
  const twinLeads = isOverflow ? [] : stories.slice(0, 2);
  const feedCards = isOverflow ? stories : stories.slice(2);

  return (
    <div className={["mf", isOverflow ? "mf--overflow" : null, transitionClass].filter(Boolean).join(" ")} key={filterKey}>
      {/* Brief Pill — main feed only. Skipped on overflow so we don't duplicate
          the daily-brief teaser inside the inline World section. */}
      {!isOverflow && (
        <MobileBriefPill state={dailyBriefState} className="anim-cold-open-pill" />
      )}

      {/* Twin top stories — main feed only. Overflow has no leads. */}
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
