"use client";

import type { Story, EditionMeta } from "../lib/types";
import type { DailyBriefState } from "./DailyBrief";
import MobileStoryCard from "./MobileStoryCard";
import MobileBriefPill from "./MobileBriefPill";
import LogoWordmark from "./LogoWordmark";

/* ---------------------------------------------------------------------------
   Editorial feed constants — mirrored from HomeContent for zone boundaries.
   Mobile editorial intent: hero(1) + edition cards(~10) + wire compact(rest).
   --------------------------------------------------------------------------- */

/** Wire zone starts at index 12 (matching desktop Zone 3). */
const MOBILE_WIRE_START = 12;

interface MobileFeedProps {
  stories: Story[];
  dailyBriefState: DailyBriefState;
  onStoryClick: (story: Story, rect: DOMRect) => void;
  filterKey: string;
  kbdFocusIndex: number;
  editionMeta: EditionMeta;
  /** IDs of high-divergence stories injected at tail positions */
  divergenceTailIds: Set<string>;
  /** CSS class for edition switch cross-fade animation */
  transitionClass?: string;
}

/* ---------------------------------------------------------------------------
   MobileFeed — Mobile-native news feed layout (30-story cap, no pagination)

   Renders: Hero (story #1) → Brief → Edition cards (stories 2-11) →
            Wire compact (stories 12-29, with divergence labels on tail)
   All 30 stories render immediately. No infinite scroll, no sentinel.
   --------------------------------------------------------------------------- */

export default function MobileFeed({
  stories,
  dailyBriefState,
  onStoryClick,
  filterKey,
  kbdFocusIndex,
  editionMeta,
  divergenceTailIds,
  transitionClass,
}: MobileFeedProps) {
  const hero = stories[0];
  const editionCards = stories.slice(1, MOBILE_WIRE_START);
  const wireCards = stories.slice(MOBILE_WIRE_START);

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

      {/* Edition cards — full compact treatment with Sigil */}
      {editionCards.length > 0 && (
        <div className="mf__cards" aria-label="Top stories">
          {editionCards.map((story, idx) => (
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
      )}

      {/* Wire zone — ultra-compact, headline-only density */}
      {wireCards.length > 0 && (
        <div className="mf__wire" aria-label="Wire stories">
          {wireCards.map((story, idx) => {
            const gi = MOBILE_WIRE_START + idx;
            const isDivergent = divergenceTailIds.has(story.id);
            return (
              <div key={story.id} className={isDivergent ? "mf__wire-item--divergent" : undefined}>
                {isDivergent && (
                  <span className="wire-divergence-label" aria-label="High source disagreement">Sources Disagree</span>
                )}
                <MobileStoryCard
                  story={story}
                  index={gi}
                  variant="compact"
                  onStoryClick={onStoryClick}
                  globalIndex={gi}
                  kbdFocused={kbdFocusIndex === gi}
                />
              </div>
            );
          })}
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
