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
import { hapticMicro, hapticConfirm } from "../lib/haptics";

const ALL_CATEGORIES: ("All" | Category)[] = [
  "All", "Politics", "Conflict", "Economy", "Science", "Health", "Environment", "Culture",
];

interface NavBarProps {
  activeEdition: Edition;
  onEditionChange?: (edition: Edition) => void;
  /** Filter props — when provided, renders the compact filter row */
  activeCategory?: "All" | Category;
  onCategoryChange?: (category: "All" | Category) => void;
  activeLean?: LeanChip;
  onLeanChange?: (lean: LeanChip) => void;
  onSearchClick?: () => void;
  /** OnAir audio — kept for API compat but no longer rendered in nav */
  hasAudio?: boolean;
  isAudioPlaying?: boolean;
  onOnairClick?: () => void;
}

/* ---------------------------------------------------------------------------
   NavBar — "Depth of Field" CTA Hierarchy

   Layer 1 (Sharp Focus): Editions — Playfair typographic tabs, warm underline
   Layer 2 (Midground):   Filters  — Mono bracket notation, recessive lens
   Layer 3 (Background):  Pages    — Inter text links, departure arrow
   Special:               Weekly   — Magazine supplement, italic editorial
   Ambient:               Utility  — Icon-only, monochrome

   Row 1: Logo | [Editions] | dateline | [Pages Weekly] [🔍 ☀]
   Row 2: [ topics ▾ ]  [ ·left ·center ·right ]
   --------------------------------------------------------------------------- */

function formatDateCompact(): string {
  return new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export default function NavBar({
  activeEdition,
  onEditionChange,
  activeCategory = "All",
  onCategoryChange,
  activeLean = "All",
  onLeanChange,
  onSearchClick,
}: NavBarProps) {
  const [topicOpen, setTopicOpen] = useState(false);
  const [topicFocusIdx, setTopicFocusIdx] = useState(-1);
  const topicRef = useRef<HTMLDivElement>(null);
  const topicTriggerRef = useRef<HTMLButtonElement>(null);

  // Defer date rendering to client to avoid SSG/client hydration mismatch (#310)
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);
  const dateline = mounted ? formatDateCompact() : "\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0\u00A0";
  const timestamp = mounted ? getEditionTimestamp(activeEdition) : "\u00A0\u00A0\u00A0\u00A0\u00A0";

  const handleEditionTap = (edition: Edition) => {
    hapticConfirm();
    onEditionChange?.(edition);
  };

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

  useEffect(() => {
    if (!topicOpen) setTopicFocusIdx(-1);
  }, [topicOpen]);

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

        {/* Layer 1 — Sharp Focus: Edition tabs (desktop only) */}
        {hasFilters && (
          <nav className="nav-editions" aria-label="Edition">
            {EDITIONS.map((ed) => (
              <button
                key={ed.slug}
                type="button"
                aria-current={activeEdition === ed.slug ? "page" : undefined}
                className={`nav-ed${activeEdition === ed.slug ? " nav-ed--active" : ""}`}
                onClick={() => handleEditionTap(ed.slug)}
              >
                <EditionIcon slug={ed.slug} size={10} />
                <span>{ed.label}</span>
              </button>
            ))}
          </nav>
        )}

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
          {/* Layer 3 — Background: Page navigation */}
          <nav className="nav-pages" aria-label="Pages">
            <PageToggle activePage="feed" />
            <Link href="/ship" className="nav-page" aria-label="void --ship" title="void --ship">
              Ship
            </Link>
            <Link href="/about" className="nav-page" aria-label="About void --news" title="void --about">
              About
            </Link>
          </nav>

          {/* Special — Magazine: Weekly */}
          <Link
            href="/weekly"
            className="nav-weekly"
            aria-label="Go to Weekly digest"
            title="void --weekly"
          >
            <span className="nav-weekly__rule" aria-hidden="true" />
            <span className="nav-weekly__label">Weekly</span>
          </Link>

          {/* Ambient — Utility: Search */}
          {onSearchClick && (
            <button
              className="nav-util"
              onClick={onSearchClick}
              aria-label="Search stories (Ctrl+K)"
              title="Search (Ctrl+K)"
              type="button"
            >
              <MagnifyingGlass size={18} weight="light" />
            </button>
          )}

          {/* Ambient — Utility: Theme */}
          <ThemeToggle />
        </div>
      </nav>

      {/* ── Row 2: Filter Lens (desktop only, feed pages only) ── */}
      {hasFilters && (
        <div className="nav-lens">
          {/* Topic dropdown — bracket notation */}
          <div
            ref={topicRef}
            className={`nav-lens__topics${topicOpen ? " nav-lens__topics--open" : ""}`}
          >
            <button
              ref={topicTriggerRef}
              className="nav-lens__trigger"
              onClick={() => setTopicOpen((v) => !v)}
              aria-expanded={topicOpen}
              aria-haspopup="menu"
              aria-label="Filter by topic"
            >
              <span className="nav-lens__bracket" aria-hidden="true">[</span>
              {activeCategory === "All" ? "topics" : activeCategory.toLowerCase()}
              <span className={`nav-lens__caret${topicOpen ? " nav-lens__caret--open" : ""}`} aria-hidden="true">&#9662;</span>
              <span className="nav-lens__bracket" aria-hidden="true">]</span>
            </button>

            {topicOpen && (
              <div
                className="nav-lens__panel"
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
                    className={`nav-lens__opt${activeCategory === cat ? " nav-lens__opt--active" : ""}`}
                  >
                    {cat.toLowerCase()}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Lean selector — instrument panel */}
          <div className="nav-lens__group" role="toolbar" aria-label="Political perspective">
            <span className="nav-lens__bracket" aria-hidden="true">[</span>
            {(["Left", "Center", "Right"] as LeanChip[]).map((lean) => (
              <button
                key={lean}
                aria-pressed={activeLean === lean}
                onClick={() => handleLeanTap(lean)}
                className={`nav-lens__lean nav-lens__lean--${lean.toLowerCase()}${activeLean === lean ? " nav-lens__lean--active" : ""}`}
              >
                <span className="nav-lens__dot" aria-hidden="true" />
                {lean.toLowerCase()}
              </button>
            ))}
            <span className="nav-lens__bracket" aria-hidden="true">]</span>
          </div>

          {/* Active lean badge */}
          {activeLean !== "All" && (
            <div className="nav-lens__badge" role="status" aria-live="polite">
              <span>{activeLean.toLowerCase()}</span>
              <button
                className="nav-lens__badge-x"
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
