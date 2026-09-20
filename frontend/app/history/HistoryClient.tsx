"use client";

import { useState, useEffect } from "react";
import type { HistoricalEvent, RedactedEvent } from "./types";
import { fetchHistoryEvents, fetchRedactedEvents } from "./data";
import HistoryLanding from "./components/HistoryLanding";

/* ===========================================================================
   /history — the landing page's CLIENT half.

   Split out of page.tsx so the route can own its metadata. A Client Component
   cannot export `metadata` or `generateMetadata`, so while this file WAS the
   route, /history/ inherited the root layout: it shared the title "Void News.
   See through the void." and the site-wide card, and no share of any History
   link ever said what it was. Same split /sources and /about already use.

   The runtime fetch below is unchanged and is still a known item: the landing
   shows a spinner where Weekly server-renders. That is a larger change (the
   filter state lives in HistoryLanding) and is deliberately not bundled with
   the metadata fix.
   =========================================================================== */

export default function HistoryClient() {
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
