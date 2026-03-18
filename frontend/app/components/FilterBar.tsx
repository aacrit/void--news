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
  "All",
  "Politics",
  "Economy",
  "Tech",
  "Health",
  "Environment",
  "Conflict",
  "Science",
  "Culture",
  "Sports",
];

interface FilterBarProps {
  activeCategory: "All" | Category;
  onCategoryChange: (category: "All" | Category) => void;
}

/* ---------------------------------------------------------------------------
   FilterBar — Horizontal scrollable chips for category filtering
   "All" selected by default. Subtle fill on selection.
   No colored chips — bias colors are reserved for bias data only.
   --------------------------------------------------------------------------- */

export default function FilterBar({
  activeCategory,
  onCategoryChange,
}: FilterBarProps) {
  return (
    <div
      role="tablist"
      aria-label="Filter stories by category"
      style={{
        display: "flex",
        gap: "var(--space-2)",
        overflowX: "auto",
        padding: "var(--space-3) 0",
        scrollbarWidth: "none",
        msOverflowStyle: "none",
        WebkitOverflowScrolling: "touch",
        scrollSnapType: "x mandatory",
      }}
    >
      {ALL_CATEGORIES.map((cat) => {
        const isActive = activeCategory === cat;
        const IconComponent = CATEGORY_ICONS[cat];
        return (
          <button
            key={cat}
            role="tab"
            aria-selected={isActive}
            onClick={() => onCategoryChange(cat)}
            style={{
              fontFamily: "var(--font-structural)",
              fontSize: "var(--text-xs)",
              fontWeight: isActive ? 600 : 400,
              letterSpacing: "0.04em",
              textTransform: "uppercase",
              color: isActive ? "var(--fg-primary)" : "var(--fg-tertiary)",
              backgroundColor: isActive
                ? "var(--bg-secondary)"
                : "transparent",
              border: isActive
                ? "1px solid var(--border-strong)"
                : "1px solid var(--border-subtle)",
              borderRadius: "var(--radius-md)",
              padding: "var(--space-2) var(--space-3)",
              whiteSpace: "nowrap",
              cursor: "pointer",
              minHeight: 44,
              scrollSnapAlign: "start",
              transition:
                "color var(--dur-fast) var(--ease-out), background-color var(--dur-fast) var(--ease-out), border-color var(--dur-fast) var(--ease-out), transform var(--dur-fast) var(--spring)",
              flexShrink: 0,
              display: "flex",
              alignItems: "center",
              gap: "var(--space-1)",
            }}
            onMouseDown={(e) => {
              (e.currentTarget as HTMLElement).style.transform = "scale(0.97)";
            }}
            onMouseUp={(e) => {
              (e.currentTarget as HTMLElement).style.transform = "scale(1)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLElement).style.transform = "scale(1)";
            }}
          >
            {IconComponent && (
              <IconComponent size={14} weight="light" aria-hidden="true" />
            )}
            {cat}
          </button>
        );
      })}
    </div>
  );
}
