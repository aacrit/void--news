"use client";

import { useState, useCallback } from "react";
import Link from "next/link";
import type { Edition, Category } from "../lib/types";
import { EDITIONS } from "../lib/types";
import EditionIcon from "./EditionIcon";
import type { LeanChip } from "./FilterBar";
import type { DailyBriefState } from "./DailyBrief";
import { ScaleIcon } from "./ScaleIcon";
import { hapticMicro, hapticLight } from "../lib/haptics";
import { timeAgo } from "../lib/utils";

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

interface MobileBottomNavProps {
  activeEdition: Edition;
  activeLean: LeanChip;
  onLeanChange: (lean: LeanChip) => void;
  activeCategory: "All" | Category;
  onCategoryChange: (cat: "All" | Category) => void;
  dailyBriefState: DailyBriefState;
}

type UpwardPanel = "tldr" | "opinion" | "onair" | null;

const ALL_CATEGORIES: ("All" | Category)[] = [
  "All", "Politics", "Economy", "Science", "Health", "Culture",
];

function getEditionHref(slug: Edition): string {
  if (slug === "world") return "/";
  return `/${slug}`;
}

/* ---------------------------------------------------------------------------
   MobileBottomNav — thumb-reachable bottom bar (mobile only)

   Row: [World US India] · [L C R] · [Topics ▾] · [tl;dr] [opinion] [onair]

   Daily brief panels expand upward from the bar as bottom sheets.
   Hidden on desktop via CSS (display: none above 768px).
   --------------------------------------------------------------------------- */

export default function MobileBottomNav({
  activeEdition,
  activeLean,
  onLeanChange,
  activeCategory,
  onCategoryChange,
  dailyBriefState,
}: MobileBottomNavProps) {
  const [topicOpen, setTopicOpen] = useState(false);
  const [upwardPanel, setUpwardPanel] = useState<UpwardPanel>(null);

  const { brief, isPlaying, currentTime, duration, audioError, audioRef, handlePlayPause, handleSeek } = dailyBriefState;

  const hasAudio = !!brief?.audio_url && !audioError;
  const displayDuration = (hasAudio && brief?.audio_duration_seconds) || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;

  const handleLeanTap = (lean: LeanChip) => {
    hapticMicro();
    onLeanChange(lean === activeLean ? "All" : lean);
  };

  const handleTopicTap = (cat: "All" | Category) => {
    hapticMicro();
    onCategoryChange(cat);
    setTopicOpen(false);
  };

  const toggleUpward = useCallback((panel: UpwardPanel) => {
    hapticLight();
    setUpwardPanel((prev) => (prev === panel ? null : panel));
  }, []);

  const handleOnairTap = useCallback(() => {
    if (!hasAudio) return;
    hapticLight();
    if (upwardPanel !== "onair") {
      setUpwardPanel("onair");
      if (!isPlaying) handlePlayPause();
    } else {
      handlePlayPause();
    }
  }, [hasAudio, upwardPanel, isPlaying, handlePlayPause]);

  const paragraphs = brief?.tldr_text
    ?.split("\n")
    .map((p) => p.trim())
    .filter(Boolean) || [];

  const leanLabel = brief?.opinion_lean === "left" ? "Progressive"
    : brief?.opinion_lean === "right" ? "Conservative"
    : "Pragmatic";

  return (
    <>
      {/* Backdrop — closes panels on tap */}
      {upwardPanel && (
        <div
          className="mob-nav-backdrop"
          onClick={() => setUpwardPanel(null)}
          aria-hidden="true"
        />
      )}

      {/* Upward-expanding panels (bottom sheet style) */}
      <div className={`mob-nav-sheet${upwardPanel ? " mob-nav-sheet--open" : ""}`}>
        {/* TL;DR panel */}
        {upwardPanel === "tldr" && brief && (
          <div className="mob-nav-sheet__panel">
            <div className="mob-nav-sheet__header">
              <span className="mob-nav-sheet__title">void --tl;dr</span>
              <button className="mob-nav-sheet__close" onClick={() => setUpwardPanel(null)} aria-label="Close">&times;</button>
            </div>
            <div className="mob-nav-sheet__body daily-brief__body">
              {paragraphs.map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
          </div>
        )}

        {/* Opinion panel */}
        {upwardPanel === "opinion" && brief?.opinion_text && (
          <div className="mob-nav-sheet__panel">
            <div className="mob-nav-sheet__header">
              <span className="mob-nav-sheet__title">void --opinion</span>
              <button className="mob-nav-sheet__close" onClick={() => setUpwardPanel(null)} aria-label="Close">&times;</button>
            </div>
            <div className="mob-nav-sheet__body daily-brief__opinion">
              <p>
                {brief.opinion_text}
                {brief.opinion_lean && (
                  <span className="opinion-lean-tag"> — {leanLabel} lens</span>
                )}
              </p>
            </div>
          </div>
        )}

        {/* On Air panel */}
        {upwardPanel === "onair" && hasAudio && (
          <div className="mob-nav-sheet__panel">
            <div className="mob-nav-sheet__header">
              <span className="mob-nav-sheet__title">void --onair</span>
              <button className="mob-nav-sheet__close" onClick={() => setUpwardPanel(null)} aria-label="Close">&times;</button>
            </div>
            <div className="mob-nav-sheet__body db-panel__onair">
              <div className="db-panel__onair-controls">
                <button
                  type="button"
                  className="db-onair__play-btn"
                  onClick={handlePlayPause}
                  aria-label={isPlaying ? "Pause" : "Play"}
                >
                  {isPlaying ? "\u275A\u275A" : "\u25B6"}
                </button>
                <div className="db-panel__onair-track-wrap">
                  <div className="void-onair__track">
                    <div className="void-onair__fill" style={{ width: `${progress}%` }} />
                    <input
                      type="range"
                      className="void-onair__seek"
                      min={0}
                      max={displayDuration || 100}
                      value={currentTime}
                      step={0.5}
                      onChange={handleSeek}
                      aria-label="Broadcast progress"
                    />
                  </div>
                  <div className="db-panel__onair-meta">
                    <span className="db-panel__onair-status">
                      {isPlaying ? "Now playing" : "Paused"}
                    </span>
                    <span className="db-panel__onair-time">
                      {formatTime(currentTime)} / {formatTime(displayDuration)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Fixed bottom bar */}
      <nav className="mob-nav" aria-label="Mobile navigation">
        {/* Row 1: Edition + Lean + Topic */}
        <div className="mob-nav__filters">
          {/* Edition pills */}
          <div className="mob-nav__group" role="tablist" aria-label="Edition">
            {EDITIONS.map((ed) => (
              <Link
                key={ed.slug}
                href={getEditionHref(ed.slug)}
                role="tab"
                aria-selected={activeEdition === ed.slug}
                className={`mob-nav__ed${activeEdition === ed.slug ? " mob-nav__ed--active" : ""}`}
              >
                <EditionIcon slug={ed.slug} size={10} />
                <span>{ed.label}</span>
              </Link>
            ))}
          </div>

          <div className="mob-nav__sep" aria-hidden="true" />

          {/* Lean chips */}
          <div className="mob-nav__group" role="tablist" aria-label="Lean filter">
            {(["Left", "Center", "Right"] as LeanChip[]).map((lean) => (
              <button
                key={lean}
                role="tab"
                aria-selected={activeLean === lean}
                onClick={() => handleLeanTap(lean)}
                className={`mob-nav__lean mob-nav__lean--${lean.toLowerCase()}${activeLean === lean ? " mob-nav__lean--active" : ""}`}
              >
                {lean.charAt(0)}
              </button>
            ))}
          </div>

          <div className="mob-nav__sep" aria-hidden="true" />

          {/* Topic dropdown (opens upward) */}
          <div className={`mob-nav__topics${topicOpen ? " mob-nav__topics--open" : ""}`}>
            <button
              className="mob-nav__topic-trigger"
              onClick={() => setTopicOpen((v) => !v)}
              aria-expanded={topicOpen}
            >
              {activeCategory === "All" ? "All" : activeCategory.slice(0, 4)}
              <span className="mob-nav__topic-caret" aria-hidden="true">&#9652;</span>
            </button>

            {topicOpen && (
              <div className="mob-nav__topic-panel" role="listbox">
                {ALL_CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    role="option"
                    aria-selected={activeCategory === cat}
                    onClick={() => handleTopicTap(cat)}
                    className={`mob-nav__topic-opt${activeCategory === cat ? " mob-nav__topic-opt--active" : ""}`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Row 2: Daily Brief pills */}
        {brief && (
          <div className="mob-nav__brief">
            <button
              className={`mob-nav__pill${upwardPanel === "tldr" ? " mob-nav__pill--active" : ""}`}
              onClick={() => toggleUpward("tldr")}
              type="button"
            >
              <ScaleIcon size={10} animation="idle" className="mob-nav__pill-icon" />
              <span>tl;dr</span>
            </button>

            {brief.opinion_text && (
              <button
                className={`mob-nav__pill${upwardPanel === "opinion" ? " mob-nav__pill--active" : ""}`}
                onClick={() => toggleUpward("opinion")}
                type="button"
              >
                opinion
              </button>
            )}

            <button
              className={`mob-nav__pill mob-nav__pill--onair${isPlaying ? " mob-nav__pill--playing" : ""}${upwardPanel === "onair" ? " mob-nav__pill--active" : ""}${!hasAudio ? " mob-nav__pill--disabled" : ""}`}
              onClick={handleOnairTap}
              type="button"
              disabled={!hasAudio}
            >
              {isPlaying && <span className="mob-nav__pill-dot" />}
              <span>onair</span>
              <span className="mob-nav__pill-glyph" aria-hidden="true">
                {isPlaying ? "\u275A\u275A" : "\u25B6"}
              </span>
            </button>

            {brief.created_at && (
              <span className="mob-nav__timestamp">{timeAgo(brief.created_at)}</span>
            )}
          </div>
        )}
      </nav>
    </>
  );
}
