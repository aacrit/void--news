"use client";

import { useState, useEffect, useRef, useCallback, useMemo, forwardRef } from "react";
import type { HistoricalEvent, RedactedEvent, HistoryEra } from "../types";
import { ERAS } from "../types";
import { HOOKS, CTAS } from "../hooks";
import HistoryOverlay from "./HistoryOverlay";

/* ===========================================================================
   HistoryLanding — The Timeline
   Horizontal scroll through time. Cards snap to center. A single CSS custom
   property `--tl-focus` (0-1) drives rack focus, content reveal, and scale.
   Cardinal rules: Show Not Tell. Arrive Late, Leave Early.
   =========================================================================== */

/* ── Era groups for fast-travel buttons ── */
interface EraGroup {
  id: HistoryEra;
  label: string;
  firstIndex: number;
  lastIndex: number;
}

function buildEraGroups(events: HistoricalEvent[]): EraGroup[] {
  const eraOrder: HistoryEra[] = [
    "ancient",
    "classical",
    "medieval",
    "early-modern",
    "modern",
    "contemporary",
  ];
  const groups: EraGroup[] = [];
  for (const eraId of eraOrder) {
    const indices = events
      .map((e, i) => (e.era === eraId ? i : -1))
      .filter((i) => i !== -1);
    if (indices.length > 0) {
      const eraInfo = ERAS.find((e) => e.id === eraId);
      groups.push({
        id: eraId,
        label: eraInfo?.label || eraId,
        firstIndex: indices[0],
        lastIndex: indices[indices.length - 1],
      });
    }
  }
  return groups;
}

/* ── Perspective color map ── */
const PERSP_COLORS: Record<string, string> = {
  a: "var(--hist-persp-a)",
  b: "var(--hist-persp-b)",
  c: "var(--hist-persp-c)",
  d: "var(--hist-persp-d)",
  e: "var(--hist-persp-e)",
};

/* ── Severity → CSS modifier ── */
const SEVERITY_CLASS: Record<string, string> = {
  catastrophic: "hist-tl-card--catastrophic",
  critical: "hist-tl-card--critical",
  major: "hist-tl-card--major",
};

/* ── Extract year from YYYYMMDD dateSort ── */
function extractYear(dateSort: number, datePrimary: string): string {
  const s = String(dateSort);
  if (s.length >= 4) return s.slice(0, 4);
  const match = datePrimary.match(/\d{4}/);
  return match ? match[0] : "";
}

/* ===========================================================================
   PosterImage — Robust fallback chain
   heroImage -> media[0].url -> media[1].url -> ... -> cinematic gradient
   =========================================================================== */
function PosterImage({ event, eager }: { event: HistoricalEvent; eager?: boolean }) {
  const fallbackUrls = useMemo(() => {
    const urls: string[] = [];
    if (event.heroImage) urls.push(event.heroImage);
    event.media.forEach((m) => {
      if (m.url && m.type === "image") urls.push(m.url);
    });
    event.media.forEach((m) => {
      if (m.url && m.type !== "image" && !urls.includes(m.url)) urls.push(m.url);
    });
    return urls;
  }, [event.heroImage, event.media]);

  const [currentIndex, setCurrentIndex] = useState(0);
  const [allFailed, setAllFailed] = useState(fallbackUrls.length === 0);

  const handleError = useCallback(() => {
    const nextIdx = currentIndex + 1;
    if (nextIdx < fallbackUrls.length) {
      setCurrentIndex(nextIdx);
    } else {
      setAllFailed(true);
    }
  }, [currentIndex, fallbackUrls.length]);

  if (allFailed) {
    return <div className="hist-tl-card__photo-fallback" aria-hidden="true" />;
  }

  return (
    <img
      src={fallbackUrls[currentIndex]}
      alt={event.heroCaption || event.title}
      loading={eager ? "eager" : "lazy"}
      className="hist-tl-card__photo-img"
      onError={handleError}
    />
  );
}

/* ── Props ── */
interface HistoryLandingProps {
  events: HistoricalEvent[];
  redacted: RedactedEvent[];
}

export default function HistoryLanding({
  events,
  redacted,
}: HistoryLandingProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cardRefs = useRef<(HTMLDivElement | null)[]>([]);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const [hasScrolled, setHasScrolled] = useState(false);
  const [activeOverlay, setActiveOverlay] = useState<{
    event: HistoricalEvent;
    sourceRect: DOMRect | null;
  } | null>(null);

  /* Merge events + classified into one timeline (classified at end) */
  const allItems = useMemo(() => {
    const sorted = [...events].sort((a, b) => a.dateSort - b.dateSort);
    return { events: sorted, redacted };
  }, [events, redacted]);

  const totalCards = allItems.events.length + allItems.redacted.length;

  /* ── Era groups for fast-travel + dividers ── */
  const eraGroups = useMemo(
    () => buildEraGroups(allItems.events),
    [allItems.events]
  );

  /* Determine active era from focused index */
  const activeEra = useMemo(() => {
    for (let i = eraGroups.length - 1; i >= 0; i--) {
      if (focusedIndex >= eraGroups[i].firstIndex) return eraGroups[i].id;
    }
    return eraGroups[0]?.id || "ancient";
  }, [focusedIndex, eraGroups]);

  /* Set of indices that are first-of-era (for dividers) */
  const firstOfEraIndices = useMemo(() => {
    const set = new Set<number>();
    for (const g of eraGroups) {
      if (g.firstIndex > 0) set.add(g.firstIndex);
    }
    return set;
  }, [eraGroups]);

  /* ── Track ref for progress bar ── */
  const trackRef = useRef<HTMLDivElement>(null);

  /* ── Scroll listener: update --tl-focus on every card + progress bar ── */
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let rafId: number;
    const updateFocus = () => {
      const containerRect = container.getBoundingClientRect();
      const centerX = containerRect.left + containerRect.width / 2;
      let closestIndex = 0;
      let closestDist = Infinity;

      cardRefs.current.forEach((cardEl, i) => {
        if (!cardEl) return;
        const cardRect = cardEl.getBoundingClientRect();
        const cardCenterX = cardRect.left + cardRect.width / 2;
        const dist = Math.abs(cardCenterX - centerX);
        const maxDist = containerRect.width * 0.8;
        const t = Math.min(dist / maxDist, 1);
        cardEl.style.setProperty("--tl-focus", (1 - t).toFixed(3));

        if (dist < closestDist) {
          closestDist = dist;
          closestIndex = i;
        }
      });

      setFocusedIndex(closestIndex);

      /* Update progress bar via CSS custom property */
      if (trackRef.current && totalCards > 1) {
        const pct = (closestIndex / (totalCards - 1)) * 100;
        trackRef.current.style.setProperty("--tl-progress", `${pct.toFixed(1)}%`);
      }
    };

    const onScroll = () => {
      if (!hasScrolled) setHasScrolled(true);
      cancelAnimationFrame(rafId);
      rafId = requestAnimationFrame(updateFocus);
    };

    container.addEventListener("scroll", onScroll, { passive: true });
    updateFocus(); // initial calculation
    return () => {
      container.removeEventListener("scroll", onScroll);
      cancelAnimationFrame(rafId);
    };
  }, [allItems.events, allItems.redacted, hasScrolled, totalCards]);

  /* ── Momentum wheel: vertical scroll → horizontal with friction decay ── */
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let velocity = 0;
    let rafId: number;
    let isAnimating = false;

    const applyMomentum = () => {
      if (Math.abs(velocity) < 0.5) {
        isAnimating = false;
        return;
      }
      container.scrollLeft += velocity;
      velocity *= 0.92; // friction decay
      rafId = requestAnimationFrame(applyMomentum);
    };

    const handleWheel = (e: WheelEvent) => {
      /* Only intercept vertical wheel (mice without horizontal scroll) */
      if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
        e.preventDefault();
        velocity += e.deltaY * 0.8; // accumulate
        if (!isAnimating) {
          isAnimating = true;
          rafId = requestAnimationFrame(applyMomentum);
        }
      }
    };

    container.addEventListener("wheel", handleWheel, { passive: false });
    return () => {
      container.removeEventListener("wheel", handleWheel);
      cancelAnimationFrame(rafId);
    };
  }, []);

  /* ── Smooth scroll to card by index ── */
  const scrollToCard = useCallback(
    (index: number) => {
      const el = cardRefs.current[index];
      if (el) {
        el.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
          inline: "center",
        });
      }
    },
    []
  );

  /* ── Keyboard: arrow keys, Home, End ── */
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowRight") {
        e.preventDefault();
        scrollToCard(Math.min(focusedIndex + 1, totalCards - 1));
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        scrollToCard(Math.max(focusedIndex - 1, 0));
      } else if (e.key === "Home") {
        e.preventDefault();
        scrollToCard(0);
      } else if (e.key === "End") {
        e.preventDefault();
        scrollToCard(totalCards - 1);
      }
    },
    [focusedIndex, totalCards, scrollToCard]
  );

  /* ── Open story overlay ── */
  const openStory = useCallback(
    (event: HistoricalEvent, cardIndex: number) => {
      const photoEl = cardRefs.current[cardIndex]?.querySelector<HTMLElement>(
        ".hist-tl-card__photo"
      );
      const rect = photoEl?.getBoundingClientRect() ?? null;
      setActiveOverlay({ event, sourceRect: rect });
    },
    []
  );

  /* ── Close overlay ── */
  const closeOverlay = useCallback(() => {
    setActiveOverlay(null);
  }, []);

  /* ── Navigate to event from within overlay (Item 2) ── */
  const handleNavigateToEvent = useCallback(
    (targetEvent: HistoricalEvent) => {
      const targetIdx = allItems.events.findIndex(
        (e) => e.slug === targetEvent.slug
      );
      if (targetIdx === -1) return;

      /* Get the photo rect of the target card for FLIP morph */
      const photoRect =
        cardRefs.current[targetIdx]
          ?.querySelector(".hist-tl-card__photo")
          ?.getBoundingClientRect() ?? null;

      /* Close current overlay, open new one */
      setActiveOverlay({ event: targetEvent, sourceRect: photoRect });

      /* Scroll to the target card so it is centered */
      scrollToCard(targetIdx);
    },
    [allItems.events, scrollToCard]
  );

  return (
    <div className="hist-tl-wrapper">
      {/* ── Mission Brief — fades on first scroll ── */}
      <div
        className={`hist-tl-brief ${hasScrolled ? "hist-tl-brief--hidden" : ""}`}
        aria-hidden={hasScrolled}
      >
        <p className="hist-tl-brief__text">
          One event. Every side. Decide for yourself.
        </p>
        <span className="hist-tl-brief__hint">&larr; scroll through time &rarr;</span>
      </div>

      {/* ── Horizontal timeline scroller ── */}
      {/* eslint-disable-next-line jsx-a11y/no-static-element-interactions */}
      <div
        ref={containerRef}
        className="hist-tl-landing hist-grade"
        role="region"
        aria-label="Historical events timeline"
        aria-roledescription="timeline"
        tabIndex={0}
        onKeyDown={handleKeyDown}
      >
        {/* ── Event cards with era dividers ── */}
        {allItems.events.map((event, i) => (
          <EraCardWrapper key={event.slug} isFirstOfEra={firstOfEraIndices.has(i)}>
            <TimelineCard
              ref={(el) => { cardRefs.current[i] = el; }}
              event={event}
              index={i}
              onOpen={openStory}
            />
          </EraCardWrapper>
        ))}

        {/* ── Classified cards ── */}
        {allItems.redacted.map((event, i) => {
          const idx = allItems.events.length + i;
          return (
            <ClassifiedCard
              key={event.slug}
              ref={(el) => { cardRefs.current[idx] = el; }}
              event={event}
              index={idx}
            />
          );
        })}
      </div>

      {/* ── Era fast-travel buttons (Item 5) ── */}
      <div className="hist-tl-eras" role="navigation" aria-label="Era navigation">
        {eraGroups.map((era) => (
          <button
            key={era.id}
            className={`hist-tl-era ${activeEra === era.id ? "hist-tl-era--active" : ""}`}
            onClick={() => scrollToCard(era.firstIndex)}
            type="button"
          >
            {era.label}
          </button>
        ))}
      </div>

      {/* ── Timeline track (minimap) with progress bar ── */}
      <nav className="hist-tl-track" aria-label="Timeline navigation" ref={trackRef}>
        <div className="hist-tl-track__line" aria-hidden="true" />

        {/* Era labels above the track */}
        {eraGroups.map((era) => {
          const midpoint =
            totalCards > 1
              ? ((era.firstIndex + era.lastIndex) / 2 / (totalCards - 1)) * 90 + 5
              : 50;
          return (
            <span
              key={era.id}
              className="hist-tl-track__era-label"
              style={{ left: `${midpoint}%` }}
              aria-hidden="true"
            >
              {era.label}
            </span>
          );
        })}

        {allItems.events.map((event, i) => {
          /* Show year label on every 3rd dot + always on active */
          const showYear = i % 3 === 0;
          return (
            <button
              key={event.slug}
              className={`hist-tl-track__dot ${
                i === focusedIndex ? "hist-tl-track__dot--active" : ""
              } ${showYear ? "hist-tl-track__dot--labeled" : ""}`}
              style={{
                left: `${5 + (totalCards > 1 ? (i / (totalCards - 1)) * 90 : 45)}%`,
              }}
              onClick={() => scrollToCard(i)}
              aria-label={`${event.title} (${event.datePrimary})`}
              type="button"
            >
              <span className="hist-tl-track__year">
                {extractYear(event.dateSort, event.datePrimary)}
              </span>
            </button>
          );
        })}
        {allItems.redacted.map((event, i) => {
          const idx = allItems.events.length + i;
          return (
            <button
              key={event.slug}
              className={`hist-tl-track__dot hist-tl-track__dot--classified ${
                idx === focusedIndex ? "hist-tl-track__dot--active" : ""
              }`}
              style={{
                left: `${5 + (totalCards > 1 ? (idx / (totalCards - 1)) * 90 : 45)}%`,
              }}
              onClick={() => scrollToCard(idx)}
              aria-label={`Coming: ${event.title}`}
              type="button"
            >
              <span className="hist-tl-track__year">?</span>
            </button>
          );
        })}
      </nav>

      {/* ── Story Overlay ── */}
      {activeOverlay && (
        <HistoryOverlay
          event={activeOverlay.event}
          allEvents={allItems.events}
          sourceRect={activeOverlay.sourceRect}
          onClose={closeOverlay}
          onNavigateToEvent={handleNavigateToEvent}
        />
      )}
    </div>
  );
}

/* ===========================================================================
   EraCardWrapper — Inserts era divider before first card of a new era
   =========================================================================== */
function EraCardWrapper({
  isFirstOfEra,
  children,
}: {
  isFirstOfEra: boolean;
  children: React.ReactNode;
}) {
  if (!isFirstOfEra) return <>{children}</>;
  return (
    <>
      <div className="hist-tl-era-divider" aria-hidden="true" />
      {children}
    </>
  );
}

/* ===========================================================================
   TimelineCard — A single event in the horizontal timeline
   Rack focus driven by --tl-focus. Photo + date + title always visible.
   Hook, dots, CTA revealed when focused (--tl-focus > 0.65).
   =========================================================================== */

const TimelineCard = forwardRef<
  HTMLDivElement,
  {
    event: HistoricalEvent;
    index: number;
    onOpen: (event: HistoricalEvent, cardIndex: number) => void;
  }
>(function TimelineCard({ event, index, onOpen }, ref) {
  const hook =
    HOOKS[event.slug] ||
    event.contextNarrative.split(". ").slice(0, 2).join(". ") + ".";

  const cta =
    CTAS[event.slug] ||
    `Explore ${event.perspectives.length} accounts of ${event.title}`;

  const handleClick = useCallback(() => {
    onOpen(event, index);
  }, [event, index, onOpen]);

  const severityClass = SEVERITY_CLASS[event.severity] || "";

  return (
    <article
      ref={ref}
      className={`hist-tl-card ${severityClass}`}
      style={{ "--tl-focus": "0.5" } as React.CSSProperties}
      data-slug={event.slug}
    >
      {/* Photo -- always visible, Ken Burns when focused */}
      <div className="hist-tl-card__photo">
        <PosterImage event={event} eager={index === 0} />
      </div>

      {/* Body content */}
      <div className="hist-tl-card__body">
        {/* Always visible: date + title */}
        <span className="hist-tl-card__date">{event.datePrimary}</span>
        <h3 className="hist-tl-card__title">{event.title}</h3>

        {/* Revealed when focused */}
        <blockquote className="hist-tl-card__hook">{hook}</blockquote>

        <div
          className="hist-tl-card__dots"
          aria-label={`${event.perspectives.length} perspectives`}
        >
          {event.perspectives.map((p) => (
            <span
              key={p.id}
              className="hist-tl-card__dot"
              style={{
                background: PERSP_COLORS[p.color] || PERSP_COLORS.a,
              }}
              title={p.viewpointName}
              aria-hidden="true"
            />
          ))}
        </div>

        <button
          className="hist-tl-card__cta"
          onClick={handleClick}
          type="button"
        >
          <span className="hist-tl-card__cta-text">{cta}</span>
          <span className="hist-tl-card__cta-arrow" aria-hidden="true">
            &rarr;
          </span>
        </button>
      </div>

      {/* Severity accent */}
      <div className="hist-tl-card__severity" aria-hidden="true" />
    </article>
  );
});

/* ===========================================================================
   ClassifiedCard — Desaturated, redacted text, click-to-flip
   Same --tl-focus system, plus dashed border + desaturation
   =========================================================================== */
const ClassifiedCard = forwardRef<
  HTMLDivElement,
  {
    event: RedactedEvent;
    index: number;
  }
>(function ClassifiedCard({ event, index }, ref) {
  const [revealed, setRevealed] = useState(false);

  return (
    <div
      ref={ref}
      className={`hist-tl-card hist-tl-card--classified ${
        revealed ? "hist-tl-card--classified-revealed" : ""
      }`}
      style={{ "--tl-focus": "0.5" } as React.CSSProperties}
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
      data-index={index}
    >
      <div className="hist-tl-card__body">
        {/* Redacted title */}
        <h3 className="hist-tl-card__title">
          {event.title.split(" ")[0]}{" "}
          <span className="hist-tl-card--classified__redacted">
            {event.title
              .split(" ")
              .slice(1)
              .map((w) => "\u2588".repeat(w.length))
              .join(" ")}
          </span>
        </h3>

        {/* Contradictory quotes */}
        {event.quoteA && (
          <p className="hist-tl-card--classified__quote">{event.quoteA}</p>
        )}
        {event.quoteB && (
          <p className="hist-tl-card--classified__quote hist-tl-card--classified__quote-b">
            {event.quoteB}
          </p>
        )}

        {/* Date hint + badge */}
        <div className="hist-tl-card--classified__meta">
          <span className="hist-tl-card--classified__date">
            {event.dateHint}
          </span>
          <span className="hist-tl-card--classified__badge">COMING</span>
        </div>
      </div>

      {/* Reveal overlay */}
      <div
        className="hist-tl-card--classified__reveal"
        aria-hidden={!revealed}
      >
        <span className="hist-tl-card--classified__reveal-title">
          {event.title}
        </span>
        <span className="hist-tl-card--classified__reveal-hint">
          Coming soon
        </span>
      </div>
    </div>
  );
});
