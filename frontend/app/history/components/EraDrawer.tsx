/* DEFERRED: Not rendered in current version. Preserved for Phase 2. */
"use client";

import { useState } from "react";
import type { HistoricalEvent, EraInfo } from "../types";
import EventCard from "./EventCard";

/* ===========================================================================
   EraDrawer — Expandable era section
   Era name + date range + event count header. Slides open to reveal
   EventCards within. Unfold animation via CSS.
   =========================================================================== */

interface EraDrawerProps {
  era: EraInfo;
  events: HistoricalEvent[];
  defaultOpen?: boolean;
}

export default function EraDrawer({ era, events, defaultOpen = false }: EraDrawerProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className={`hist-era-drawer ${isOpen ? "hist-era-drawer--open" : ""}`}>
      <button
        className="hist-era-drawer__header"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
        aria-controls={`era-content-${era.id}`}
      >
        <div className="hist-era-drawer__left">
          <span className="hist-era-drawer__name">{era.label}</span>
          <span className="hist-era-drawer__range">{era.dateRange}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
          <span className="hist-era-drawer__count">
            {events.length} event{events.length !== 1 ? "s" : ""}
          </span>
          <span className="hist-era-drawer__chevron" aria-hidden="true">
            &#9662;
          </span>
        </div>
      </button>
      <div
        className="hist-era-drawer__content"
        id={`era-content-${era.id}`}
        role="region"
        aria-label={`${era.label} era events`}
      >
        {events.length > 0 ? (
          <div className="hist-card-grid">
            {events.map((event) => (
              <EventCard key={event.slug} event={event} />
            ))}
          </div>
        ) : (
          <p style={{
            fontFamily: "var(--font-data)",
            fontSize: "var(--text-sm)",
            color: "var(--hist-ink-muted)",
            fontStyle: "italic",
            padding: "var(--space-4) 0",
          }}>
            Events for this era are being researched and documented.
          </p>
        )}
      </div>
    </div>
  );
}
