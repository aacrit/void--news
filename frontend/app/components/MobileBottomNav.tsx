"use client";

import { useState } from "react";
import Link from "next/link";
import type { Edition, Category } from "../lib/types";
import { EDITIONS } from "../lib/types";
import EditionIcon from "./EditionIcon";
import type { LeanChip } from "./FilterBar";
import { hapticMicro } from "../lib/haptics";

interface MobileBottomNavProps {
  activeEdition: Edition;
  activeLean: LeanChip;
  onLeanChange: (lean: LeanChip) => void;
  activeCategory: "All" | Category;
  onCategoryChange: (cat: "All" | Category) => void;
}

const ALL_CATEGORIES: ("All" | Category)[] = [
  "All", "Politics", "Conflict", "Economy", "Science", "Health", "Environment", "Culture",
];

function getEditionHref(slug: Edition): string {
  if (slug === "world") return "/";
  return `/${slug}`;
}

/* ---------------------------------------------------------------------------
   MobileBottomNav — single-row thumb-reachable bottom bar (mobile only).

   Row: [World  US  India] · [L  C  R] · [Topics ▾]

   Daily Brief content renders in-body via DailyBriefText.
   Hidden on desktop via CSS (display: none above 768px).
   --------------------------------------------------------------------------- */

export default function MobileBottomNav({
  activeEdition,
  activeLean,
  onLeanChange,
  activeCategory,
  onCategoryChange,
}: MobileBottomNavProps) {
  const [topicOpen, setTopicOpen] = useState(false);

  const handleLeanTap = (lean: LeanChip) => {
    hapticMicro();
    onLeanChange(lean === activeLean ? "All" : lean);
  };

  const handleTopicTap = (cat: "All" | Category) => {
    hapticMicro();
    onCategoryChange(cat);
    setTopicOpen(false);
  };

  return (
    <nav className="mob-nav" aria-label="Mobile navigation">
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
    </nav>
  );
}
