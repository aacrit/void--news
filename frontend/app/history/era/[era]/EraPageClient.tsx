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
      <div className="hist-main" style={{ paddingTop: "var(--space-7)", textAlign: "center" }}>
        <h1 style={{
          fontFamily: "var(--font-editorial)",
          fontSize: "var(--text-xl)",
          fontWeight: 700,
          color: "var(--hist-ink)",
          marginBottom: "var(--space-3)",
        }}>
          Era Not Found
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
      {/* Era header */}
      <section style={{ padding: "var(--space-6) 0 var(--space-4)" }}>
        <Link href="/history" style={{
          fontFamily: "var(--font-data)",
          fontSize: "var(--text-xs)",
          color: "var(--hist-ink-muted)",
          textDecoration: "none",
          display: "inline-block",
          marginBottom: "var(--space-3)",
        }}>
          &larr; All eras
        </Link>
        <h1 style={{
          fontFamily: "var(--font-editorial)",
          fontSize: "clamp(1.5rem, 1.2rem + 1.2vw, 2.5rem)",
          fontWeight: 700,
          color: "var(--hist-ink)",
          marginBottom: "var(--space-2)",
        }}>
          {eraInfo.label}
        </h1>
        <p style={{
          fontFamily: "var(--font-data)",
          fontSize: "var(--text-sm)",
          color: "var(--hist-ink-muted)",
          marginBottom: "var(--space-1)",
        }}>
          {eraInfo.dateRange}
        </p>
        <p style={{
          fontFamily: "var(--font-structural)",
          fontSize: "var(--text-base)",
          color: "var(--hist-ink-secondary)",
          maxWidth: "600px",
        }}>
          {eraInfo.description}
        </p>
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
          No events documented for this era yet.
        </p>
      )}

      {/* Era navigation */}
      <nav style={{
        display: "flex",
        justifyContent: "center",
        gap: "var(--space-3)",
        flexWrap: "wrap",
        paddingTop: "var(--space-6)",
        borderTop: "1px solid var(--hist-border-subtle)",
        marginTop: "var(--space-6)",
      }} aria-label="Browse other eras">
        {ERAS.map((e) => (
          <Link
            key={e.id}
            href={`/history/era/${e.id}`}
            style={{
              fontFamily: "var(--font-meta)",
              fontSize: "var(--text-xs)",
              textTransform: "uppercase",
              letterSpacing: "0.06em",
              color: e.id === era ? "var(--hist-accent)" : "var(--hist-ink-muted)",
              textDecoration: e.id === era ? "underline" : "none",
              textUnderlineOffset: "3px",
              padding: "var(--space-1) var(--space-2)",
            }}
            aria-current={e.id === era ? "page" : undefined}
          >
            {e.label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
