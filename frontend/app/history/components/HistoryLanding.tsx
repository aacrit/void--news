"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import type { HistoricalEvent, RedactedEvent, HistoryRegion } from "../types";
import { ERAS, REGIONS } from "../types";
import EventCard from "./EventCard";
import EraDrawer from "./EraDrawer";
import RedactedDossier from "./RedactedDossier";
import HistoryTimeline from "./HistoryTimeline";
import MapView from "./MapView";

/* ===========================================================================
   HistoryLanding — Main landing page for void --history
   Hero pull quote, timeline, era drawers, region pills, featured events,
   redacted dossier cards, map view.
   =========================================================================== */

interface HistoryLandingProps {
  events: HistoricalEvent[];
  redacted: RedactedEvent[];
}

/* ── Organic Ink Divider ── */
function InkRule() {
  return (
    <svg
      className="hist-ink-rule"
      viewBox="0 0 400 4"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d="M0 2 C20 0.5, 40 3.5, 80 2 S160 0.5, 200 2 S280 3.5, 320 2 S380 0.5, 400 2"
        stroke="currentColor"
        strokeWidth="1.2"
        fill="none"
        opacity="0.35"
      />
    </svg>
  );
}

export default function HistoryLanding({ events, redacted }: HistoryLandingProps) {
  const [activeRegion, setActiveRegion] = useState<HistoryRegion | null>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  /* Filter events by region */
  const filteredEvents = useMemo(() => {
    if (!activeRegion) return events;
    return events.filter((e) => e.regions.includes(activeRegion));
  }, [events, activeRegion]);

  /* Group events by era */
  const eventsByEra = useMemo(() => {
    const map = new Map<string, HistoricalEvent[]>();
    ERAS.forEach((era) => map.set(era.id, []));
    filteredEvents.forEach((event) => {
      const list = map.get(event.era);
      if (list) list.push(event);
    });
    return map;
  }, [filteredEvents]);

  /* Featured events (first 3) */
  const featured = useMemo(
    () => filteredEvents.slice(0, 3),
    [filteredEvents]
  );

  /* Scroll reveal */
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("hist-reveal--visible");
          }
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );

    const sections = contentRef.current?.querySelectorAll(".hist-reveal");
    sections?.forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [filteredEvents]);

  return (
    <div ref={contentRef}>
      {/* ── Hero: Pull Quote ── */}
      <section className="hist-landing-hero hist-cold-open--hero" aria-label="Introduction">
        <blockquote className="hist-landing-hero__quote">
          &ldquo;History is not what happened. It is who told the story.&rdquo;
        </blockquote>
        <p className="hist-landing-hero__attribution">
          &mdash; The same event, told by the victor, the vanquished, and the bystander,
          becomes three different truths.
        </p>
      </section>

      <div className="hist-main hist-grade">
        {/* ── Timeline Hero ── */}
        <div className="hist-reveal">
          <HistoryTimeline events={events} />
        </div>

        <InkRule />

        {/* ── Map View ── */}
        <div className="hist-reveal">
          <h2 className="hist-section-label">Geographic Scope</h2>
          <MapView
            events={filteredEvents}
            activeRegion={activeRegion ?? undefined}
            onRegionClick={(region) => {
              setActiveRegion(region === activeRegion ? null : region);
            }}
          />
        </div>

        {/* ── Region Pills ── */}
        <div className="hist-reveal">
          <div className="hist-region-pills" role="group" aria-label="Filter by region">
            <button
              className={`hist-region-pill ${!activeRegion ? "hist-region-pill--active" : ""}`}
              onClick={() => setActiveRegion(null)}
              aria-pressed={!activeRegion}
            >
              All Regions
            </button>
            {REGIONS.filter((r) => r.id !== "global").map((region) => {
              const count = events.filter((e) => e.regions.includes(region.id)).length;
              if (count === 0) return null;
              return (
                <button
                  key={region.id}
                  className={`hist-region-pill ${activeRegion === region.id ? "hist-region-pill--active" : ""}`}
                  onClick={() =>
                    setActiveRegion(region.id === activeRegion ? null : region.id)
                  }
                  aria-pressed={activeRegion === region.id}
                >
                  {region.label} ({count})
                </button>
              );
            })}
          </div>
        </div>

        <InkRule />

        {/* ── Featured Events ── */}
        {featured.length > 0 && (
          <section className="hist-reveal hist-featured" aria-label="Featured events">
            <h2 className="hist-section-label">Featured Events</h2>
            <div className="hist-card-grid">
              {featured.map((event) => (
                <EventCard key={event.slug} event={event} />
              ))}
            </div>
          </section>
        )}

        <InkRule />

        {/* ── Era Drawers ── */}
        <section className="hist-reveal" aria-label="Browse by era">
          <h2 className="hist-section-label">Browse by Era</h2>
          {ERAS.map((era) => {
            const eraEvents = eventsByEra.get(era.id) ?? [];
            return (
              <EraDrawer
                key={era.id}
                era={era}
                events={eraEvents}
                defaultOpen={eraEvents.length > 0}
              />
            );
          })}
        </section>

        <InkRule />

        {/* ── Redacted Dossiers: Coming ── */}
        {redacted.length > 0 && (
          <section className="hist-reveal" aria-label="Coming events">
            <h2 className="hist-section-label">Classified Dossiers</h2>
            <p style={{
              fontFamily: "var(--font-structural)",
              fontSize: "var(--text-sm)",
              color: "var(--hist-ink-muted)",
              marginBottom: "var(--space-4)",
              maxWidth: "600px",
            }}>
              These events are being researched and documented. Each will present
              the contradictory perspectives that history has recorded.
            </p>
            <div className="hist-card-grid">
              {redacted.map((event) => (
                <RedactedDossier key={event.slug} event={event} />
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
