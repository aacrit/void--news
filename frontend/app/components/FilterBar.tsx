"use client";

import type { Category } from "../lib/types";
import type { Icon } from "@phosphor-icons/react";
import {
  SquaresFour,
  Scales,
  ChartLineUp,
  Cpu,
  Heartbeat,
  Leaf,
  ShieldWarning,
  Flask,
  PaintBrush,
  Trophy,
} from "@phosphor-icons/react";

const CATEGORY_ICONS: Record<string, Icon> = {
  All: SquaresFour,
  Politics: Scales,
  Economy: ChartLineUp,
  Tech: Cpu,
  Health: Heartbeat,
  Environment: Leaf,
  Conflict: ShieldWarning,
  Science: Flask,
  Culture: PaintBrush,
  Sports: Trophy,
};

const ALL_CATEGORIES: ("All" | Category)[] = [
  "All", "Politics", "Economy", "Tech", "Health",
  "Environment", "Conflict", "Science", "Culture", "Sports",
];

interface FilterBarProps {
  activeCategory: "All" | Category;
  onCategoryChange: (category: "All" | Category) => void;
}

/* ---------------------------------------------------------------------------
   FilterBar — Horizontal scrollable chips for category filtering
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
