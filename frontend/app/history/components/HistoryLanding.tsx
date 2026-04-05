"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
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

        {/* ── Declassified Dossiers ── */}
        <section
          ref={gridRef}
          className="hist-dossier-grid"
          aria-label="Declassified event dossiers"
        >
          {events.map((event, i) => (
            <DossierTile
              key={event.slug}
              event={event}
              index={i}
              isFirst={i === 0}
            />
          ))}
        </section>

        {/* ── Section Divider ── */}
        {redacted.length > 0 && (
          <div className="hist-classified-divider">
            <span className="hist-classified-divider__line" aria-hidden="true" />
            <span className="hist-classified-divider__label">CLASSIFIED — PENDING DECLASSIFICATION</span>
            <span className="hist-classified-divider__line" aria-hidden="true" />
          </div>
        )}

        {/* ── Classified Dossiers ── */}
        {redacted.length > 0 && (
          <section
            className="hist-dossier-grid hist-dossier-grid--classified"
            aria-label="Classified upcoming event dossiers"
          >
            {redacted.map((event, i) => (
              <RedactedTile
                key={event.slug}
                event={event}
                index={i}
              />
            ))}
          </section>
        )}
      </div>
    </div>
  );
}

/* ===========================================================================
   DossierTile — Published event as a BOOK
   Closed book on arrival. Lifts on hover. Opens with spine-hinge on click
   to reveal expanded content ("pages") before navigating to the story.
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
  const router = useRouter();
  const [expanded, setExpanded] = useState(false);
  const [opening, setOpening] = useState(false);
  const [hasInteracted, setHasInteracted] = useState(false);
  const tileRef = useRef<HTMLDivElement>(null);

  const blurb = BLURBS[event.slug] || event.contextNarrative.split(". ").slice(0, 2).join(". ") + ".";
  const divergenceTeaser = DIVERGENCE_TEASERS[event.slug] || "";
  const divergence = computeDivergence(event);
  const sourceCount = countSources(event);

  /* Polygon clip-path for organic irregular edges — same pattern as classified tiles */
  const polygonVariants = [
    "polygon(1% 0%, 98% 1%, 100% 2%, 99% 97%, 97% 100%, 2% 99%, 0% 98%, 0.5% 3%)",
    "polygon(2% 1%, 99% 0%, 100% 3%, 98% 98%, 100% 100%, 1% 99%, 0% 97%, 1% 2%)",
    "polygon(0% 2%, 97% 0%, 99% 1%, 100% 99%, 98% 100%, 3% 98%, 0% 100%, 1% 1%)",
  ];
  const clipPath = polygonVariants[index % polygonVariants.length];

  /* Desktop: hover expand. Mobile: tap toggle. */
  const handleMouseEnter = useCallback(() => {
    if (opening) return;
    setExpanded(true);
    if (!hasInteracted) setHasInteracted(true);
  }, [hasInteracted, opening]);

  const handleMouseLeave = useCallback(() => {
    if (opening) return;
    setExpanded(false);
  }, [opening]);

  /* Click → Open book → Navigate after animation */
  const handleNavigate = useCallback(() => {
    if (opening) return;

    /* Check prefers-reduced-motion — skip animation */
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reducedMotion) {
      router.push(`/history/${event.slug}`);
      return;
    }

    /* Trigger the book-opening animation */
    setOpening(true);
    setExpanded(true);

    /* Mobile gets faster animation */
    const isMobile = window.innerWidth < 768;
    const delay = isMobile ? 350 : 650;

    setTimeout(() => {
      router.push(`/history/${event.slug}`);
    }, delay);
  }, [router, event.slug, opening]);

  const handleClick = useCallback(() => {
    if (!hasInteracted) setHasInteracted(true);

    /* Mobile: first tap expands, second tap navigates */
    const isTouchDevice = window.matchMedia("(hover: none)").matches;
    if (isTouchDevice && !expanded) {
      setExpanded(true);
      return;
    }

    handleNavigate();
  }, [hasInteracted, expanded, handleNavigate]);

  return (
    <div
      ref={tileRef}
      className={[
        "hist-tile",
        "hist-tile--published",
        "hist-tile--book",
        `hist-tile--severity-${event.severity}`,
        expanded ? "hist-tile--expanded" : "",
        opening ? "hist-tile--opening" : "",
        isFirst && !hasInteracted ? "hist-tile--first" : "",
      ]
        .filter(Boolean)
        .join(" ")}
      style={{
        animationDelay: `${100 + index * 80}ms`,
        clipPath: expanded || opening ? "none" : clipPath,
      } as React.CSSProperties}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onClick={handleClick}
      role="article"
      aria-label={`${event.title} \u2014 ${event.datePrimary}`}
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          if (expanded) {
            handleNavigate();
          } else {
            setExpanded(true);
          }
        }
        if (e.key === "Escape") setExpanded(false);
      }}
      onFocus={() => { if (!opening) setExpanded(true); }}
      onBlur={() => { if (!opening) setExpanded(false); }}
    >
      {/* Pages behind cover — visible when book opens */}
      <div className="hist-tile__pages" aria-hidden="true">
        <div className="hist-tile__pages-content">
          {/* Blurb as first page content */}
          <p className="hist-tile__blurb">{blurb}</p>

          {/* Perspective names */}
          <span className="hist-tile__persp-count">
            {event.perspectives.length} PERSPECTIVES
          </span>
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

          {/* Intel row */}
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

          {/* CTA on the pages */}
          <Link
            href={`/history/${event.slug}`}
            className="hist-tile__cta"
            onClick={(e) => e.stopPropagation()}
            tabIndex={expanded ? 0 : -1}
          >
            Enter the dossier
            <span className="hist-tile__cta-arrow" aria-hidden="true">{"\u2192"}</span>
          </Link>
        </div>
      </div>

      {/* Front Cover — the book face */}
      <div className="hist-tile__cover">
        {/* Spine (left edge) */}
        <div className="hist-tile__spine" aria-hidden="true" />

        {/* Page edge (right side) */}
        <div className="hist-tile__page-edge" aria-hidden="true" />

        {/* Cover art — header band at top, no text overlay */}
        {event.heroImage && (
          <div className="hist-tile__cover-art">
            <img
              src={event.heroImage}
              alt=""
              loading="lazy"
              className="hist-tile__cover-img"
              onError={(e) => {
                e.currentTarget.style.display = "none";
              }}
            />
          </div>
        )}

        {/* Title block — below the cover art */}
        <div className="hist-tile__compact">
          <h3 className="hist-tile__title">{event.title}</h3>
          <span className="hist-tile__date">{event.datePrimary}</span>
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
            <span className="hist-tile__accent-label">{event.severity}</span>
          </div>
        </div>

        {/* "START HERE" badge on first book */}
        {isFirst && !hasInteracted && (
          <div className="hist-tile__start" aria-hidden="true">
            START HERE
          </div>
        )}
      </div>
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

  /* More irregular polygons for classified — rougher edges */
  const polygonVariants = [
    "polygon(2% 1%, 96% 0%, 99% 3%, 97% 96%, 100% 99%, 3% 98%, 0% 95%, 1% 2%)",
    "polygon(0% 3%, 98% 1%, 100% 4%, 99% 97%, 97% 100%, 1% 97%, 0% 99%, 2% 1%)",
    "polygon(1% 0%, 97% 2%, 100% 1%, 98% 100%, 96% 98%, 2% 100%, 0% 97%, 0.5% 3%)",
    "polygon(3% 2%, 99% 0%, 97% 3%, 100% 98%, 98% 100%, 0% 97%, 1% 100%, 0% 1%)",
  ];
  const clipPath = polygonVariants[index % polygonVariants.length];

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
        clipPath,
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
