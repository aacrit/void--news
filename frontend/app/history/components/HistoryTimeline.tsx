"use client";

import Link from "next/link";
import type { HistoricalEvent } from "../types";

/* ===========================================================================
   HistoryTimeline — Full horizontal/vertical timeline
   Event dots positioned by date, era background bands, hover reveals title.
   Organic ink aesthetic for the timeline track.
   Desktop: horizontal scroll-snap. Mobile: vertical.
   =========================================================================== */

interface HistoryTimelineProps {
  events: HistoricalEvent[];
  activeSlug?: string;
}

/* Organic ink SVG track */
function InkTrack({ orientation = "horizontal" }: { orientation?: "horizontal" | "vertical" }) {
  if (orientation === "vertical") {
    return (
      <svg
        className="hist-timeline__track"
        viewBox="0 0 4 400"
        preserveAspectRatio="none"
        aria-hidden="true"
        style={{ width: "4px", height: "100%", position: "absolute", left: "50%", transform: "translateX(-50%)" }}
      >
        <path
          d="M2 0 C0.5 20, 3.5 40, 2 80 S0.5 160, 2 200 S3.5 280, 2 320 S0.5 380, 2 400"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
          opacity="0.25"
          strokeDasharray="8 4"
        />
      </svg>
    );
  }

  return (
    <svg
      className="hist-timeline__track"
      viewBox="0 0 400 4"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d="M0 2 C20 0.5, 40 3.5, 80 2 S160 0.5, 200 2 S280 3.5, 320 2 S380 0.5, 400 2"
        stroke="currentColor"
        strokeWidth="1.5"
        fill="none"
        opacity="0.25"
        strokeDasharray="8 4"
      />
    </svg>
  );
}

export default function HistoryTimeline({ events, activeSlug }: HistoryTimelineProps) {
  if (events.length === 0) return null;

  const sorted = [...events].sort((a, b) => a.dateSort - b.dateSort);

  return (
    <nav className="hist-timeline" aria-label="Event timeline">
      <InkTrack />
      <div className="hist-timeline__events">
        {sorted.map((event) => {
          const isActive = event.slug === activeSlug;
          return (
            <Link
              key={event.slug}
              href={`/history/${event.slug}`}
              className={`hist-timeline__dot ${isActive ? "hist-timeline__dot--active" : ""}`}
              aria-label={`${event.title} (${event.datePrimary})`}
              aria-current={isActive ? "page" : undefined}
            >
              <span className="hist-timeline__dot-circle" />
              <span className="hist-timeline__dot-label">{event.datePrimary}</span>
              <span className="hist-timeline__dot-title">{event.title}</span>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
