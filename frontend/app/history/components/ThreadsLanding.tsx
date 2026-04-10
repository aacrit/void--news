"use client";

import { useMemo } from "react";
import Link from "next/link";
import type { HistoricalEvent } from "../types";
import { THREADS } from "../threads";
import { HOOKS } from "../hooks";

/* ===========================================================================
   ThreadsLanding — Thematic thread strips across the full archive
   Each thread: label on far left, events sorted by dateSort across the strip.
   Event nodes show year + title + HOOK. No explanatory paragraphs.
   The juxtaposition of HOOKS does all the work.
   =========================================================================== */

interface ThreadsLandingProps {
  events: HistoricalEvent[];
}

export default function ThreadsLanding({ events }: ThreadsLandingProps) {
  /* Build lookup: slug -> event */
  const eventMap = useMemo(() => {
    const map = new Map<string, HistoricalEvent>();
    for (const e of events) {
      map.set(e.slug, e);
    }
    return map;
  }, [events]);

  /* Resolve thread events */
  const resolvedThreads = useMemo(() => {
    return THREADS.map((thread) => {
      const resolved = thread.eventSlugs
        .map((slug) => eventMap.get(slug))
        .filter((e): e is HistoricalEvent => e !== undefined)
        .sort((a, b) => a.dateSort - b.dateSort);
      return { ...thread, events: resolved };
    }).filter((t) => t.events.length >= 2);
  }, [eventMap]);

  return (
    <div className="hist-threads">
      <header className="hist-threads__header">
        <h1 className="hist-threads__title">Thematic Threads</h1>
        <p className="hist-threads__subtitle">
          <Link href="/history">
            &larr; Back to The Archive
          </Link>
        </p>
      </header>

      <div className="hist-threads__strips">
        {resolvedThreads.map((thread) => (
          <div key={thread.id} className="hist-threads__strip">
            <div className="hist-threads__strip-label" style={{ color: thread.colorVar }}>
              {thread.label}
            </div>
            <div className="hist-threads__strip-track">
              {thread.events.map((event, i) => {
                const year = extractDisplayYear(event);
                const hookText = HOOKS[event.slug] ?? "";

                return (
                  <div key={event.slug} className="hist-threads__node">
                    {/* Connecting line (not on first node) */}
                    {i > 0 && (
                      <hr
                        className="hist-threads__connector"
                        style={{ borderColor: thread.colorVar }}
                        aria-hidden="true"
                      />
                    )}
                    <Link
                      href={`/history/${event.slug}`}
                      className="hist-threads__node-card"
                    >
                      <span className="hist-threads__node-year">{year}</span>
                      <span className="hist-threads__node-title">{event.title}</span>
                      {hookText && (
                        <span className="hist-threads__node-hook">{hookText}</span>
                      )}
                    </Link>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Extract display year from dateSort ── */
function extractDisplayYear(event: HistoricalEvent): string {
  const abs = Math.abs(event.dateSort);
  const s = String(abs);
  if (s.length >= 8) {
    const y = s.slice(0, 4);
    return event.dateSort < 0 ? `${y} BCE` : y;
  }
  if (s.length >= 4) {
    const y = s.slice(0, s.length >= 8 ? 4 : s.length);
    return event.dateSort < 0 ? `${y} BCE` : y;
  }
  const match = event.datePrimary.match(/\d{4}/);
  return match ? match[0] : "";
}
