"use client";

import { useMemo, useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import type { HistoricalEvent } from "../types";
import { THREADS, type ThematicThread } from "../threads";
import { HOOKS } from "../hooks";

/* ===========================================================================
   ThreadsLanding — Scrollable Story Card Carousel
   Each thread: header row (label + count), then a horizontal scroll strip
   of richly styled event cards. IntersectionObserver triggers staggered
   entrance per strip. Scroll snap + nav buttons for keyboard accessibility.

   Card anatomy: hero image bg (or burnt umber gradient), year badge,
   title (3 lines max), hook (italic one-liner), read link. Left border
   in thread perspective color.

   Cardinal rules: Show Not Tell. Arrive Late, Leave Early.
   =========================================================================== */

interface ThreadsLandingProps {
  events: HistoricalEvent[];
}

export default function ThreadsLanding({ events }: ThreadsLandingProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  /* Build lookup: slug -> event */
  const eventMap = useMemo(() => {
    const map = new Map<string, HistoricalEvent>();
    for (const e of events) {
      map.set(e.slug, e);
    }
    return map;
  }, [events]);

  /* Resolve thread events */
  const resolvedThreads = useMemo(() => {
    return THREADS.map((thread) => {
      const resolved = thread.eventSlugs
        .map((slug) => eventMap.get(slug))
        .filter((e): e is HistoricalEvent => e !== undefined)
        .sort((a, b) => a.dateSort - b.dateSort);
      return { ...thread, events: resolved };
    }).filter((t) => t.events.length >= 2);
  }, [eventMap]);

  return (
    <div className="hist-threads" ref={containerRef}>
      <header className="hist-threads__header">
        <h1 className="hist-threads__title">Thematic Threads</h1>
        <p className="hist-threads__subtitle">
          <Link href="/history">
            &larr; Back to The Archive
          </Link>
        </p>
      </header>

      <div className="hist-threads__strips">
        {resolvedThreads.map((thread, i) => (
          <ThreadStrip
            key={thread.id}
            thread={thread}
            events={thread.events}
            isLast={i === resolvedThreads.length - 1}
          />
        ))}
      </div>
    </div>
  );
}


/* ===========================================================================
   ThreadStrip — One horizontal carousel of event story cards
   Observes itself for viewport intersection, then triggers staggered
   card entrance. Includes scroll buttons and snap behavior.
   =========================================================================== */
function ThreadStrip({
  thread,
  events,
  isLast,
}: {
  thread: ThematicThread & { events: HistoricalEvent[] };
  events: HistoricalEvent[];
  isLast: boolean;
}) {
  const stripRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [revealed, setRevealed] = useState(false);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  /* ── Viewport reveal: observe the strip container ── */
  useEffect(() => {
    const el = stripRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            setRevealed(true);
            observer.disconnect();
          }
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  /* ── Scroll state: check if we can scroll left/right ── */
  const updateScrollState = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 2);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 2);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    updateScrollState();
    el.addEventListener("scroll", updateScrollState, { passive: true });
    window.addEventListener("resize", updateScrollState, { passive: true });
    return () => {
      el.removeEventListener("scroll", updateScrollState);
      window.removeEventListener("resize", updateScrollState);
    };
  }, [updateScrollState, events]);

  const scrollBy = useCallback((direction: -1 | 1) => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollBy({ left: direction * 240, behavior: "smooth" });
  }, []);

  /* Use 2-row layout for threads with more than 8 events */
  const useDoubleRow = events.length > 8;

  return (
    <div
      ref={stripRef}
      className={`hist-threads__strip${revealed ? " hist-threads__strip--revealed" : ""}`}
    >
      {/* Thread header */}
      <div className="hist-threads__strip-header">
        <h2
          className="hist-threads__strip-label"
          style={{ color: thread.colorVar }}
        >
          {thread.label}
        </h2>
        <span className="hist-threads__strip-count">
          {events.length} events
        </span>
      </div>

      {/* Track line behind cards */}
      <div className="hist-threads__track-line-wrap">
        <hr
          className="hist-threads__track-line"
          style={{ borderColor: thread.colorVar }}
          aria-hidden="true"
        />
      </div>

      {/* Scroll container with cards */}
      <div className="hist-threads__scroll-wrap">
        {/* Left scroll button */}
        <button
          type="button"
          className={`hist-threads__scroll-btn hist-threads__scroll-btn--left${canScrollLeft ? " hist-threads__scroll-btn--visible" : ""}`}
          onClick={() => scrollBy(-1)}
          aria-label={`Scroll ${thread.label} left`}
          tabIndex={canScrollLeft ? 0 : -1}
        >
          &larr;
        </button>

        {/* Scrollable card row */}
        <div
          ref={scrollRef}
          className={`hist-threads__card-row${useDoubleRow ? " hist-threads__card-row--double" : ""}`}
          role="list"
          aria-label={`${thread.label} events`}
        >
          {events.map((event, i) => (
            <StoryCard
              key={event.slug}
              event={event}
              index={i}
              thread={thread}
              revealed={revealed}
            />
          ))}
        </div>

        {/* Right scroll button */}
        <button
          type="button"
          className={`hist-threads__scroll-btn hist-threads__scroll-btn--right${canScrollRight ? " hist-threads__scroll-btn--visible" : ""}`}
          onClick={() => scrollBy(1)}
          aria-label={`Scroll ${thread.label} right`}
          tabIndex={canScrollRight ? 0 : -1}
        >
          &rarr;
        </button>

        {/* Right fade hint */}
        {canScrollRight && (
          <div className="hist-threads__fade-hint" aria-hidden="true" />
        )}
      </div>

      {/* Divider between strips */}
      {!isLast && (
        <hr className="hist-threads__divider" aria-hidden="true" />
      )}
    </div>
  );
}


/* ===========================================================================
   StoryCard — Individual event card within a thread carousel
   Hero image bg, year badge, title, hook, read link. Left border color
   from the thread's perspective color.
   =========================================================================== */
function StoryCard({
  event,
  index,
  thread,
  revealed,
}: {
  event: HistoricalEvent;
  index: number;
  thread: ThematicThread;
  revealed: boolean;
}) {
  const year = extractDisplayYear(event);
  const hookText = HOOKS[event.slug] ?? "";
  const fallbackHook = hookText
    || (event.contextNarrative || "").split(". ").slice(0, 1).join(". ");

  const hasHero = !!event.heroImage;

  return (
    <Link
      href={`/history/${event.slug}`}
      className={`hist-threads__card${revealed ? " hist-threads__card--visible" : ""}`}
      style={{
        "--card-delay": `${index * 80}ms`,
        "--thread-color": thread.colorVar,
      } as React.CSSProperties}
      role="listitem"
      aria-label={`${event.title} — ${year}`}
    >
      {/* Hero image or gradient fallback */}
      <div className="hist-threads__card-bg" aria-hidden="true">
        {hasHero ? (
          <img
            src={event.heroImage}
            alt=""
            className="hist-threads__card-img"
            loading="lazy"
          />
        ) : (
          <div className="hist-threads__card-gradient" />
        )}
        <div className="hist-threads__card-overlay" />
      </div>

      {/* Thread color indicator — left border */}
      <div
        className="hist-threads__card-indicator"
        style={{ background: thread.colorVar }}
        aria-hidden="true"
      />

      {/* Content */}
      <div className="hist-threads__card-content">
        <span className="hist-threads__card-year">{year}</span>
        <h3 className="hist-threads__card-title">{event.title}</h3>
        {fallbackHook && (
          <p className="hist-threads__card-hook">{fallbackHook}</p>
        )}
        <span className="hist-threads__card-read" aria-hidden="true">
          Read &rarr;
        </span>
      </div>
    </Link>
  );
}


/* ── Extract display year from dateSort ── */
function extractDisplayYear(event: HistoricalEvent): string {
  const abs = Math.abs(event.dateSort);
  const s = String(abs);
  if (s.length >= 8) {
    const y = s.slice(0, 4);
    return event.dateSort < 0 ? `${y} BCE` : y;
  }
  if (s.length >= 4) {
    const y = s.slice(0, s.length >= 8 ? 4 : s.length);
    return event.dateSort < 0 ? `${y} BCE` : y;
  }
  const match = event.datePrimary.match(/\d{4}/);
  return match ? match[0] : "";
}
