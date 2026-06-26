"use client";

import dynamic from "next/dynamic";
import type { Story, EditionMeta } from "../lib/types";
import type { DailyBriefState } from "./DailyBrief";
import MobileStoryCard from "./MobileStoryCard";
import MobileBriefPill from "./MobileBriefPill";

// Inline Deep Dive — expands in place inside the mobile feed (mirrors the
// desktop broadsheet). ssr:false because it does its own Supabase fetch +
// accordion measurement on mount. Reused as-is; never edited for mobile.
const InlineDeepDive = dynamic(() => import("./InlineDeepDive"), { ssr: false });

interface MobileFeedProps {
  stories: Story[];
  dailyBriefState: DailyBriefState;
  onStoryClick: (story: Story, rect: DOMRect) => void;
  filterKey: string;
  kbdFocusIndex: number;
  editionMeta: EditionMeta;
  /** The story currently expanded inline (null = none open). When set, the flat
   *  feed list is split so the InlineDeepDive block renders in that card's slot
   *  and pushes the following cards down. Mirrors the desktop broadsheet split. */
  selectedStory: Story | null;
  /** Collapse the inline block — clears the open story + restores scroll. */
  onInlineCollapse: () => void;
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

   Inline Deep Dive (mobile): tapping a card opens it IN PLACE. The flat list
   splits around the open story so the full-width <InlineDeepDive> renders in
   that card's slot and pushes later cards down (mirrors the desktop split in
   HomeContent). Two cases: the open story is one of the twin leads (the whole
   twin block is replaced by the InlineDeepDive) or a compact card (.mf__cards
   is split into a before-list and an after-list with the InlineDeepDive
   between). Each card's ORIGINAL index/globalIndex is preserved so kbd-focus +
   variant logic stay correct. The other cards recede (opacity + scale, no blur)
   via the --recede modifiers.
   --------------------------------------------------------------------------- */

export default function MobileFeed({
  stories,
  dailyBriefState,
  onStoryClick,
  filterKey,
  kbdFocusIndex,
  editionMeta,
  selectedStory,
  onInlineCollapse,
  transitionClass,
  variant = "main",
}: MobileFeedProps) {
  const isOverflow = variant === "overflow";
  // v3 (2026-05-14): twin top stories on mobile (main only). Overflow renders
  // ALL stories as compact cards — no leads, no hero scale.
  const twinLeads = isOverflow ? [] : stories.slice(0, 2);
  const feedCards = isOverflow ? stories : stories.slice(2);

  // --- Inline split bookkeeping -------------------------------------------
  // Index of the open story within `stories` (the same order both bands derive
  // from): 0/1 = twin lead, >=2 = compact card.
  const inlineActive = selectedStory != null;
  const inlineIndex = inlineActive
    ? stories.findIndex((s) => s.id === selectedStory!.id)
    : -1;
  // Open story is one of the twin leads — the whole twin block is replaced.
  const inlineInLead = !isOverflow && inlineIndex >= 0 && inlineIndex < 2;
  // Open story is a compact card — split position within `feedCards`.
  // (feedCards starts at story index 2 on main; at 0 on overflow.)
  const feedCardBaseIndex = isOverflow ? 0 : 2;
  const inlineCardSplit =
    inlineActive && inlineIndex >= feedCardBaseIndex
      ? inlineIndex - feedCardBaseIndex
      : -1;

  // Single compact-card renderer — shared by the unsplit band and both halves
  // of the split so the index-derived props (globalIndex, keyboard focus) stay
  // identical regardless of which path renders the card. `idx` is the card's
  // position within feedCards (globalIndex = idx + feedCardBaseIndex). Mirrors
  // the desktop renderGridCard(story, originalIndex).
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

  const inlineBlock = (
    <InlineDeepDive
      key={selectedStory?.id}
      story={selectedStory!}
      onCollapse={onInlineCollapse}
    />
  );

  return (
    <div className={["mf", isOverflow ? "mf--overflow" : null, transitionClass].filter(Boolean).join(" ")} key={filterKey}>
      {/* Brief Pill — main feed only. Skipped on overflow so we don't duplicate
          the daily-brief teaser inside the inline World section. */}
      {!isOverflow && (
        <MobileBriefPill state={dailyBriefState} className="anim-cold-open-pill" />
      )}

      {/* Twin top stories — main feed only. Overflow has no leads.
          Inline mode: when one of the twin leads is open, the whole twin block
          is replaced by the full-width InlineDeepDive. */}
      {inlineInLead ? (
        inlineBlock
      ) : (
        twinLeads.length > 0 && (
          <div className={`mf__twin-leads${inlineActive ? " mf__twin-leads--recede" : ""}`}>
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
        )
      )}

      {/* Feed cards — compact treatment for ranks 2+.
          Inline mode: when a compact card is open, .mf__cards is split into a
          before-list and an after-list with the InlineDeepDive between them so
          it renders full-width in that card's slot and pushes later cards down.
          The original index is preserved on each card so globalIndex + kbd
          focus math is identical to the unsplit band. */}
      {feedCards.length > 0 && (
        inlineCardSplit >= 0 ? (
          <>
            {inlineCardSplit > 0 && (
              <div className="mf__cards mf__cards--recede" aria-label="Stories">
                {feedCards.slice(0, inlineCardSplit).map((story, idx) =>
                  renderCompactCard(story, idx),
                )}
              </div>
            )}
            {inlineBlock}
            {inlineCardSplit < feedCards.length - 1 && (
              <div className="mf__cards mf__cards--recede" aria-label="Stories">
                {feedCards.slice(inlineCardSplit + 1).map((story, sIdx) =>
                  renderCompactCard(story, inlineCardSplit + 1 + sIdx),
                )}
              </div>
            )}
          </>
        ) : (
          <div className={`mf__cards${inlineActive ? " mf__cards--recede" : ""}`} aria-label="Stories">
            {feedCards.map((story, idx) => renderCompactCard(story, idx))}
          </div>
        )
      )}

    </div>
  );
}
