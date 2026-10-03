"use client";

import Link from "next/link";
import type { HistoricalEvent } from "../types";

/* ===========================================================================
   CompactTimeline — Prev / Current / Next for event detail pages
   Shows neighboring events on the timeline, current event highlighted.
   =========================================================================== */

interface CompactTimelineProps {
  events: HistoricalEvent[];
  currentSlug: string;
}

export default function CompactTimeline({ events, currentSlug }: CompactTimelineProps) {
  const sorted = [...events].sort((a, b) => a.dateSort - b.dateSort);
  const currentIdx = sorted.findIndex((e) => e.slug === currentSlug);

  if (currentIdx === -1) return null;

  const prev = currentIdx > 0 ? sorted[currentIdx - 1] : null;
  const next = currentIdx < sorted.length - 1 ? sorted[currentIdx + 1] : null;
  const current = sorted[currentIdx];

  return (
    <nav className="hist-compact-timeline" aria-label="Timeline navigation">
      {prev ? (
        <Link
          href={`/history/${prev.slug}`}
          className="hist-compact-timeline__link"
          aria-label={`Previous event: ${prev.title}`}
        >
          <span className="hist-compact-timeline__arrow">&larr;</span>
          <span className="hist-compact-timeline__label">{prev.datePrimary}</span>
          <span className="hist-compact-timeline__title">{prev.title}</span>
        </Link>
      ) : (
        <div style={{ flex: 1 }} />
      )}

      <div className="hist-compact-timeline__current" aria-current="page">
        <span className="hist-compact-timeline__current-dot" />
        <span className="hist-compact-timeline__label">{current.datePrimary}</span>
      </div>

      {next ? (
        <Link
          href={`/history/${next.slug}`}
          className="hist-compact-timeline__link"
          aria-label={`Next event: ${next.title}`}
        >
          <span className="hist-compact-timeline__arrow">&rarr;</span>
          <span className="hist-compact-timeline__label">{next.datePrimary}</span>
          <span className="hist-compact-timeline__title">{next.title}</span>
        </Link>
      ) : (
        <div style={{ flex: 1 }} />
      )}
    </nav>
  );
}
