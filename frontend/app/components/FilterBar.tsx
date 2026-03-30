"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import type { Category, Edition } from "../lib/types";
import { EDITIONS } from "../lib/types";
import EditionIcon from "./EditionIcon";
import { hapticMicro } from "../lib/haptics";

export type LeanChip = "All" | "Left" | "Center" | "Right";

/* Lean chip boundaries — used by HomeContent to filter stories */
export const LEAN_RANGES: Record<LeanChip, { min: number; max: number } | null> = {
  All: null,
  Left: { min: 0, max: 46 },
  Center: { min: 35, max: 65 },
  Right: { min: 54, max: 100 },
};

const ALL_CATEGORIES: ("All" | Category)[] = [
  "All", "Politics", "Conflict", "Economy", "Science", "Health", "Environment", "Culture",
];

interface FilterBarProps {
  activeCategory: "All" | Category;
  onCategoryChange: (category: "All" | Category) => void;
  activeLean: LeanChip;
  onLeanChange: (lean: LeanChip) => void;
  activeEdition: Edition;
}

/* ---------------------------------------------------------------------------
   FilterBar — Unified single-row filter system

   Three distinct filter types, visually differentiated, in one row:
   1. Edition pills (World/US/India) — navigation, bold, icon+label
   2. Lean chips (Left/Center/Right) — perspective filter, colored dots
   3. Topic dropdown (All Topics ▾) — content filter, understated

   Desktop: single horizontal row, all visible
   Mobile: wraps to 2 rows naturally via flex-wrap
   --------------------------------------------------------------------------- */

export default function FilterBar({
  activeCategory,
  onCategoryChange,
  activeLean,
  onLeanChange,
  activeEdition,
}: FilterBarProps) {
  const [topicOpen, setTopicOpen] = useState(false);
  const [topicFocusIdx, setTopicFocusIdx] = useState(-1);
  const topicRef = useRef<HTMLDivElement>(null);
  const topicTriggerRef = useRef<HTMLButtonElement>(null);

  function getEditionHref(slug: Edition): string {
    if (slug === "world") return "/";
    return `/${slug}`;
  }

  const handleLeanTap = (lean: LeanChip) => {
    hapticMicro();
    onLeanChange(lean === activeLean ? "All" : lean);
  };

  const handleTopicTap = (cat: "All" | Category) => {
    hapticMicro();
    onCategoryChange(cat);
    setTopicOpen(false);
    setTopicFocusIdx(-1);
    topicTriggerRef.current?.focus();
  };

  // Arrow-key navigation for topic dropdown (WAI-ARIA menu pattern)
  const handleTopicPanelKeyDown = (e: React.KeyboardEvent) => {
    const items = ALL_CATEGORIES;
    let nextIdx = topicFocusIdx;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        nextIdx = topicFocusIdx < items.length - 1 ? topicFocusIdx + 1 : 0;
        break;
      case "ArrowUp":
        e.preventDefault();
        nextIdx = topicFocusIdx > 0 ? topicFocusIdx - 1 : items.length - 1;
        break;
      case "Home":
        e.preventDefault();
        nextIdx = 0;
        break;
      case "End":
        e.preventDefault();
        nextIdx = items.length - 1;
        break;
      case "Escape":
        e.preventDefault();
        setTopicOpen(false);
        setTopicFocusIdx(-1);
        topicTriggerRef.current?.focus();
        return;
      default:
        return;
    }

    setTopicFocusIdx(nextIdx);
    const panel = topicRef.current?.querySelector('[role="menu"]');
    const buttons = panel?.querySelectorAll<HTMLButtonElement>('[role="menuitem"]');
    buttons?.[nextIdx]?.focus();
  };

  // Reset focus index when dropdown closes
  useEffect(() => {
    if (!topicOpen) setTopicFocusIdx(-1);
  }, [topicOpen]);

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
    <div className="ubar">
      {/* ── Edition pills — navigation CTAs ── */}
      <div className="ubar__group ubar__editions" role="navigation" aria-label="Edition">
        {EDITIONS.map((ed) => (
          <Link
            key={ed.slug}
            href={getEditionHref(ed.slug)}
            aria-current={activeEdition === ed.slug ? "page" : undefined}
            className={`ubar__edition${activeEdition === ed.slug ? " ubar__edition--active" : ""}`}
          >
            <EditionIcon slug={ed.slug} size={12} />
            <span>{ed.label}</span>
          </Link>
        ))}
      </div>

      {/* ── Separator ── */}
      <div className="ubar__sep" aria-hidden="true" />

      {/* ── Lean chips — perspective filter ── */}
      <div className="ubar__group ubar__leans" role="group" aria-label="Filter by perspective">
        {(["Left", "Center", "Right"] as LeanChip[]).map((lean) => (
          <button
            key={lean}
            aria-pressed={activeLean === lean}
            onClick={() => handleLeanTap(lean)}
            className={`ubar__lean ubar__lean--${lean.toLowerCase()}${activeLean === lean ? " ubar__lean--active" : ""}`}
          >
            <span className="ubar__lean-dot" aria-hidden="true" />
            {lean}
          </button>
        ))}
      </div>

      {/* ── Separator ── */}
      <div className="ubar__sep" aria-hidden="true" />

      {/* ── Topic dropdown — content filter ── */}
      <div
        ref={topicRef}
        className={`ubar__group ubar__topics${topicOpen ? " ubar__topics--open" : ""}`}
      >
        <button
          ref={topicTriggerRef}
          className="ubar__topic-trigger"
          onClick={() => setTopicOpen((v) => !v)}
          onMouseEnter={() => setTopicOpen(true)}
          aria-expanded={topicOpen}
          aria-haspopup="menu"
          aria-label="Filter by topic"
        >
          {activeCategory === "All" ? "All Topics" : activeCategory}
          <span className={`ubar__topic-caret${topicOpen ? " ubar__topic-caret--open" : ""}`} aria-hidden="true">&#9662;</span>
        </button>

        {/* Dropdown panel */}
        {topicOpen && (
          <div
            className="ubar__topic-panel"
            role="menu"
            aria-label="Topics"
            onMouseLeave={() => setTopicOpen(false)}
            onKeyDown={handleTopicPanelKeyDown}
          >
            {ALL_CATEGORIES.map((cat) => (
              <button
                key={cat}
                role="menuitem"
                aria-current={activeCategory === cat ? "true" : undefined}
                onClick={() => handleTopicTap(cat)}
                className={`ubar__topic-option${activeCategory === cat ? " ubar__topic-option--active" : ""}`}
              >
                {cat}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* ── Active filter badge (lean) ── */}
      {activeLean !== "All" && (
        <div className="ubar__active-badge" role="status" aria-live="polite">
          <span className="ubar__active-badge-text">{activeLean}</span>
          <button
            className="ubar__active-badge-x"
            onClick={() => { hapticMicro(); onLeanChange("All"); }}
            aria-label={`Clear ${activeLean} filter`}
          >
            &times;
          </button>
        </div>
      )}
    </div>
  );
}
