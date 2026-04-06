"use client";

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import type { HistoricalEvent, Perspective } from "../types";

/* ===========================================================================
   EventDetail — 6-Stage Guided Journey
   Cardinal rules: Show Not Tell. Arrive Late, Leave Early.

   Stage 1 — THE SCENE: Drop into the event (sticky hero, curtain-rise)
   Stage 2 — THE CRACK: One fact that breaks the textbook (single blockquote)
   Stage 3 — THE PERSPECTIVES: Witnesses enter left/right
   Stage 4 — THE OMISSIONS: Emphasized vs. What They Left Out
   Stage 5 — THE EVIDENCE: Stark numbers + archival images
   Stage 6 — YOUR TURN: Point to next event, no summary
   =========================================================================== */

/* ── Hooks — the "crack" for each event ── */
const HOOKS: Record<string, string> = {
  "partition-of-india":
    "A lawyer who\u2019d never been to India drew the border in five weeks. 15 million crossed it.",
  "hiroshima-nagasaki":
    "66,000 dead in 8.5 seconds. Seven of eight five-star American generals said it wasn\u2019t necessary.",
  "rwandan-genocide":
    "The UN had a fax warning them. They reduced their force from 2,500 to 270. 800,000 died in 100 days.",
};

/* ── CTAs for next event navigation ── */
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

interface EventDetailProps {
  event: HistoricalEvent;
  allEvents: HistoricalEvent[];
  onNavigateToEvent?: (event: HistoricalEvent) => void;
  onClose?: () => void;
}

export default function EventDetail({ event, allEvents, onNavigateToEvent, onClose }: EventDetailProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  /* Determine next event for Stage 6 navigation */
  const nextEvent = useMemo(() => {
    const sorted = [...allEvents].sort((a, b) => a.dateSort - b.dateSort);
    const idx = sorted.findIndex((e) => e.slug === event.slug);
    if (idx === -1 || idx >= sorted.length - 1) return null;
    return sorted[idx + 1];
  }, [allEvents, event.slug]);

  /* The crack — hook text */
  const hook =
    HOOKS[event.slug] ||
    event.contextNarrative.split(". ").slice(0, 2).join(". ") + ".";

  /* ── Scroll reveal observer for all .hist-reveal elements ── */
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
  }, []);

  /* ── Witness background dimming: when a new witness becomes visible,
       add background class to previously revealed witnesses ── */
  useEffect(() => {
    const witnesses = contentRef.current?.querySelectorAll(".hist-witness");
    if (!witnesses || witnesses.length === 0) return;

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && entry.intersectionRatio >= 0.3) {
            /* Mark this witness as the focus */
            witnesses.forEach((w) => {
              if (w === entry.target) {
                w.classList.remove("hist-witness--background");
              } else if (w.classList.contains("hist-reveal--visible")) {
                w.classList.add("hist-witness--background");
              }
            });
          }
        });
      },
      { threshold: [0.3], rootMargin: "-10% 0px -10% 0px" }
    );

    witnesses.forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={contentRef}>
      {/* ═══════════════════════════════════════════
          Stage 1 — THE SCENE (Arrive Late)
          Full-viewport hero image, sticky behind content.
          Content scrolls OVER the hero (curtain rising).
          ═══════════════════════════════════════════ */}
      <section className="hist-stage hist-stage--scene">
        <div
          className="hist-stage__hero"
          style={
            event.heroImage
              ? { backgroundImage: `url(${event.heroImage})` }
              : undefined
          }
        >
          {!event.heroImage && <div className="hist-stage__hero-fallback" />}
          <div className="hist-stage__hero-overlay" />
          <div className="hist-stage__hero-content">
            <span className="hist-stage__date">{event.datePrimary}</span>
            <h1 className="hist-stage__title">{event.title}</h1>
            {event.subtitle && (
              <p className="hist-stage__subtitle">{event.subtitle}</p>
            )}
          </div>
          {event.heroAttribution && (
            <span className="hist-stage__attribution">
              {event.heroAttribution}
            </span>
          )}
        </div>
        {/* Scroll indicator */}
        <div className="hist-stage__scroll-hint" aria-hidden="true">
          <span className="hist-stage__scroll-line" />
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          Stage 2 — THE CRACK (Show Not Tell)
          One fact that breaks the textbook.
          Short. Just one blockquote. Arrive late, leave early.
          ═══════════════════════════════════════════ */}
      <section className="hist-stage hist-stage--crack">
        <blockquote className="hist-crack__text hist-reveal">
          {hook}
        </blockquote>
      </section>

      {/* ═══════════════════════════════════════════
          Stage 2.5 — THE FULL STORY (Context Narrative)
          The crack hooks them. Now the full story grounds them.
          No title — content speaks for itself (arrive late).
          ═══════════════════════════════════════════ */}
      <section className="hist-stage hist-stage--context">
        <div className="hist-context__body hist-reveal">
          {event.contextNarrative}
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          Key Facts — Compact reference panel
          Date, location, key figures, death toll, displaced, duration.
          ═══════════════════════════════════════════ */}
      <section className="hist-stage hist-stage--keyfacts">
        <div className="hist-keyfacts hist-reveal">
          <div className="hist-keyfacts__grid">
            <div className="hist-keyfacts__item">
              <span className="hist-keyfacts__label">Date</span>
              <span className="hist-keyfacts__value">{event.dateRange || event.datePrimary}</span>
            </div>
            <div className="hist-keyfacts__item">
              <span className="hist-keyfacts__label">Location</span>
              <span className="hist-keyfacts__value">{event.location}</span>
            </div>
            {event.deathToll && (
              <div className="hist-keyfacts__item">
                <span className="hist-keyfacts__label">Death toll</span>
                <span className="hist-keyfacts__value hist-keyfacts__value--figure">{event.deathToll}</span>
              </div>
            )}
            {event.displaced && (
              <div className="hist-keyfacts__item">
                <span className="hist-keyfacts__label">Displaced</span>
                <span className="hist-keyfacts__value hist-keyfacts__value--figure">{event.displaced}</span>
              </div>
            )}
            {event.duration && (
              <div className="hist-keyfacts__item">
                <span className="hist-keyfacts__label">Duration</span>
                <span className="hist-keyfacts__value">{event.duration}</span>
              </div>
            )}
          </div>

          {/* Key Figures */}
          {event.keyFigures.length > 0 && (
            <div className="hist-keyfacts__figures">
              <span className="hist-keyfacts__label">Key figures</span>
              <div className="hist-keyfacts__figures-list">
                {event.keyFigures.map((fig, i) => (
                  <span key={i} className="hist-keyfacts__figure">
                    <strong className="hist-keyfacts__figure-name">{fig.name}</strong>
                    <span className="hist-keyfacts__figure-role">{fig.role}</span>
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          Stage 3 — THE PERSPECTIVES (The Conversation)
          Each perspective enters as a "witness."
          Alternating left/right on desktop, stacked on mobile.
          Interactive: expandable full narrative, all quotes, all key narratives.
          ═══════════════════════════════════════════ */}
      <section className="hist-stage hist-stage--perspectives">
        <h2 className="hist-stage__label hist-stage__label--sm hist-reveal">THE PERSPECTIVES</h2>

        {event.perspectives.map((perspective, i) => (
          <WitnessBlock
            key={perspective.id}
            perspective={perspective}
            index={i}
          />
        ))}
      </section>

      {/* ═══════════════════════════════════════════
          Stage 4 — THE OMISSIONS (The Climax)
          Two panels: "What They Stress" vs "What They Leave Out"
          ═══════════════════════════════════════════ */}
      <section className="hist-stage hist-stage--omissions">
        <h2 className="hist-stage__label hist-stage__label--sm hist-reveal">WHAT THEY LEFT OUT</h2>

        <div className="hist-omissions-split">
          <div className="hist-omissions-split__panel hist-omissions-split__panel--emphasized hist-reveal">
            <h3 className="hist-omissions-split__heading">
              What each side stresses
            </h3>
            {event.perspectives.map((p) => (
              <div key={p.id} className="hist-omissions-split__group">
                <span
                  className="hist-omissions-split__name"
                  style={{ color: PERSP_COLORS[p.color] }}
                >
                  {p.viewpointName}
                </span>
                <ul className="hist-omissions-split__list">
                  {p.keyNarratives.map((n, ni) => (
                    <li key={ni}>{n}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>

          <div className="hist-omissions-split__panel hist-omissions-split__panel--omitted hist-reveal">
            <h3 className="hist-omissions-split__heading">
              What each side ignores
            </h3>
            {event.perspectives
              .filter((p) => p.omissions.length > 0)
              .map((p) => (
                <div key={p.id} className="hist-omissions-split__group">
                  <span
                    className="hist-omissions-split__name"
                    style={{ color: PERSP_COLORS[p.color] }}
                  >
                    {p.viewpointName}
                  </span>
                  <ul className="hist-omissions-split__list">
                    {p.omissions.map((o, oi) => (
                      <li key={oi} className="hist-omission--struck">
                        {o}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
          </div>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          Stage 5 — THE EVIDENCE (Images + Data)
          Stark numbers + archival images.
          ═══════════════════════════════════════════ */}
      <section className="hist-stage hist-stage--evidence">
        <h2 className="hist-stage__label hist-stage__label--sm hist-reveal">THE EVIDENCE</h2>

        {/* Stark numbers */}
        {(event.deathToll || event.displaced || event.duration) && (
          <div className="hist-evidence__numbers hist-reveal">
            {event.deathToll && (
              <div className="hist-evidence__stat">
                <span className="hist-evidence__figure">{event.deathToll}</span>
                <span className="hist-evidence__unit">killed</span>
              </div>
            )}
            {event.displaced && (
              <div className="hist-evidence__stat">
                <span className="hist-evidence__figure">{event.displaced}</span>
                <span className="hist-evidence__unit">displaced</span>
              </div>
            )}
            {event.duration && (
              <div className="hist-evidence__stat">
                <span className="hist-evidence__figure">{event.duration}</span>
              </div>
            )}
          </div>
        )}

        {/* Archival images — vertical, alternating, with context */}
        {event.media.length > 0 && (
          <div className="hist-evidence__gallery">
            {event.media.map((item, i) => (
              <div
                key={item.id}
                className={`hist-evidence__image hist-evidence__image--${i % 2 === 0 ? "left" : "right"} hist-reveal`}
                style={{ transitionDelay: `${i * 100}ms` }}
              >
                <img
                  src={item.url}
                  alt={item.caption}
                  loading="lazy"
                  onError={(e) => {
                    e.currentTarget.style.display = "none";
                  }}
                />
                <p className="hist-evidence__caption">{item.caption}</p>
                <span className="hist-evidence__image-attribution">
                  {item.attribution}
                  {item.year && ` (${item.year})`}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ═══════════════════════════════════════════
          Stage 6 — YOUR TURN (Leave Early)
          No summary. Point to next event, or return.
          ═══════════════════════════════════════════ */}
      <section className="hist-stage hist-stage--next hist-reveal">
        {nextEvent ? (
          <>
            <p className="hist-next__prompt">Now read:</p>
            <button
              className="hist-next__cta"
              type="button"
              onClick={() => onNavigateToEvent?.(nextEvent)}
            >
              {CTAS[nextEvent.slug] ||
                `Explore ${nextEvent.perspectives.length} accounts of ${nextEvent.title}`}
            </button>
          </>
        ) : (
          <button
            className="hist-next__cta"
            type="button"
            onClick={() => onClose?.()}
          >
            Return to The Archive
          </button>
        )}
      </section>
    </div>
  );
}

/* ===========================================================================
   WitnessBlock — A single perspective "witness" (interactive v2)
   Identity (dot + name + type), ALL key arguments, ALL primary source quotes,
   expandable full narrative.
   =========================================================================== */
function WitnessBlock({
  perspective,
  index,
}: {
  perspective: Perspective;
  index: number;
}) {
  const side = index % 2 === 0 ? "left" : "right";
  const [expanded, setExpanded] = useState(false);

  const toggleExpand = useCallback(() => {
    setExpanded((prev) => !prev);
  }, []);

  return (
    <div
      className={`hist-witness hist-witness--${side} hist-reveal`}
      style={{ transitionDelay: `${index * 150}ms` }}
    >
      {/* Witness identity */}
      <div className="hist-witness__identity">
        <span
          className="hist-witness__dot"
          style={{
            background: PERSP_COLORS[perspective.color] || PERSP_COLORS.a,
          }}
          aria-hidden="true"
        />
        <span className="hist-witness__name">{perspective.viewpointName}</span>
        <span className="hist-witness__type">{perspective.viewpointType}</span>
      </div>

      {/* Key arguments — ALL items, not just first. Prominent (Playfair italic). */}
      {perspective.keyNarratives.length > 0 && (
        <div className="hist-witness__arguments">
          {perspective.keyNarratives.map((narrative, ni) => (
            <blockquote key={ni} className="hist-witness__argument">
              {narrative}
            </blockquote>
          ))}
        </div>
      )}

      {/* ALL primary source quotes — archival treatment */}
      {perspective.primarySources.map((source, si) => (
        <div key={si} className="hist-witness__source">
          <p className="hist-witness__quote">
            &ldquo;{source.text}&rdquo;
          </p>
          <cite className="hist-witness__cite">
            &mdash; {source.author}, <em>{source.work}</em>, {source.date}
          </cite>
        </div>
      ))}

      {/* Expand toggle — read full perspective narrative */}
      <button
        className="hist-witness__expand"
        type="button"
        onClick={toggleExpand}
        aria-expanded={expanded}
      >
        {expanded ? "Collapse perspective" : "Read full perspective"}
        <span className={`hist-witness__expand-arrow ${expanded ? "hist-witness__expand-arrow--open" : ""}`} aria-hidden="true">
          &#9662;
        </span>
      </button>

      {/* Full narrative — progressive disclosure */}
      {expanded && (
        <div className="hist-witness__full-narrative">
          <p className="hist-witness__narrative-text">
            {perspective.narrative}
          </p>

          {/* Disputed claims */}
          {perspective.disputed.length > 0 && (
            <div className="hist-witness__disputed">
              <span className="hist-witness__disputed-label">Disputed</span>
              <ul className="hist-witness__disputed-list">
                {perspective.disputed.map((d, di) => (
                  <li key={di}>{d}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
