"use client";

import { useState, useEffect } from "react";
import { supabase } from "../lib/supabase";
import type { LiveUpdate } from "../lib/types";
import { timeAgo } from "../lib/utils";

interface LiveUpdatesSectionProps {
  storyMemoryId: string;
}

/**
 * LiveUpdatesSection — displays articles discovered by the live poller
 * between pipeline runs for the current top story.
 *
 * Polls Supabase every 90 seconds for fresh updates. Only renders when
 * there are actual live updates to show.
 */
export default function LiveUpdatesSection({ storyMemoryId }: LiveUpdatesSectionProps) {
  const [updates, setUpdates] = useState<LiveUpdate[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const fetchUpdates = async () => {
      if (!supabase) return;
      try {
        const { data, error } = await supabase
          .from("live_updates")
          .select("*")
          .eq("story_memory_id", storyMemoryId)
          .is("merged_into_cluster_id", null)
          .order("discovered_at", { ascending: false })
          .limit(10);

        if (!cancelled && !error) {
          setUpdates(data || []);
        }
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    fetchUpdates();

    // Poll every 90 seconds for fresh updates
    const interval = setInterval(fetchUpdates, 90_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [storyMemoryId]);

  if (isLoading) {
    return (
      <div className="live-updates-section" aria-busy="true">
        <div className="live-updates__skeleton" />
      </div>
    );
  }

  if (!updates.length) return null;

  return (
    <section className="live-updates-section" role="region" aria-label="Live Updates">
      <h3 className="live-updates__header">
        <span className="live-updates__icon" aria-hidden="true">&#9679;</span>
        Latest Updates ({updates.length})
      </h3>

      <div className="live-updates__list">
        {updates.map((update) => (
          <a
            key={update.id}
            href={update.article_url}
            className="live-update-card"
            target="_blank"
            rel="noopener noreferrer"
          >
            <div className="live-update__meta">
              <time
                className="live-update__time"
                dateTime={update.discovered_at}
              >
                {timeAgo(update.discovered_at)}
              </time>
              <span className="live-update__source">{update.source_name}</span>
            </div>
            <h4 className="live-update__title">{update.title}</h4>
            {update.update_summary && (
              <p className="live-update__summary">{update.update_summary}</p>
            )}
          </a>
        ))}
      </div>
    </section>
  );
}
