"use client";

import { useRef, useEffect, useState, type RefObject } from "react";
import type { Story, EditionMeta } from "../lib/types";
import type { DailyBriefState } from "./DailyBrief";
import LeadStory from "./LeadStory";
import DigestRow from "./DigestRow";
import WireCard from "./WireCard";
import SkyboxBanner, { OnAirBand } from "./SkyboxBanner";
import LogoWordmark from "./LogoWordmark";

interface DesktopFeedProps {
  stories: Story[];
  dailyBriefState: DailyBriefState;
  onStoryClick: (story: Story, rect: DOMRect) => void;
  filterKey: string;
  visibleCount: number;
  hasMore: boolean;
  sentinelRef: RefObject<HTMLDivElement | null>;
  loadMoreStories: () => void;
  kbdFocusIndex: number;
  editionMeta: EditionMeta;
}

/* ---------------------------------------------------------------------------
   DesktopFeed — Three-zone broadsheet layout (experimental v2)

   Zone 1 (Lead): 2fr|1fr asymmetric, stories 0-1
   Zone 2 (Digest): Headline-only rows with colored left border, stories 2-7
   Zone 3 (Wire): 4-5 col ultra-compact grid, stories 8+
   SkyboxBanner: 40px collapsed brief above Zone 1
   --------------------------------------------------------------------------- */

export default function DesktopFeed({
  stories,
  dailyBriefState,
  onStoryClick,
  filterKey,
  visibleCount,
  hasMore,
  sentinelRef,
  loadMoreStories,
  kbdFocusIndex,
  editionMeta,
}: DesktopFeedProps) {
  const leadStories = stories.slice(0, 2);
  const digestStories = stories.slice(2, 8);
  const wireStories = stories.slice(8);
  const visibleWire = wireStories.slice(0, visibleCount);

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

      {/* OnAir Band — standalone broadcast strip */}
      <OnAirBand state={dailyBriefState} edition={editionMeta.slug} />

      {/* Zone 1: Broadsheet Lead — asymmetric 2fr | 1fr */}
      {leadStories.length > 0 && (
        <section aria-label="Lead stories" className="df-lead anim-broadsheet-unfold">
          {leadStories.map((story, i) => (
            <div key={story.id} className={`df-lead__col df-lead__col--${i === 0 ? "primary" : "secondary"}`} data-story-index={i}>
              <LeadStory story={story} rank={i} onStoryClick={onStoryClick} kbdFocused={kbdFocusIndex === i} />
            </div>
          ))}
        </section>
      )}

      {/* Zone 2: Digest — headline-only rows */}
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

      {/* Zone 3: Wire — ultra-compact grid */}
      {wireStories.length > 0 && (
        <>
          <section
            ref={wireRef}
            aria-label="More stories"
            className={`df-wire${wireVisible ? " df-wire--visible" : ""}`}
          >
            {visibleWire.map((story, idx) => {
              const gi = leadStories.length + digestStories.length + idx;
              return (
                <WireCard
                  key={story.id}
                  story={story}
                  onStoryClick={onStoryClick}
                  globalIndex={gi}
                  kbdFocused={kbdFocusIndex === gi}
                />
              );
            })}
          </section>

          {hasMore && (
            <div className="feed-continuation" ref={sentinelRef}>
              <div className="feed-continuation__fade" aria-hidden="true" />
              <button
                className="feed-continuation__link"
                onClick={loadMoreStories}
                aria-label="Show more stories"
              >
                Continue reading
              </button>
            </div>
          )}
        </>
      )}

      {/* Edition footer */}
      {stories.length > 0 && (
        <div className="edition-line">
          <span className="edition-meta">
            {editionMeta.label} Edition / {stories.length} stories
          </span>
          <LogoWordmark height={14} />
        </div>
      )}
    </div>
  );
}
