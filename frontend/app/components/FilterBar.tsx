"use client";

import { useState, useRef, useEffect } from "react";
import type { Category } from "../lib/types";
import { hapticMicro } from "../lib/haptics";

export type LeanChip = "All" | "Left" | "Center" | "Right";

/* Lean chip boundaries — used by HomeContent to filter stories */
export const LEAN_RANGES: Record<LeanChip, { min: number; max: number } | null> = {
  All: null,
  Left: { min: 0, max: 46 },
  Center: { min: 35, max: 65 },
  Right: { min: 54, max: 100 },
};

const LEAN_PULSE_KEY = "void-news-lean-pulse-seen";

const ALL_CATEGORIES: ("All" | Category)[] = [
  "All", "Politics", "Economy", "Science", "Health", "Culture",
];

interface FilterBarProps {
  activeCategory: "All" | Category;
  onCategoryChange: (category: "All" | Category) => void;
  activeLean: LeanChip;
  onLeanChange: (lean: LeanChip) => void;
}

/* ---------------------------------------------------------------------------
   FilterBar — Two-row filter system
   Row 1: Lean segmented control (hero) — Left / Center / Right
   Row 2: Topic filter — collapsed on desktop, compact chips on mobile

   5b additions:
   - First-load pulse on lean bar (localStorage gated, 3s, one-time)
   - Active filter badge pill with dismiss × below the lean bar
   --------------------------------------------------------------------------- */

export default function FilterBar({
  activeCategory,
  onCategoryChange,
  activeLean,
  onLeanChange,
}: FilterBarProps) {
  const [topicOpen, setTopicOpen] = useState(false);
  const topicRef = useRef<HTMLDivElement>(null);
  const [leanPulse, setLeanPulse] = useState(false);

  // One-time lean bar pulse on first visit
  useEffect(() => {
    try {
      if (!localStorage.getItem(LEAN_PULSE_KEY)) {
        setLeanPulse(true);
        const timer = setTimeout(() => {
          setLeanPulse(false);
          localStorage.setItem(LEAN_PULSE_KEY, "1");
        }, 3000);
        return () => clearTimeout(timer);
      }
    } catch {
      // localStorage blocked — skip pulse silently
    }
  }, []);

  const handleLeanTap = (lean: LeanChip) => {
    hapticMicro();
    onLeanChange(lean === activeLean ? "All" : lean);
  };

  const handleTopicTap = (cat: "All" | Category) => {
    hapticMicro();
    onCategoryChange(cat);
    setTopicOpen(false);
  };

  // Close topic panel on outside click
  useEffect(() => {
    if (!topicOpen) return;
    const close = (e: MouseEvent) => {
      if (topicRef.current && !topicRef.current.contains(e.target as Node)) {
        setTopicOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [topicOpen]);

  return (
    <div className="filter-bar-wrapper">
      {/* Row 1: Lean segmented control — hero filter */}
      <div
        className={`lean-bar${leanPulse ? " lean-bar--pulse" : ""}`}
        role="tablist"
        aria-label="Filter by political perspective"
      >
        <button
          role="tab"
          aria-selected={activeLean === "Left"}
          onClick={() => handleLeanTap("Left")}
          className={`lean-bar__seg lean-bar__seg--left${activeLean === "Left" ? " lean-bar__seg--active" : ""}`}
        >
          <span className="lean-bar__dot" aria-hidden="true" />
          Left
        </button>
        <button
          role="tab"
          aria-selected={activeLean === "Center"}
          onClick={() => handleLeanTap("Center")}
          className={`lean-bar__seg lean-bar__seg--center${activeLean === "Center" ? " lean-bar__seg--active" : ""}`}
        >
          <span className="lean-bar__dot" aria-hidden="true" />
          Center
        </button>
        <button
          role="tab"
          aria-selected={activeLean === "Right"}
          onClick={() => handleLeanTap("Right")}
          className={`lean-bar__seg lean-bar__seg--right${activeLean === "Right" ? " lean-bar__seg--active" : ""}`}
        >
          <span className="lean-bar__dot" aria-hidden="true" />
          Right
        </button>
        <div className="lean-bar__gradient" aria-hidden="true" />
      </div>

      {/* Active lean filter badge — shown when a lean is selected */}
      {activeLean !== "All" && (
        <div className="lean-active-badge" role="status" aria-live="polite" aria-label={`Active filter: ${activeLean}`}>
          <span className="lean-active-badge__text text-data">
            Filtered by {activeLean}
          </span>
          <button
            className="lean-active-badge__dismiss"
            onClick={() => { hapticMicro(); onLeanChange("All"); }}
            aria-label={`Clear ${activeLean} filter`}
          >
            &#x2715;
          </button>
        </div>
      )}

      {/* Row 2: Topic filter — collapsed on desktop, scrollable on mobile */}
      <div
        ref={topicRef}
        className={`topic-bar${topicOpen ? " topic-bar--open" : ""}`}
        onMouseEnter={() => setTopicOpen(true)}
        onMouseLeave={() => setTopicOpen(false)}
      >
        {/* Desktop: collapsed trigger — hidden on mobile */}
        <button
          className="topic-bar__trigger"
          onClick={() => setTopicOpen((v) => !v)}
          aria-expanded={topicOpen}
          aria-label="Toggle topic filter menu"
        >
          {activeCategory === "All" ? "All Topics" : activeCategory}
          <span
            className={`topic-bar__caret${topicOpen ? " topic-bar__caret--open" : ""}`}
            aria-hidden="true"
          >
            &#9662;
          </span>
        </button>

        {/* Category chips */}
        <div className="topic-bar__chips" role="tablist" aria-label="Filter by topic">
          {ALL_CATEGORIES.map((cat) => (
            <button
              key={cat}
              role="tab"
              aria-selected={activeCategory === cat}
              onClick={() => handleTopicTap(cat)}
              className={`topic-bar__chip${activeCategory === cat ? " topic-bar__chip--active" : ""}`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
