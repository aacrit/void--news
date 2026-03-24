"use client";

import {
  useState,
  useEffect,
  useRef,
  useCallback,
  useId,
  forwardRef,
  useImperativeHandle,
} from "react";
import { supabase } from "../lib/supabase";
import type { LiveUpdate } from "../lib/types";
import { timeAgo } from "../lib/utils";

/* ---------------------------------------------------------------------------
   Public handle — lets LeadStory trigger expand via ref
   --------------------------------------------------------------------------- */
export interface LiveUpdatesSectionHandle {
  expand: () => void;
}

interface LiveUpdatesSectionProps {
  storyMemoryId: string;
}

/* ---------------------------------------------------------------------------
   Timestamp formatting helpers
   --------------------------------------------------------------------------- */

/**
 * Returns a relative timestamp for updates within the last hour,
 * otherwise an absolute HH:MM UTC string — newspaper dateline convention.
 */
function formatTimestamp(dateStr: string): string {
  const now = new Date();
  const then = new Date(dateStr);
  const diffMs = now.getTime() - then.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin} min ago`;
  // Absolute for older updates: "2:30 PM UTC"
  return then.toLocaleString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "UTC",
  }) + " UTC";
}

/**
 * Machine-readable ISO string for <time dateTime>.
 */
function isoString(dateStr: string): string {
  try {
    return new Date(dateStr).toISOString();
  } catch {
    return dateStr;
  }
}

/* ---------------------------------------------------------------------------
   Group updates that arrived within 10 minutes of each other.
   Groups share a single timeline node header.
   --------------------------------------------------------------------------- */
interface UpdateGroup {
  /** Representative timestamp for the group header */
  timestamp: string;
  updates: LiveUpdate[];
}

function groupUpdates(updates: LiveUpdate[]): UpdateGroup[] {
  const groups: UpdateGroup[] = [];
  const WINDOW_MS = 10 * 60 * 1000; // 10 minutes

  for (const update of updates) {
    const last = groups[groups.length - 1];
    const updateTime = new Date(update.discovered_at).getTime();
    const groupTime = last
      ? new Date(last.timestamp).getTime()
      : -Infinity;

    if (last && Math.abs(updateTime - groupTime) <= WINDOW_MS) {
      last.updates.push(update);
    } else {
      groups.push({ timestamp: update.discovered_at, updates: [update] });
    }
  }

  return groups;
}

/* ---------------------------------------------------------------------------
   LiveUpdatesSection — CNN/BBC-style expandable live timeline
   --------------------------------------------------------------------------- */

const INITIAL_VISIBLE = 5;
const POLL_INTERVAL_MS = 60_000;

const LiveUpdatesSection = forwardRef<
  LiveUpdatesSectionHandle,
  LiveUpdatesSectionProps
>(function LiveUpdatesSection({ storyMemoryId }, ref) {
  const [updates, setUpdates] = useState<LiveUpdate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isExpanded, setIsExpanded] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [hasNewWhileCollapsed, setHasNewWhileCollapsed] = useState(false);
  const [newCount, setNewCount] = useState(0);

  const sectionRef = useRef<HTMLElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const prevCountRef = useRef(0);

  const headingId = useId();
  const contentId = useId();

  /* Expose expand() to parent via ref */
  useImperativeHandle(ref, () => ({
    expand() {
      if (!isExpanded) {
        setIsExpanded(true);
        setHasNewWhileCollapsed(false);
        setNewCount(0);
        // Scroll section into view after the CSS grid transition starts
        setTimeout(() => {
          sectionRef.current?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          });
        }, 80);
      } else {
        sectionRef.current?.scrollIntoView({
          behavior: "smooth",
          block: "start",
        });
      }
    },
  }));

  const fetchUpdates = useCallback(async () => {
    if (!supabase) return;
    try {
      const { data, error } = await supabase
        .from("live_updates")
        .select("*")
        .eq("story_memory_id", storyMemoryId)
        .is("merged_into_cluster_id", null)
        .order("discovered_at", { ascending: false })
        .limit(20);

      if (!error && data) {
        setUpdates((prev) => {
          const incoming = data as LiveUpdate[];
          const added = incoming.length - prevCountRef.current;
          if (prevCountRef.current > 0 && added > 0) {
            // Notify user of new updates if collapsed
            setHasNewWhileCollapsed((collapsed) => {
              if (collapsed || !isExpanded) {
                setNewCount(added);
                return true;
              }
              return false;
            });
          }
          prevCountRef.current = incoming.length;
          return incoming;
        });
      }
    } finally {
      setIsLoading(false);
    }
  }, [storyMemoryId, isExpanded]);

  /* Initial fetch */
  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      if (!supabase) { setIsLoading(false); return; }
      try {
        const { data, error } = await supabase
          .from("live_updates")
          .select("*")
          .eq("story_memory_id", storyMemoryId)
          .is("merged_into_cluster_id", null)
          .order("discovered_at", { ascending: false })
          .limit(20);

        if (!cancelled && !error && data) {
          const incoming = data as LiveUpdate[];
          prevCountRef.current = incoming.length;
          setUpdates(incoming);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    run();
    return () => { cancelled = true; };
  }, [storyMemoryId]);

  /* Poll every 60 seconds when expanded */
  useEffect(() => {
    if (!isExpanded) return;
    const interval = setInterval(fetchUpdates, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [isExpanded, fetchUpdates]);

  /* Expand/collapse toggle */
  const handleToggle = useCallback(() => {
    setIsExpanded((prev) => {
      const next = !prev;
      if (next) {
        setHasNewWhileCollapsed(false);
        setNewCount(0);
        // Move focus into content after CSS transition (300ms)
        setTimeout(() => {
          const first = contentRef.current?.querySelector<HTMLElement>(
            "a, button, [tabindex]"
          );
          first?.focus({ preventScroll: true });
        }, 320);
      } else {
        // Return focus to trigger on collapse
        setTimeout(() => triggerRef.current?.focus({ preventScroll: true }), 50);
      }
      return next;
    });
  }, []);

  const handleShowAll = useCallback(() => {
    setShowAll(true);
  }, []);

  /* Nothing to show */
  if (isLoading) return null;
  if (!updates.length) return null;

  /* Slice updates for "show earlier" behaviour */
  const visibleUpdates = showAll ? updates : updates.slice(0, INITIAL_VISIBLE);
  const hiddenCount = updates.length - INITIAL_VISIBLE;
  const groups = groupUpdates(visibleUpdates);
  const mostRecentAt = updates[0]?.discovered_at;

  return (
    <section
      ref={sectionRef}
      className={`live-timeline${isExpanded ? " live-timeline--expanded" : ""}`}
      role="region"
      aria-labelledby={headingId}
    >
      {/* ----------------------------------------------------------------
          Trigger bar — always visible, collapsed by default
          ---------------------------------------------------------------- */}
      <button
        ref={triggerRef}
        id={headingId}
        className={`live-timeline__trigger${hasNewWhileCollapsed && !isExpanded ? " live-timeline__trigger--new" : ""}`}
        onClick={handleToggle}
        aria-expanded={isExpanded}
        aria-controls={contentId}
        type="button"
      >
        {/* Left: brand + live indicator */}
        <span className="live-timeline__trigger-left">
          <span className="live-timeline__live-dot" aria-hidden="true" />
          <span className="live-timeline__brand">void --live</span>
          <span className="live-timeline__sep" aria-hidden="true">·</span>
          <span className="live-timeline__count">
            {updates.length} update{updates.length !== 1 ? "s" : ""}
          </span>
          {mostRecentAt && (
            <>
              <span className="live-timeline__sep" aria-hidden="true">·</span>
              <time
                className="live-timeline__last-updated"
                dateTime={isoString(mostRecentAt)}
              >
                Updated {timeAgo(mostRecentAt)}
              </time>
            </>
          )}
        </span>

        {/* Right: new-update pill + chevron */}
        <span className="live-timeline__trigger-right" aria-hidden="true">
          {hasNewWhileCollapsed && !isExpanded && (
            <span className="live-timeline__new-pill">
              +{newCount} new
            </span>
          )}
          <span
            className={`live-timeline__chevron${isExpanded ? " live-timeline__chevron--open" : ""}`}
          >
            &#8964;
          </span>
        </span>
      </button>

      {/* ----------------------------------------------------------------
          Expandable content — grid-template-rows trick for smooth CSS animation
          ---------------------------------------------------------------- */}
      <div
        id={contentId}
        className={`live-timeline__body${isExpanded ? " live-timeline__body--open" : ""}`}
        role="list"
        aria-label="Live updates timeline"
      >
        <div ref={contentRef} className="live-timeline__inner">
          {groups.map((group, gi) => (
            <div
              key={`group-${gi}`}
              className="live-timeline__group"
              role="listitem"
            >
              {/* Group time marker — sits on the vertical rail */}
              <div className="live-timeline__node" aria-hidden="true">
                <span className="live-timeline__node-dot" />
                {gi < groups.length - 1 && (
                  <span className="live-timeline__node-line" />
                )}
              </div>

              {/* Updates in this group */}
              <div className="live-timeline__group-content">
                <time
                  className="live-timeline__group-time"
                  dateTime={isoString(group.timestamp)}
                >
                  {formatTimestamp(group.timestamp)}
                </time>

                {group.updates.map((update, ui) => (
                  <article
                    key={update.id}
                    className={`live-timeline__item${ui > 0 ? " live-timeline__item--stacked" : ""}`}
                    aria-label={update.title}
                  >
                    {/* Source attribution — the differentiator */}
                    <span className="live-timeline__source">
                      {update.source_name}
                    </span>

                    {/* Headline — links to original article */}
                    <a
                      href={update.article_url}
                      className="live-timeline__headline"
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {update.title}
                    </a>

                    {/* Delta summary — Gemini-generated "what's new" */}
                    {update.update_summary && (
                      <p className="live-timeline__delta">
                        {update.update_summary}
                      </p>
                    )}
                  </article>
                ))}
              </div>
            </div>
          ))}

          {/* Show earlier — revealed when >5 updates exist and not all shown */}
          {!showAll && hiddenCount > 0 && (
            <div className="live-timeline__show-earlier">
              <div className="live-timeline__earlier-rail" aria-hidden="true" />
              <button
                className="live-timeline__show-earlier-btn"
                onClick={handleShowAll}
                type="button"
              >
                Show {hiddenCount} earlier update{hiddenCount !== 1 ? "s" : ""}
              </button>
            </div>
          )}
        </div>
      </div>
    </section>
  );
});

export default LiveUpdatesSection;
