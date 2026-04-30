"use client";

import { useState, useEffect } from "react";
import type { HistoricalEvent, RedactedEvent } from "./types";
import { fetchHistoryEvents, fetchRedactedEvents } from "./data";
import HistoryLanding from "./components/HistoryLanding";

/* ===========================================================================
   /history — Landing page for void --history
   Fetches all events and redacted stubs, renders HistoryLanding.
   =========================================================================== */

export default function HistoryPage() {
  const [events, setEvents] = useState<HistoricalEvent[]>([]);
  const [redacted, setRedacted] = useState<RedactedEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const [evts, red] = await Promise.all([
        fetchHistoryEvents(),
        fetchRedactedEvents(),
      ]);
      if (!cancelled) {
        setEvents(evts);
        setRedacted(red);
        setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) {
    return (
      <div className="hist-main" style={{ paddingTop: "var(--space-7)", textAlign: "center" }}>
        <p style={{
          fontFamily: "var(--font-data)",
          fontSize: "var(--text-sm)",
          color: "var(--hist-ink-muted)",
          fontStyle: "italic",
        }}>
          Opening the archive...
        </p>
      </div>
    );
  }

  return <HistoryLanding events={events} redacted={redacted} />;
}
