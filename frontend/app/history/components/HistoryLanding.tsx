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
      {/* ── Hero: Pull Quote ── */}
      <section className="hist-landing-hero hist-cold-open--hero" aria-label="Introduction">
        <blockquote className="hist-landing-hero__quote">
          &ldquo;History is not what happened. It is who told the story.&rdquo;
        </blockquote>
        <p className="hist-landing-hero__sub">
          {events.length} events. Multiple perspectives. Every side.
        </p>
      </section>

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
      className="hist-dossier"
      style={{ animationDelay: `${80 + index * 60}ms` }}
      aria-label={`${event.title} — ${event.datePrimary}`}
    >
      {/* Classified header strip */}
      <div className="hist-dossier__header">
        <span className="hist-dossier__classification">
          Declassified
        </span>
        <span className="hist-dossier__date">{event.datePrimary}</span>
      </div>

      {/* Title block */}
      <h3 className="hist-dossier__title">{event.title}</h3>

      {/* Subtitle / hook */}
      {event.subtitle && (
        <p className="hist-dossier__subtitle">{event.subtitle}</p>
      )}

      {/* Severity + perspectives count */}
      <div className="hist-dossier__meta">
        <span className={`hist-dossier__severity hist-dossier__severity--${event.severity}`}>
          {event.severity}
        </span>
        <span className="hist-dossier__perspectives">
          {event.perspectives.length} perspective{event.perspectives.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Teaser: one line from the context */}
      <p className="hist-dossier__teaser">
        {event.contextNarrative.split(". ").slice(0, 2).join(". ")}.
      </p>

      {/* Redaction bars for texture */}
      <div className="hist-dossier__bars" aria-hidden="true">
        <span className="hist-dossier__bar" />
        <span className="hist-dossier__bar hist-dossier__bar--short" />
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
      onClick={() => setRevealed((p) => !p)}
      aria-label={`Coming: ${event.title}`}
    >
      {/* Classified header strip */}
      <div className="hist-dossier__header">
        <span className="hist-dossier__classification hist-dossier__classification--classified">
          Classified
        </span>
        <span className="hist-dossier__date">{event.dateHint}</span>
      </div>

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

      {/* Stamp */}
      <span className="hist-dossier__stamp">[Declassified: Coming]</span>

      {/* Reveal overlay */}
      <div className="hist-dossier__reveal">
        <span className="hist-dossier__reveal-title">{event.title}</span>
      </div>
    </div>
  );
}
