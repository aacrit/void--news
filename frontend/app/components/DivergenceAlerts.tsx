"use client";

import { useMemo, useState } from "react";
import type { Story } from "../lib/types";
import type { LeanChip } from "./FilterBar";
import { LEAN_RANGES } from "./FilterBar";

/* ---------------------------------------------------------------------------
   DivergenceAlerts — surfacing high-divergence stories + blind-spot banner.

   Alert cards: top 3 stories in the 80th+ divergence percentile (source ≥ 3).
   Blind Spot: when a lean filter is active and top stories have no matching
   sources, show a dismissible banner.
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
    const p80idx = Math.floor(sorted.length * 0.8);
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

    // Check top 10 stories for missing lean coverage
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
    <div className="div-alerts" role="region" aria-label="Narrative divergence alerts">
      {/* ---- Blind Spot Banner ---- */}
      {blindSpotLabel && (
        <div className="div-alerts__blind-spot" role="alert" aria-live="polite">
          <div className="div-alerts__blind-spot-content">
            <span className="div-alerts__blind-spot-icon" aria-hidden="true">&#9651;</span>
            <p className="div-alerts__blind-spot-text text-data">
              <strong>Blind Spot:</strong>{" "}
              {blindSpotLabel}{" "}
              <span className="div-alerts__blind-spot-hint">
                Explore counter-takes?
              </span>
            </p>
          </div>
          <button
            className="div-alerts__blind-spot-dismiss"
            onClick={() => setBlindSpotDismissed(true)}
            aria-label="Dismiss blind spot alert"
          >
            &#x2715;
          </button>
        </div>
      )}

      {/* ---- Alert cards ---- */}
      {alertStories.length > 0 && (
        <>
          <div className="div-alerts__header">
            <span className="div-alerts__header-label text-data">Narratives Diverge</span>
          </div>
          <div className="div-alerts__scroll-row" role="list">
            {alertStories.map((story) => {
              const divergenceInsight = Array.isArray(story.deepDive?.divergence) && story.deepDive.divergence.length > 0
                ? story.deepDive.divergence[0]
                : "Sources differ significantly on framing";

              return (
                <article
                  key={story.id}
                  className="div-alert-card"
                  role="listitem"
                  onClick={(e) => {
                    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
                    onStoryClick(story, rect);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
                      onStoryClick(story, rect);
                    }
                  }}
                  tabIndex={0}
                  aria-label={`High divergence story: ${story.title}. ${divergenceInsight}`}
                >
                  <div className="div-alert-card__accent" aria-hidden="true" />

                  <header className="div-alert-card__header">
                    <span className="div-alert-card__label text-data">Divergent</span>
                    <span className="div-alert-card__score text-data">
                      {Math.round(story.divergenceScore)}
                    </span>
                  </header>

                  <h3 className="div-alert-card__headline">
                    {story.title}
                  </h3>

                  <p className="div-alert-card__insight text-data">
                    {divergenceInsight.length > 120
                      ? divergenceInsight.slice(0, 117) + "..."
                      : divergenceInsight}
                  </p>

                  <div className="div-alert-card__footer">
                    <span className="div-alert-card__source-count text-data">
                      {story.source.count} sources
                    </span>
                    <span className="div-alert-card__cta text-data">
                      Deep Dive &#8594;
                    </span>
                  </div>
                </article>
              );
            })}
          </div>
        </>
      )}
    </div>
  );
}
