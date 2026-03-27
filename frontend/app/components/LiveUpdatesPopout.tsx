"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { X, CaretLeft, CaretRight } from "@phosphor-icons/react";
import type { Story, LiveUpdate } from "../lib/types";
import { supabase } from "../lib/supabase";
import { timeAgo } from "../lib/utils";
import { hapticLight, hapticMedium } from "../lib/haptics";

/* ---------------------------------------------------------------------------
   LiveUpdatesPopout — "void --live" popup overlay.
   Desktop: centered panel (65vw, max 800px, 80vh).
   Mobile: full-screen bottom sheet with safe-area insets.
   --------------------------------------------------------------------------- */

interface LiveUpdatesPopoutProps {
  story: Story;
  onClose: () => void;
  originRect?: DOMRect | null;
  onNavigate?: (direction: "prev" | "next") => void;
  storyIndex?: number;
  totalStories?: number;
}

/* ---------------------------------------------------------------------------
   Timestamp helpers — shared with LiveUpdatesSection formatting convention
   --------------------------------------------------------------------------- */

function formatTimestamp(dateStr: string): string {
  const now = new Date();
  const then = new Date(dateStr);
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin} min ago`;
  return (
    then.toLocaleString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
      timeZone: "UTC",
    }) + " UTC"
  );
}

function isoString(dateStr: string): string {
  try {
    return new Date(dateStr).toISOString();
  } catch {
    return dateStr;
  }
}

/** Tracking duration from first_published to now, in "Xh Ym" format. */
function trackingDuration(publishedAt: string): string {
  const start = new Date(publishedAt).getTime();
  const now = Date.now();
  const diffMin = Math.floor((now - start) / 60_000);
  if (diffMin < 60) return `${diffMin}m`;
  const h = Math.floor(diffMin / 60);
  const m = diffMin % 60;
  return m > 0 ? `${h}h ${m}m` : `${h}h`;
}

/* ---------------------------------------------------------------------------
   Group updates that arrived within 10 minutes of each other.
   Same algorithm as LiveUpdatesSection.
   --------------------------------------------------------------------------- */
interface UpdateGroup {
  timestamp: string;
  updates: LiveUpdate[];
}

function groupUpdates(updates: LiveUpdate[]): UpdateGroup[] {
  const groups: UpdateGroup[] = [];
  const WINDOW_MS = 10 * 60 * 1000;

  for (const update of updates) {
    const last = groups[groups.length - 1];
    const updateTime = new Date(update.discovered_at).getTime();
    const groupTime = last ? new Date(last.timestamp).getTime() : -Infinity;

    if (last && Math.abs(updateTime - groupTime) <= WINDOW_MS) {
      last.updates.push(update);
    } else {
      groups.push({ timestamp: update.discovered_at, updates: [update] });
    }
  }

  return groups;
}

const INITIAL_VISIBLE = 5;
const POLL_INTERVAL_MS = 30_000;

export default function LiveUpdatesPopout({
  story,
  onClose,
  onNavigate,
  storyIndex = -1,
  totalStories = 0,
}: LiveUpdatesPopoutProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [contentVisible, setContentVisible] = useState(false);
  const [updates, setUpdates] = useState<LiveUpdate[]>([]);
  const [isLoadingUpdates, setIsLoadingUpdates] = useState(true);
  const [showAll, setShowAll] = useState(false);

  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  const onNavigateRef = useRef(onNavigate);
  onNavigateRef.current = onNavigate;

  /* ---- Fetch live updates from Supabase -------------------------------- */
  const fetchUpdates = useCallback(async () => {
    if (!supabase || !story.storyMemoryId) return;
    try {
      const { data, error } = await supabase
        .from("live_updates")
        .select("*")
        .eq("story_memory_id", story.storyMemoryId)
        .is("merged_into_cluster_id", null)
        .order("discovered_at", { ascending: false })
        .limit(30);

      if (!error && data) {
        setUpdates(data as LiveUpdate[]);
      }
    } finally {
      setIsLoadingUpdates(false);
    }
  }, [story.storyMemoryId]);

  /* Initial fetch */
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (!supabase || !story.storyMemoryId) {
        setIsLoadingUpdates(false);
        return;
      }
      try {
        const { data, error } = await supabase
          .from("live_updates")
          .select("*")
          .eq("story_memory_id", story.storyMemoryId)
          .is("merged_into_cluster_id", null)
          .order("discovered_at", { ascending: false })
          .limit(30);

        if (!cancelled && !error && data) {
          setUpdates(data as LiveUpdate[]);
        }
      } finally {
        if (!cancelled) setIsLoadingUpdates(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [story.storyMemoryId]);

  /* Poll every 30s */
  useEffect(() => {
    const interval = setInterval(fetchUpdates, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchUpdates]);

  /* ---- Open animation — scale + translateY reveal ---------------------- */
  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement;

    const scrollY = window.scrollY;
    const originalOverflow = document.body.style.overflow;
    const originalPosition = document.body.style.position;
    const originalWidth = document.body.style.width;
    const originalTop = document.body.style.top;

    document.body.style.overflow = "hidden";
    document.body.style.position = "fixed";
    document.body.style.width = "100%";
    document.body.style.top = `-${scrollY}px`;

    hapticMedium();

    requestAnimationFrame(() => {
      setIsVisible(true);
      const delay = window.innerWidth >= 768 ? 180 : 30;
      setTimeout(() => setContentVisible(true), delay);
    });

    return () => {
      document.body.style.overflow = originalOverflow;
      document.body.style.position = originalPosition;
      document.body.style.width = originalWidth;
      document.body.style.top = originalTop;
      window.scrollTo(0, scrollY);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* ---- Focus trap + Escape + Arrow navigation -------------------------- */
  useEffect(() => {
    if (!isVisible) return;
    panelRef.current?.focus();

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        handleClose();
        return;
      }

      if (onNavigateRef.current && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
        e.preventDefault();
        onNavigateRef.current(e.key === "ArrowLeft" ? "prev" : "next");
        return;
      }

      if (e.key === "Tab" && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
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
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isVisible]);

  /* ---- Close — snappy exit animation ------------------------------------ */
  const handleClose = useCallback(() => {
    hapticLight();
    setContentVisible(false);
    setIsVisible(false);
    // Allow CSS transition to complete before unmounting
    setTimeout(() => {
      previousFocusRef.current?.focus();
      onClose();
    }, 380);
  }, [onClose]);

  /* ---- Reset showAll when story changes --------------------------------- */
  useEffect(() => {
    setShowAll(false);
    setIsLoadingUpdates(true);
  }, [story.id]);

  /* ---- Compute visible updates ----------------------------------------- */
  const visibleUpdates = showAll ? updates : updates.slice(0, INITIAL_VISIBLE);
  const hiddenCount = updates.length - INITIAL_VISIBLE;
  const groups = groupUpdates(visibleUpdates);
  const mostRecentAt = updates[0]?.discovered_at;

  const hasPrev = storyIndex > 0;
  const hasNext = storyIndex >= 0 && storyIndex < totalStories - 1;

  return (
    <>
      {/* Backdrop */}
      <div
        className={`live-popout-backdrop${isVisible ? " live-popout-backdrop--visible" : ""}`}
        onClick={handleClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Live updates: ${story.title}`}
        tabIndex={-1}
        className={`live-popout-panel${isVisible ? " live-popout-panel--visible" : ""}`}
      >
        {/* ---- Sticky header ------------------------------------------- */}
        <header className="live-popout__header">
          {/* Brand + story headline row */}
          <div className="live-popout__header-top">
            <div className="live-popout__brand-row">
              <span className="live-popout__live-dot" aria-hidden="true" />
              <span className="live-popout__brand">void --live</span>
              {mostRecentAt && (
                <>
                  <span className="live-popout__brand-sep" aria-hidden="true">·</span>
                  <time
                    className="live-popout__brand-updated"
                    dateTime={isoString(mostRecentAt)}
                  >
                    Updated {timeAgo(mostRecentAt)}
                  </time>
                </>
              )}
            </div>

            {/* Nav + close controls */}
            <div className="live-popout__controls">
              {onNavigate && (
                <>
                  <button
                    className="live-popout__nav-btn"
                    onClick={() => { hapticLight(); onNavigate("prev"); }}
                    disabled={!hasPrev}
                    aria-label="Previous live story"
                    type="button"
                  >
                    <CaretLeft size={16} weight="bold" aria-hidden="true" />
                  </button>
                  {totalStories > 0 && storyIndex >= 0 && (
                    <span className="live-popout__nav-count" aria-hidden="true">
                      {storyIndex + 1}/{totalStories}
                    </span>
                  )}
                  <button
                    className="live-popout__nav-btn"
                    onClick={() => { hapticLight(); onNavigate("next"); }}
                    disabled={!hasNext}
                    aria-label="Next live story"
                    type="button"
                  >
                    <CaretRight size={16} weight="bold" aria-hidden="true" />
                  </button>
                </>
              )}
              <button
                className="live-popout__close-btn"
                onClick={handleClose}
                aria-label="Close live updates"
                type="button"
              >
                <X size={18} weight="bold" aria-hidden="true" />
              </button>
            </div>
          </div>

          {/* Story headline */}
          <h2 className="live-popout__headline">{story.title}</h2>

          {/* Meta row: category · source count · tracking duration */}
          <div className="live-popout__meta">
            <span className="live-popout__meta-category">{story.category}</span>
            <span className="live-popout__meta-sep" aria-hidden="true">·</span>
            <span className="live-popout__meta-sources">
              {story.source.count} source{story.source.count !== 1 ? "s" : ""}
            </span>
            <span className="live-popout__meta-sep" aria-hidden="true">·</span>
            <span className="live-popout__meta-tracking">
              Tracking {trackingDuration(story.publishedAt)}
            </span>
            {!isLoadingUpdates && updates.length > 0 && (
              <>
                <span className="live-popout__meta-sep" aria-hidden="true">·</span>
                <span className="live-popout__meta-count">
                  {updates.length} update{updates.length !== 1 ? "s" : ""}
                </span>
              </>
            )}
          </div>
        </header>

        {/* ---- Timeline body ------------------------------------------- */}
        <div
          className={`live-popout__timeline${contentVisible ? " live-popout__timeline--visible" : ""}`}
          role="list"
          aria-label="Live updates timeline"
          aria-busy={isLoadingUpdates}
        >
          {isLoadingUpdates && (
            <div className="live-popout__loading" aria-live="polite">
              <span className="live-popout__loading-dot" aria-hidden="true" />
              <span className="live-popout__loading-dot" aria-hidden="true" />
              <span className="live-popout__loading-dot" aria-hidden="true" />
              <span className="sr-only">Loading updates&hellip;</span>
            </div>
          )}

          {!isLoadingUpdates && updates.length === 0 && (
            <div className="live-popout__empty">
              <p className="live-popout__empty-text">
                No live updates yet. Check back soon.
              </p>
            </div>
          )}

          {!isLoadingUpdates && groups.map((group, gi) => (
            <div
              key={`group-${gi}`}
              className="live-popout__group"
              role="listitem"
            >
              {/* Vertical rail node */}
              <div className="live-popout__node" aria-hidden="true">
                <span className={`live-popout__node-dot${gi === 0 ? " live-popout__node-dot--latest" : ""}`} />
                {gi < groups.length - 1 && (
                  <span className="live-popout__node-line" />
                )}
              </div>

              {/* Group content */}
              <div className="live-popout__group-content">
                <time
                  className="live-popout__group-time"
                  dateTime={isoString(group.timestamp)}
                >
                  {formatTimestamp(group.timestamp)}
                </time>

                {group.updates.map((update, ui) => (
                  <article
                    key={update.id}
                    className={`live-popout__update${ui > 0 ? " live-popout__update--stacked" : ""}`}
                    aria-label={update.title}
                  >
                    <span className="live-popout__source">{update.source_name}</span>
                    <a
                      href={update.article_url}
                      className="live-popout__update-headline"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {update.title}
                    </a>
                    {update.update_summary && (
                      <p className="live-popout__delta">{update.update_summary}</p>
                    )}
                  </article>
                ))}
              </div>
            </div>
          ))}

          {/* Show earlier */}
          {!isLoadingUpdates && !showAll && hiddenCount > 0 && (
            <div className="live-popout__show-earlier">
              <div className="live-popout__earlier-rail" aria-hidden="true" />
              <button
                className="live-popout__show-earlier-btn"
                onClick={() => setShowAll(true)}
                type="button"
              >
                Show {hiddenCount} earlier update{hiddenCount !== 1 ? "s" : ""}
              </button>
            </div>
          )}
        </div>

        {/* ---- Footer -------------------------------------------------- */}
        <footer className="live-popout__footer">
          <button
            className="live-popout__footer-btn"
            onClick={handleClose}
            type="button"
          >
            View Full Analysis
          </button>
        </footer>
      </div>
    </>
  );
}
