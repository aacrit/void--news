"use client";

import { useState, useRef, useEffect } from "react";
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

const LEANS: LeanChip[] = ["Left", "Balanced", "Right"];

/* ---------------------------------------------------------------------------
   MobileBottomNav — Unified filter trigger (mobile only).

   CEO 2026-05-14: lean filter was eating a full row above the feed. Buried it
   inside the topics panel as a "tilt" section so the bar is a single trigger.
   The space freed lets MobileBriefPill render a TL;DR + Opinion teaser in its
   collapsed state.

   [ filters ▾ ]   — trigger
       ↓
   [ tilt:   ·left   ·balanced   ·right ]
   [ topics: all  politics  conflict  …  ]

   Hidden on desktop via CSS.
   --------------------------------------------------------------------------- */

export default function MobileBottomNav({
  activeLean,
  onLeanChange,
  activeCategory,
  onCategoryChange,
}: MobileBottomNavProps) {
  const [panelOpen, setPanelOpen] = useState(false);
  const navRef = useRef<HTMLElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    if (!panelOpen) return;
    const close = (e: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setPanelOpen(false);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [panelOpen]);

  useEffect(() => {
    if (!panelOpen) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") { e.preventDefault(); setPanelOpen(false); triggerRef.current?.focus(); }
    };
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [panelOpen]);

  useEffect(() => {
    if (panelOpen && panelRef.current) {
      requestAnimationFrame(() => {
        panelRef.current?.querySelector<HTMLElement>("button")?.focus();
      });
    }
  }, [panelOpen]);

  const handleLeanTap = (lean: LeanChip) => {
    hapticMicro();
    onLeanChange(lean === activeLean ? "All" : lean);
  };

  const handleTopicTap = (cat: "All" | Category) => {
    hapticMicro();
    onCategoryChange(cat);
  };

  const hasActiveFilter = activeLean !== "All" || activeCategory !== "All";
  const leanLabel = activeLean !== "All" ? activeLean.toLowerCase() : null;
  const topicLabel = activeCategory !== "All" ? activeCategory.toLowerCase() : null;
  // Trigger label collapses to "filters" by default; reveals active values when set.
  const triggerLabel = leanLabel && topicLabel
    ? `${leanLabel} · ${topicLabel}`
    : leanLabel || topicLabel || "filters";

  return (
    <nav className="mob-nav mob-nav--inline" aria-label="Feed filters" ref={navRef}>
      {panelOpen && (
        <div
          ref={panelRef}
          className="mob-nav__panel"
          role="menu"
          aria-label="Filters"
        >
          <div className="mob-nav__panel-section">
            <span className="mob-nav__panel-label">tilt</span>
            <div className="mob-nav__panel-row" role="group" aria-label="Coverage tilt">
              {LEANS.map((lean) => {
                const isActive = activeLean === lean;
                return (
                  <button
                    key={lean}
                    role="menuitemradio"
                    aria-checked={isActive}
                    aria-label={isActive ? `${lean} filter active — tap to clear` : `Filter to ${lean}`}
                    onClick={() => handleLeanTap(lean)}
                    className={`mob-nav__lean mob-nav__lean--${lean.toLowerCase()}${isActive ? " mob-nav__lean--active" : ""}`}
                  >
                    <span className="mob-nav__dot" aria-hidden="true" />
                    {lean.toLowerCase()}
                  </button>
                );
              })}
            </div>
          </div>

          <div className="mob-nav__panel-section">
            <span className="mob-nav__panel-label">topics</span>
            <div className="mob-nav__panel-row mob-nav__panel-row--wrap" role="group" aria-label="Topics">
              {ALL_CATEGORIES.map((cat) => (
                <button
                  key={cat}
                  role="menuitemradio"
                  aria-checked={activeCategory === cat}
                  className={`mob-nav__topic-opt${activeCategory === cat ? " mob-nav__topic-opt--active" : ""}`}
                  onClick={() => handleTopicTap(cat)}
                >
                  {cat === "All" ? "all" : cat.toLowerCase()}
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="mob-nav__bar">
        <button
          ref={triggerRef}
          type="button"
          className={`mob-nav__trigger${hasActiveFilter ? " mob-nav__trigger--active" : ""}`}
          onClick={() => { hapticLight(); setPanelOpen((v) => !v); }}
          aria-expanded={panelOpen}
          aria-haspopup="menu"
          aria-label={hasActiveFilter ? `Filters active: ${triggerLabel}` : "Open filters"}
        >
          <span className="mob-nav__bracket" aria-hidden="true">[</span>
          {leanLabel && (
            <span
              className={`mob-nav__trigger-dot mob-nav__trigger-dot--${activeLean.toLowerCase()}`}
              aria-hidden="true"
            />
          )}
          <span className="mob-nav__trigger-label">{triggerLabel}</span>
          <span className={`mob-nav__caret${panelOpen ? " mob-nav__caret--open" : ""}`} aria-hidden="true">&#9662;</span>
          <span className="mob-nav__bracket" aria-hidden="true">]</span>
        </button>
      </div>
    </nav>
  );
}
