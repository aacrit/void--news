"use client";

import { useState, useRef, useEffect } from "react";
import type { Category } from "../lib/types";

export type LeanChip = "All" | "Left" | "Center" | "Right";

/* Lean chip boundaries — used by HomeContent to filter stories */
export const LEAN_RANGES: Record<LeanChip, { min: number; max: number } | null> = {
  All: null,
  Left: { min: 0, max: 46 },
  Center: { min: 35, max: 65 },
  Right: { min: 54, max: 100 },
};

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
   --------------------------------------------------------------------------- */

export default function FilterBar({
  activeCategory,
  onCategoryChange,
  activeLean,
  onLeanChange,
}: FilterBarProps) {
  const [topicOpen, setTopicOpen] = useState(false);
  const topicRef = useRef<HTMLDivElement>(null);

  const handleLeanTap = (lean: LeanChip) => {
    if (typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(10);
    onLeanChange(lean === activeLean ? "All" : lean);
  };

  const handleTopicTap = (cat: "All" | Category) => {
    if (typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(10);
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
      <div className="lean-bar" role="tablist" aria-label="Filter by political perspective">
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
