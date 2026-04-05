"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import type { HistoricalEvent, RedactedEvent } from "../types";

/* ===========================================================================
   HistoryLanding — Dossier-first landing for void --history
   Simple classified dossier tiles as primary entry. Everything else secondary.
   =========================================================================== */

interface HistoryLandingProps {
  events: HistoricalEvent[];
  redacted: RedactedEvent[];
}

export default function HistoryLanding({ events, redacted }: HistoryLandingProps) {
  const contentRef = useRef<HTMLDivElement>(null);

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
  }, [events]);

  return (
    <div ref={contentRef}>
      <div className="hist-main hist-grade">
        {/* ── Primary: Dossier Grid ── */}
        <section className="hist-reveal hist-dossier-grid" aria-label="Historical events">
          {events.map((event, i) => (
            <DossierTile key={event.slug} event={event} index={i} />
          ))}
          {redacted.map((event, i) => (
            <RedactedTile key={event.slug} event={event} index={events.length + i} />
          ))}
        </section>
      </div>
    </div>
  );
}

/* ── Dossier Tile: Published Event ── */
function DossierTile({ event, index }: { event: HistoricalEvent; index: number }) {
  return (
    <Link
      href={`/history/${event.slug}`}
      className={`hist-dossier hist-dossier--severity-${event.severity}`}
      style={{ animationDelay: `${80 + index * 60}ms` }}
      aria-label={`${event.title} — ${event.datePrimary}`}
    >
      {/* Title block */}
      <h3 className="hist-dossier__title">{event.title}</h3>

      {/* Subtitle / hook */}
      {event.subtitle && (
        <p className="hist-dossier__subtitle">{event.subtitle}</p>
      )}

      {/* Date + perspectives count */}
      <div className="hist-dossier__meta">
        <span className="hist-dossier__date">{event.datePrimary}</span>
        <span className="hist-dossier__perspectives">
          {event.perspectives.length} perspective{event.perspectives.length !== 1 ? "s" : ""}
        </span>
      </div>
    </Link>
  );
}

/* ── Redacted Tile: Coming Event ── */
function RedactedTile({ event, index }: { event: RedactedEvent; index: number }) {
  const [revealed, setRevealed] = useState(false);

  return (
    <div
      className={`hist-dossier hist-dossier--classified ${revealed ? "hist-dossier--revealed" : ""}`}
      style={{ animationDelay: `${80 + index * 60}ms` }}
      role="button"
      tabIndex={0}
      onClick={() => setRevealed((p) => !p)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setRevealed((p) => !p); } }}
      aria-label={`Coming: ${event.title}`}
      aria-pressed={revealed}
    >
      {/* Redacted title */}
      <h3 className="hist-dossier__title hist-dossier__title--redacted">
        {event.title.split(" ")[0]}{" "}
        <span className="hist-dossier__redacted-text">
          {event.title.split(" ").slice(1).map((w) => "\u2588".repeat(w.length)).join(" ")}
        </span>
      </h3>

      {/* Contradictory quotes */}
      {event.quoteA && (
        <p className="hist-dossier__quote">&ldquo;{event.quoteA}&rdquo;</p>
      )}
      {event.quoteB && (
        <p className="hist-dossier__quote hist-dossier__quote--b">&ldquo;{event.quoteB}&rdquo;</p>
      )}

      {/* Date hint */}
      <div className="hist-dossier__meta">
        <span className="hist-dossier__date">{event.dateHint}</span>
        <span className="hist-dossier__classification hist-dossier__classification--classified">
          Classified
        </span>
      </div>

      {/* Reveal overlay */}
      <div className="hist-dossier__reveal">
        <span className="hist-dossier__reveal-title">{event.title}</span>
      </div>
    </div>
  );
}
