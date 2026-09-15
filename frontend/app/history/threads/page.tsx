"use client";

import { useState, useEffect } from "react";
import type { HistoricalEvent } from "../types";
import { fetchHistoryEvents } from "../data";
import { ARC_FEATURES } from "../arc-features";
import ThreadsLanding from "../components/ThreadsLanding";

/* ===========================================================================
   /history/threads — Thematic Threads across the archive
   Shows 5 editorial threads connecting events across centuries.
   =========================================================================== */

export default function ThreadsPage() {
  const [events, setEvents] = useState<HistoricalEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const evts = await fetchHistoryEvents();
      if (!cancelled) {
        setEvents(evts);
        setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  if (!ARC_FEATURES.LEDGER) {
    return (
      <div className="hist-main" style={{ paddingTop: "var(--space-7)", textAlign: "center" }}>
        <p style={{
          fontFamily: "var(--font-editorial)",
          fontSize: "var(--text-lg)",
          color: "var(--hist-ink-muted)",
          fontStyle: "italic",
        }}>
          Coming soon.
        </p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="hist-main" style={{ paddingTop: "var(--space-7)", textAlign: "center" }}>
        <p style={{
          fontFamily: "var(--font-data)",
          fontSize: "var(--text-sm)",
          color: "var(--hist-ink-muted)",
          fontStyle: "italic",
        }}>
          Tracing the threads...
        </p>
      </div>
    );
  }

  return <ThreadsLanding events={events} />;
}
