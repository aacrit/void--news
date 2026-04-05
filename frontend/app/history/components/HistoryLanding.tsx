"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import type { HistoricalEvent, RedactedEvent } from "../types";

/* ===========================================================================
   HistoryLanding — "Campaign Select" for void --history
   Organic living dossier tiles. Published = interactive expanding cards.
   Classified = desaturated, dashed, redacted. Self-marketing mission brief.
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

/* ── Compute divergence level from omissions across perspectives ── */
function computeDivergence(event: HistoricalEvent): "HIGH" | "MODERATE" | "LOW" {
  const totalOmissions = event.perspectives.reduce(
    (sum, p) => sum + p.omissions.length,
    0
  );
  const totalDisputed = event.perspectives.reduce(
    (sum, p) => sum + p.disputed.length,
    0
  );
  const score = totalOmissions + totalDisputed * 2;
  if (score >= 10) return "HIGH";
  if (score >= 5) return "MODERATE";
  return "LOW";
}

/* ── Count primary sources across all perspectives ── */
function countSources(event: HistoricalEvent): number {
  return event.perspectives.reduce(
    (sum, p) => sum + p.primarySources.length,
    0
  );
}

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
  const gridRef = useRef<HTMLDivElement>(null);

  /* Stagger entrance with IO */
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
    const tiles = gridRef.current?.querySelectorAll(".hist-tile");
    tiles?.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, [events]);

  return (
    <div>
      <div className="hist-main hist-grade">
        {/* ── Mission Brief: Self-marketing header ── */}
        <header className="hist-brief" aria-label="Archive mission brief">
          <h2 className="hist-brief__title">THE ARCHIVE</h2>
          <p className="hist-brief__line">
            One event. Multiple witnesses. Every side has a story.
          </p>
          <p className="hist-brief__line">
            Pick a dossier. Read every perspective. Decide for yourself.
          </p>
        </header>

        {/* ── Dossier Grid ── */}
        <section
          ref={gridRef}
          className="hist-dossier-grid"
          aria-label="Historical event dossiers"
        >
          {events.map((event, i) => (
            <DossierTile
              key={event.slug}
              event={event}
              index={i}
              isFirst={i === 0}
            />
          ))}
          {redacted.map((event, i) => (
            <RedactedTile
              key={event.slug}
              event={event}
              index={events.length + i}
            />
          ))}
        </section>
      </div>
    </div>
  );
}

/* ===========================================================================
   DossierTile — Published event: organic, expanding, alive
   Compact on arrival. Expands on hover (desktop) / tap (mobile).
   Structured like a mission-select campaign card.
   =========================================================================== */
function DossierTile({
  event,
  index,
  isFirst,
}: {
  event: HistoricalEvent;
  index: number;
  isFirst: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const tileRef = useRef<HTMLDivElement>(null);
  const [mousePos, setMousePos] = useState({ x: 0.5, y: 0.5 });

  const blurb = BLURBS[event.slug] || event.contextNarrative.split(". ").slice(0, 2).join(". ") + ".";
  const divergenceTeaser = DIVERGENCE_TEASERS[event.slug] || "";
  const divergence = computeDivergence(event);
  const sourceCount = countSources(event);

  /* Mouse parallax for hero image */
  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!tileRef.current) return;
      const rect = tileRef.current.getBoundingClientRect();
      setMousePos({
        x: (e.clientX - rect.left) / rect.width,
        y: (e.clientY - rect.top) / rect.height,
      });
    },
    []
  );

  /* Desktop: hover expand. Mobile: tap toggle. */
  const handleMouseEnter = useCallback(() => {
    setExpanded(true);
    if (!hasInteracted) setHasInteracted(true);
  }, [hasInteracted]);

  const handleMouseLeave = useCallback(() => {
    setExpanded(false);
  }, []);

  const handleTap = useCallback(() => {
    /* On touch devices, toggle expansion; on second tap when expanded, navigate */
    setExpanded((prev) => !prev);
    if (!hasInteracted) setHasInteracted(true);
  }, [hasInteracted]);

  /* nth-child organic border radius variety */
  const radiusVariants = [
    "3px 10px 5px 14px",
    "10px 4px 12px 5px",
    "6px 12px 3px 8px",
  ];
  const organicRadius = radiusVariants[index % radiusVariants.length];

  /* Hero image parallax transform */
  const parallaxX = (mousePos.x - 0.5) * 8;
  const parallaxY = (mousePos.y - 0.5) * 6;

  return (
    <div
      ref={tileRef}
      className={[
        "hist-tile",
        "hist-tile--published",
        `hist-tile--severity-${event.severity}`,
        expanded ? "hist-tile--expanded" : "",
        isFirst && !hasInteracted ? "hist-tile--pulse" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={{
        animationDelay: `${100 + index * 80}ms`,
        borderRadius: organicRadius,
        "--parallax-x": `${parallaxX}px`,
        "--parallax-y": `${parallaxY}px`,
      } as React.CSSProperties}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onMouseMove={handleMouseMove}
      onClick={handleTap}
      role="article"
      aria-label={`${event.title} \u2014 ${event.datePrimary}`}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (expanded) {
            /* Navigate on Enter when expanded */
            window.location.href = `/history/${event.slug}`;
          } else {
            setExpanded(true);
          }
        }
        if (e.key === "Escape") setExpanded(false);
      }}
      onFocus={() => setExpanded(true)}
      onBlur={() => setExpanded(false)}
    >
      {/* Hero image as background texture */}
      {event.heroImage && (
        <div
          className="hist-tile__hero"
          style={{
            backgroundImage: `url(${event.heroImage})`,
            transform: `translate(${parallaxX}px, ${parallaxY}px) scale(1.15)`,
          }}
          aria-hidden="true"
        />
      )}

      {/* Severity accent line */}
      <div className="hist-tile__accent" aria-hidden="true" />

      {/* ── Compact content (always visible) ── */}
      <div className="hist-tile__compact">
        {/* Date */}
        <span className="hist-tile__date">{event.datePrimary}</span>

        {/* Title */}
        <h3 className="hist-tile__title">{event.title}</h3>

        {/* Void voice blurb */}
        <p className="hist-tile__blurb">{blurb}</p>

        {/* Meta row: perspective dots + divergence */}
        <div className="hist-tile__meta">
          <div className="hist-tile__dots" aria-label={`${event.perspectives.length} perspectives`}>
            {event.perspectives.map((p) => (
              <span
                key={p.id}
                className="hist-tile__dot"
                style={{ backgroundColor: PERSP_COLORS[p.color] || PERSP_COLORS.a }}
                title={p.viewpointName}
              />
            ))}
          </div>
          <span className="hist-tile__persp-count">
            {event.perspectives.length} PERSPECTIVES
          </span>
        </div>
      </div>

      {/* ── Expanded content (revealed on hover/tap) ── */}
      <div className="hist-tile__expand" aria-hidden={!expanded}>
        <div className="hist-tile__expand-inner">
          {/* Perspective names — staggered reveal */}
          <div className="hist-tile__perspectives">
            {event.perspectives.map((p, pi) => (
              <span
                key={p.id}
                className="hist-tile__persp-name"
                style={{
                  transitionDelay: `${pi * 40}ms`,
                  color: PERSP_COLORS[p.color] || PERSP_COLORS.a,
                }}
              >
                {p.viewpointName}
              </span>
            ))}
          </div>

          {/* Divergence teaser */}
          {divergenceTeaser && (
            <p className="hist-tile__divergence-teaser">{divergenceTeaser}</p>
          )}

          {/* Mission intel row */}
          <div className="hist-tile__intel">
            <div className="hist-tile__intel-item">
              <span className="hist-tile__intel-label">DIVERGENCE</span>
              <span
                className={`hist-tile__intel-value hist-tile__intel-value--${divergence.toLowerCase()}`}
              >
                {divergence}
              </span>
            </div>
            <div className="hist-tile__intel-item">
              <span className="hist-tile__intel-label">SOURCES</span>
              <span className="hist-tile__intel-value">{sourceCount}</span>
            </div>
            {event.connections.length > 0 && (
              <div className="hist-tile__intel-item">
                <span className="hist-tile__intel-label">LINKED</span>
                <span className="hist-tile__intel-value">
                  {event.connections.length} event{event.connections.length !== 1 ? "s" : ""}
                </span>
              </div>
            )}
          </div>

          {/* Stark data */}
          {(event.deathToll || event.displaced) && (
            <div className="hist-tile__stark">
              {event.deathToll && (
                <span className="hist-tile__stark-figure">
                  {event.deathToll} killed
                </span>
              )}
              {event.displaced && (
                <span className="hist-tile__stark-figure">
                  {event.displaced} displaced
                </span>
              )}
            </div>
          )}

          {/* CTA */}
          <Link
            href={`/history/${event.slug}`}
            className="hist-tile__cta"
            onClick={(e) => e.stopPropagation()}
            tabIndex={expanded ? 0 : -1}
          >
            Enter the dossier
            <span className="hist-tile__cta-arrow" aria-hidden="true">\u2192</span>
          </Link>
        </div>
      </div>

      {/* First tile pulse indicator */}
      {isFirst && !hasInteracted && (
        <div className="hist-tile__start" aria-hidden="true">
          START HERE
        </div>
      )}
    </div>
  );
}

/* ===========================================================================
   RedactedTile — Upcoming event: locked, desaturated, classified
   Click-to-flip reveals full title. No expansion on hover.
   =========================================================================== */
function RedactedTile({
  event,
  index,
}: {
  event: RedactedEvent;
  index: number;
}) {
  const [revealed, setRevealed] = useState(false);

  /* Organic radius — dashed variant */
  const radiusVariants = [
    "8px 3px 10px 4px",
    "4px 10px 3px 8px",
    "6px 4px 8px 12px",
    "3px 8px 6px 4px",
    "10px 5px 4px 8px",
    "5px 12px 8px 3px",
  ];
  const organicRadius = radiusVariants[index % radiusVariants.length];

  return (
    <div
      className={[
        "hist-tile",
        "hist-tile--classified",
        revealed ? "hist-tile--revealed" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={{
        animationDelay: `${100 + index * 80}ms`,
        borderRadius: organicRadius,
      }}
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
      <h3 className="hist-tile__title hist-tile__title--redacted">
        {event.title.split(" ")[0]}{" "}
        <span className="hist-tile__redacted-chars">
          {event.title
            .split(" ")
            .slice(1)
            .map((w) => "\u2588".repeat(w.length))
            .join(" ")}
        </span>
      </h3>

      {/* Contradictory quotes */}
      {event.quoteA && (
        <p className="hist-tile__quote">{event.quoteA}</p>
      )}
      {event.quoteB && (
        <p className="hist-tile__quote hist-tile__quote--b">{event.quoteB}</p>
      )}

      {/* Date hint + classified badge */}
      <div className="hist-tile__meta">
        <span className="hist-tile__date">{event.dateHint}</span>
        <span className="hist-tile__badge hist-tile__badge--classified">
          CLASSIFIED
        </span>
      </div>

      {/* Flip reveal overlay */}
      <div className="hist-tile__reveal" aria-hidden={!revealed}>
        <span className="hist-tile__reveal-title">{event.title}</span>
        <span className="hist-tile__reveal-hint">Coming soon</span>
      </div>
    </div>
  );
}
