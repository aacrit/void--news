"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import type { HistoricalEvent } from "../../types";
import { ERAS } from "../../types";
import { fetchHistoryEventsByEra } from "../../data";
import EventCard from "../../components/EventCard";

/* ===========================================================================
   EraPageClient — Client component for era browser pages
   =========================================================================== */

interface EraPageClientProps {
  eraPromise: Promise<{ era: string }>;
}

export default function EraPageClient({ eraPromise }: EraPageClientProps) {
  const { era } = use(eraPromise);

  const [events, setEvents] = useState<HistoricalEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const eraInfo = ERAS.find((e) => e.id === era);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const evts = await fetchHistoryEventsByEra(era);
      if (!cancelled) {
        setEvents(evts);
        setLoading(false);
      }
    }

    if (era) load();
    return () => { cancelled = true; };
  }, [era]);

  if (!eraInfo) {
    return (
      <div className="hist-main hist-not-found">
        <h1>Era Not Found</h1>
        <Link href="/history" className="hist-breadcrumb">
          &larr; Back to archive
        </Link>
      </div>
    );
  }

  return (
    <div className="hist-main hist-grade">
      {/* Era header */}
      <section className="hist-browse-header">
        <Link href="/history" className="hist-breadcrumb">
          &larr; All eras
        </Link>
        <h1 className="hist-browse-title">
          {eraInfo.label}
        </h1>
        <p className="hist-breadcrumb" style={{ marginBottom: "var(--space-1)" }}>
          {eraInfo.dateRange}
        </p>
        <p className="hist-browse-description">
          {eraInfo.description}
        </p>
      </section>

      {/* Events */}
      {loading ? (
        <p className="hist-empty-state">
          Searching the archive...
        </p>
      ) : events.length > 0 ? (
        <div className="hist-card-grid">
          {events.map((event) => (
            <EventCard key={event.slug} event={event} />
          ))}
        </div>
      ) : (
        <p className="hist-empty-state">
          No events documented for this era yet.
        </p>
      )}

      {/* Era navigation */}
      <nav className="hist-compare-selector" style={{
        justifyContent: "center",
        paddingTop: "var(--space-6)",
        borderTop: "1px solid var(--hist-border-subtle)",
        marginTop: "var(--space-6)",
      }} aria-label="Browse other eras">
        {ERAS.map((e) => (
          <Link
            key={e.id}
            href={`/history/era/${e.id}`}
            className={`hist-compare-option ${e.id === era ? "hist-compare-option--active" : ""}`}
            aria-current={e.id === era ? "page" : undefined}
          >
            {e.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
