"use client";

import type { Category } from "../lib/types";
import type { Icon } from "@phosphor-icons/react";
import {
  SquaresFour,
  Scales,
  ChartLineUp,
  Flask,
  Heartbeat,
  MaskHappy,
} from "@phosphor-icons/react";

const CATEGORY_ICONS: Record<string, Icon> = {
  All: SquaresFour,
  Politics: Scales,        // Politics + Conflict
  Economy: ChartLineUp,    // Economy
  Science: Flask,           // Science + Tech
  Health: Heartbeat,        // Health + Environment
  Culture: MaskHappy,       // Culture + Sports
};

const ALL_CATEGORIES: ("All" | Category)[] = [
  "All", "Politics", "Economy", "Science", "Health", "Culture",
];

interface FilterBarProps {
  activeCategory: "All" | Category;
  onCategoryChange: (category: "All" | Category) => void;
}

/* ---------------------------------------------------------------------------
   FilterBar — Horizontal scrollable chips for category filtering
   5 merged desks: Politics (+ Conflict), Economy, Science (+ Tech),
   Health (+ Environment), Culture (+ Sports).
   --------------------------------------------------------------------------- */

export default function FilterBar({ activeCategory, onCategoryChange }: FilterBarProps) {
  const handleChipTap = (cat: "All" | Category) => {
    // Haptic feedback on mobile
    if (typeof navigator !== "undefined" && navigator.vibrate) {
      navigator.vibrate(10);
    }
    onCategoryChange(cat);
  };

  return (
    <div className="filter-bar-wrapper">
      <div className="filter-bar" role="tablist" aria-label="Filter stories by category">
        {ALL_CATEGORIES.map((cat) => {
          const isActive = activeCategory === cat;
          const IconComponent = CATEGORY_ICONS[cat];
          return (
            <button
              key={cat}
              role="tab"
              aria-selected={isActive}
              onClick={() => handleChipTap(cat)}
              className={`filter-chip${isActive ? " filter-chip--active" : ""}`}
            >
              <span className="filter-chip__icon">
                {IconComponent && (
                  <IconComponent size={14} weight="light" aria-hidden="true" />
                )}
              </span>
              {cat}
            </button>
          );
        })}
      </div>
    </div>
  );
}
