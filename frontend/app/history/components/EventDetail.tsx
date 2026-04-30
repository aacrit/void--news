"use client";

import { useState, useEffect, useRef, useMemo, useCallback, Fragment } from "react";
import Link from "next/link";
import type { HistoricalEvent, Perspective, MediaItem, EventConnection, ConnectionType } from "../types";
import { HOOKS, CTAS } from "../hooks";
import { ARC_FEATURES } from "../arc-features";
import HistoryAudioCue from "./HistoryAudioCue";

/* ===========================================================================
   EventDetail — Museum Journey
   Cardinal rules: Show Not Tell. Arrive Late, Leave Early.

   Hero      — full-screen cinematic entry
   Crack     — one inscribed line that breaks the textbook
   Record    — merged facts + figures, aged artifact treatment
   Context   — balanced full story, significance, legacy
   Witnesses — perspectives one argument at a time (museum vitrine)
   Omissions — what each side hides (toggle on mobile)
   Evidence  — archival gallery
   Exit      — dossier or cliffhanger
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

/* ── Connection type directional glyphs (Show Don't Tell) ── */
const CONNECTION_GLYPH: Record<ConnectionType, string> = {
  caused: "↓",
  consequence: "↑",
  "response-to": "↑",
  influenced: "·",
  parallel: "·",
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
  const [omissionsView, setOmissionsView] = useState<"stressed" | "ignored">("stressed");

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

  /* Format year for Key Figures: ≤0 = BCE */
  const fmtYear = (y: number) => y <= 0 ? `${Math.abs(y) + (y === 0 ? 1 : 0)} BCE` : String(y);

  return (
    <div ref={contentRef} className={`hist-event-detail${showSidebar ? " hist-layout-sidebar" : ""}`}>

      {/* ── HERO — full-screen cinematic entry, unchanged ── */}
      <section className="hist-stage hist-stage--scene">
        <div
          className="hist-stage__hero"
          style={event.heroImage ? { backgroundImage: `url(${event.heroImage})` } : undefined}
        >
          {!event.heroImage && <div className="hist-stage__hero-fallback" />}
          <div className="hist-stage__hero-overlay" />
          <div className="hist-stage__hero-content">
            <span className="hist-stage__date">{event.datePrimary}</span>
            <h1 className="hist-stage__title">{event.title}</h1>
            {event.subtitle && <p className="hist-stage__subtitle">{event.subtitle}</p>}
            {event.audioUrl && (
              <button
                type="button"
                className="hist-hero-listen"
                onClick={() => {
                  const playBtn = document.querySelector('.hist-audio-cue__play') as HTMLButtonElement;
                  if (playBtn) playBtn.click();
                }}
                aria-label={`Listen to ${event.title} — ${event.perspectives.length} perspectives`}
              >
                <svg width="12" height="14" viewBox="0 0 12 14" fill="currentColor" aria-hidden="true" className="hist-hero-listen__icon">
                  <path d="M1 1.5v11l10-5.5z" />
                </svg>
                <span className="hist-hero-listen__label">Listen</span>
                <span className="hist-hero-listen__meta">{event.perspectives.length} perspectives · {Math.floor((event.audioDuration ?? 0) / 60)}:{String((event.audioDuration ?? 0) % 60).padStart(2, '0')}</span>
              </button>
            )}
          </div>
          {event.heroAttribution && (
            <span className="hist-stage__attribution">{event.heroAttribution}</span>
          )}
        </div>
        <div className="hist-stage__scroll-hint" aria-hidden="true">
          <span className="hist-stage__scroll-line" />
        </div>
      </section>

      {/* ── AUDIO COMPANION — void --onair for history
           In-flow between Scene and The Crack.
           Renders only when audio has been generated for this event. ── */}
      {event.audioUrl && (
        <HistoryAudioCue
          audioUrl={event.audioUrl}
          durationSeconds={event.audioDuration ?? 0}
          eventTitle={event.title}
          perspectives={event.perspectives}
        />
      )}

      {/* ── CRACK — inscribed line, separate scroll stop ── */}
      <section className="hist-stage hist-stage--crack">
        <blockquote className="hist-crack__text hist-reveal">{hook}</blockquote>
      </section>

      {/* ── RECORD — merged facts + figures, aged artifact ── */}
      <section className="hist-stage hist-stage--record">
        <div className="hist-record hist-reveal">
          <dl className="hist-record__ledger">
            <div className="hist-record__row">
              <dt>Date</dt>
              <dd>{event.dateRange || event.datePrimary}</dd>
            </div>
            <div className="hist-record__row">
              <dt>Location</dt>
              <dd>{event.location}</dd>
            </div>
            {event.duration && (
              <div className="hist-record__row">
                <dt>Duration</dt>
                <dd>{event.duration}</dd>
              </div>
            )}
            {event.deathToll && event.deathToll !== "N/A" && (
              <div className="hist-record__row">
                <dt>Killed</dt>
                <dd>{event.deathToll}</dd>
              </div>
            )}
            {event.displaced && event.displaced !== "N/A" && (
              <div className="hist-record__row">
                <dt>Displaced</dt>
                <dd>{event.displaced}</dd>
              </div>
            )}
          </dl>

          {event.keyFigures.length > 0 && (
            <>
              <div className="hist-record__divider" aria-hidden="true" />
              <dl className="hist-record__ledger hist-record__ledger--figures">
                {event.keyFigures.map((fig, i) => {
                  const hasDates = fig.born != null || fig.died != null;
                  const dateStr = hasDates
                    ? `${fig.born != null ? fmtYear(fig.born) : "?"}–${fig.died != null ? fmtYear(fig.died) : "?"}`
                    : null;
                  return (
                    <div key={i} className="hist-record__row hist-record__row--figure">
                      <dt>
                        {fig.wikipedia ? (
                          <a
                            href={fig.wikipedia}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="hist-record__figure-name"
                            aria-label={`${fig.name} on Wikipedia (opens in new tab)`}
                          >
                            {fig.name}
                          </a>
                        ) : (
                          <span className="hist-record__figure-name">{fig.name}</span>
                        )}
                        {dateStr && (
                          <span className="hist-record__figure-dates">{dateStr}</span>
                        )}
                      </dt>
                      <dd>{fig.role}</dd>
                    </div>
                  );
                })}
              </dl>
            </>
          )}
        </div>
      </section>

      {/* ── CONTEXT — balanced full story, then significance + legacy ── */}
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
                          onError={(e) => { (e.currentTarget.parentElement as HTMLElement).style.display = "none"; }}
                        />
                        <figcaption>
                          {contextImage.caption}
                          <span className="hist-context__figure-attr">{contextImage.attribution}</span>
                        </figcaption>
                      </figure>
                    )}
                  </Fragment>
                ))}

                {/* Significance — long-term impact pull quote */}
                {event.significance && (
                  <blockquote className="hist-context__significance">
                    {event.significance}
                  </blockquote>
                )}

                {extra.length > 0 && (
                  <>
                    {storyExpanded && (
                      <div className="hist-context__extra">
                        {extra.map((para, i) => (
                          <p key={i + 2}>{para}</p>
                        ))}
                        {/* Legacy points — surfaced in expanded section */}
                        {event.legacyPoints && event.legacyPoints.length > 0 && (
                          <ul className="hist-context__legacy">
                            {event.legacyPoints.map((point, li) => (
                              <li key={li}>{point}</li>
                            ))}
                          </ul>
                        )}
                      </div>
                    )}
                    <button
                      type="button"
                      className="hist-context__more-toggle"
                      onClick={() => setStoryExpanded((prev) => !prev)}
                      aria-expanded={storyExpanded}
                    >
                      {storyExpanded ? "\u25B4" : "\u25BE"}
                    </button>
                  </>
                )}
              </>
            );
          })()}
        </div>
      </section>

      {/* ── PERSPECTIVES — witnesses, one argument visible, museum vitrine ── */}
      <section className="hist-stage hist-stage--perspectives">
        {event.perspectives.map((perspective, i) => (
          <Fragment key={perspective.id}>
            <WitnessBlock perspective={perspective} index={i} />
            {(i + 1) % 2 === 0 && perspectiveIntercuts[Math.floor(i / 2)] && (
              <figure className="hist-intercut hist-reveal">
                <img
                  src={perspectiveIntercuts[Math.floor(i / 2)].url}
                  alt={perspectiveIntercuts[Math.floor(i / 2)].caption}
                  loading="lazy"
                  onError={(e) => { (e.currentTarget.parentElement as HTMLElement).style.display = "none"; }}
                />
                <figcaption>
                  {perspectiveIntercuts[Math.floor(i / 2)].caption}
                  {perspectiveIntercuts[Math.floor(i / 2)].year && (
                    <span className="hist-intercut__year">
                      {" "}({perspectiveIntercuts[Math.floor(i / 2)].year})
                    </span>
                  )}
                  <span className="hist-intercut__attribution">
                    {perspectiveIntercuts[Math.floor(i / 2)].attribution}
                  </span>
                </figcaption>
              </figure>
            )}
          </Fragment>
        ))}
      </section>

      {/* ── OMISSIONS — stressed vs ignored, mobile toggle ── */}
      <section className="hist-stage hist-stage--omissions">
        {/* Mobile toggle — flip the card */}
        <div className="hist-omissions__toggle-bar" role="group" aria-label="Omissions view">
          <button
            type="button"
            className={`hist-omissions__toggle-btn${omissionsView === "stressed" ? " hist-omissions__toggle-btn--active" : ""}`}
            onClick={() => setOmissionsView("stressed")}
            aria-pressed={omissionsView === "stressed"}
          >
            stressed
          </button>
          <span className="hist-omissions__toggle-sep" aria-hidden="true">·</span>
          <button
            type="button"
            className={`hist-omissions__toggle-btn${omissionsView === "ignored" ? " hist-omissions__toggle-btn--active" : ""}`}
            onClick={() => setOmissionsView("ignored")}
            aria-pressed={omissionsView === "ignored"}
          >
            ignored
          </button>
        </div>

        <div className="hist-omissions-split">
          <div
            className={`hist-omissions-split__panel hist-omissions-split__panel--emphasized hist-reveal${omissionsView === "stressed" ? " hist-omissions-split__panel--mobile-visible" : ""}`}
          >
            {event.perspectives.map((p) => (
              <div key={p.id} className="hist-omissions-split__group">
                <span className="hist-omissions-split__name" style={{ color: PERSP_COLORS[p.color] }}>
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

          {omissionImage && (
            <figure className="hist-intercut hist-intercut--omission hist-reveal">
              <img
                src={omissionImage.url}
                alt={omissionImage.caption}
                loading="lazy"
                onError={(e) => { (e.currentTarget.parentElement as HTMLElement).style.display = "none"; }}
              />
              <figcaption>
                {omissionImage.caption}
                <span className="hist-intercut__attribution">{omissionImage.attribution}</span>
              </figcaption>
            </figure>
          )}

          <div
            className={`hist-omissions-split__panel hist-omissions-split__panel--omitted hist-reveal${omissionsView === "ignored" ? " hist-omissions-split__panel--mobile-visible" : ""}`}
          >
            {event.perspectives.filter((p) => p.omissions.length > 0).map((p) => (
              <div key={p.id} className="hist-omissions-split__group">
                <span className="hist-omissions-split__name" style={{ color: PERSP_COLORS[p.color] }}>
                  {p.viewpointName}
                </span>
                <ul className="hist-omissions-split__list">
                  {p.omissions.map((o, oi) => (
                    <li key={oi} className="hist-omission--struck">{o}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── EVIDENCE — archival gallery, no label ── */}
      {galleryImages.length > 0 && (
        <section className="hist-stage hist-stage--evidence">
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
                    onError={(e) => { e.currentTarget.style.display = "none"; }}
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

      {/* ── EXIT — dossier or cliffhanger ── */}
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
                  || `${linkedEvent?.perspectives.length ?? 0} accounts`;
                const heroImg = linkedEvent?.heroImage;
                const glyph = CONNECTION_GLYPH[connection.type] ?? "·";

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
                      <span className="hist-dossier__card-glyph" aria-hidden="true">{glyph}</span>
                      <p className="hist-dossier__card-hook">{hookText}</p>
                      <span className="hist-dossier__card-cta">{ctaText}</span>
                    </div>
                  </Link>
                );
              })}
            </div>
            {nextEvent && (
              <p className="hist-dossier__chrono">
                <Link href={`/history/${nextEvent.slug}`}>
                  chronologically &rarr;
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
                      {CONNECTION_GLYPH[conn.type] ?? "·"}
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
                <img src={nextEvent.heroImage} alt="" className="hist-next__thumb" loading="lazy" />
              </div>
            )}
            <p className="hist-next__hook">
              {HOOKS[nextEvent.slug] || (nextEvent.contextNarrative || nextEvent.title).split(". ").slice(0, 2).join(". ") + "."}
            </p>
            <Link href={`/history/${nextEvent.slug}`} className="hist-next__cta">
              {CTAS[nextEvent.slug] || `${nextEvent.perspectives.length} accounts of ${nextEvent.title}`}
            </Link>
          </div>
        ) : (
          <Link href="/history" className="hist-next__cta">Return to The Archive</Link>
        )}
      </section>

      {showSidebar && (
        <SidebarElsewhere connections={sidebarConnections} allEvents={allEvents} />
      )}
    </div>
  );
}

/* ===========================================================================
   WitnessBlock — Museum vitrine model
   Identity + ONE argument visible. Rest behind expand.
   Cinematic reveal: lean in to see more.
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
  const toggleExpand = useCallback(() => setExpanded((prev) => !prev), []);
  const perspColor = PERSP_COLORS[perspective.color] || PERSP_COLORS.a;

  const leadArgument = perspective.keyNarratives[0];
  const remainingArguments = perspective.keyNarratives.slice(1);
  const hasMore = remainingArguments.length > 0 || perspective.primarySources.length > 0 || !!perspective.narrative;
  const moreCount = remainingArguments.length + perspective.primarySources.length;

  return (
    <div
      className={`hist-witness hist-witness--${side} hist-reveal`}
      style={{ transitionDelay: `${index * 150}ms`, "--persp-color": perspColor } as React.CSSProperties}
    >
      {/* Identity */}
      <div className="hist-witness__identity">
        <span
          className="hist-witness__dot"
          style={{ background: perspColor }}
          aria-hidden="true"
        />
        <span className="hist-witness__name">{perspective.viewpointName}</span>
        <span className="hist-witness__type">{perspective.viewpointType}</span>
      </div>

      {/* Lead argument — always visible */}
      {leadArgument && (
        <blockquote className="hist-witness__argument">{leadArgument}</blockquote>
      )}

      {/* Expand — remaining arguments + narrative + sources */}
      {hasMore && (
        <button
          className="hist-witness__expand"
          type="button"
          onClick={toggleExpand}
          aria-expanded={expanded}
        >
          <span className={`hist-witness__expand-arrow${expanded ? " hist-witness__expand-arrow--open" : ""}`} aria-hidden="true">
            {expanded ? "\u25B4" : "\u25BE"}
          </span>
          {!expanded && moreCount > 0 && (
            <span className="hist-witness__expand-count">{moreCount}</span>
          )}
        </button>
      )}

      {expanded && (
        <div className="hist-witness__full-narrative">
          {/* Remaining key arguments */}
          {remainingArguments.map((narrative, ni) => (
            <blockquote key={ni} className="hist-witness__argument hist-witness__argument--secondary">
              {narrative}
            </blockquote>
          ))}

          {/* Full narrative */}
          {perspective.narrative && (
            <p className="hist-witness__narrative-text">{perspective.narrative}</p>
          )}

          {/* Primary source quotes */}
          {perspective.primarySources.map((source, si) => (
            <div key={si} className="hist-witness__source">
              <p className="hist-witness__quote">&ldquo;{source.text}&rdquo;</p>
              <cite className="hist-witness__cite">
                &mdash; {source.author}
                {source.work && <>, <em>{source.work}</em></>}
                {source.date && `, ${source.date}`}
              </cite>
            </div>
          ))}

          {/* Disputed claims */}
          {perspective.disputed.length > 0 && (
            <div className="hist-witness__disputed">
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
