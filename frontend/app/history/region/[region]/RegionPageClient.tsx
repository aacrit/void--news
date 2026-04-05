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
      <div className="hist-main" style={{ paddingTop: "var(--space-7)", textAlign: "center" }}>
        <h1 style={{
          fontFamily: "var(--font-editorial)",
          fontSize: "var(--text-xl)",
          fontWeight: 700,
          color: "var(--hist-ink)",
          marginBottom: "var(--space-3)",
        }}>
          Region Not Found
        </h1>
        <Link href="/history" style={{
          fontFamily: "var(--font-data)",
          fontSize: "var(--text-sm)",
          color: "var(--hist-brass)",
        }}>
          &larr; Back to archive
        </Link>
      </div>
    );
  }

  return (
    <div className="hist-main hist-grade">
      {/* Region header */}
      <section style={{ padding: "var(--space-6) 0 var(--space-4)" }}>
        <Link href="/history" style={{
          fontFamily: "var(--font-data)",
          fontSize: "var(--text-xs)",
          color: "var(--hist-ink-muted)",
          textDecoration: "none",
          display: "inline-block",
          marginBottom: "var(--space-3)",
        }}>
          &larr; All regions
        </Link>
        <h1 style={{
          fontFamily: "var(--font-editorial)",
          fontSize: "clamp(1.5rem, 1.2rem + 1.2vw, 2.5rem)",
          fontWeight: 700,
          color: "var(--hist-ink)",
          marginBottom: "var(--space-3)",
        }}>
          {regionInfo.label}
        </h1>
      </section>

      {/* Events */}
      {loading ? (
        <p style={{
          fontFamily: "var(--font-data)",
          fontSize: "var(--text-sm)",
          color: "var(--hist-ink-muted)",
          fontStyle: "italic",
          textAlign: "center",
          padding: "var(--space-6) 0",
        }}>
          Searching the archive...
        </p>
      ) : events.length > 0 ? (
        <div className="hist-card-grid">
          {events.map((event) => (
            <EventCard key={event.slug} event={event} />
          ))}
        </div>
      ) : (
        <p style={{
          fontFamily: "var(--font-data)",
          fontSize: "var(--text-sm)",
          color: "var(--hist-ink-muted)",
          fontStyle: "italic",
          textAlign: "center",
          padding: "var(--space-6) 0",
        }}>
          No events documented for this region yet.
        </p>
      )}

      {/* Region navigation */}
      <nav style={{
        display: "flex",
        justifyContent: "center",
        gap: "var(--space-3)",
        flexWrap: "wrap",
        paddingTop: "var(--space-6)",
        borderTop: "1px solid var(--hist-border-subtle)",
        marginTop: "var(--space-6)",
      }} aria-label="Browse other regions">
        {REGIONS.filter((r) => r.id !== "global").map((r) => (
          <Link
            key={r.id}
            href={`/history/region/${r.id}`}
            style={{
              fontFamily: "var(--font-meta)",
              fontSize: "var(--text-xs)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              color: r.id === region ? "var(--hist-accent)" : "var(--hist-ink-muted)",
              textDecoration: r.id === region ? "underline" : "none",
              textUnderlineOffset: "3px",
              padding: "var(--space-1) var(--space-2)",
            }}
            aria-current={r.id === region ? "page" : undefined}
          >
            {r.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
