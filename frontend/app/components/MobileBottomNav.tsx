"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { Category, LeanChip } from "../lib/types";
import { hapticMicro, hapticLight } from "../lib/haptics";

interface MobileBottomNavProps {
  activeLean: LeanChip;
  onLeanChange: (lean: LeanChip) => void;
  activeCategory: "All" | Category;
  onCategoryChange: (cat: "All" | Category) => void;
}

const ALL_CATEGORIES: ("All" | Category)[] = [
  "All", "Politics", "Conflict", "Economy", "Science", "Health", "Environment", "Culture",
];

/* ---------------------------------------------------------------------------
   MobileBottomNav — Now an INLINE bracket-notation filter bar (feed-only).
   Renders in the content flow below edition tabs, above the feed.
   No longer fixed-bottom. MobileTabBar handles global navigation.

   Matches desktop nav-lens design language exactly:
   - IBM Plex Mono, lowercase, bracket notation
   - Colored dots for lean (6px, same as desktop)
   - Dotted underline active state
   - Topic dropdown with caret

   [ ·left  ·center  ·right ]   [ topics ▾ ]

   Hidden on desktop via CSS (display: none above 768px).
   --------------------------------------------------------------------------- */

export default function MobileBottomNav({
  activeLean,
  onLeanChange,
  activeCategory,
  onCategoryChange,
}: MobileBottomNavProps) {
  const [topicOpen, setTopicOpen] = useState(false);
  const navRef = useRef<HTMLElement>(null);
  const topicPanelRef = useRef<HTMLDivElement>(null);
  const topicTriggerRef = useRef<HTMLButtonElement | null>(null);

  // Close on outside tap
  useEffect(() => {
    if (!topicOpen) return;
    const close = (e: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setTopicOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [topicOpen]);

  // Close on Escape
  useEffect(() => {
    if (!topicOpen) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); setTopicOpen(false); topicTriggerRef.current?.focus(); }
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [topicOpen]);

  // Focus management
  useEffect(() => {
    if (topicOpen && topicPanelRef.current) {
      requestAnimationFrame(() => {
        topicPanelRef.current?.querySelector<HTMLElement>("button")?.focus();
      });
    }
  }, [topicOpen]);

  const handleLeanTap = (lean: LeanChip) => {
    hapticMicro();
    onLeanChange(lean === activeLean ? "All" : lean);
  };

  const handleTopicTap = (cat: "All" | Category) => {
    hapticMicro();
    onCategoryChange(cat);
    setTopicOpen(false);
    topicTriggerRef.current?.focus();
  };

  return (
    <nav className="mob-nav mob-nav--inline" aria-label="Feed filters" ref={navRef}>
      {/* Topic dropdown panel — slides up */}
      {topicOpen && (
        <div
          ref={topicPanelRef}
          className="mob-nav__topic-panel"
          role="menu"
          aria-label="Topics"
        >
          {ALL_CATEGORIES.map((cat) => (
            <button
              key={cat}
              role="menuitem"
              aria-current={activeCategory === cat ? "true" : undefined}
              className={`mob-nav__topic-opt${activeCategory === cat ? " mob-nav__topic-opt--active" : ""}`}
              onClick={() => handleTopicTap(cat)}
            >
              {cat === "All" ? "all topics" : cat.toLowerCase()}
            </button>
          ))}
        </div>
      )}

      {/* Filter bar — bracket notation matching desktop nav-lens */}
      <div className="mob-nav__bar">
        {/* Tilt selector: [ ·left ·balanced ·right ] */}
        <div className="mob-nav__lens" role="toolbar" aria-label="Coverage tilt">
          <span className="mob-nav__bracket" aria-hidden="true">[</span>
          {(["Left", "Balanced", "Right"] as LeanChip[]).map((lean) => (
            <button
              key={lean}
              aria-pressed={activeLean === lean}
              onClick={() => handleLeanTap(lean)}
              className={`mob-nav__lean mob-nav__lean--${lean.toLowerCase()}${activeLean === lean ? " mob-nav__lean--active" : ""}`}
            >
              <span className="mob-nav__dot" aria-hidden="true" />
              {lean.toLowerCase()}
            </button>
          ))}
          <span className="mob-nav__bracket" aria-hidden="true">]</span>
        </div>

        {/* Topic dropdown: [ topics ▾ ] */}
        <div className="mob-nav__topics">
          <button
            ref={topicTriggerRef}
            className="mob-nav__topic-trigger"
            onClick={() => { hapticLight(); setTopicOpen((v) => !v); }}
            aria-expanded={topicOpen}
            aria-haspopup="menu"
            aria-label="Filter by topic"
          >
            <span className="mob-nav__bracket" aria-hidden="true">[</span>
            {activeCategory === "All" ? "topics" : activeCategory.toLowerCase()}
            <span className={`mob-nav__caret${topicOpen ? " mob-nav__caret--open" : ""}`} aria-hidden="true">&#9662;</span>
            <span className="mob-nav__bracket" aria-hidden="true">]</span>
          </button>
        </div>
      </div>
    </nav>
  );
}
