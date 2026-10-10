"use client";

import { useState, useEffect } from "react";
import type { HistoricalEvent } from "../types";
import { fetchHistoryEvents } from "../data";
import { ARC_FEATURES } from "../arc-features";
import ThreadsLanding from "../components/ThreadsLanding";

/* ===========================================================================
   /history/threads — the CLIENT half.

   Split out of page.tsx so the route can own its metadata. While this WAS the
   route it carried "use client", and a client component cannot export
   `metadata` at all, so the served page inherited the root layout's title and
   the site-wide card. Same split /history and /sources already use. The fetch
   and the feature gate below are unchanged.
   =========================================================================== */

export default function ThreadsPageClient() {
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
