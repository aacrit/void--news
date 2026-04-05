"use client";

import Link from "next/link";
import type { HistoricalEvent } from "../types";
import { ERAS, REGIONS } from "../types";

/* ===========================================================================
   EventCard — Archive document card for event listings
   Hero thumbnail + archival grade filter + metadata.
   =========================================================================== */

interface EventCardProps {
  event: HistoricalEvent;
}

export default function EventCard({ event }: EventCardProps) {
  const eraInfo = ERAS.find((e) => e.id === event.era);
  const primaryRegion = REGIONS.find((r) => r.id === event.regions[0]);

  return (
    <Link
      href={`/history/${event.slug}`}
      className="hist-event-card"
      aria-label={`${event.title} — ${event.datePrimary}`}
    >
      <div className="hist-event-card__image">
        {event.heroImage ? (
          <img
            src={event.heroImage}
            alt={event.heroCaption ?? event.title}
            loading="lazy"
          />
        ) : (
          <div
            style={{
              width: "100%",
              height: "100%",
              background: `linear-gradient(135deg, var(--hist-paper-deep) 0%, var(--hist-bg-card) 100%)`,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-editorial)",
                fontSize: "var(--text-xl)",
                fontWeight: 700,
                color: "var(--hist-ink-muted)",
                opacity: 0.3,
              }}
            >
              {event.title.charAt(0)}
            </span>
          </div>
        )}
        {event.severity && (
          <span
            className={`hist-event-card__severity hist-event-card__severity--${event.severity}`}
          >
            {event.severity}
          </span>
        )}
      </div>
      <div className="hist-event-card__body">
        <span className="hist-event-card__region">
          {primaryRegion?.label ?? event.regions[0]}
        </span>
        <h3 className="hist-event-card__title">{event.title}</h3>
        <span className="hist-event-card__date">{event.datePrimary}</span>
        <div className="hist-event-card__meta">
          <span className="hist-event-card__perspectives">
            {event.perspectives.length} perspective{event.perspectives.length !== 1 ? "s" : ""}
          </span>
          {eraInfo && (
            <span className="hist-event-card__date">{eraInfo.label}</span>
          )}
        </div>
      </div>
    </Link>
  );
}
