"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MagnifyingGlass } from "@phosphor-icons/react";
import { timeAgo } from "../lib/utils";
import type { Story } from "../lib/types";

/* ---------------------------------------------------------------------------
   SearchOverlay — Cmd+K command palette for void --news.
   Center-modal spotlight search over loaded stories.
   Fuzzy substring matching, keyboard navigation, spring entrance.
   --------------------------------------------------------------------------- */

interface SearchOverlayProps {
  stories: Story[];
  onStorySelect: (story: Story) => void;
  isOpen: boolean;
  onClose: () => void;
}

const MAX_RESULTS = 8;

/** Simple case-insensitive substring search with title > summary priority. */
function scoreStory(story: Story, query: string): number {
  const q = query.toLowerCase();
  const titleMatch = story.title.toLowerCase().includes(q);
  const summaryMatch = story.summary.toLowerCase().includes(q);

  if (!titleMatch && !summaryMatch) return -1;

  // Title match weighted heavily, summary match less so.
  // importanceScore tiebreaker keeps editorial ranking.
  let score = 0;
  if (titleMatch) score += 1000;
  if (summaryMatch) score += 100;
  score += story.importance;

  return score;
}

export default function SearchOverlay({
  stories,
  onStorySelect,
  isOpen,
  onClose,
}: SearchOverlayProps) {
  const [query, setQuery] = useState("");
  const [activeIndex, setActiveIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLUListElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  // Filtered + scored results
  const results = useMemo(() => {
    const trimmed = query.trim();
    if (!trimmed) return [];

    const scored = stories
      .map((story) => ({ story, score: scoreStory(story, trimmed) }))
      .filter((s) => s.score >= 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, MAX_RESULTS);

    return scored.map((s) => s.story);
  }, [stories, query]);

  // Reset active index when results change
  useEffect(() => {
    setActiveIndex(0);
  }, [results.length]);

  // Reset query on open
  useEffect(() => {
    if (isOpen) {
      setQuery("");
      setActiveIndex(0);
      // Auto-focus input after mount + animation frame
      requestAnimationFrame(() => {
        inputRef.current?.focus();
      });
    }
  }, [isOpen]);

  // Scroll active result into view
  useEffect(() => {
    if (!listRef.current) return;
    const active = listRef.current.children[activeIndex] as HTMLElement | undefined;
    active?.scrollIntoView({ block: "nearest" });
  }, [activeIndex]);

  // Keyboard handler
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      switch (e.key) {
        case "ArrowDown":
          e.preventDefault();
          setActiveIndex((prev) =>
            results.length > 0 ? Math.min(prev + 1, results.length - 1) : 0
          );
          break;
        case "ArrowUp":
          e.preventDefault();
          setActiveIndex((prev) => Math.max(prev - 1, 0));
          break;
        case "Enter":
          e.preventDefault();
          if (results[activeIndex]) {
            onStorySelect(results[activeIndex]);
            onClose();
          }
          break;
        case "Escape":
          e.preventDefault();
          onClose();
          break;
      }
    },
    [results, activeIndex, onStorySelect, onClose]
  );

  // Backdrop click
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose]
  );

  // Focus trap: keep focus within the overlay
  const handleFocusTrap = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key !== "Tab") return;
      if (!panelRef.current) return;

      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'input, button, [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];

      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    },
    []
  );

  if (!isOpen) return null;

  return (
    <div
      className="search-overlay"
      onClick={handleBackdropClick}
      onKeyDown={handleFocusTrap}
      role="dialog"
      aria-modal="true"
      aria-label="Search stories"
    >
      <div
        className="search-overlay__panel"
        ref={panelRef}
        onKeyDown={handleKeyDown}
      >
        {/* Search input */}
        <div className="search-overlay__input-wrap">
          <MagnifyingGlass
            className="search-overlay__icon"
            size={20}
            weight="regular"
            aria-hidden="true"
          />
          <input
            ref={inputRef}
            className="search-overlay__input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search stories..."
            aria-label="Search stories"
            aria-controls="search-results"
            aria-activedescendant={
              results.length > 0 ? `search-result-${activeIndex}` : undefined
            }
            role="combobox"
            aria-expanded={results.length > 0}
            aria-autocomplete="list"
            autoComplete="off"
            spellCheck={false}
          />
        </div>

        {/* Results list */}
        {results.length > 0 && (
          <ul
            className="search-overlay__results"
            id="search-results"
            role="listbox"
            ref={listRef}
          >
            {results.map((story, idx) => (
              <li
                key={story.id}
                id={`search-result-${idx}`}
                className={`search-overlay__result${
                  idx === activeIndex ? " search-overlay__result--active" : ""
                }`}
                role="option"
                aria-selected={idx === activeIndex}
                onClick={() => {
                  onStorySelect(story);
                  onClose();
                }}
                onMouseEnter={() => setActiveIndex(idx)}
              >
                <span className="search-overlay__result-title">
                  {story.title}
                </span>
                <span className="search-overlay__result-meta">
                  <span className="search-overlay__result-category">
                    {story.category}
                  </span>
                  <span className="search-overlay__result-sep" aria-hidden="true">
                    /
                  </span>
                  <span>{timeAgo(story.publishedAt)}</span>
                  <span className="search-overlay__result-sep" aria-hidden="true">
                    /
                  </span>
                  <span>
                    {story.source.count} source{story.source.count !== 1 ? "s" : ""}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        )}

        {/* Empty state */}
        {query.trim().length > 0 && results.length === 0 && (
          <div className="search-overlay__empty">
            No stories match &ldquo;{query.trim()}&rdquo;
          </div>
        )}

        {/* Keyboard hints footer */}
        <div className="search-overlay__footer" aria-hidden="true">
          <span>
            <kbd>&uarr;</kbd><kbd>&darr;</kbd> Navigate
          </span>
          <span>
            <kbd>&crarr;</kbd> Open
          </span>
          <span>
            <kbd>esc</kbd> Close
          </span>
        </div>
      </div>
    </div>
  );
}
