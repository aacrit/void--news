"use client";

import type { HistoricalEvent } from "../types";

/* ===========================================================================
   KeyFacts — Structured fact block in IBM Plex Mono
   Date, Location, Key Actors, Death Toll, Displaced, Duration.
   Compact two-column layout.
   =========================================================================== */

interface KeyFactsProps {
  event: HistoricalEvent;
}

interface FactItem {
  label: string;
  value: string | undefined;
}

export default function KeyFacts({ event }: KeyFactsProps) {
  const facts: FactItem[] = [
    { label: "Date", value: event.dateRange || event.datePrimary },
    { label: "Location", value: event.location },
    { label: "Key Actors", value: event.keyFigures.map((f) => f.name).join(", ") },
    { label: "Death Toll", value: event.deathToll },
    { label: "Displaced", value: event.displaced },
    { label: "Duration", value: event.duration },
  ].filter((f) => f.value);

  if (facts.length === 0) return null;

  return (
    <div className="hist-key-facts" role="list" aria-label="Key facts">
      {facts.map((fact) => (
        <div key={fact.label} className="hist-key-fact" role="listitem">
          <span className="hist-key-fact__label">{fact.label}</span>
          <span className="hist-key-fact__value">{fact.value}</span>
        </div>
      ))}
    </div>
  );
}
