"use client";

import { useState, useEffect, use } from "react";
import type { HistoricalEvent } from "../types";
import { fetchHistoryEvent, fetchHistoryEvents } from "../data";
import EventDetail from "../components/EventDetail";

/* ===========================================================================
   EventPageClient — Client component for event detail pages
   Receives slug via promise (Next.js 16 async params pattern).
   =========================================================================== */

interface EventPageClientProps {
  slugPromise: Promise<{ slug: string }>;
}

export default function EventPageClient({ slugPromise }: EventPageClientProps) {
  const { slug } = use(slugPromise);

  const [event, setEvent] = useState<HistoricalEvent | null>(null);
  const [allEvents, setAllEvents] = useState<HistoricalEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const [evt, all] = await Promise.all([
        fetchHistoryEvent(slug),
        fetchHistoryEvents(),
      ]);
      if (!cancelled) {
        if (!evt) {
          setNotFound(true);
        } else {
          setEvent(evt);
          setAllEvents(all);
        }
        setLoading(false);
      }
    }

    if (slug) load();
    return () => { cancelled = true; };
  }, [slug]);

  if (loading) {
    return (
      <div className="hist-main hist-loading-state">
        <p>Retrieving archival record...</p>
      </div>
    );
  }

  if (notFound || !event) {
    return (
      <div className="hist-main hist-not-found">
        <h1>Record Not Found</h1>
        <p>This archival record has not been declassified or does not exist.</p>
      </div>
    );
  }

  return <EventDetail event={event} allEvents={allEvents} />;
}
