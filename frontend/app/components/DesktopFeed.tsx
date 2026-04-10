"use client";

import { useRef, useEffect, useState } from "react";
import type { Story, EditionMeta } from "../lib/types";
import type { DailyBriefState } from "./DailyBrief";
import LeadStory from "./LeadStory";
import DigestRow from "./DigestRow";
import WireCard from "./WireCard";
import SkyboxBanner from "./SkyboxBanner";
import LogoWordmark from "./LogoWordmark";

/* ---------------------------------------------------------------------------
   Editorial feed constants — mirrored from HomeContent.
   --------------------------------------------------------------------------- */
const ZONE_LEAD_END = 2;
const ZONE_EDITION_END = 12;

interface DesktopFeedProps {
  stories: Story[];
  dailyBriefState: DailyBriefState;
  onStoryClick: (story: Story, rect: DOMRect) => void;
  filterKey: string;
  kbdFocusIndex: number;
  editionMeta: EditionMeta;
  /** IDs of high-divergence stories injected at tail positions */
  divergenceTailIds?: Set<string>;
}

/* ---------------------------------------------------------------------------
   DesktopFeed — Three-zone broadsheet layout (30-story cap, no pagination)

   Zone 1 (Lead): 2fr|1fr asymmetric, stories 0-1
   Zone 2 (Digest): Headline-only rows with colored left border, stories 2-11
   Zone 3 (Wire): 4-5 col ultra-compact grid, stories 12-29
   SkyboxBanner: 40px collapsed brief above Zone 1
   --------------------------------------------------------------------------- */

export default function DesktopFeed({
  stories,
  dailyBriefState,
  onStoryClick,
  filterKey,
  kbdFocusIndex,
  editionMeta,
  divergenceTailIds = new Set(),
}: DesktopFeedProps) {
  const leadStories = stories.slice(0, ZONE_LEAD_END);
  const digestStories = stories.slice(ZONE_LEAD_END, ZONE_EDITION_END);
  const wireStories = stories.slice(ZONE_EDITION_END);

  // Wire zone batch reveal — entire grid fades in as a unit
  const wireRef = useRef<HTMLElement>(null);
  const [wireVisible, setWireVisible] = useState(false);
  useEffect(() => {
    const el = wireRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight + 200) { setWireVisible(true); return; }
    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) { setWireVisible(true); observer.disconnect(); } },
      { threshold: 0.05 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return (
    <div className="df" key={filterKey}>
      {/* Skybox Banner — editorial brief (TL;DR + Opinion) */}
      <SkyboxBanner state={dailyBriefState} />

      {/* Zone 1: Broadsheet Lead — asymmetric 2fr | 1fr (indexes 0-1) */}
      {leadStories.length > 0 && (
        <section aria-label="Lead stories" className="df-lead">
          {leadStories.map((story, i) => (
            <div key={story.id} className={`df-lead__col df-lead__col--${i === 0 ? "primary" : "secondary"}`} data-story-index={i}>
              <LeadStory story={story} rank={i} onStoryClick={onStoryClick} kbdFocused={kbdFocusIndex === i} />
            </div>
          ))}
        </section>
      )}

      {/* Zone 2: Digest — headline-only rows (indexes 2-11) */}
      {digestStories.length > 0 && (
        <section aria-label="Top stories" className="df-digest">
          {digestStories.map((story, idx) => {
            const gi = leadStories.length + idx;
            return (
              <DigestRow
                key={story.id}
                story={story}
                index={idx}
                onStoryClick={onStoryClick}
                globalIndex={gi}
                kbdFocused={kbdFocusIndex === gi}
              />
            );
          })}
        </section>
      )}

      {/* Zone 3: Wire — ultra-compact grid (indexes 12-29) */}
      {wireStories.length > 0 && (
        <section
          ref={wireRef}
          aria-label="Wire stories"
          className={`df-wire${wireVisible ? " df-wire--visible" : ""}`}
        >
          {wireStories.map((story, idx) => {
            const gi = leadStories.length + digestStories.length + idx;
            const isDivergent = divergenceTailIds.has(story.id);
            return (
              <div key={story.id} className={isDivergent ? "df-wire__item--divergent" : undefined}>
                {isDivergent && (
                  <span className="wire-divergence-label" aria-label="High source disagreement">Sources Disagree</span>
                )}
                <WireCard
                  story={story}
                  onStoryClick={onStoryClick}
                  globalIndex={gi}
                  kbdFocused={kbdFocusIndex === gi}
                />
              </div>
            );
          })}
        </section>
      )}

      {/* Edition footer */}
      {stories.length > 0 && (
        <div className="edition-line">
          <span className="edition-meta">
            {stories.length} stories
          </span>
          <LogoWordmark height={14} />
        </div>
      )}
    </div>
  );
}
