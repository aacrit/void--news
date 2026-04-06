"use client";

import { useState, useEffect, useRef, useMemo, useCallback, Fragment } from "react";
import type { HistoricalEvent, Perspective } from "../types";
import { HOOKS, CTAS } from "../hooks";

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

  /* ── Image distribution algorithm — documentary intercut model ──
     Distributes media across stages: context insert, perspective intercuts,
     omission exhibit, and remaining gallery. Maps first for context priority. */
  const { contextImage, perspectiveIntercuts, omissionImage, galleryImages } = useMemo(() => {
    const media = event.media;
    if (media.length === 0) return { contextImage: null, perspectiveIntercuts: [], omissionImage: null, galleryImages: [] };

    // First map for context, fallback to first image
    const mapIdx = media.findIndex(m => m.type === 'map');
    const ctxIdx = mapIdx >= 0 ? mapIdx : 0;
    const contextImage = media[ctxIdx];

    const remaining = media.filter((_, i) => i !== ctxIdx);

    // Intercuts between witnesses: up to (perspectives - 1)
    const maxIntercuts = Math.min(
      Math.max(event.perspectives.length - 1, 0),
      Math.floor(remaining.length / 2)
    );
    const perspectiveIntercuts = remaining.slice(0, maxIntercuts);
    const afterIntercuts = remaining.slice(maxIntercuts);

    // Omission image only if 6+ total
    const omissionImage = media.length >= 6 && afterIntercuts.length > 1 ? afterIntercuts[0] : null;
    const galleryImages = omissionImage ? afterIntercuts.slice(1) : afterIntercuts;

    return { contextImage, perspectiveIntercuts, omissionImage, galleryImages };
  }, [event.media, event.perspectives.length]);

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
          Context image inserted after first paragraph (documentary intercut).
          ═══════════════════════════════════════════ */}
      <section className="hist-stage hist-stage--context">
        <div className="hist-context__body hist-reveal">
          {event.contextNarrative.split("\n").filter(Boolean).map((para, i) => (
            <Fragment key={i}>
              <p>{para}</p>
              {/* Insert context image after first paragraph */}
              {i === 0 && contextImage && (
                <figure className="hist-context__figure hist-reveal">
                  <img
                    src={contextImage.url}
                    alt={contextImage.caption}
                    loading="lazy"
                    onError={(e) => { (e.currentTarget.parentElement as HTMLElement).style.display = 'none'; }}
                  />
                  <figcaption>
                    {contextImage.caption}
                    <span className="hist-context__figure-attr">{contextImage.attribution}</span>
                  </figcaption>
                </figure>
              )}
            </Fragment>
          ))}
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
          <Fragment key={perspective.id}>
            <WitnessBlock perspective={perspective} index={i} />
            {/* Insert intercut image after every 2nd witness — documentary evidence exhibit */}
            {(i + 1) % 2 === 0 && perspectiveIntercuts[Math.floor(i / 2)] && (
              <figure className="hist-intercut hist-reveal">
                <img
                  src={perspectiveIntercuts[Math.floor(i / 2)].url}
                  alt={perspectiveIntercuts[Math.floor(i / 2)].caption}
                  loading="lazy"
                  onError={(e) => { (e.currentTarget.parentElement as HTMLElement).style.display = 'none'; }}
                />
                <figcaption>
                  {perspectiveIntercuts[Math.floor(i / 2)].caption}
                  <span className="hist-intercut__attribution">
                    {perspectiveIntercuts[Math.floor(i / 2)].attribution}
                  </span>
                </figcaption>
              </figure>
            )}
          </Fragment>
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

          {/* Omission exhibit — evidence between the two analyses */}
          {omissionImage && (
            <figure className="hist-intercut hist-intercut--omission hist-reveal">
              <img
                src={omissionImage.url}
                alt={omissionImage.caption}
                loading="lazy"
                onError={(e) => { (e.currentTarget.parentElement as HTMLElement).style.display = 'none'; }}
              />
              <figcaption>
                {omissionImage.caption}
                <span className="hist-intercut__attribution">
                  {omissionImage.attribution}
                </span>
              </figcaption>
            </figure>
          )}

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
          Stage 5 — THE RECORD (Images + Data)
          Stark numbers + remaining archival images (after distribution).
          Only renders if galleryImages remain or stark numbers exist.
          ═══════════════════════════════════════════ */}
      {(galleryImages.length > 0 || event.deathToll || event.displaced || event.duration) && (
        <section className="hist-stage hist-stage--evidence">
          <h2 className="hist-stage__label hist-stage__label--sm hist-reveal">THE RECORD</h2>

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
          {galleryImages.length > 0 && (
            <div className="hist-evidence__gallery">
              {galleryImages.map((item, i) => (
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
      )}

      {/* ═══════════════════════════════════════════
          Stage 6 — YOUR TURN (Leave Early)
          Cliffhanger: hook teaser + thumbnail + CTA.
          ═══════════════════════════════════════════ */}
      <section className="hist-stage hist-stage--next hist-reveal">
        {nextEvent ? (
          <div className="hist-next__cliffhanger">
            {/* Next event hero thumbnail for visual pull */}
            {nextEvent.heroImage && (
              <div className="hist-next__thumb-wrap">
                <img
                  src={nextEvent.heroImage}
                  alt=""
                  className="hist-next__thumb"
                  loading="lazy"
                />
              </div>
            )}
            {/* Hook teaser — the crack of the next story */}
            <p className="hist-next__hook">
              {HOOKS[nextEvent.slug] || nextEvent.contextNarrative.split(". ").slice(0, 2).join(". ") + "."}
            </p>
            <p className="hist-next__prompt">Now read:</p>
            <button
              className="hist-next__cta"
              type="button"
              onClick={() => onNavigateToEvent?.(nextEvent)}
            >
              {CTAS[nextEvent.slug] ||
                `Explore ${nextEvent.perspectives.length} accounts of ${nextEvent.title}`}
            </button>
          </div>
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
