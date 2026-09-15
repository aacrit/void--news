"use client";

import type { Story, EditionMeta } from "../lib/types";
import type { DailyBriefState } from "./DailyBrief";
import MobileStoryCard from "./MobileStoryCard";
import MobileBriefPill from "./MobileBriefPill";

// Deep Dive is a global modal (centered card / full-screen bottom sheet) rendered
// by HomeContent, so the mobile feed no longer expands anything in place — it is
// a flat list. The former inline-split path was removed 2026-08-09.

interface MobileFeedProps {
  stories: Story[];
  dailyBriefState: DailyBriefState;
  onStoryClick: (story: Story, rect: DOMRect) => void;
  filterKey: string;
  kbdFocusIndex: number;
  editionMeta: EditionMeta;
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

   Tapping a card opens the global Deep Dive modal (owned by HomeContent); the
   feed itself stays a flat list and never splits.
   --------------------------------------------------------------------------- */

export default function MobileFeed({
  stories,
  dailyBriefState,
  onStoryClick,
  filterKey,
  kbdFocusIndex,
  editionMeta,
  variant = "main",
}: MobileFeedProps) {
  const isOverflow = variant === "overflow";
  // v3 (2026-05-14): twin top stories on mobile (main only). Overflow renders
  // ALL stories as compact cards — no leads, no hero scale.
  const twinLeads = isOverflow ? [] : stories.slice(0, 2);
  const feedCards = isOverflow ? stories : stories.slice(2);

  // feedCards starts at story index 2 on main; at 0 on overflow.
  const feedCardBaseIndex = isOverflow ? 0 : 2;

  // Single compact-card renderer. `idx` is the card's position within feedCards
  // (globalIndex = idx + feedCardBaseIndex). Mirrors the desktop
  // renderGridCard(story, originalIndex).
  const renderCompactCard = (story: Story, idx: number) => {
    const gi = idx + feedCardBaseIndex;
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
  };

  return (
    <div className={["mf", isOverflow ? "mf--overflow" : null].filter(Boolean).join(" ")} key={filterKey}>
      {/* Brief Pill — main feed only. Skipped on overflow so we don't duplicate
          the daily-brief teaser inside the inline World section. */}
      {!isOverflow && (
        <MobileBriefPill state={dailyBriefState} className="anim-cold-open-pill" />
      )}

      {/* Boundary line — marks where the brief ("about the day") ends and the
          story feed ("the day") begins. Main feed only; overflow has no brief. */}
      {!isOverflow && (
        <div className="feed-start" aria-hidden="true">Today&rsquo;s Top Stories</div>
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

      {/* Feed cards — compact treatment for ranks 2+. */}
      {feedCards.length > 0 && (
        <div className="mf__cards" aria-label="Stories">
          {feedCards.map((story, idx) => renderCompactCard(story, idx))}
        </div>
      )}

    </div>
  );
}
