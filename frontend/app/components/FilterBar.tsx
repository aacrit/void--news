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

export type LeanChip = "All" | "Left" | "Center" | "Right";

/* Lean chip boundaries — used by HomeContent to filter stories */
export const LEAN_RANGES: Record<LeanChip, { min: number; max: number } | null> = {
  All: null,
  Left: { min: 0, max: 46 },
  Center: { min: 35, max: 65 },
  Right: { min: 54, max: 100 },
};

const CATEGORY_ICONS: Record<string, Icon> = {
  All: SquaresFour,
  Politics: Scales,
  Economy: ChartLineUp,
  Science: Flask,
  Health: Heartbeat,
  Culture: MaskHappy,
};

const ALL_CATEGORIES: ("All" | Category)[] = [
  "All", "Politics", "Economy", "Science", "Health", "Culture",
];

const LEAN_CHIPS: LeanChip[] = ["Left", "Center", "Right"];

const LEAN_DOT_COLOR: Record<string, string> = {
  Left: "var(--bias-left)",
  Center: "var(--bias-center)",
  Right: "var(--bias-right)",
};

interface FilterBarProps {
  activeCategory: "All" | Category;
  onCategoryChange: (category: "All" | Category) => void;
  activeLean: LeanChip;
  onLeanChange: (lean: LeanChip) => void;
}

/* ---------------------------------------------------------------------------
   FilterBar — Category chips + Lean chips in one row
   --------------------------------------------------------------------------- */

export default function FilterBar({
  activeCategory,
  onCategoryChange,
  activeLean,
  onLeanChange,
}: FilterBarProps) {
  const handleChipTap = (cat: "All" | Category) => {
    if (typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(10);
    onCategoryChange(cat);
  };

  const handleLeanTap = (lean: LeanChip) => {
    if (typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(10);
    onLeanChange(lean === activeLean ? "All" : lean);
  };

  return (
    <div className="filter-bar-wrapper">
      <div className="filter-bar" role="tablist" aria-label="Filter stories by category and lean">
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

        {/* Lean divider */}
        <span className="filter-bar__divider" aria-hidden="true" />

        {/* Lean chips — Left / Center / Right */}
        {LEAN_CHIPS.map((lean) => {
          const isActive = activeLean === lean;
          return (
            <button
              key={lean}
              role="tab"
              aria-selected={isActive}
              onClick={() => handleLeanTap(lean)}
              className={`filter-chip${isActive ? " filter-chip--active" : ""}`}
            >
              <span
                className="filter-chip__dot"
                style={{ backgroundColor: LEAN_DOT_COLOR[lean] }}
                aria-hidden="true"
              />
              {lean}
            </button>
          );
        })}
      </div>
    </div>
  );
}
