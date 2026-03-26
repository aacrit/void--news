"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { supabase } from "../lib/supabase";
import type { LiveUpdate } from "../lib/types";

interface LiveUpdatesInlineProps {
  storyMemoryId: string;
  maxVisible?: number;
}

const POLL_INTERVAL_MS = 60_000;

/**
 * Format timestamp for display:
 * - <1 hour: "2 min ago"
 * - Otherwise: "2:15 PM" (short, no date)
 */
function formatBulletTime(dateStr: string): string {
  const now = new Date();
  const then = new Date(dateStr);
  const diffMin = Math.floor((now.getTime() - then.getTime()) / 60_000);
  if (diffMin < 1) return "now";
  if (diffMin < 60) return `${diffMin}m ago`;
  return then.toLocaleString("en-US", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  });
}

/* ---------------------------------------------------------------------------
   LiveUpdatesInline — compact timestamped bullets embedded in LeadStory.
   Each bullet: time · source — one-liner
   Polls every 60s. Max 5 visible, "+N more" if overflow.
   --------------------------------------------------------------------------- */

export default function LiveUpdatesInline({
  storyMemoryId,
  maxVisible = 5,
}: LiveUpdatesInlineProps) {
  const [updates, setUpdates] = useState<LiveUpdate[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showAll, setShowAll] = useState(false);
  const prevCountRef = useRef(0);

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
        prevCountRef.current = data.length;
        setUpdates(data as LiveUpdate[]);
      }
    } finally {
      setIsLoading(false);
    }
  }, [storyMemoryId]);

  // Initial fetch
  useEffect(() => {
    fetchUpdates();
  }, [fetchUpdates]);

  // Poll every 60s
  useEffect(() => {
    const interval = setInterval(fetchUpdates, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [fetchUpdates]);

  if (isLoading || updates.length === 0) return null;

  const visible = showAll ? updates : updates.slice(0, maxVisible);
  const hiddenCount = updates.length - maxVisible;

  return (
    <div className="live-inline" role="list" aria-label="Live updates">
      <div className="live-inline__header">
        <span className="live-inline__dot" aria-hidden="true" />
        <span className="live-inline__label">Live</span>
      </div>

      {visible.map((update) => {
        const text = update.update_summary || update.title;
        const timeStr = formatBulletTime(update.discovered_at);
        return (
          <div key={update.id} className="live-inline__item" role="listitem">
            <time className="live-inline__time" dateTime={update.discovered_at}>
              {timeStr}
            </time>
            <span className="live-inline__source">{update.source_name}</span>
            <span className="live-inline__sep" aria-hidden="true">&mdash;</span>
            <a
              href={update.article_url}
              className="live-inline__text"
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
            >
              {text}
            </a>
          </div>
        );
      })}

      {!showAll && hiddenCount > 0 && (
        <button
          className="live-inline__more"
          onClick={(e) => { e.stopPropagation(); setShowAll(true); }}
          type="button"
        >
          +{hiddenCount} more update{hiddenCount !== 1 ? "s" : ""}
        </button>
      )}
    </div>
  );
}
