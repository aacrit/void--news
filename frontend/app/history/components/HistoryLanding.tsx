"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { HistoricalEvent, RedactedEvent } from "../types";
import HistoryOverlay from "./HistoryOverlay";

/* ===========================================================================
   HistoryLanding — Full-width vertical tiles for void --history
   P1: Content is the cinematography. Divergence teasers, death tolls,
       contradictory quotes ARE the cinematic moments.
   P2: One surface, no portals. Story loads as overlay. No router.push.
   P3: Tiles at full size. Flat, generous. Depth from focus/blur on scroll.
   P4: Divergence is the hook. Teaser is LARGEST text on each tile.
   P5: Organic means texture, not geometry. No clip-path polygons.
   =========================================================================== */

/* ── Void Voice Blurbs — wired, punchy, concrete ── */
const BLURBS: Record<string, string> = {
  "partition-of-india":
    "A lawyer who\u2019d never been to India drew the border in five weeks. 15 million crossed it. Trains arrived carrying only corpses.",
  "hiroshima-nagasaki":
    "66,000 dead in 8.5 seconds. Two governments still disagree about why it was necessary. Seven of eight five-star U.S. officers said it wasn\u2019t.",
  "rwandan-genocide":
    "100 days. 800,000 dead. The killing rate exceeded the Holocaust. The UN reduced its force from 2,500 to 270 and left.",
};

/* ── Divergence Teasers — one-line perspective clash ── */
const DIVERGENCE_TEASERS: Record<string, string> = {
  "partition-of-india":
    "Britain says \u2018orderly transfer.\u2019 India says \u2018imperial sabotage.\u2019 Pakistan says \u2018democratic creation.\u2019",
  "hiroshima-nagasaki":
    "Washington says \u2018saved a million lives.\u2019 Survivors say \u2018my classmate Emiko couldn\u2019t find her mother.\u2019 Historians say \u2018Japan was already seeking surrender.\u2019",
  "rwandan-genocide":
    "Survivors say \u2018the neighbors came with lists.\u2019 The UN says \u2018our mandate was limited.\u2019 Scholars say \u2018colonial categories marked people for death.\u2019",
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
  const feedRef = useRef<HTMLDivElement>(null);
  const [activeOverlay, setActiveOverlay] = useState<{
    event: HistoricalEvent;
    sourceRect: DOMRect | null;
  } | null>(null);

  /* ── Scroll cinematography: rack focus via IntersectionObserver ── */
  useEffect(() => {
    const tiles = feedRef.current?.querySelectorAll(".hist-event-tile");
    if (!tiles || tiles.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.3) {
            entry.target.classList.remove("hist-event-tile--blurred");
          } else {
            entry.target.classList.add("hist-event-tile--blurred");
          }
        });
      },
      { threshold: [0, 0.3, 0.6], rootMargin: "-10% 0px -10% 0px" }
    );

    tiles.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [events]);

  /* ── Cold open stagger ── */
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
    const tiles = feedRef.current?.querySelectorAll(".hist-event-tile, .hist-classified-tile");
    tiles?.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [events, redacted]);

  /* ── Open story overlay ── */
  const openStory = useCallback((event: HistoricalEvent, photoEl: HTMLElement | null) => {
    const rect = photoEl?.getBoundingClientRect() ?? null;
    setActiveOverlay({ event, sourceRect: rect });
  }, []);

  /* ── Close overlay: restore URL + scroll ── */
  const closeOverlay = useCallback(() => {
    setActiveOverlay(null);
    /* URL is restored by popstate/history.back in the overlay */
  }, []);

  return (
    <div>
      <div className="hist-main hist-grade">
        {/* ── Mission Brief ── */}
        <header className="hist-brief" aria-label="Archive mission brief">
          <h2 className="hist-brief__title">THE ARCHIVE</h2>
          <p className="hist-brief__line">
            One event. Every side. Decide for yourself.
          </p>
        </header>

        {/* ── Event Tiles — full-width vertical sections ── */}
        <section
          ref={feedRef}
          className="hist-event-feed"
          aria-label="Historical event archive"
        >
          {events.map((event, i) => (
            <EventTile
              key={event.slug}
              event={event}
              index={i}
              onOpen={openStory}
            />
          ))}
        </section>

        {/* ── Classified Divider ── */}
        {redacted.length > 0 && (
          <div className="hist-classified-divider">
            <span className="hist-classified-divider__line" aria-hidden="true" />
            <span className="hist-classified-divider__label">CLASSIFIED — PENDING DECLASSIFICATION</span>
            <span className="hist-classified-divider__line" aria-hidden="true" />
          </div>
        )}

        {/* ── Classified Tiles ── */}
        {redacted.length > 0 && (
          <section
            className="hist-classified-feed"
            aria-label="Classified upcoming event dossiers"
          >
            {redacted.map((event, i) => (
              <ClassifiedTile key={event.slug} event={event} index={i} />
            ))}
          </section>
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
   EventTile — Full-width vertical section for a published event
   Photo on top, title block below, divergence teaser as largest text,
   perspective dots, stark data, specific CTA.
   =========================================================================== */
function EventTile({
  event,
  index,
  onOpen,
}: {
  event: HistoricalEvent;
  index: number;
  onOpen: (event: HistoricalEvent, photoEl: HTMLElement | null) => void;
}) {
  const photoRef = useRef<HTMLDivElement>(null);
  const divergenceTeaser =
    DIVERGENCE_TEASERS[event.slug] ||
    event.perspectives
      .slice(0, 3)
      .map((p) => `${p.viewpointName} says \u2018${p.keyNarratives[0]?.toLowerCase() ?? "..."}\u2019`)
      .join(" ");

  const blurb =
    BLURBS[event.slug] ||
    event.contextNarrative.split(". ").slice(0, 2).join(". ") + ".";

  const handleClick = useCallback(() => {
    onOpen(event, photoRef.current);
  }, [event, onOpen]);

  return (
    <article
      className="hist-event-tile hist-reveal"
      data-slug={event.slug}
      style={{ animationDelay: `${100 + index * 120}ms` }}
    >
      {/* 1. Full-width archival photo */}
      <div
        ref={photoRef}
        className="hist-event-tile__photo"
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
          <div className="hist-event-tile__photo-fallback" />
        )}
      </div>

      {/* 2. Title block — below the photo */}
      <div className="hist-event-tile__body">
        <span className="hist-event-tile__date">{event.datePrimary}</span>
        <h3 className="hist-event-tile__title">{event.title}</h3>
        {event.subtitle && (
          <p className="hist-event-tile__subtitle">{event.subtitle}</p>
        )}

        {/* 3. DIVERGENCE TEASER — largest text, the hook */}
        <blockquote className="hist-event-tile__divergence">
          {divergenceTeaser}
        </blockquote>

        {/* Blurb — concrete, punchy context */}
        <p className="hist-event-tile__blurb">{blurb}</p>

        {/* 4. Perspective dots + names */}
        <div className="hist-event-tile__perspectives">
          {event.perspectives.map((p) => (
            <span key={p.id} className="hist-event-tile__persp">
              <span
                className="hist-event-tile__dot"
                style={{ background: PERSP_COLORS[p.color] || PERSP_COLORS.a }}
              />
              {p.viewpointName}
            </span>
          ))}
        </div>

        {/* 5. Stark data */}
        {(event.deathToll || event.displaced) && (
          <div className="hist-event-tile__stark">
            {event.deathToll && (
              <span className="hist-event-tile__stark-figure">
                {event.deathToll} killed
              </span>
            )}
            {event.displaced && (
              <span className="hist-event-tile__stark-figure">
                {event.displaced} displaced
              </span>
            )}
          </div>
        )}

        {/* 6. CTA — specific, tells you what you get */}
        <button
          className="hist-event-tile__cta"
          onClick={handleClick}
          type="button"
        >
          Read all {event.perspectives.length} perspectives
        </button>
      </div>
    </article>
  );
}

/* ===========================================================================
   ClassifiedTile — Upcoming event: desaturated, redacted text
   Click toggles redacted text reveal. No navigation. Much simpler.
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
        <span className="hist-classified-tile__reveal-title">{event.title}</span>
        <span className="hist-classified-tile__reveal-hint">Coming soon</span>
      </div>
    </div>
  );
}
