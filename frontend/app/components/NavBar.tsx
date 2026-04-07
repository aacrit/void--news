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

/** When only one edition exists, edition UI is hidden and Row 2 shows content links instead. */
const MULTI_EDITION = EDITIONS.length > 1;

interface NavBarProps {
  activeEdition: Edition;
  onEditionChange?: (edition: Edition) => void;
  activeCategory?: "All" | Category;
  onCategoryChange?: (category: "All" | Category) => void;
  activeLean?: LeanChip;
  onLeanChange?: (lean: LeanChip) => void;
  onSearchClick?: () => void;
  hasAudio?: boolean;
  isAudioPlaying?: boolean;
  onOnairClick?: () => void;
}

/* ---------------------------------------------------------------------------
   NavBar — "Depth of Field" CTA Hierarchy (v2)

   Row 1 (Chrome — structural, about the app):
     Logo | dateline · timestamp | Sources Ship About | Theme

   Row 2 (Lens — content-shaping, inset shadow texture):
     Multi-edition:  World US Europe South-Asia | [ topics ] [ ·L ·C ·R ] | Search
     Single-edition: History  Weekly | [ topics ] [ ·L ·C ·R ] | Search

   Edition tabs auto-show when EDITIONS.length > 1. When parked (world-only),
   Row 2 reclaims the space for content navigation links.
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
  const [searchFocused, setSearchFocused] = useState(false);
  const topicRef = useRef<HTMLDivElement>(null);
  const topicTriggerRef = useRef<HTMLButtonElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

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

  const handleSearchBarClick = () => {
    onSearchClick?.();
  };

  const handleSearchBarKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onSearchClick?.();
    }
  };

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
      {/* ── Row 1: Chrome — structural, about the app ── */}
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
          {dateline}
        </span>

        {/* Spinoff links — only shown when multi-edition (otherwise they move to Row 2) */}
        {MULTI_EDITION && (
          <nav className="nav-spinoffs" aria-label="Spinoff editions">
            <Link href="/weekly" className="nav-weekly" aria-label="Go to Weekly digest" title="void --weekly">
              <span className="nav-weekly__rule" aria-hidden="true" />
              <span className="nav-weekly__label">Weekly</span>
            </Link>
            <Link href="/history" className="nav-history" aria-label="Go to History archive" title="void --history">
              <span className="nav-history__rule" aria-hidden="true" />
              <span className="nav-history__label">History</span>
            </Link>
          </nav>
        )}

        <div className="nav-right">
          {/* Page navigation — destinations */}
          <nav className="nav-pages" aria-label="Pages">
            <PageToggle activePage="feed" />
            <Link href="/ship" className="nav-page" aria-label="void --ship" title="void --ship">
              Ship
            </Link>
            <Link href="/about" className="nav-page" aria-label="About void --news" title="void --about">
              About
            </Link>
          </nav>

          {/* Utility: Theme (hidden on mobile — ThemeToggle is in MobileSidePanel) */}
          <ThemeToggle />
        </div>
      </nav>

      {/* ── Mobile edition tabs — only when multi-edition ── */}
      {MULTI_EDITION && onEditionChange && (
        <nav className="nav-mob-editions" aria-label="Edition">
          {EDITIONS.map((ed) => (
            <button
              key={ed.slug}
              type="button"
              aria-current={activeEdition === ed.slug ? "page" : undefined}
              className={`nav-mob-ed${activeEdition === ed.slug ? " nav-mob-ed--active" : ""}`}
              onClick={() => handleEditionTap(ed.slug)}
            >
              {ed.label}
            </button>
          ))}
        </nav>
      )}

      {/* ── Row 2: Lens — content-shaping controls, inset texture ── */}
      {hasFilters && (
        <div className="nav-lens">
          {/* Edition tabs — only when multi-edition */}
          {MULTI_EDITION ? (
            <nav className="nav-lens__editions" aria-label="Edition">
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
          ) : (
            /* Single-edition: content navigation replaces edition tabs */
            <nav className="nav-lens__content" aria-label="Content sections">
              <Link href="/history" className="nav-lens__content-link nav-lens__content-link--history" title="void --history">
                History
              </Link>
              <Link href="/weekly" className="nav-lens__content-link nav-lens__content-link--weekly" title="void --weekly">
                Weekly
              </Link>
            </nav>
          )}

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

          {/* Tilt selector — instrument panel */}
          <div className="nav-lens__group" role="toolbar" aria-label="Coverage tilt">
            <span className="nav-lens__bracket" aria-hidden="true">[</span>
            {(["Left", "Balanced", "Right"] as LeanChip[]).map((lean) => (
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

          {/* Active tilt badge */}
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

          {/* Search bar — expandable, right-anchored */}
          {onSearchClick && (
            <div
              className={`nav-lens__search${searchFocused ? " nav-lens__search--focused" : ""}`}
              onClick={handleSearchBarClick}
              onKeyDown={handleSearchBarKeyDown}
              role="search"
            >
              <MagnifyingGlass size={14} weight="regular" className="nav-lens__search-icon" aria-hidden="true" />
              <input
                ref={searchInputRef}
                className="nav-lens__search-input"
                type="text"
                placeholder="Search stories..."
                readOnly
                tabIndex={0}
                onFocus={() => { setSearchFocused(true); onSearchClick?.(); }}
                onBlur={() => setSearchFocused(false)}
                aria-label="Search stories (Ctrl+K)"
              />
              <kbd className="nav-lens__search-kbd" aria-hidden="true">&#8984;K</kbd>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
