"use client";

import { useState, useEffect, useRef, useMemo, Fragment } from "react";
import Link from "next/link";
import type { HistoricalEvent, MediaItem, EventConnection, ConnectionType } from "../types";
import { HOOKS, CTAS } from "../hooks";
import { ARC_FEATURES } from "../arc-features";
import HistoryAudioCue from "./HistoryAudioCue";
import StorySpine, { type SpineSection } from "./StorySpine";
import DossierRail from "./DossierRail";
import PerspectiveExhibit from "./PerspectiveExhibit";
import MediaGallery from "./MediaGallery";

/* ===========================================================================
   EventDetail — "The Dossier"
   Cardinal rules: Show Not Tell. Arrive Late, Leave Early.

   Cinematic cold open (Hero + Crack) then a navigable, two-column body:
     reading column  — The Account, The Voices, The Evidence, Threads
     dossier rail    — the record (facts, figures, parallel threads)
   A sticky spine lets the reader orient and jump instead of scrolling blind.
   =========================================================================== */

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

export default function EventDetail({ event, allEvents }: EventDetailProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const [storyExpanded, setStoryExpanded] = useState(false);

  /* Determine next event for the chronological exit */
  const nextEvent = useMemo(() => {
    const sorted = [...allEvents].sort((a, b) => a.dateSort - b.dateSort);
    const idx = sorted.findIndex((e) => e.slug === event.slug);
    if (idx === -1 || idx >= sorted.length - 1) return null;
    return sorted[idx + 1];
  }, [allEvents, event.slug]);

  /* Context image (map preferred) for inline narrative; the rest go to the
     contained Evidence gallery. */
  const { contextImage, galleryMedia } = useMemo(() => {
    const media = event.media;
    if (media.length === 0) return { contextImage: null, galleryMedia: [] as MediaItem[] };
    const mapIdx = media.findIndex((m) => m.type === "map");
    const ctxIdx = mapIdx >= 0 ? mapIdx : 0;
    return {
      contextImage: media[ctxIdx],
      galleryMedia: media.filter((_, i) => i !== ctxIdx),
    };
  }, [event.media]);

  /* The crack — hook text */
  const hook =
    HOOKS[event.slug] ||
    (event.contextNarrative || event.title).split(". ").slice(0, 2).join(". ") + ".";

  const sortedConnections = useMemo(() => {
    return [...event.connections].sort(
      (a, b) => (CONNECTION_PRIORITY[b.type] ?? 0) - (CONNECTION_PRIORITY[a.type] ?? 0)
    );
  }, [event.connections]);

  /* Dossier: top 3 connection-ranked events */
  const dossierEvents = useMemo(() => {
    if (!ARC_FEATURES.DOSSIER || sortedConnections.length === 0) return [];
    return sortedConnections.slice(0, 3).map((conn) => {
      const linked = allEvents.find((e) => e.slug === conn.targetSlug);
      return { connection: conn, event: linked ?? null };
    });
  }, [sortedConnections, allEvents]);

  /* Rail: parallel + consequence connections for "Elsewhere, Meanwhile" */
  const sidebarConnections = useMemo(() => {
    if (!ARC_FEATURES.SIDEBAR) return [] as EventConnection[];
    return event.connections.filter(
      (c) => c.type === "parallel" || c.type === "consequence"
    );
  }, [event.connections]);

  /* Story paragraphs */
  const paragraphs = useMemo(
    () => (event.contextNarrative || "").split("\n").filter(Boolean),
    [event.contextNarrative]
  );
  const visibleParas = paragraphs.slice(0, 2);
  const extraParas = paragraphs.slice(2);

  /* Spine sections — only those actually rendered */
  const hasThreads = (ARC_FEATURES.DOSSIER && dossierEvents.length > 0) || !!nextEvent;
  const sections = useMemo<SpineSection[]>(() => {
    const s: SpineSection[] = [];
    if (paragraphs.length > 0) s.push({ id: "story", label: "The Account" });
    if (event.perspectives.length > 0) s.push({ id: "voices", label: "The Voices" });
    if (galleryMedia.length > 0) s.push({ id: "evidence", label: "The Evidence" });
    if (hasThreads) s.push({ id: "threads", label: "Threads" });
    return s;
  }, [paragraphs.length, event.perspectives.length, galleryMedia.length, hasThreads]);

  /* Scroll reveal for .hist-reveal elements + dossier cards */
  useEffect(() => {
    const root = contentRef.current;
    if (!root) return;
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add("hist-reveal--visible");
        });
      },
      { threshold: 0.1, rootMargin: "0px 0px -40px 0px" }
    );
    root.querySelectorAll(".hist-reveal, .hist-dossier__card").forEach((el) =>
      observer.observe(el)
    );
    return () => observer.disconnect();
  }, []);

  return (
    <div ref={contentRef} className="hist-event-detail hist-story">

      {/* ── HERO — full-screen cinematic cold open ── */}
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

      {/* ── AUDIO COMPANION — void --onair (gated; renders only if generated) ── */}
      {event.audioUrl && (
        <HistoryAudioCue
          audioUrl={event.audioUrl}
          durationSeconds={event.audioDuration ?? 0}
          eventTitle={event.title}
          perspectives={event.perspectives}
        />
      )}

      {/* ── CRACK — inscribed line, bridge from cinema to dossier ── */}
      <section className="hist-stage hist-stage--crack">
        <blockquote className="hist-crack__text hist-reveal">{hook}</blockquote>
      </section>

      {/* ── BODY — two columns: reading column + sticky dossier rail ── */}
      <div className="hist-story__body">
        <StorySpine sections={sections} />

        <main className="hist-story__main">
          {/* THE ACCOUNT */}
          {paragraphs.length > 0 && (
            <section id="story" className="hist-story-section hist-reveal">
              <h2 className="hist-story-section__label">The Account</h2>
              <div className="hist-context__body">
                {visibleParas.map((para, i) => (
                  <Fragment key={i}>
                    <p>{para}</p>
                    {i === 0 && contextImage && (
                      <figure className="hist-context__figure">
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

                {event.significance && (
                  <blockquote className="hist-context__significance">
                    {event.significance}
                  </blockquote>
                )}

                {(extraParas.length > 0 || (event.legacyPoints && event.legacyPoints.length > 0)) && (
                  <>
                    {storyExpanded && (
                      <div className="hist-context__extra">
                        {extraParas.map((para, i) => (
                          <p key={i + 2}>{para}</p>
                        ))}
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
                      onClick={() => setStoryExpanded((v) => !v)}
                      aria-expanded={storyExpanded}
                    >
                      {storyExpanded ? "▴ Less" : "▾ Continue the account"}
                    </button>
                  </>
                )}
              </div>
            </section>
          )}

          {/* THE VOICES */}
          {event.perspectives.length > 0 && (
            <section id="voices" className="hist-story-section hist-reveal">
              <h2 className="hist-story-section__label">
                The Voices
                <span className="hist-story-section__count">{event.perspectives.length} accounts</span>
              </h2>
              <PerspectiveExhibit perspectives={event.perspectives} />
            </section>
          )}

          {/* THE EVIDENCE */}
          {galleryMedia.length > 0 && (
            <section id="evidence" className="hist-story-section hist-reveal">
              <h2 className="hist-story-section__label">The Evidence</h2>
              <MediaGallery media={galleryMedia} />
            </section>
          )}

          {/* THREADS — exit / dossier */}
          {hasThreads && (
            <section id="threads" className="hist-story-section hist-reveal">
              <h2 className="hist-story-section__label">Threads</h2>
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
                      <Link href={`/history/${nextEvent.slug}`}>chronologically &rarr;</Link>
                    </p>
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
              ) : null}
            </section>
          )}
        </main>

        <DossierRail
          event={event}
          sidebarConnections={sidebarConnections}
          allEvents={allEvents}
        />
      </div>

      {/* Return link */}
      <div className="hist-story__return">
        <Link href="/history" className="hist-next__cta">Return to The Archive</Link>
      </div>
    </div>
  );
}
