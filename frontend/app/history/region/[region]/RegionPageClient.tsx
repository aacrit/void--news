"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import type { HistoricalEvent } from "../../types";
import { REGIONS } from "../../types";
import { fetchHistoryEventsByRegion } from "../../data";
import EventCard from "../../components/EventCard";

/* ===========================================================================
   RegionPageClient — Client component for region explorer pages
   =========================================================================== */

interface RegionPageClientProps {
  regionPromise: Promise<{ region: string }>;
}

export default function RegionPageClient({ regionPromise }: RegionPageClientProps) {
  const { region } = use(regionPromise);

  const [events, setEvents] = useState<HistoricalEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const regionInfo = REGIONS.find((r) => r.id === region);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      const evts = await fetchHistoryEventsByRegion(region);
      if (!cancelled) {
        setEvents(evts);
        setLoading(false);
      }
    }

    if (region) load();
    return () => { cancelled = true; };
  }, [region]);

  if (!regionInfo) {
    return (
      <div className="hist-main hist-not-found">
        <h1>Region Not Found</h1>
        <Link href="/history" className="hist-breadcrumb">
          &larr; Back to archive
        </Link>
      </div>
    );
  }

  return (
    <div className="hist-main hist-grade">
      {/* Region header */}
      <section className="hist-browse-header">
        <Link href="/history" className="hist-breadcrumb">
          &larr; All regions
        </Link>
        <h1 className="hist-browse-title">
          {regionInfo.label}
        </h1>
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
          No events documented for this region yet.
        </p>
      )}

      {/* Region navigation */}
      <nav className="hist-compare-selector" style={{
        justifyContent: "center",
        paddingTop: "var(--space-6)",
        borderTop: "1px solid var(--hist-border-subtle)",
        marginTop: "var(--space-6)",
      }} aria-label="Browse other regions">
        {REGIONS.filter((r) => r.id !== "global").map((r) => (
          <Link
            key={r.id}
            href={`/history/region/${r.id}`}
            className={`hist-compare-option ${r.id === region ? "hist-compare-option--active" : ""}`}
            aria-current={r.id === region ? "page" : undefined}
          >
            {r.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
