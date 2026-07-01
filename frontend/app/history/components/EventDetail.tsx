"use client";

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import Link from "next/link";
import type { HistoricalEvent, Perspective, MediaItem, ConnectionType } from "../types";
import { HOOKS, CTAS } from "../hooks";
import { ARC_FEATURES } from "../arc-features";
import HistoryAudioCue from "./HistoryAudioCue";
import ReelScrubber, { type ScrubNode } from "./ReelScrubber";
import PerspectiveFrame from "./PerspectiveFrame";
import PerspectiveReader from "./PerspectiveReader";
import Lightbox from "./Lightbox";

/* ===========================================================================
   EventDetail — "The Testimony Reel"
   Cardinal rules: Show Not Tell. Arrive Late, Leave Early.

   The full-screen hero stays the cold open. Beneath it, a thin facts readout,
   then a horizontal, snap-scrubbable reel: one perspective per frame, then a
   Threads exit. A drawn ink-track scrubber (echoing the timeline) tracks
   position; depth lives in a reader overlay. Mobile flips to vertical snap.
   =========================================================================== */

const CONNECTION_PRIORITY: Record<ConnectionType, number> = {
  caused: 4,
  consequence: 3,
  "response-to": 3,
  influenced: 2,
  parallel: 1,
};

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
  const reelRef = useRef<HTMLDivElement>(null);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const [fraction, setFraction] = useState(0);
  const [reader, setReader] = useState<Perspective | null>(null);
  const [evidenceIndex, setEvidenceIndex] = useState<number | null>(null);
  const [isVertical, setIsVertical] = useState(false);

  const perspectives = event.perspectives;
  const frameCount = perspectives.length + 1; // voices + threads

  /* Background images for voice frames (skip video posters) */
  const bgImages = useMemo(
    () => event.media.filter((m) => m.type !== "video"),
    [event.media]
  );
  const bgFor = (i: number): MediaItem | null =>
    bgImages.length ? bgImages[i % bgImages.length] : null;

  /* Chronological next */
  const nextEvent = useMemo(() => {
    const sorted = [...allEvents].sort((a, b) => a.dateSort - b.dateSort);
    const idx = sorted.findIndex((e) => e.slug === event.slug);
    return idx === -1 || idx >= sorted.length - 1 ? null : sorted[idx + 1];
  }, [allEvents, event.slug]);

  const sortedConnections = useMemo(
    () =>
      [...event.connections].sort(
        (a, b) => (CONNECTION_PRIORITY[b.type] ?? 0) - (CONNECTION_PRIORITY[a.type] ?? 0)
      ),
    [event.connections]
  );

  const dossierEvents = useMemo(() => {
    if (!ARC_FEATURES.DOSSIER || sortedConnections.length === 0) return [];
    return sortedConnections.slice(0, 3).map((conn) => ({
      connection: conn,
      event: allEvents.find((e) => e.slug === conn.targetSlug) ?? null,
    }));
  }, [sortedConnections, allEvents]);

  /* Scrubber nodes: one per voice + the threads exit */
  const scrubNodes = useMemo<ScrubNode[]>(() => {
    const voices = perspectives.map((p) => ({
      key: p.id,
      label: p.viewpointName,
      sublabel: p.viewpointType,
      color: `var(--hist-persp-${p.color})`,
    }));
    return [
      ...voices,
      { key: "threads", label: "Threads", sublabel: "connections", color: "var(--hist-accent)" },
    ];
  }, [perspectives]);

  /* Facts readout */
  const facts = useMemo(() => {
    const f: { label: string; value: string }[] = [];
    f.push({ label: "Date", value: event.dateRange || event.datePrimary });
    if (event.location) f.push({ label: "Location", value: event.location });
    if (event.deathToll && event.deathToll !== "N/A") f.push({ label: "Killed", value: event.deathToll });
    if (event.displaced && event.displaced !== "N/A") f.push({ label: "Displaced", value: event.displaced });
    return f;
  }, [event]);

  const cast = useMemo(
    () => event.keyFigures.slice(0, 5).map((k) => k.name).join("  ·  "),
    [event.keyFigures]
  );

  /* Orientation: vertical snap on narrow screens (mirrors the timeline) */
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1023px)");
    const apply = () => setIsVertical(mq.matches);
    apply();
    mq.addEventListener("change", apply);
    return () => mq.removeEventListener("change", apply);
  }, []);

  /* Scroll choreography: focus tracking + progress fraction + parallax */
  useEffect(() => {
    const el = reelRef.current;
    if (!el) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const onScroll = () => {
      const frames = Array.from(el.children) as HTMLElement[];
      if (frames.length === 0) return;

      let closest = 0;
      let closestDist = Infinity;
      if (isVertical) {
        const center = el.scrollTop + el.clientHeight / 2;
        frames.forEach((fr, i) => {
          const c = fr.offsetTop + fr.offsetHeight / 2;
          const d = Math.abs(c - center);
          if (d < closestDist) { closestDist = d; closest = i; }
        });
        const max = el.scrollHeight - el.clientHeight;
        setFraction(max > 0 ? el.scrollTop / max : 0);
      } else {
        const center = el.scrollLeft + el.clientWidth / 2;
        frames.forEach((fr, i) => {
          const c = fr.offsetLeft + fr.offsetWidth / 2;
          const d = Math.abs(c - center);
          if (d < closestDist) { closestDist = d; closest = i; }
        });
        const max = el.scrollWidth - el.clientWidth;
        setFraction(max > 0 ? el.scrollLeft / max : 0);
      }
      setFocusedIndex(closest);

      /* Parallax: shift each frame's background against the scroll */
      if (!reduce) {
        frames.forEach((fr) => {
          const bg = fr.querySelector<HTMLElement>(".hist-frame__bg");
          if (!bg) return;
          if (isVertical) {
            const rel = (fr.offsetTop - el.scrollTop) / el.clientHeight;
            bg.style.transform = `translateY(${rel * 40}px) scale(1.14)`;
          } else {
            const rel = (fr.offsetLeft - el.scrollLeft) / el.clientWidth;
            bg.style.transform = `translateX(${rel * 48}px) scale(1.14)`;
          }
        });
      }
    };

    onScroll();
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [isVertical, frameCount]);

  /* Desktop: translate vertical wheel into horizontal scrubbing, releasing to
     the page at the left edge so the reader can scroll back up to the hero. */
  useEffect(() => {
    const el = reelRef.current;
    if (!el || isVertical) return;

    const onWheel = (e: WheelEvent) => {
      /* Only scrub once the reel has snapped to fill the viewport — otherwise
         let the page finish scrolling the hero away. */
      if (el.getBoundingClientRect().top > 2) return;
      const delta = Math.abs(e.deltaY) > Math.abs(e.deltaX) ? e.deltaY : e.deltaX;
      const max = el.scrollWidth - el.clientWidth;
      const atLeft = el.scrollLeft <= 0;
      const atRight = el.scrollLeft >= max - 1;
      if ((atLeft && delta < 0) || (atRight && delta > 0)) return; // release to page
      e.preventDefault();
      el.scrollLeft += delta;
    };

    el.addEventListener("wheel", onWheel, { passive: false });
    return () => el.removeEventListener("wheel", onWheel);
  }, [isVertical]);

  const goToFrame = useCallback((i: number) => {
    const el = reelRef.current;
    if (!el) return;
    const frame = el.children[i] as HTMLElement | undefined;
    if (!frame) return;
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    frame.scrollIntoView({
      behavior: reduce ? "auto" : "smooth",
      inline: "center",
      block: "center",
    });
  }, []);

  const onReelKey = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowRight" || e.key === "ArrowDown") {
        e.preventDefault();
        goToFrame(Math.min(focusedIndex + 1, frameCount - 1));
      } else if (e.key === "ArrowLeft" || e.key === "ArrowUp") {
        e.preventDefault();
        goToFrame(Math.max(focusedIndex - 1, 0));
      } else if (e.key === "Home") {
        e.preventDefault();
        goToFrame(0);
      } else if (e.key === "End") {
        e.preventDefault();
        goToFrame(frameCount - 1);
      }
    },
    [focusedIndex, frameCount, goToFrame]
  );

  return (
    <div className="hist-event-detail hist-reel-page">

      {/* ── HERO — full-screen cold open (unchanged) ── */}
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

      {/* ── AUDIO COMPANION (gated; renders only if generated) ── */}
      {event.audioUrl && (
        <HistoryAudioCue
          audioUrl={event.audioUrl}
          durationSeconds={event.audioDuration ?? 0}
          eventTitle={event.title}
          perspectives={event.perspectives}
        />
      )}

      {/* ── FACTS READOUT — the only persistent supporting material ── */}
      <div className="hist-readout">
        <dl className="hist-readout__facts">
          {facts.map((f) => (
            <div key={f.label} className="hist-readout__fact">
              <dt>{f.label}</dt>
              <dd>{f.value}</dd>
            </div>
          ))}
        </dl>
        <div className="hist-readout__aside">
          {cast && <p className="hist-readout__cast">{cast}</p>}
          {bgImages.length > 0 && (
            <button
              type="button"
              className="hist-readout__evidence"
              onClick={() => setEvidenceIndex(0)}
            >
              Evidence ({event.media.length})
            </button>
          )}
        </div>
      </div>

      {/* ── THE REEL — one voice per frame, then Threads ── */}
      <section className="hist-reel-section">
        <div
          ref={reelRef}
          className={`hist-reel${isVertical ? " hist-reel--vertical" : ""}`}
          tabIndex={0}
          role="group"
          aria-label={`${perspectives.length} accounts of ${event.title}. Use arrow keys to move between them.`}
          onKeyDown={onReelKey}
        >
          {perspectives.map((p, i) => (
            <PerspectiveFrame
              key={p.id}
              perspective={p}
              index={i}
              total={perspectives.length}
              background={bgFor(i)}
              active={focusedIndex === i}
              onReadFull={() => setReader(p)}
            />
          ))}

          {/* Threads exit frame */}
          <section className="hist-reel__frame hist-frame hist-frame--threads">
            <div className="hist-frame__content hist-frame__content--threads">
              <span className="hist-frame__eyebrow">Threads</span>
              <h2 className="hist-frame__name">What this connects to</h2>
              {dossierEvents.length > 0 ? (
                <div className="hist-exit">
                  {dossierEvents.map(({ connection, event: linked }) => {
                    const slug = connection.targetSlug;
                    const hookText = HOOKS[slug]
                      || (linked?.contextNarrative || connection.targetTitle).split(". ").slice(0, 2).join(". ") + ".";
                    const glyph = CONNECTION_GLYPH[connection.type] ?? "·";
                    return (
                      <Link key={slug} href={`/history/${slug}`} className="hist-exit__card">
                        <span className="hist-exit__glyph" aria-hidden="true">{glyph}</span>
                        <span className="hist-exit__title">{connection.targetTitle}</span>
                        <span className="hist-exit__hook">{hookText}</span>
                      </Link>
                    );
                  })}
                </div>
              ) : (
                <p className="hist-frame__lead">A single thread in a longer record.</p>
              )}
              <div className="hist-exit__exits">
                {nextEvent && (
                  <Link href={`/history/${nextEvent.slug}`} className="hist-exit__next">
                    {CTAS[nextEvent.slug] || `Next: ${nextEvent.title}`} →
                  </Link>
                )}
                <Link href="/history" className="hist-exit__archive">Return to The Archive</Link>
              </div>
            </div>
          </section>
        </div>

        <ReelScrubber
          nodes={scrubNodes}
          activeIndex={focusedIndex}
          fraction={fraction}
          onSelect={goToFrame}
        />
      </section>

      {reader && (
        <PerspectiveReader perspective={reader} onClose={() => setReader(null)} />
      )}

      {evidenceIndex !== null && event.media.length > 0 && (
        <Lightbox
          media={event.media}
          currentIndex={evidenceIndex}
          onClose={() => setEvidenceIndex(null)}
          onNavigate={setEvidenceIndex}
        />
      )}
    </div>
  );
}
