"use client";

import { useMemo, useEffect, useRef } from "react";
import Link from "next/link";
import type { HistoricalEvent } from "../types";
import { THREADS } from "../threads";
import { HOOKS } from "../hooks";

/* ===========================================================================
   ThreadsLanding — Thematic thread strips across the full archive
   Each thread: label on far left, events sorted by dateSort across the strip.
   Event nodes show year + title + HOOK. No explanatory paragraphs.
   The juxtaposition of HOOKS does all the work.

   Micro-interaction choreography:
   - Nodes reveal sequentially as the user scrolls past each strip.
   - Connector ink lines draw between nodes after each node appears.
   - Per-node stagger (80ms gap) creates the sense of a timeline being
     assembled on screen -- archival documents being laid out in sequence.
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

  /* ── Scroll reveal: observe each .hist-threads__node for staggered entrance ── */
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("hist-reveal--visible");
          }
        });
      },
      { threshold: 0.15, rootMargin: "0px 0px -30px 0px" }
    );

    containerRef.current
      ?.querySelectorAll(".hist-threads__node")
      .forEach((el) => observer.observe(el));

    return () => observer.disconnect();
  }, [resolvedThreads]);

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
        {resolvedThreads.map((thread) => (
          <div key={thread.id} className="hist-threads__strip">
            <div className="hist-threads__strip-label" style={{ color: thread.colorVar }}>
              {thread.label}
            </div>
            <div className="hist-threads__strip-track">
              {thread.events.map((event, i) => {
                const year = extractDisplayYear(event);
                const hookText = HOOKS[event.slug] ?? "";

                return (
                  <div
                    key={event.slug}
                    className="hist-threads__node"
                    style={{ transitionDelay: `${i * 80}ms` }}
                  >
                    {/* Connecting ink line (not on first node) */}
                    {i > 0 && (
                      <hr
                        className="hist-threads__connector"
                        style={{ borderColor: thread.colorVar }}
                        aria-hidden="true"
                      />
                    )}
                    <Link
                      href={`/history/${event.slug}`}
                      className="hist-threads__node-card"
                    >
                      <span className="hist-threads__node-year">{year}</span>
                      <span className="hist-threads__node-title">{event.title}</span>
                      {hookText && (
                        <span className="hist-threads__node-hook">{hookText}</span>
                      )}
                    </Link>
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
    </div>
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
