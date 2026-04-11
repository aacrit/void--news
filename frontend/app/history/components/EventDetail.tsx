"use client";

import { useState, useEffect, useRef, useMemo, useCallback, Fragment } from "react";
import Link from "next/link";
import type { HistoricalEvent, Perspective, MediaItem, EventConnection, ConnectionType } from "../types";
import { HOOKS, CTAS } from "../hooks";
import { ARC_FEATURES } from "../arc-features";

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

/* ── Connection type priority for sorting ── */
const CONNECTION_PRIORITY: Record<ConnectionType, number> = {
  caused: 4,
  consequence: 3,
  "response-to": 3,
  influenced: 2,
  parallel: 1,
};

interface EventDetailProps {
  event: HistoricalEvent;
  allEvents: HistoricalEvent[];
  onNavigateToEvent?: (event: HistoricalEvent) => void;
  onClose?: () => void;
}

export default function EventDetail({ event, allEvents, onNavigateToEvent, onClose }: EventDetailProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [storyExpanded, setStoryExpanded] = useState(false);

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
    (event.contextNarrative || event.title).split(". ").slice(0, 2).join(". ") + ".";

  const sortedConnections = useMemo(() => {
    return [...event.connections].sort(
      (a, b) => (CONNECTION_PRIORITY[b.type] ?? 0) - (CONNECTION_PRIORITY[a.type] ?? 0)
    );
  }, [event.connections]);

  /* ── Dossier: top 3 connection-ranked events ── */
  const dossierEvents = useMemo(() => {
    if (!ARC_FEATURES.DOSSIER || sortedConnections.length === 0) return [];
    return sortedConnections.slice(0, 3).map((conn) => {
      const linked = allEvents.find((e) => e.slug === conn.targetSlug);
      return { connection: conn, event: linked ?? null };
    });
  }, [sortedConnections, allEvents]);

  /* ── Sidebar: parallel + consequence connections for "Elsewhere" ── */
  const sidebarConnections = useMemo(() => {
    if (!ARC_FEATURES.SIDEBAR) return [];
    return event.connections.filter(
      (c) => c.type === "parallel" || c.type === "consequence"
    );
  }, [event.connections]);

  const showSidebar = ARC_FEATURES.SIDEBAR && sidebarConnections.length >= 2;

  /* ── Scroll reveal observer for all .hist-reveal elements ──
       Also observes arc connection elements that have their own
       CSS transitions triggered by hist-reveal--visible:
       - .hist-thread-stage (parent for divider + lead quote)
       - .hist-thread-stage__item (staggered connection list items)
       - .hist-dossier__card (staggered dossier cards)
       - .hist-sidebar__entry (margin note slide-in) */
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

    const root = contentRef.current;
    if (!root) return;

    /* Standard stage sections */
    root.querySelectorAll(".hist-reveal").forEach((el) => observer.observe(el));

    /* Arc connection elements — each observed individually for
       per-element stagger timing (delays set via inline style) */
    root.querySelectorAll(
      ".hist-thread-stage, .hist-thread-stage__item, .hist-dossier__card, .hist-sidebar__entry"
    ).forEach((el) => observer.observe(el));

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
    <div ref={contentRef} className={showSidebar ? "hist-layout-sidebar" : ""}>
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
          Key Facts — Pure Ledger
          All facts as ruled document rows. Equal weight.
          No dominant numbers — the data doesn't support it.
          ═══════════════════════════════════════════ */}
      <section className="hist-stage hist-stage--keyfacts">
        <div className="hist-keyfacts hist-reveal">
          <dl className="hist-keyfacts__ledger">
            <div className="hist-keyfacts__ledger-row">
              <dt>Date</dt>
              <dd>{event.dateRange || event.datePrimary}</dd>
            </div>
            <div className="hist-keyfacts__ledger-row">
              <dt>Location</dt>
              <dd>{event.location}</dd>
            </div>
            {event.duration && (
              <div className="hist-keyfacts__ledger-row">
                <dt>Duration</dt>
                <dd>{event.duration}</dd>
              </div>
            )}
            {event.deathToll && event.deathToll !== "N/A" && (
              <div className="hist-keyfacts__ledger-row">
                <dt>Killed</dt>
                <dd>{event.deathToll}</dd>
              </div>
            )}
            {event.displaced && event.displaced !== "N/A" && (
              <div className="hist-keyfacts__ledger-row">
                <dt>Displaced</dt>
                <dd>{event.displaced}</dd>
              </div>
            )}
          </dl>
        </div>
      </section>

      {/* ═══════════════════════════════════════════
          Key Figures — Name Plate treatment
          Standalone section. Playfair Display name, IBM Plex Mono dates.
          No card background — thin ruled separators only.
          ═══════════════════════════════════════════ */}
      {event.keyFigures.length > 0 && (
        <section className="hist-stage hist-stage--figures">
          <h2 className="hist-stage__label hist-stage__label--sm hist-reveal">THE FIGURES</h2>
          <div className="hist-figures hist-reveal">
            {event.keyFigures.map((fig, i) => {
              const hasDates = fig.born != null || fig.died != null;
              /* Format year: ≤0 means BCE (year 0 = 1 BCE in historical convention) */
              const fmtYear = (y: number) => y <= 0 ? `${Math.abs(y) + (y === 0 ? 1 : 0)} BCE` : String(y);
              const dateStr = hasDates
                ? `(${fig.born != null ? fmtYear(fig.born) : "?"}–${fig.died != null ? fmtYear(fig.died) : "?"})`
                : null;
              return (
                <div key={i} className="hist-figures__plate">
                  <div className="hist-figures__namerow">
                    {fig.wikipedia ? (
                      <a
                        href={fig.wikipedia}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="hist-figures__name"
                        aria-label={`${fig.name} on Wikipedia (opens in new tab)`}
                      >
                        {fig.name}
                      </a>
                    ) : (
                      <span className="hist-figures__name">{fig.name}</span>
                    )}
                    {dateStr && (
                      <span className="hist-figures__dates">{dateStr}</span>
                    )}
                  </div>
                  <p className="hist-figures__role">{fig.role}</p>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* ═══════════════════════════════════════════
          Stage 2.5 — THE FULL STORY (Context Narrative)
          The crack hooks them. Now the full story grounds them.
          No title — content speaks for itself (arrive late).
          Context image inserted after first paragraph (documentary intercut).
          Progressive disclosure: first 2 paragraphs visible, rest behind toggle.
          ═══════════════════════════════════════════ */}
      <section className="hist-stage hist-stage--context">
        <div className="hist-context__body hist-reveal">
          {(() => {
            const paragraphs = (event.contextNarrative || "").split("\n").filter(Boolean);
            const visible = paragraphs.slice(0, 2);
            const extra = paragraphs.slice(2);
            return (
              <>
                {visible.map((para, i) => (
                  <Fragment key={i}>
                    <p>{para}</p>
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
                {extra.length > 0 && (
                  <>
                    {storyExpanded && (
                      <div className="hist-context__extra">
                        {extra.map((para, i) => (
                          <p key={i + 2}>{para}</p>
                        ))}
                      </div>
                    )}
                    <button
                      type="button"
                      className="hist-context__more-toggle"
                      onClick={() => setStoryExpanded((prev) => !prev)}
                      aria-expanded={storyExpanded}
                    >
                      {storyExpanded ? "Collapse \u25B4" : "Continue reading \u25BE"}
                    </button>
                  </>
                )}
              </>
            );
          })()}
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
          Stage 5 — THE RECORD (Gallery Images)
          Remaining archival images (after distribution).
          Only renders if galleryImages remain.
          ═══════════════════════════════════════════ */}
      {galleryImages.length > 0 && (
        <section className="hist-stage hist-stage--evidence">
          <h2 className="hist-stage__label hist-stage__label--sm hist-reveal">THE RECORD</h2>

          {/* Archival images + video — vertical, alternating, with context */}
          <div className="hist-evidence__gallery">
            {galleryImages.map((item, i) => (
              <div
                key={item.id}
                className={`hist-evidence__image hist-evidence__image--${i % 2 === 0 ? "left" : "right"} hist-reveal`}
                style={{ transitionDelay: `${i * 100}ms` }}
              >
                {item.type === "video" && item.videoEmbedUrl ? (
                  <ArchivalVideo item={item} />
                ) : (
                  <img
                    src={item.url}
                    alt={item.caption}
                    loading="lazy"
                    onError={(e) => {
                      e.currentTarget.style.display = "none";
                    }}
                  />
                )}
                <p className="hist-evidence__caption">{item.caption}</p>
                <span className="hist-evidence__image-attribution">
                  {item.type === "video" ? "Filmed by: " : ""}
                  {item.attribution}
                  {item.year && ` (${item.year})`}
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

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
          Stage 6 — YOUR TURN (Leave Early)
          Dossier mode: connection-ranked next reads (up to 3).
          Thread lead absorbed as intro blockquote before cards.
          Fallback: chronological next event (original behavior).
          ═══════════════════════════════════════════ */}
      <section className="hist-stage hist-stage--next hist-reveal">
        {ARC_FEATURES.DOSSIER && dossierEvents.length > 0 ? (
          <>
            {ARC_FEATURES.THREAD_STAGE && sortedConnections.length > 0 && (
              <blockquote className="hist-dossier__thread-lead hist-reveal">
                {sortedConnections[0].description}
              </blockquote>
            )}
            <div className="hist-dossier">
              {dossierEvents.map(({ connection, event: linkedEvent }, cardIndex) => {
                const slug = connection.targetSlug;
                const hookText = HOOKS[slug]
                  || (linkedEvent?.contextNarrative || connection.targetTitle).split(". ").slice(0, 2).join(". ") + ".";
                const ctaText = CTAS[slug]
                  || `Explore ${linkedEvent?.perspectives.length ?? 0} accounts of ${connection.targetTitle}`;
                const heroImg = linkedEvent?.heroImage;
                const firstSentence = connection.description.split(". ")[0] + ".";

                return (
                  <Link
                    key={slug}
                    href={`/history/${slug}`}
                    className="hist-dossier__card"
                    style={{ transitionDelay: `${cardIndex * 120}ms` }}
                  >
                    {heroImg && (
                      <div
                        className="hist-dossier__card-bg"
                        style={{ backgroundImage: `url(${heroImg})` }}
                        aria-hidden="true"
                      />
                    )}
                    <div className="hist-dossier__card-content">
                      <p className="hist-dossier__card-hook">{hookText}</p>
                      <p className="hist-dossier__card-connection">{firstSentence}</p>
                      <span className="hist-dossier__card-cta">{ctaText}</span>
                    </div>
                  </Link>
                );
              })}
            </div>
            {/* Chronological fallback link */}
            {nextEvent && (
              <p className="hist-dossier__chrono">
                <Link href={`/history/${nextEvent.slug}`}>
                  Or continue chronologically &rarr;
                </Link>
              </p>
            )}
            {ARC_FEATURES.THREAD_STAGE && sortedConnections.length > 1 && (
              <div className="hist-thread-stage__list hist-reveal">
                {sortedConnections.slice(1).map((conn, i) => (
                  <div
                    key={`${conn.targetSlug}-${i}`}
                    className={`hist-thread-stage__item hist-thread-stage__item--${conn.type}`}
                    style={{ transitionDelay: `${i * 150}ms` }}
                  >
                    <span className="hist-thread-stage__indicator" aria-hidden="true">
                      {conn.type === "caused" || conn.type === "consequence" ? "\u2193" : ""}
                      {conn.type === "response-to" ? "\u2191" : ""}
                    </span>
                    <div className="hist-thread-stage__content">
                      <Link href={`/history/${conn.targetSlug}`} className="hist-thread-stage__title">
                        {conn.targetTitle}
                      </Link>
                      <span className="hist-thread-stage__date">
                        {allEvents.find((e) => e.slug === conn.targetSlug)?.datePrimary ?? ""}
                      </span>
                      <p className="hist-thread-stage__desc">{conn.description.split(". ")[0]}.</p>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        ) : nextEvent ? (
          <div className="hist-next__cliffhanger">
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
            <p className="hist-next__hook">
              {HOOKS[nextEvent.slug] || (nextEvent.contextNarrative || nextEvent.title).split(". ").slice(0, 2).join(". ") + "."}
            </p>
            <p className="hist-next__prompt">Now read:</p>
            <Link
              href={`/history/${nextEvent.slug}`}
              className="hist-next__cta"
            >
              {CTAS[nextEvent.slug] ||
                `Explore ${nextEvent.perspectives.length} accounts of ${nextEvent.title}`}
            </Link>
          </div>
        ) : (
          <Link
            href="/history"
            className="hist-next__cta"
          >
            Return to The Archive
          </Link>
        )}
      </section>

      {/* ═══════════════════════════════════════════
          THE PARALLAX SIDEBAR — "Elsewhere, Meanwhile"
          Desktop: sticky right column alongside all content.
          Mobile: accordion section below the main flow.
          Only renders when >=2 parallel/consequence connections exist.
          ═══════════════════════════════════════════ */}
      {showSidebar && (
        <SidebarElsewhere connections={sidebarConnections} allEvents={allEvents} />
      )}
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

  const perspColor = PERSP_COLORS[perspective.color] || PERSP_COLORS.a;

  return (
    <div
      className={`hist-witness hist-witness--${side} hist-reveal`}
      style={{ transitionDelay: `${index * 150}ms`, "--persp-color": perspColor } as React.CSSProperties}
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

/* ===========================================================================
   SidebarElsewhere — "Elsewhere, Meanwhile" margin notes
   Desktop: sticky right column (via CSS grid on parent).
   Mobile: disclosure accordion.
   =========================================================================== */
function SidebarElsewhere({
  connections,
  allEvents,
}: {
  connections: EventConnection[];
  allEvents: HistoricalEvent[];
}) {
  const [mobileOpen, setMobileOpen] = useState(false);

  const entries = connections.map((conn) => {
    const linked = allEvents.find((e) => e.slug === conn.targetSlug);
    return {
      slug: conn.targetSlug,
      title: conn.targetTitle,
      year: linked?.datePrimary ?? "",
      description: conn.description.split(". ")[0] + ".",
    };
  });

  return (
    <aside className="hist-sidebar--elsewhere" aria-label="Parallel events">
      {/* Desktop heading — always visible (section is at bottom of page) */}
      <span className="hist-sidebar__eyebrow hist-sidebar__eyebrow--desktop">ELSEWHERE, MEANWHILE</span>

      {/* Mobile accordion trigger */}
      <button
        className="hist-sidebar--mobile-toggle"
        type="button"
        onClick={() => setMobileOpen((prev) => !prev)}
        aria-expanded={mobileOpen}
      >
        <span className="hist-sidebar__eyebrow">ELSEWHERE, MEANWHILE</span>
        <span
          className={`hist-sidebar__disclosure ${mobileOpen ? "hist-sidebar__disclosure--open" : ""}`}
          aria-hidden="true"
        >
          &#9662;
        </span>
      </button>

      {/* Content — always visible on desktop, toggle on mobile */}
      <div className={`hist-sidebar__content ${mobileOpen ? "hist-sidebar__content--open" : ""}`}>
        {entries.map((entry, entryIndex) => (
          <div
            key={entry.slug}
            className="hist-sidebar__entry hist-reveal"
            style={{ transitionDelay: `${entryIndex * 100}ms` }}
          >
            <span className="hist-sidebar__entry-year">{entry.year}</span>
            <Link
              href={`/history/${entry.slug}`}
              className="hist-sidebar__entry-title"
            >
              {entry.title}
            </Link>
            <p className="hist-sidebar__entry-desc">{entry.description}</p>
          </div>
        ))}
      </div>
    </aside>
  );
}

/* ===========================================================================
   ArchivalVideo — Poster frame with play overlay → Internet Archive iframe
   No self-hosting. Camera-holder attribution is prominent ("Filmed by:").
   =========================================================================== */
function ArchivalVideo({ item }: { item: MediaItem }) {
  const [playing, setPlaying] = useState(false);

  if (playing && item.videoEmbedUrl) {
    return (
      <div className="hist-video">
        <iframe
          src={item.videoEmbedUrl}
          className="hist-video__iframe"
          allowFullScreen
          title={item.caption}
          loading="lazy"
        />
      </div>
    );
  }

  return (
    <button
      className="hist-video hist-video--poster"
      onClick={() => setPlaying(true)}
      type="button"
      aria-label={`Play archival footage: ${item.caption}`}
    >
      <img
        src={item.url}
        alt={item.caption}
        className="hist-video__poster"
        loading="lazy"
      />
      <div className="hist-video__play" aria-hidden="true">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <circle cx="24" cy="24" r="23" stroke="currentColor" strokeWidth="1.5" opacity="0.8" />
          <path d="M19 16l14 8-14 8V16z" fill="currentColor" opacity="0.9" />
        </svg>
      </div>
    </button>
  );
}
