"use client";

import { Suspense, useEffect, useState } from "react";
import type { HistoricalEvent, RedactedEvent } from "../history/types";
import { fetchHistoryEvents, fetchRedactedEvents } from "../history/data";
import ArchiveTabs from "./ArchiveTabs";

/* ===========================================================================
   /archive — one roof for void --history and void --revolt.
   Fetches the History data exactly as /history does (Revolt fetches its own
   inside RevoltTimeline), then hands both to the tabbed client shell. The
   original /history and /revolt routes stay intact so their deep sub-routes
   keep resolving; this is an entry-point merge, not a data re-architecture.
   =========================================================================== */

export default function ArchivePage() {
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
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    // useSearchParams() inside ArchiveTabs requires a Suspense boundary under
    // static export.
    <Suspense fallback={null}>
      <ArchiveTabs events={events} redacted={redacted} loading={loading} />
    </Suspense>
  );
}
