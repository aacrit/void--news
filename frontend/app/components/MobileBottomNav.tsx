"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import type { Edition, Category } from "../lib/types";
import { EDITIONS } from "../lib/types";
import EditionIcon from "./EditionIcon";
import type { LeanChip } from "./FilterBar";
import { hapticMicro, hapticLight } from "../lib/haptics";

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

type OpenPanel = null | "edition" | "lean" | "topic";

/* ---------------------------------------------------------------------------
   MobileBottomNav — 3 expandable CTA buttons at bottom (mobile only).

   [Edition ▾]  [Perspective ▾]  [Topic ▾]

   Each button shows current selection. Tapping expands an upward panel
   with options. Only one panel open at a time.
   Hidden on desktop via CSS (display: none above 768px).
   --------------------------------------------------------------------------- */

export default function MobileBottomNav({
  activeEdition,
  activeLean,
  onLeanChange,
  activeCategory,
  onCategoryChange,
}: MobileBottomNavProps) {
  const [openPanel, setOpenPanel] = useState<OpenPanel>(null);
  const navRef = useRef<HTMLElement>(null);

  const toggle = (panel: OpenPanel) => {
    hapticLight();
    setOpenPanel((prev) => (prev === panel ? null : panel));
  };

  const handleLeanTap = (lean: LeanChip) => {
    hapticMicro();
    onLeanChange(lean === activeLean ? "All" : lean);
    setOpenPanel(null);
  };

  const handleTopicTap = (cat: "All" | Category) => {
    hapticMicro();
    onCategoryChange(cat);
    setOpenPanel(null);
  };

  // Close on outside tap
  useEffect(() => {
    if (!openPanel) return;
    const close = (e: MouseEvent) => {
      if (navRef.current && !navRef.current.contains(e.target as Node)) {
        setOpenPanel(null);
      }
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [openPanel]);

  const editionLabel = EDITIONS.find((e) => e.slug === activeEdition)?.label ?? "World";
  const leanLabel = activeLean === "All" ? "All" : activeLean;
  const topicLabel = activeCategory === "All" ? "All Topics" : activeCategory;

  return (
    <nav className="mob-nav" aria-label="Mobile navigation" ref={navRef}>
      {/* Expanded panel (rendered above the buttons) */}
      {openPanel === "edition" && (
        <div className="mob-nav__panel" role="listbox" aria-label="Edition">
          {EDITIONS.map((ed) => (
            <Link
              key={ed.slug}
              href={getEditionHref(ed.slug)}
              role="option"
              aria-selected={activeEdition === ed.slug}
              className={`mob-nav__opt${activeEdition === ed.slug ? " mob-nav__opt--active" : ""}`}
              onClick={() => setOpenPanel(null)}
            >
              <EditionIcon slug={ed.slug} size={12} />
              {ed.label}
            </Link>
          ))}
        </div>
      )}

      {openPanel === "lean" && (
        <div className="mob-nav__panel" role="listbox" aria-label="Perspective">
          {(["All", "Left", "Center", "Right"] as LeanChip[]).map((lean) => (
            <button
              key={lean}
              role="option"
              aria-selected={activeLean === lean}
              className={`mob-nav__opt mob-nav__opt--lean-${lean.toLowerCase()}${activeLean === lean ? " mob-nav__opt--active" : ""}`}
              onClick={() => handleLeanTap(lean)}
            >
              {lean === "All" ? "All Perspectives" : lean}
            </button>
          ))}
        </div>
      )}

      {openPanel === "topic" && (
        <div className="mob-nav__panel" role="listbox" aria-label="Topic">
          {ALL_CATEGORIES.map((cat) => (
            <button
              key={cat}
              role="option"
              aria-selected={activeCategory === cat}
              className={`mob-nav__opt${activeCategory === cat ? " mob-nav__opt--active" : ""}`}
              onClick={() => handleTopicTap(cat)}
            >
              {cat === "All" ? "All Topics" : cat}
            </button>
          ))}
        </div>
      )}

      {/* Three CTA buttons */}
      <div className="mob-nav__bar">
        <button
          className={`mob-nav__cta${openPanel === "edition" ? " mob-nav__cta--open" : ""}`}
          onClick={() => toggle("edition")}
          aria-expanded={openPanel === "edition"}
          type="button"
        >
          <EditionIcon slug={activeEdition} size={10} />
          <span className="mob-nav__cta-label">{editionLabel}</span>
          <span className="mob-nav__cta-caret" aria-hidden="true">&#9652;</span>
        </button>

        <button
          className={`mob-nav__cta${openPanel === "lean" ? " mob-nav__cta--open" : ""}`}
          onClick={() => toggle("lean")}
          aria-expanded={openPanel === "lean"}
          type="button"
        >
          <span className="mob-nav__cta-label">{leanLabel}</span>
          <span className="mob-nav__cta-caret" aria-hidden="true">&#9652;</span>
        </button>

        <button
          className={`mob-nav__cta${openPanel === "topic" ? " mob-nav__cta--open" : ""}`}
          onClick={() => toggle("topic")}
          aria-expanded={openPanel === "topic"}
          type="button"
        >
          <span className="mob-nav__cta-label">{topicLabel}</span>
          <span className="mob-nav__cta-caret" aria-hidden="true">&#9652;</span>
        </button>
      </div>
    </nav>
  );
}
