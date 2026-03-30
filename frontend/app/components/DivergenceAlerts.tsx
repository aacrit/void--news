"use client";

import { useMemo, useState } from "react";
import type { Story, LeanChip } from "../lib/types";
import { LEAN_RANGES } from "../lib/types";
import { timeAgo } from "../lib/utils";

/* ---------------------------------------------------------------------------
   DivergenceAlerts — editorial section surfacing high-divergence stories.

   Understated, newspaper-style. No accent colors. Consistent fonts.
   Positioned below lead headlines + daily brief, above medium stories.

   Alert cards: top 3 stories in the 80th+ divergence percentile (source ≥ 3).
   Blind Spot: when a lean filter is active and top stories have no matching
   sources, show a dismissible note.
   --------------------------------------------------------------------------- */

interface DivergenceAlertsProps {
  stories: Story[];
  activeLean: LeanChip;
  onStoryClick: (story: Story, rect: DOMRect) => void;
}

export default function DivergenceAlerts({
  stories,
  activeLean,
  onStoryClick,
}: DivergenceAlertsProps) {
  const [blindSpotDismissed, setBlindSpotDismissed] = useState(false);

  /* ---- Compute p80 divergence threshold ---- */
  const alertStories = useMemo(() => {
    const eligible = stories.filter((s) => s.source.count >= 3 && s.divergenceScore > 0);
    if (eligible.length < 3) return [];

    const sorted = [...eligible].sort((a, b) => a.divergenceScore - b.divergenceScore);
    const p80idx = Math.min(Math.ceil(sorted.length * 0.8) - 1, sorted.length - 1);
    const p80 = sorted[p80idx]?.divergenceScore ?? 0;

    return eligible
      .filter((s) => s.divergenceScore >= p80)
      .sort((a, b) => b.divergenceScore - a.divergenceScore)
      .slice(0, 3);
  }, [stories]);

  /* ---- Blind spot detection ---- */
  const blindSpotLabel = useMemo(() => {
    if (activeLean === "All" || blindSpotDismissed) return null;
    const leanRange = LEAN_RANGES[activeLean];
    if (!leanRange) return null;

    const top10 = stories.slice(0, 10);
    const missingCount = top10.filter(
      (s) => s.lensData.lean < leanRange.min || s.lensData.lean > leanRange.max,
    ).length;

    if (missingCount >= 3) {
      return `${missingCount} top stories have no ${activeLean} sources reporting.`;
    }
    return null;
  }, [stories, activeLean, blindSpotDismissed]);

  if (alertStories.length === 0 && !blindSpotLabel) return null;

  return (
    <section className="div-alerts" aria-label="Sources diverge on these stories">
      {/* ---- Section header — editorial rule + label ---- */}
      {alertStories.length > 0 && (
        <>
          <div className="div-alerts__rule" aria-hidden="true" />
          <h3 className="div-alerts__heading">Sources Diverge</h3>

          <div className="div-alerts__row" role="list">
            {alertStories.map((story) => {
              const insight = Array.isArray(story.deepDive?.divergence) && story.deepDive.divergence.length > 0
                ? story.deepDive.divergence[0]
                : "Sources differ significantly on framing";

              return (
                <article
                  key={story.id}
                  className="div-alert-card"
                  role="listitem"
                  tabIndex={0}
                  onClick={(e) => onStoryClick(story, e.currentTarget.getBoundingClientRect())}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      onStoryClick(story, e.currentTarget.getBoundingClientRect());
                    }
                  }}
                  aria-label={`${story.title}. ${insight}`}
                >
                  <h4 className="div-alert-card__headline">{story.title}</h4>
                  <p className="div-alert-card__insight">{
                    insight.length > 100 ? insight.slice(0, 97) + "..." : insight
                  }</p>
                  <span className="div-alert-card__meta">
                    {story.source.count} sources &middot; {timeAgo(story.publishedAt)}
                  </span>
                </article>
              );
            })}
          </div>
        </>
      )}

      {/* ---- Blind Spot — subtle editorial note ---- */}
      {blindSpotLabel && (
        <div className="div-alerts__blind-spot">
          <p className="div-alerts__blind-spot-text">
            {blindSpotLabel}
          </p>
          <button
            className="div-alerts__blind-spot-dismiss"
            onClick={() => setBlindSpotDismissed(true)}
            aria-label="Dismiss"
          >
            &times;
          </button>
        </div>
      )}
    </section>
  );
}
