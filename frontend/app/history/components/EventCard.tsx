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
      aria-label={`${event.title}, ${event.datePrimary}`}
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
          {event.perspectives.length > 0 && (
            <span className="hist-event-card__perspectives">
              {event.perspectives.length} perspective{event.perspectives.length !== 1 ? "s" : ""}
            </span>
          )}
          {eraInfo && (
            <span className="hist-event-card__date">{eraInfo.label}</span>
          )}
          {/* A waveform, not a play triangle: the card links to the event, it
              does not start audio, and a triangle would promise a control that
              is not here. Carries a title + screen-reader label because on its
              own it is decoration. */}
          {event.audioUrl && (
            <span
              className="hist-event-card__audio"
              title="Audio edition available"
            >
              <svg width="14" height="10" viewBox="0 0 14 10" aria-hidden="true" focusable="false">
                <g fill="currentColor">
                  <rect x="0" y="4" width="1.5" height="2" rx="0.75" />
                  <rect x="3" y="2" width="1.5" height="6" rx="0.75" />
                  <rect x="6" y="0" width="1.5" height="10" rx="0.75" />
                  <rect x="9" y="2.5" width="1.5" height="5" rx="0.75" />
                  <rect x="12" y="4" width="1.5" height="2" rx="0.75" />
                </g>
              </svg>
              <span className="sr-only">Audio edition available</span>
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
