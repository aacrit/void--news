"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import type { Edition, Category } from "../lib/types";
import { EDITIONS } from "../lib/types";
import ThemeToggle from "./ThemeToggle";
import PageToggle from "./PageToggle";
import LogoFull from "./LogoFull";
import EditionIcon from "./EditionIcon";
import { getEditionTimestamp } from "../lib/utils";
import type { LeanChip } from "./FilterBar";
import { hapticMicro } from "../lib/haptics";

const ALL_CATEGORIES: ("All" | Category)[] = [
  "All", "Politics", "Economy", "Science", "Health", "Culture",
];

interface NavBarProps {
  activeEdition: Edition;
  /** Filter props — when provided, renders the compact filter row */
  activeCategory?: "All" | Category;
  onCategoryChange?: (category: "All" | Category) => void;
  activeLean?: LeanChip;
  onLeanChange?: (lean: LeanChip) => void;
}

/* ---------------------------------------------------------------------------
   NavBar — Newspaper masthead with integrated compact filter row

   Row 1: Logo | dateline | Sources | Theme
   Row 2: [World US India] · [L C R] · [Topics ▾] [×badge]

   Everything in one sticky header. No separate filter bar, no bottom nav.
   --------------------------------------------------------------------------- */

function formatDateCompact(): string {
  return new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function getEditionHref(slug: Edition): string {
  if (slug === "world") return "/";
  return `/${slug}`;
}

export default function NavBar({
  activeEdition,
  activeCategory = "All",
  onCategoryChange,
  activeLean = "All",
  onLeanChange,
}: NavBarProps) {
  const [topicOpen, setTopicOpen] = useState(false);
  const topicRef = useRef<HTMLDivElement>(null);

  const handleLeanTap = (lean: LeanChip) => {
    hapticMicro();
    onLeanChange?.(lean === activeLean ? "All" : lean);
  };

  const handleTopicTap = (cat: "All" | Category) => {
    hapticMicro();
    onCategoryChange?.(cat);
    setTopicOpen(false);
  };

  // Close topic dropdown on outside click
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

  const hasFilters = !!onLeanChange;

  return (
    <header className="nav-header">
      {/* ── Row 1: Masthead ── */}
      <nav className="nav-inner" aria-label="Main navigation">
        <div className="nav-left">
          <Link href="/" aria-label="void --news — home" className="nav-logo si-hoverable">
            <span className="nav-logo-desktop">
              <LogoFull height={32} />
            </span>
            <span className="nav-logo-mobile">
              <LogoFull height={22} />
            </span>
          </Link>
        </div>

        <span className="nav-dateline-inline" aria-hidden="true">
          {formatDateCompact()}
          <span className="nav-dateline-inline__sep">&middot;</span>
          <span className="nav-dateline-inline__time">{getEditionTimestamp(activeEdition)}</span>
        </span>
        <span className="nav-dateline-mobile" aria-hidden="true">
          {formatDateCompact()}
        </span>

        <div className="nav-right">
          <PageToggle activePage="feed" />
          <ThemeToggle />
        </div>
      </nav>

      {/* ── Row 2: Compact filters (editions + lean + topic) ── */}
      {hasFilters && (
        <div className="nav-filters">
          {/* Edition pills */}
          <div className="nav-filters__group" role="tablist" aria-label="Edition">
            {EDITIONS.map((ed) => (
              <Link
                key={ed.slug}
                href={getEditionHref(ed.slug)}
                role="tab"
                aria-selected={activeEdition === ed.slug}
                className={`nav-filters__ed${activeEdition === ed.slug ? " nav-filters__ed--active" : ""}`}
              >
                <EditionIcon slug={ed.slug} size={11} />
                <span>{ed.label}</span>
              </Link>
            ))}
          </div>

          <div className="nav-filters__sep" aria-hidden="true" />

          {/* Lean chips */}
          <div className="nav-filters__group" role="tablist" aria-label="Political perspective">
            {(["Left", "Center", "Right"] as LeanChip[]).map((lean) => (
              <button
                key={lean}
                role="tab"
                aria-selected={activeLean === lean}
                onClick={() => handleLeanTap(lean)}
                className={`nav-filters__lean nav-filters__lean--${lean.toLowerCase()}${activeLean === lean ? " nav-filters__lean--active" : ""}`}
              >
                <span className="nav-filters__lean-dot" aria-hidden="true" />
                {lean}
              </button>
            ))}
          </div>

          <div className="nav-filters__sep" aria-hidden="true" />

          {/* Topic dropdown */}
          <div
            ref={topicRef}
            className={`nav-filters__topics${topicOpen ? " nav-filters__topics--open" : ""}`}
          >
            <button
              className="nav-filters__topic-trigger"
              onClick={() => setTopicOpen((v) => !v)}
              onMouseEnter={() => setTopicOpen(true)}
              aria-expanded={topicOpen}
              aria-label="Filter by topic"
            >
              {activeCategory === "All" ? "Topics" : activeCategory}
              <span className={`nav-filters__topic-caret${topicOpen ? " nav-filters__topic-caret--open" : ""}`} aria-hidden="true">&#9662;</span>
            </button>

            {topicOpen && (
              <div
                className="nav-filters__topic-panel"
                role="listbox"
                aria-label="Topics"
                onMouseLeave={() => setTopicOpen(false)}
              >
                {ALL_CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    role="option"
                    aria-selected={activeCategory === cat}
                    onClick={() => handleTopicTap(cat)}
                    className={`nav-filters__topic-opt${activeCategory === cat ? " nav-filters__topic-opt--active" : ""}`}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Active lean badge */}
          {activeLean !== "All" && (
            <div className="nav-filters__badge" role="status" aria-live="polite">
              <span>{activeLean}</span>
              <button
                className="nav-filters__badge-x"
                onClick={() => { hapticMicro(); onLeanChange?.("All"); }}
                aria-label={`Clear ${activeLean} filter`}
              >
                &times;
              </button>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
