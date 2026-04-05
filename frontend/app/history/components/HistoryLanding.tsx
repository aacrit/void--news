"use client";

import { useState, useEffect, useRef } from "react";
import Link from "next/link";
import type { HistoricalEvent, RedactedEvent } from "../types";
import LogoIcon from "../../components/LogoIcon";

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
      {/* ── SVG Defs: Organic Clip-Path Shapes ──
          4 hand-drawn document edge shapes for dossier tiles.
          Each mimics torn/foxed/weathered manuscript edges. */}
      <svg width="0" height="0" aria-hidden="true" style={{ position: "absolute" }}>
        <defs>
          {/* Shape 1: Slightly ragged left + bottom edges */}
          <clipPath id="hist-organic-edge-1" clipPathUnits="objectBoundingBox">
            <path d="M0.01,0.005 L0.98,0 C0.99,0 1,0.01 0.995,0.03 L1,0.97 C1,0.99 0.985,1 0.97,0.995 L0.03,1 C0.015,1 0.005,0.99 0,0.97 L0.005,0.04 C0.002,0.02 0,0.01 0.01,0.005Z" />
          </clipPath>
          {/* Shape 2: Torn top-right corner */}
          <clipPath id="hist-organic-edge-2" clipPathUnits="objectBoundingBox">
            <path d="M0.005,0.01 L0.93,0 C0.95,0.005 0.97,0.008 0.985,0.02 C1,0.03 0.995,0.04 1,0.06 L0.995,0.96 C0.998,0.98 0.99,0.995 0.97,1 L0.02,0.995 C0.01,0.998 0,0.985 0,0.97 L0.008,0.03 C0.003,0.02 0,0.01 0.005,0.01Z" />
          </clipPath>
          {/* Shape 3: Soft wavy bottom edge */}
          <clipPath id="hist-organic-edge-3" clipPathUnits="objectBoundingBox">
            <path d="M0.008,0 L0.99,0.005 C0.995,0.005 1,0.02 1,0.03 L0.995,0.94 C0.99,0.96 0.97,0.99 0.94,0.995 C0.85,1 0.72,0.985 0.6,0.995 C0.48,1 0.35,0.985 0.22,0.998 C0.12,0.99 0.04,1 0.02,0.995 C0.005,0.99 0,0.97 0,0.95 L0.005,0.03 C0.003,0.01 0.005,0 0.008,0Z" />
          </clipPath>
          {/* Shape 4: Irregular left edge, pinched corners */}
          <clipPath id="hist-organic-edge-4" clipPathUnits="objectBoundingBox">
            <path d="M0.02,0.008 L0.975,0 C0.99,0.003 1,0.015 0.998,0.03 L1,0.965 C0.998,0.985 0.985,1 0.965,0.998 L0.03,1 C0.015,0.995 0.008,0.985 0.005,0.965 C0,0.85 0.01,0.7 0.005,0.55 C0,0.4 0.01,0.25 0.005,0.12 C0.003,0.06 0,0.03 0.02,0.008Z" />
          </clipPath>
        </defs>
      </svg>

      {/* ── Hero: Pull Quote ── */}
      <section className="hist-landing-hero hist-cold-open--hero" aria-label="Introduction">
        <div className="hist-landing-hero__logo" aria-hidden="true">
          <LogoIcon size={32} animation="idle" />
        </div>
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
      role="button"
      tabIndex={0}
      onClick={() => setRevealed((p) => !p)}
      onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setRevealed((p) => !p); } }}
      aria-label={`Coming: ${event.title}`}
      aria-pressed={revealed}
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
