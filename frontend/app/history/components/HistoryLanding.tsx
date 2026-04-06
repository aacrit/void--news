"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { HistoricalEvent, RedactedEvent } from "../types";
import HistoryOverlay from "./HistoryOverlay";

/* ===========================================================================
   HistoryLanding — The Corridor
   Museum corridor. Events are spotlit exhibits in dim surroundings.
   Continuous vertical scroll with atmospheric fog between events.
   Cardinal rules: Show Not Tell. Arrive Late, Leave Early.
   =========================================================================== */

/* ── Hooks — story-specific, "Arrive Late, Leave Early" ── */
const HOOKS: Record<string, string> = {
  "partition-of-india":
    "A lawyer who\u2019d never been to India drew the border in five weeks. 15 million crossed it.",
  "hiroshima-nagasaki":
    "66,000 dead in 8.5 seconds. Seven of eight five-star American generals said it wasn\u2019t necessary.",
  "rwandan-genocide":
    "The UN had a fax warning them. They reduced their force from 2,500 to 270. 800,000 died in 100 days.",
};

/* ── CTAs — story-specific ── */
const CTAS: Record<string, string> = {
  "partition-of-india": "See how 4 nations remember August 15, 1947",
  "hiroshima-nagasaki":
    "Compare what Washington said vs. what survivors remember",
  "rwandan-genocide":
    "Read what the world chose not to see for 100 days",
};

/* ── Perspective color map ── */
const PERSP_COLORS: Record<string, string> = {
  a: "var(--hist-persp-a)",
  b: "var(--hist-persp-b)",
  c: "var(--hist-persp-c)",
  d: "var(--hist-persp-d)",
  e: "var(--hist-persp-e)",
};

/* ── Props ── */
interface HistoryLandingProps {
  events: HistoricalEvent[];
  redacted: RedactedEvent[];
}

export default function HistoryLanding({
  events,
  redacted,
}: HistoryLandingProps) {
  const corridorRef = useRef<HTMLDivElement>(null);
  const [activeOverlay, setActiveOverlay] = useState<{
    event: HistoricalEvent;
    sourceRect: DOMRect | null;
  } | null>(null);

  /* ── Scroll cinematography: poster reveal via IntersectionObserver ── */
  useEffect(() => {
    const posters = corridorRef.current?.querySelectorAll(".hist-poster");
    if (!posters || posters.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("hist-poster--visible");
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -40px 0px" }
    );

    posters.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [events]);

  /* ── Classified tile reveal observer ── */
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("hist-reveal--visible");
          }
        });
      },
      { threshold: 0.05, rootMargin: "0px 0px -30px 0px" }
    );
    const tiles = corridorRef.current?.querySelectorAll(".hist-classified-tile");
    tiles?.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [redacted]);

  /* ── Open story overlay ── */
  const openStory = useCallback(
    (event: HistoricalEvent, photoEl: HTMLElement | null) => {
      const rect = photoEl?.getBoundingClientRect() ?? null;
      setActiveOverlay({ event, sourceRect: rect });
    },
    []
  );

  /* ── Close overlay ── */
  const closeOverlay = useCallback(() => {
    setActiveOverlay(null);
  }, []);

  return (
    <div>
      <div ref={corridorRef} className="hist-corridor hist-grade">
        {/* ── Mission Brief — one line, cold open ── */}
        <header className="hist-brief" aria-label="Archive mission brief">
          <p className="hist-brief__line">
            One event. Every side. Decide for yourself.
          </p>
        </header>

        {/* ── Fog zone after brief ── */}
        <div className="hist-fog" aria-hidden="true" />

        {/* ── Event Posters ── */}
        {events.map((event, i) => (
          <div key={event.slug}>
            <EventPoster
              event={event}
              index={i}
              onOpen={openStory}
            />
            {/* Fog zone between events (not after the last) */}
            {i < events.length - 1 && (
              <div className="hist-fog" aria-hidden="true" />
            )}
          </div>
        ))}

        {/* ── Classified Section ── */}
        {redacted.length > 0 && (
          <>
            <div className="hist-fog" aria-hidden="true" />
            <div className="hist-classified-divider">
              <span className="hist-classified-divider__line" aria-hidden="true" />
              <span className="hist-classified-divider__label">
                CLASSIFIED — PENDING DECLASSIFICATION
              </span>
              <span className="hist-classified-divider__line" aria-hidden="true" />
            </div>

            <section
              className="hist-classified-feed"
              aria-label="Classified upcoming event dossiers"
            >
              {redacted.map((event, i) => (
                <ClassifiedTile key={event.slug} event={event} index={i} />
              ))}
            </section>
          </>
        )}
      </div>

      {/* ── Story Overlay ── */}
      {activeOverlay && (
        <HistoryOverlay
          event={activeOverlay.event}
          allEvents={events}
          sourceRect={activeOverlay.sourceRect}
          onClose={closeOverlay}
        />
      )}
    </div>
  );
}

/* ===========================================================================
   EventPoster — Full-width spotlit exhibit
   Archival photo (Ken Burns drift), date + title, THE HOOK,
   perspective dots (colored circles, no names), story-specific CTA.
   =========================================================================== */
function EventPoster({
  event,
  index,
  onOpen,
}: {
  event: HistoricalEvent;
  index: number;
  onOpen: (event: HistoricalEvent, photoEl: HTMLElement | null) => void;
}) {
  const photoRef = useRef<HTMLDivElement>(null);

  const hook =
    HOOKS[event.slug] ||
    event.contextNarrative.split(". ").slice(0, 2).join(". ") + ".";

  const cta =
    CTAS[event.slug] ||
    `Explore ${event.perspectives.length} accounts of ${event.title}`;

  const handleClick = useCallback(() => {
    onOpen(event, photoRef.current);
  }, [event, onOpen]);

  return (
    <article
      className="hist-poster"
      data-slug={event.slug}
      style={{ transitionDelay: index === 0 ? "300ms" : undefined }}
    >
      {/* 1. Full-width archival photo */}
      <div
        ref={photoRef}
        className="hist-poster__photo"
        data-slug={event.slug}
      >
        {event.heroImage ? (
          <img
            src={event.heroImage}
            alt={event.heroCaption ?? event.title}
            loading={index === 0 ? "eager" : "lazy"}
            onError={(e) => {
              e.currentTarget.style.display = "none";
            }}
          />
        ) : (
          <div className="hist-poster__photo-fallback" />
        )}
      </div>

      {/* 2. Date + Title */}
      <div className="hist-poster__body">
        <span className="hist-poster__date">{event.datePrimary}</span>
        <h3 className="hist-poster__title">{event.title}</h3>

        {/* 3. THE HOOK — the most important line */}
        <blockquote className="hist-poster__hook">{hook}</blockquote>

        {/* 4. Perspective dots — colored circles, no names */}
        <div className="hist-poster__dots" aria-label={`${event.perspectives.length} perspectives`}>
          {event.perspectives.map((p) => (
            <span
              key={p.id}
              className="hist-poster__dot"
              style={{ background: PERSP_COLORS[p.color] || PERSP_COLORS.a }}
              aria-hidden="true"
            />
          ))}
        </div>

        {/* 5. CTA — story-specific, prominent */}
        <button
          className="hist-poster__cta"
          onClick={handleClick}
          type="button"
        >
          {cta}
        </button>
      </div>
    </article>
  );
}

/* ===========================================================================
   ClassifiedTile — Desaturated, redacted text, click-to-flip
   =========================================================================== */
function ClassifiedTile({
  event,
  index,
}: {
  event: RedactedEvent;
  index: number;
}) {
  const [revealed, setRevealed] = useState(false);

  return (
    <div
      className={`hist-classified-tile hist-reveal ${revealed ? "hist-classified-tile--revealed" : ""}`}
      style={{ animationDelay: `${100 + index * 80}ms` }}
      role="button"
      tabIndex={0}
      onClick={() => setRevealed((p) => !p)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          setRevealed((p) => !p);
        }
      }}
      aria-label={`Coming: ${event.title}`}
      aria-pressed={revealed}
    >
      {/* Redacted title */}
      <h3 className="hist-classified-tile__title">
        {event.title.split(" ")[0]}{" "}
        <span className="hist-classified-tile__redacted">
          {event.title
            .split(" ")
            .slice(1)
            .map((w) => "\u2588".repeat(w.length))
            .join(" ")}
        </span>
      </h3>

      {/* Contradictory quotes */}
      {event.quoteA && (
        <p className="hist-classified-tile__quote">{event.quoteA}</p>
      )}
      {event.quoteB && (
        <p className="hist-classified-tile__quote hist-classified-tile__quote--b">
          {event.quoteB}
        </p>
      )}

      {/* Date hint + badge */}
      <div className="hist-classified-tile__meta">
        <span className="hist-classified-tile__date">{event.dateHint}</span>
        <span className="hist-classified-tile__badge">COMING</span>
      </div>

      {/* Reveal overlay */}
      <div className="hist-classified-tile__reveal" aria-hidden={!revealed}>
        <span className="hist-classified-tile__reveal-title">
          {event.title}
        </span>
        <span className="hist-classified-tile__reveal-hint">Coming soon</span>
      </div>
    </div>
  );
}
