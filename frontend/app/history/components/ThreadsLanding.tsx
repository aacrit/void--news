"use client";

import { useMemo, useEffect, useRef, useState, useCallback } from "react";
import Link from "next/link";
import type { HistoricalEvent } from "../types";
import { THREADS, type ThematicThread } from "../threads";
import EventCard from "./EventCard";

/* ===========================================================================
   ThreadsLanding — Scrollable EventCard Carousel per Thematic Thread
   Each thread: colored header + count, then a horizontal scroll strip of
   EventCards (same archival card used on era/region pages — consistent look).
   IntersectionObserver triggers staggered entrance per strip.
   Scroll snap + nav buttons for keyboard accessibility.

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
            <div
              key={event.slug}
              className={`hist-threads__event-wrap${revealed ? " hist-threads__event-wrap--visible" : ""}`}
              style={{ "--card-delay": `${i * 80}ms` } as React.CSSProperties}
              role="listitem"
            >
              <EventCard event={event} />
            </div>
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
