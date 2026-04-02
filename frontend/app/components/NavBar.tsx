"use client";

import { useState, useRef, useEffect } from "react";
import Link from "next/link";
import { MagnifyingGlass } from "@phosphor-icons/react";
import type { Edition, Category, LeanChip } from "../lib/types";
import { EDITIONS } from "../lib/types";
import ThemeToggle from "./ThemeToggle";
import PageToggle from "./PageToggle";
import LogoFull from "./LogoFull";
import EditionIcon from "./EditionIcon";
import { getEditionTimestamp } from "../lib/utils";
import { hapticMicro } from "../lib/haptics";

const ALL_CATEGORIES: ("All" | Category)[] = [
  "All", "Politics", "Conflict", "Economy", "Science", "Health", "Environment", "Culture",
];

interface NavBarProps {
  activeEdition: Edition;
  /** Filter props — when provided, renders the compact filter row */
  activeCategory?: "All" | Category;
  onCategoryChange?: (category: "All" | Category) => void;
  activeLean?: LeanChip;
  onLeanChange?: (lean: LeanChip) => void;
  onSearchClick?: () => void;
  /** OnAir audio — show broadcast button in nav */
  hasAudio?: boolean;
  isAudioPlaying?: boolean;
  onOnairClick?: () => void;
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
  onSearchClick,
  hasAudio,
  isAudioPlaying,
  onOnairClick,
}: NavBarProps) {
  const [topicOpen, setTopicOpen] = useState(false);
  const [topicFocusIdx, setTopicFocusIdx] = useState(-1);
  const topicRef = useRef<HTMLDivElement>(null);
  const topicTriggerRef = useRef<HTMLButtonElement>(null);

  // Defer date rendering to client to avoid SSG/client hydration mismatch (#310)
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);
  const dateline = mounted ? formatDateCompact() : "";
  const timestamp = mounted ? getEditionTimestamp(activeEdition) : "";

  const handleLeanTap = (lean: LeanChip) => {
    hapticMicro();
    onLeanChange?.(lean === activeLean ? "All" : lean);
  };

  const handleTopicTap = (cat: "All" | Category) => {
    hapticMicro();
    onCategoryChange?.(cat);
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
    <header className="nav-header anim-cold-open-nav">
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

        <span className="nav-dateline-inline" aria-hidden="true" suppressHydrationWarning>
          {dateline}
          <span className="nav-dateline-inline__sep">&middot;</span>
          <span className="nav-dateline-inline__time">{timestamp}</span>
        </span>
        <span className="nav-dateline-mobile" aria-hidden="true" suppressHydrationWarning>
          <span className="nav-edition-badge">
            <EditionIcon slug={activeEdition} size={10} />
            {EDITIONS.find(e => e.slug === activeEdition)?.label ?? "World"}
          </span>
          <span className="nav-dateline-sep">&middot;</span>
          {dateline}
        </span>

        <div className="nav-right">
          {onSearchClick && (
            <button
              className="nav-search-btn"
              onClick={onSearchClick}
              aria-label="Search stories (Ctrl+K)"
              title="Search (Ctrl+K)"
              type="button"
            >
              <MagnifyingGlass size={18} weight="light" />
            </button>
          )}
          {hasAudio && onOnairClick && (
            <button
              className={`nav-onair${isAudioPlaying ? " nav-onair--active" : ""}`}
              onClick={onOnairClick}
              type="button"
              aria-label={isAudioPlaying ? "Now playing — open player" : "Listen to broadcast"}
            >
              {isAudioPlaying && <span className="nav-onair__dot" aria-hidden="true" />}
              <span className="nav-onair__label">onair</span>
            </button>
          )}
          <PageToggle activePage="feed" />
          <ThemeToggle />
        </div>
      </nav>

      {/* ── Row 2: Compact filters (editions + lean + topic) ── */}
      {hasFilters && (
        <div className="nav-filters">
          {/* Edition pills */}
          <nav className="nav-filters__group" aria-label="Edition">
            {EDITIONS.map((ed) => (
              <Link
                key={ed.slug}
                href={getEditionHref(ed.slug)}
                aria-current={activeEdition === ed.slug ? "page" : undefined}
                className={`nav-filters__ed${activeEdition === ed.slug ? " nav-filters__ed--active" : ""}`}
              >
                <EditionIcon slug={ed.slug} size={11} />
                <span>{ed.label}</span>
              </Link>
            ))}
          </nav>

          <div className="nav-filters__sep" aria-hidden="true" />

          {/* Lean chips */}
          <div className="nav-filters__group" role="toolbar" aria-label="Political perspective">
            {(["Left", "Center", "Right"] as LeanChip[]).map((lean) => (
              <button
                key={lean}
                aria-pressed={activeLean === lean}
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
              ref={topicTriggerRef}
              className="nav-filters__topic-trigger"
              onClick={() => setTopicOpen((v) => !v)}
              aria-expanded={topicOpen}
              aria-haspopup="menu"
              aria-label="Filter by topic"
            >
              {activeCategory === "All" ? "Topics" : activeCategory}
              <span className={`nav-filters__topic-caret${topicOpen ? " nav-filters__topic-caret--open" : ""}`} aria-hidden="true">&#9662;</span>
            </button>

            {topicOpen && (
              <div
                className="nav-filters__topic-panel"
                role="menu"
                aria-label="Topics"
                onKeyDown={handleTopicPanelKeyDown}
              >
                {ALL_CATEGORIES.map((cat) => (
                  <button
                    key={cat}
                    role="menuitem"
                    aria-current={activeCategory === cat ? "true" : undefined}
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
