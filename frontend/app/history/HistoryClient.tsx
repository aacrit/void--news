"use client";

import { useState, useEffect } from "react";
import type { HistoricalEvent, RedactedEvent } from "./types";
import { fetchHistoryEvents } from "./data";
import HistoryLanding from "./components/HistoryLanding";

/* ===========================================================================
   /history — the landing page's CLIENT half.

   Split out of page.tsx so the route can own its metadata. A Client Component
   cannot export `metadata` or `generateMetadata`, so while this file WAS the
   route, /history/ inherited the root layout: it shared the title "Void News.
   See through the void." and the site-wide card, and no share of any History
   link ever said what it was. Same split /sources and /about already use.

   The runtime fetch is now the FALLBACK, not the path. page.tsx reads the
   emitted catalogue at build and passes it in, so the served HTML carries the
   heading and all 78 event titles and links. The effect below runs only when
   that prop arrives empty, which means the snapshot was missing at build; it
   then fetches, and failing that `fetchHistoryEvents` returns mock data. A
   checkout that has never run the pipeline still renders a visibly
   placeholder archive rather than a blank page.
   =========================================================================== */

interface HistoryClientProps {
  events: HistoricalEvent[];
  redacted: RedactedEvent[];
}

export default function HistoryClient({ events, redacted }: HistoryClientProps) {
  const prerendered = events.length > 0;
  const [fetched, setFetched] = useState<HistoricalEvent[]>([]);
  const [loading, setLoading] = useState(!prerendered);

  useEffect(() => {
    if (prerendered) return;
    let cancelled = false;

    async function load() {
      const evts = await fetchHistoryEvents();
      if (!cancelled) {
        setFetched(evts);
        setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [prerendered]);

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

  return <HistoryLanding events={prerendered ? events : fetched} redacted={redacted} />;
}
