"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import type { HistoricalEvent, RedactedEvent, HistoryEra } from "../types";
import { ERAS } from "../types";
import { HOOKS, CTAS } from "../hooks";
import EventDetail from "./EventDetail";

/* ===========================================================================
   HistoryLanding — Organic Ink Timeline
   Horizontal scroll through time with above/below card layout.
   Organic SVG ink track at vertical center. Cards alternate above
   (catastrophic) and below (critical/major) the track. Proportionate
   temporal spacing (sqrt scale). Inline story loading replaces overlay.

   Two states:
     A — Full Timeline (default): horizontal scroll, above/below cards,
         fixed era header, fun facts, cinematic entrance, snap-assist
     B — Story Active: floating "Back to Timeline" CTA + EventDetail inline

   Desktop: horizontal scroll, edge-scroll zones, parallax, Ken Burns
   Mobile (<768px): vertical timeline, ink track on left, tap to open

   Cardinal rules: Show Not Tell. Arrive Late, Leave Early.
   =========================================================================== */

/* ── Era context — rich descriptions for the fixed era header ── */
const ERA_CONTEXT: Record<string, { label: string; years: string; description: string; color: string }> = {
  ancient: {
    label: "The Ancient World",
    years: "3000 BCE — 500 BCE",
    description: "First civilizations, written law, and organized warfare",
    color: "var(--hist-persp-c)",
  },
  classical: {
    label: "The Classical Age",
    years: "500 BCE — 500 CE",
    description: "Empires rose and fell. Democracy was invented. So was crucifixion.",
    color: "var(--hist-persp-a)",
  },
  medieval: {
    label: "The Medieval World",
    years: "500 — 1500",
    description: "Crusades, plagues, and the Mongol storm. Europe called them the Dark Ages. The rest of the world didn\u2019t.",
    color: "var(--hist-persp-d)",
  },
  "early-modern": {
    label: "The Early Modern Period",
    years: "1500 — 1800",
    description: "Colonialism begins. Millions enslaved. Revolutions brew.",
    color: "var(--hist-persp-b)",
  },
  modern: {
    label: "The Modern Era",
    years: "1800 — 1945",
    description: "Industry, nationalism, two world wars, and the atom split open",
    color: "var(--hist-accent)",
  },
  contemporary: {
    label: "The Contemporary World",
    years: "1945 — Present",
    description: "Decolonization, cold war, genocide, and the unfinished project of human rights",
    color: "var(--hist-brass)",
  },
};

/* ── Fun facts — ephemeral context between events ── */
const FUN_FACTS: { yearStart: number; yearEnd: number; text: string }[] = [
  { yearStart: 500, yearEnd: 1095, text: "While Europe slept through the \u2018Dark Ages\u2019, the Islamic Golden Age produced algebra, optics, and hospitals." },
  { yearStart: 1095, yearEnd: 1258, text: "The Crusades lasted 200 years. Both sides claimed God was on theirs." },
  { yearStart: 1500, yearEnd: 1789, text: "Between 1500 and 1800, European empires moved 12.5 million Africans across the Atlantic in chains." },
  { yearStart: 1789, yearEnd: 1839, text: "Napoleon sold Louisiana for $15 million. Today that\u2019s about 4 cents per acre." },
  { yearStart: 1839, yearEnd: 1884, text: "In 50 years, the telegraph, photograph, telephone, and light bulb were all invented. The world shrank." },
  { yearStart: 1884, yearEnd: 1945, text: "In 1884, Europe carved up Africa at a conference. Not a single African was invited." },
  { yearStart: 1945, yearEnd: 1947, text: "Between VJ Day and Indian independence: 712 days. Two empires ended." },
  { yearStart: 1948, yearEnd: 1989, text: "For 41 years, the world was divided by an idea: which economic system would survive." },
  { yearStart: 1989, yearEnd: 1994, text: "The Berlin Wall fell on a Thursday. Nobody planned it. A spokesman misread his notes at a press conference." },
];

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

/* ── Severity -> side mapping: catastrophic = above, others = below ── */
function getCardSide(event: HistoricalEvent): "above" | "below" {
  if (event.severity === "catastrophic") return "above";
  return "below";
}

/* ── Extract year from YYYYMMDD dateSort ── */
function extractYear(dateSort: number, datePrimary: string): string {
  const abs = Math.abs(dateSort);
  const s = String(abs);
  if (s.length >= 4) {
    const y = s.slice(0, s.length >= 8 ? 4 : s.length);
    return dateSort < 0 ? `${y} BCE` : y;
  }
  const match = datePrimary.match(/\d{4}/);
  return match ? match[0] : "";
}

/* ── Extract numeric year for positioning ── */
function extractNumericYear(dateSort: number): number {
  const abs = Math.abs(dateSort);
  if (abs > 10000) return dateSort < 0 ? -Math.floor(abs / 10000) : Math.floor(abs / 10000);
  return dateSort;
}

/* ── Proportionate spacing with sqrt scale ── */
function computePositions(events: HistoricalEvent[]): number[] {
  if (events.length === 0) return [];
  if (events.length === 1) return [0.5];

  const years = events.map((e) => extractNumericYear(e.dateSort));
  const minYear = Math.min(...years);
  const maxYear = Math.max(...years);
  const range = maxYear - minYear;

  if (range === 0) return events.map(() => 0.5);

  return years.map((year) => {
    const normalized = year - minYear;
    const position = Math.sqrt(Math.max(0, normalized)) / Math.sqrt(range);
    return 0.05 + position * 0.9;
  });
}

/* ── Resolve collisions: ensure minimum spacing between adjacent cards ── */
function resolveCollisions(
  positions: number[],
  events: HistoricalEvent[],
  totalWidth: number
): { positions: number[]; sides: ("above" | "below")[] } {
  const MIN_GAP_PX = 200;
  const minGapNorm = totalWidth > 0 ? MIN_GAP_PX / totalWidth : 0.08;
  const resolved = [...positions];
  const sides = events.map((e) => getCardSide(e));

  const aboveIndices = events.map((_, i) => i).filter((i) => sides[i] === "above");
  const belowIndices = events.map((_, i) => i).filter((i) => sides[i] === "below");

  for (const group of [aboveIndices, belowIndices]) {
    for (let pass = 0; pass < 5; pass++) {
      let changed = false;
      for (let gi = 1; gi < group.length; gi++) {
        const i = group[gi];
        const prev = group[gi - 1];
        const gap = resolved[i] - resolved[prev];
        if (gap < minGapNorm) {
          resolved[i] = resolved[prev] + minGapNorm;
          changed = true;
        }
      }
      if (!changed) break;
    }
  }

  // Flip side on same-position collisions between above and below
  for (let i = 0; i < resolved.length; i++) {
    for (let j = i + 1; j < resolved.length; j++) {
      if (Math.abs(resolved[i] - resolved[j]) < minGapNorm * 0.5) {
        if (sides[i] === sides[j]) {
          sides[j] = sides[j] === "above" ? "below" : "above";
        }
      }
    }
  }

  return { positions: resolved, sides };
}

/* ── Generate organic ink SVG path ── */
function generateInkPath(width: number): string {
  const segments = Math.max(20, Math.floor(width / 50));
  const step = width / segments;
  let d = `M0,2`;
  for (let i = 1; i <= segments; i++) {
    const x = i * step;
    const wobble = Math.sin(i * 1.7) * 1.2 + Math.cos(i * 2.3) * 0.8;
    d += ` S${(x - step * 0.3).toFixed(1)},${(2 + wobble).toFixed(2)} ${x.toFixed(1)},${(2 - wobble * 0.5).toFixed(2)}`;
  }
  return d;
}

/* ===========================================================================
   PosterImage — Robust fallback chain
   heroImage -> media[0].url -> ... -> cinematic gradient
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

  const indexRef = useRef(0);
  const imgRef = useRef<HTMLImageElement>(null);
  const [allFailed, setAllFailed] = useState(fallbackUrls.length === 0);

  const handleError = useCallback(() => {
    const nextIdx = indexRef.current + 1;
    if (nextIdx < fallbackUrls.length) {
      indexRef.current = nextIdx;
      if (imgRef.current) {
        imgRef.current.src = fallbackUrls[nextIdx];
      }
    } else {
      setAllFailed(true);
    }
  }, [fallbackUrls]);

  if (allFailed) {
    return <div className="hist-tl-card__photo-fallback" aria-hidden="true" />;
  }

  return (
    <img
      ref={imgRef}
      src={fallbackUrls[0]}
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
  const timelineRef = useRef<HTMLDivElement>(null);
  const bgLayerRef = useRef<HTMLDivElement>(null);
  const inkPathRef = useRef<SVGPathElement>(null);
  const scrollVelocityRef = useRef(0);
  const [hasScrolled, setHasScrolled] = useState(false);
  const [activeEvent, setActiveEvent] = useState<HistoricalEvent | null>(null);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const [prevEra, setPrevEra] = useState<string | null>(null);
  const [eraFlashColor, setEraFlashColor] = useState<string | null>(null);
  const [entranceReady, setEntranceReady] = useState(false);
  const activeEventIndexRef = useRef<number>(0);

  /* Sort events chronologically */
  const sortedEvents = useMemo(
    () => [...events].sort((a, b) => a.dateSort - b.dateSort),
    [events]
  );

  /* ── Era groups ── */
  const eraGroups = useMemo(
    () => buildEraGroups(sortedEvents),
    [sortedEvents]
  );

  /* ── Compute total width & positions ── */
  const totalWidthVw = useMemo(
    () => Math.max(100, sortedEvents.length * 280),
    [sortedEvents.length]
  );

  const rawPositions = useMemo(
    () => computePositions(sortedEvents),
    [sortedEvents]
  );

  const { positions, sides } = useMemo(
    () => resolveCollisions(rawPositions, sortedEvents, totalWidthVw),
    [rawPositions, sortedEvents, totalWidthVw]
  );

  /* ── Ink path ── */
  const inkPath = useMemo(
    () => generateInkPath(totalWidthVw),
    [totalWidthVw]
  );

  /* ── Reduced motion ── */
  const [reducedMotion, setReducedMotion] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  /* ── Entrance animation trigger ── */
  useEffect(() => {
    if (reducedMotion) {
      setEntranceReady(true);
      return;
    }
    const timer = setTimeout(() => setEntranceReady(true), 100);
    return () => clearTimeout(timer);
  }, [reducedMotion]);

  /* ── Ink track draw-on: measure path length ── */
  useEffect(() => {
    if (reducedMotion) return;
    const path = inkPathRef.current;
    if (!path) return;
    try {
      const len = path.getTotalLength();
      path.style.setProperty("--track-length", String(len));
    } catch {
      /* SVG path measurement unavailable */
    }
  }, [inkPath, reducedMotion]);

  /* ── Focused index tracking — find nearest card to viewport center ── */
  useEffect(() => {
    if (activeEvent) return;
    const container = timelineRef.current;
    if (!container) return;

    const updateFocusedIndex = () => {
      const scrollCenter = container.scrollLeft + container.clientWidth / 3; /* Rule of Thirds: left third */
      const totalW = container.scrollWidth;
      let closest = 0;
      let closestDist = Infinity;
      for (let i = 0; i < positions.length; i++) {
        const cardX = positions[i] * totalW;
        const dist = Math.abs(cardX - scrollCenter);
        if (dist < closestDist) {
          closestDist = dist;
          closest = i;
        }
      }
      setFocusedIndex(closest);
    };

    container.addEventListener("scroll", updateFocusedIndex, { passive: true });
    updateFocusedIndex();
    return () => container.removeEventListener("scroll", updateFocusedIndex);
  }, [activeEvent, positions]);

  /* ── Era transition flash ── */
  const currentEra = sortedEvents[focusedIndex]?.era || "ancient";
  useEffect(() => {
    if (reducedMotion || !hasScrolled) return;
    if (prevEra && prevEra !== currentEra) {
      const ctx = ERA_CONTEXT[currentEra];
      if (ctx) {
        setEraFlashColor(ctx.color);
        const timer = setTimeout(() => setEraFlashColor(null), 600);
        return () => clearTimeout(timer);
      }
    }
    setPrevEra(currentEra);
  }, [currentEra, prevEra, reducedMotion, hasScrolled]);

  /* ── Decade label for post-1800 events ── */
  const decadeLabel = useMemo(() => {
    const ev = sortedEvents[focusedIndex];
    if (!ev) return null;
    const year = extractNumericYear(ev.dateSort);
    if (year >= 1800) {
      const decade = Math.floor(year / 10) * 10;
      return `${decade}s`;
    }
    return null;
  }, [sortedEvents, focusedIndex]);

  /* ── Fun facts: compute positions and match to scroll ── */
  const funFactPositions = useMemo(() => {
    if (sortedEvents.length === 0) return [];
    const years = sortedEvents.map((e) => extractNumericYear(e.dateSort));
    const minYear = Math.min(...years);
    const maxYear = Math.max(...years);
    const range = maxYear - minYear;
    if (range === 0) return [];

    return FUN_FACTS.map((fact) => {
      const midYear = (fact.yearStart + fact.yearEnd) / 2;
      if (midYear < minYear || midYear > maxYear) return null;
      const normalized = midYear - minYear;
      const position = Math.sqrt(Math.max(0, normalized)) / Math.sqrt(range);
      return { ...fact, position: 0.05 + position * 0.9 };
    }).filter(Boolean) as (typeof FUN_FACTS[0] & { position: number })[];
  }, [sortedEvents]);

  /* ── Parallax scroll handler — enhanced differential (bg 0.3x = 0.7x relative) ── */
  useEffect(() => {
    if (reducedMotion || activeEvent) return;
    const container = timelineRef.current;
    const bg = bgLayerRef.current;
    if (!container || !bg) return;

    const handleScroll = () => {
      const scrollLeft = container.scrollLeft;
      bg.style.transform = `translateX(${-scrollLeft * 0.30}px)`;
      /* Note: cards scroll at native 1x. Background at 0.7x effective (0.30 offset).
         The 0.3x differential is sufficient for depth perception. Adding 1.05x to cards
         would fight with their absolute positioning + Dutch angle transforms. */
      if (!hasScrolled) setHasScrolled(true);
    };

    container.addEventListener("scroll", handleScroll, { passive: true });
    return () => container.removeEventListener("scroll", handleScroll);
  }, [reducedMotion, activeEvent, hasScrolled]);

  /* ── Momentum wheel: vertical scroll -> horizontal, snappier physics ── */
  useEffect(() => {
    if (activeEvent) return;
    const container = timelineRef.current;
    if (!container) return;

    let velocity = 0;
    let rafId: number;
    let isAnimating = false;

    const applyMomentum = () => {
      if (Math.abs(velocity) < 0.5) {
        isAnimating = false;
        /* Snap assist: settle on nearest card */
        const scrollCenter = container.scrollLeft + container.clientWidth / 3;
        const totalW = container.scrollWidth;
        let closest = 0;
        let closestDist = Infinity;
        for (let i = 0; i < positions.length; i++) {
          const cardX = positions[i] * totalW;
          const dist = Math.abs(cardX - scrollCenter);
          if (dist < closestDist) {
            closestDist = dist;
            closest = i;
          }
        }
        const targetLeft = positions[closest] * totalW - container.clientWidth / 3;
        const currentLeft = container.scrollLeft;
        if (Math.abs(targetLeft - currentLeft) > 5 && Math.abs(targetLeft - currentLeft) < 400) {
          container.scrollTo({ left: targetLeft, behavior: "smooth" });
        }
        return;
      }
      container.scrollLeft += velocity;
      velocity *= 0.88;
      rafId = requestAnimationFrame(applyMomentum);
    };

    const handleWheel = (e: WheelEvent) => {
      if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
        e.preventDefault();
        velocity += e.deltaY * 1.2;
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
  }, [activeEvent, positions]);

  /* ── Edge scroll: mouse near left/right edge triggers auto-scroll (desktop) ── */
  useEffect(() => {
    if (activeEvent || reducedMotion) return;
    const container = timelineRef.current;
    if (!container) return;

    /* Only on desktop (pointer: fine) */
    const isTouch = window.matchMedia("(pointer: coarse)").matches;
    if (isTouch) return;

    const EDGE_ZONE = 60;
    const MAX_SPEED = 12;

    const handleMouseMove = (e: MouseEvent) => {
      if (e.clientX < EDGE_ZONE) {
        const intensity = 1 - e.clientX / EDGE_ZONE;
        scrollVelocityRef.current = -MAX_SPEED * intensity;
      } else if (e.clientX > window.innerWidth - EDGE_ZONE) {
        const intensity = 1 - (window.innerWidth - e.clientX) / EDGE_ZONE;
        scrollVelocityRef.current = MAX_SPEED * intensity;
      } else {
        scrollVelocityRef.current = 0;
      }
    };

    const handleMouseLeave = () => {
      scrollVelocityRef.current = 0;
    };

    let rafId: number;
    const tick = () => {
      if (scrollVelocityRef.current !== 0 && container) {
        container.scrollLeft += scrollVelocityRef.current;
      }
      rafId = requestAnimationFrame(tick);
    };
    rafId = requestAnimationFrame(tick);

    window.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseleave", handleMouseLeave);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseleave", handleMouseLeave);
      cancelAnimationFrame(rafId);
      scrollVelocityRef.current = 0;
    };
  }, [activeEvent, reducedMotion]);

  /* ── Auto-scroll to 1945 on initial load ── */
  useEffect(() => {
    if (activeEvent) return;
    const container = timelineRef.current;
    if (!container || sortedEvents.length === 0) return;

    /* Find card closest to 1945 */
    let closest = 0;
    let closestDist = Infinity;
    for (let i = 0; i < sortedEvents.length; i++) {
      const year = extractNumericYear(sortedEvents[i].dateSort);
      const dist = Math.abs(year - 1945);
      if (dist < closestDist) {
        closestDist = dist;
        closest = i;
      }
    }

    /* Instant scroll — user lands at 1945, doesn't watch scroll */
    const totalW = container.scrollWidth;
    const targetLeft = positions[closest] * totalW - container.clientWidth / 3;
    container.scrollTo({ left: Math.max(0, targetLeft), behavior: "instant" as ScrollBehavior });
    setFocusedIndex(closest);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortedEvents.length]); /* Run once after events load */

  /* ── URL management ── */
  const openStory = useCallback((event: HistoricalEvent) => {
    /* Remember which card index was opened */
    const idx = sortedEvents.findIndex((e) => e.slug === event.slug);
    if (idx !== -1) activeEventIndexRef.current = idx;
    setActiveEvent(event);
    window.history.pushState(
      { historyInline: true, slug: event.slug },
      "",
      `/history/${event.slug}`
    );
  }, [sortedEvents]);

  const closeStory = useCallback(() => {
    setActiveEvent(null);
    window.history.pushState({}, "", "/history");
    /* Scroll timeline back to the card the user was viewing */
    requestAnimationFrame(() => {
      const container = timelineRef.current;
      if (!container) return;
      const idx = activeEventIndexRef.current;
      const totalW = container.scrollWidth;
      const targetLeft = positions[idx] * totalW - container.clientWidth / 3;
      container.scrollTo({ left: Math.max(0, targetLeft), behavior: "instant" as ScrollBehavior });
    });
  }, [positions]);

  /* popstate listener for browser back */
  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname;
      if (path === "/history" || path === "/history/") {
        setActiveEvent(null);
      } else {
        const slug = path.replace("/history/", "");
        const found = sortedEvents.find((e) => e.slug === slug);
        if (found) {
          setActiveEvent(found);
        } else {
          setActiveEvent(null);
        }
      }
    };

    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, [sortedEvents]);

  /* ── Navigate between events (from EventDetail Stage 6) ── */
  const navigateToEvent = useCallback(
    (event: HistoricalEvent) => {
      setActiveEvent(event);
      window.history.pushState(
        { historyInline: true, slug: event.slug },
        "",
        `/history/${event.slug}`
      );
      /* Scroll to top of inline story */
      window.scrollTo({ top: 0, behavior: "smooth" });
    },
    []
  );

  /* ── State B: Story active — floating Back CTA + inline story ── */
  if (activeEvent) {
    return (
      <div className="hist-tl-wrapper hist-tl-wrapper--story-active">
        {/* Floating Back to Timeline CTA — slides in after 1s */}
        <BackToTimelineCTA onClose={closeStory} />

        {/* Inline story — swipe gestures for mobile next/prev */}
        <StoryContainer
          event={activeEvent}
          allEvents={sortedEvents}
          onNavigateToEvent={navigateToEvent}
          onClose={closeStory}
        />
      </div>
    );
  }

  /* ── Current era context for header ── */
  const eraCtx = ERA_CONTEXT[currentEra] || ERA_CONTEXT.contemporary;

  /* ── State A: Full timeline ── */
  return (
    <div className="hist-tl-wrapper">
      {/* Fixed Era Header — updates as user scrolls */}
      <div
        className={`hist-tl-era-header ${hasScrolled ? "" : "hist-tl-era-header--hidden"}`}
        aria-live="polite"
        aria-atomic="true"
        style={{ "--era-color": eraCtx.color } as React.CSSProperties}
      >
        <div className="hist-tl-era-header__label">{eraCtx.label}</div>
        <div className="hist-tl-era-header__meta">
          <span className="hist-tl-era-header__years">{eraCtx.years}</span>
          {decadeLabel && (
            <span className="hist-tl-era-header__decade">{decadeLabel}</span>
          )}
        </div>
        <div className="hist-tl-era-header__desc">{eraCtx.description}</div>
      </div>

      {/* Mission Brief -- fades on first scroll */}
      <div
        className={`hist-tl-brief ${hasScrolled ? "hist-tl-brief--hidden" : ""}`}
        aria-hidden={hasScrolled}
      >
        <p className="hist-tl-brief__text">
          One event. Every side. Decide for yourself.
        </p>
        <span className="hist-tl-brief__hint">&larr; scroll through time &rarr;</span>
      </div>

      {/* Full timeline -- horizontal scroll */}
      {/* eslint-disable-next-line jsx-a11y/no-static-element-interactions */}
      <div
        ref={timelineRef}
        className={`hist-tl-full hist-grade${eraFlashColor ? " hist-tl-full--era-flash" : ""}`}
        role="region"
        aria-label="Historical events timeline"
        aria-roledescription="timeline"
        tabIndex={0}
        style={eraFlashColor ? { "--era-flash-color": `color-mix(in srgb, ${eraFlashColor} 8%, transparent)` } as React.CSSProperties : undefined}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") {
            e.preventDefault();
            timelineRef.current?.scrollBy({ left: 300, behavior: "smooth" });
          } else if (e.key === "ArrowLeft") {
            e.preventDefault();
            timelineRef.current?.scrollBy({ left: -300, behavior: "smooth" });
          }
        }}
      >
        {/* Parallax background layer: era gradient bands */}
        <div
          ref={bgLayerRef}
          className="hist-tl-full__bg-layer"
          aria-hidden="true"
          style={{ width: `${totalWidthVw}px` }}
        >
          {eraGroups.map((era) => {
            const startPct = sortedEvents.length > 1
              ? (positions[era.firstIndex] || 0) * 100
              : 0;
            const endPct = sortedEvents.length > 1
              ? (positions[era.lastIndex] || 1) * 100
              : 100;
            return (
              <div
                key={era.id}
                className={`hist-tl-full__era-band hist-tl-full__era-band--${era.id}`}
                style={{
                  left: `${startPct}%`,
                  width: `${Math.max(endPct - startPct, 5)}%`,
                }}
              >
                <span className="hist-tl-full__era-label">{era.label}</span>
              </div>
            );
          })}
        </div>

        {/* Inner container with total width for absolute positioning */}
        <div
          className="hist-tl-full__inner"
          style={{ width: `${totalWidthVw}px`, minWidth: `${totalWidthVw}px` }}
        >
          {/* Organic SVG ink track at vertical center — draw-on animation */}
          <svg
            className={`hist-tl-full__track${entranceReady && !reducedMotion ? " hist-tl-full__track--draw" : ""}`}
            viewBox={`0 0 ${totalWidthVw} 4`}
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <path
              ref={inkPathRef}
              className="hist-tl-full__ink-path"
              d={inkPath}
              stroke="var(--hist-accent)"
              strokeWidth="1.5"
              fill="none"
              opacity="0.6"
            />
          </svg>

          {/* Fun facts — positioned at midpoints between events */}
          {funFactPositions.map((fact, fi) => (
            <FunFact
              key={fi}
              text={fact.text}
              position={fact.position}
              totalWidth={totalWidthVw}
              containerRef={timelineRef}
            />
          ))}

          {/* Cards + stems + dots */}
          {sortedEvents.map((event, i) => {
            const side = sides[i];
            const pct = positions[i] * 100;
            const isFocused = i === focusedIndex;

            return (
              <div
                key={event.slug}
                className="hist-tl-full__station"
                style={{ left: `${pct}%` }}
              >
                {/* Dot on track */}
                <div
                  className={`hist-tl-full__dot hist-tl-full__dot--${event.severity}${isFocused ? " hist-tl-full__dot--focused" : ""}`}
                  aria-hidden="true"
                />

                {/* Stem connecting card to dot — spring stretch on hover via CSS var */}
                <div
                  className={`hist-tl-full__stem hist-tl-full__stem--${side}`}
                  aria-hidden="true"
                >
                  <svg width="2" height="28" viewBox="0 0 2 28">
                    <path
                      d="M1,0 C1,8 0.5,14 1,20 S1.5,26 1,28"
                      stroke="var(--hist-brass)"
                      strokeWidth="1"
                      fill="none"
                      opacity="0.4"
                    />
                  </svg>
                </div>

                {/* Card — entrance stagger via --card-index */}
                <TimelineCard
                  event={event}
                  index={i}
                  side={side}
                  onOpen={openStory}
                  entranceReady={entranceReady}
                  reducedMotion={reducedMotion}
                />
              </div>
            );
          })}
        </div>
      </div>

      {/* Era fast-travel buttons */}
      <div className="hist-tl-eras" role="navigation" aria-label="Era navigation">
        {eraGroups.map((era) => (
          <button
            key={era.id}
            className="hist-tl-era"
            onClick={() => {
              const container = timelineRef.current;
              if (!container) return;
              const targetPct = positions[era.firstIndex] || 0;
              const totalW = container.scrollWidth;
              container.scrollTo({
                left: targetPct * totalW - container.clientWidth / 3,
                behavior: "smooth",
              });
            }}
            type="button"
          >
            {era.label}
          </button>
        ))}
      </div>

      {/* Bottom minimap track */}
      <nav className="hist-tl-minimap" aria-label="Timeline minimap">
        <div className="hist-tl-minimap__line" aria-hidden="true" />
        {sortedEvents.map((event, i) => {
          const isFocused = i === focusedIndex;
          const year = extractYear(event.dateSort, event.datePrimary);
          const showYear = i % 4 === 0;
          return (
            <button
              key={event.slug}
              className={`hist-tl-minimap__dot${showYear ? " hist-tl-minimap__dot--labeled" : ""}${isFocused ? " hist-tl-minimap__dot--active" : ""}`}
              style={{ left: `${5 + positions[i] * 90}%` }}
              onClick={() => {
                const container = timelineRef.current;
                if (!container) return;
                const totalW = container.scrollWidth;
                container.scrollTo({
                  left: positions[i] * totalW - container.clientWidth / 3,
                  behavior: "smooth",
                });
              }}
              aria-label={`${event.title} (${event.datePrimary})`}
              type="button"
            >
              {showYear && (
                <span className="hist-tl-minimap__year">{year}</span>
              )}
            </button>
          );
        })}
      </nav>
    </div>
  );
}

/* ===========================================================================
   StoryContainer — Wraps EventDetail with swipe gesture support
   Mobile: swipe left = next event, swipe right = previous
   =========================================================================== */
function StoryContainer({
  event,
  allEvents,
  onNavigateToEvent,
  onClose,
}: {
  event: HistoricalEvent;
  allEvents: HistoricalEvent[];
  onNavigateToEvent: (event: HistoricalEvent) => void;
  onClose: () => void;
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const touchStartRef = useRef<{ x: number; y: number } | null>(null);

  /* Swipe detection for mobile next/prev navigation */
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const isTouch = window.matchMedia("(pointer: coarse)").matches;
    if (!isTouch) return;

    const SWIPE_THRESHOLD = 80;
    const SWIPE_VERTICAL_LIMIT = 50;

    const handleTouchStart = (e: TouchEvent) => {
      const touch = e.touches[0];
      touchStartRef.current = { x: touch.clientX, y: touch.clientY };
    };

    const handleTouchEnd = (e: TouchEvent) => {
      if (!touchStartRef.current) return;
      const touch = e.changedTouches[0];
      const dx = touch.clientX - touchStartRef.current.x;
      const dy = Math.abs(touch.clientY - touchStartRef.current.y);
      touchStartRef.current = null;

      /* Only count horizontal swipes */
      if (Math.abs(dx) < SWIPE_THRESHOLD || dy > SWIPE_VERTICAL_LIMIT) return;

      const sorted = allEvents;
      const idx = sorted.findIndex((ev) => ev.slug === event.slug);

      if (dx < 0 && idx < sorted.length - 1) {
        /* Swipe left = next event */
        onNavigateToEvent(sorted[idx + 1]);
      } else if (dx > 0 && idx > 0) {
        /* Swipe right = prev event */
        onNavigateToEvent(sorted[idx - 1]);
      }
    };

    el.addEventListener("touchstart", handleTouchStart, { passive: true });
    el.addEventListener("touchend", handleTouchEnd, { passive: true });
    return () => {
      el.removeEventListener("touchstart", handleTouchStart);
      el.removeEventListener("touchend", handleTouchEnd);
    };
  }, [event, allEvents, onNavigateToEvent]);

  return (
    <div ref={containerRef} className="hist-inline-story">
      <EventDetail
        event={event}
        allEvents={allEvents}
        onNavigateToEvent={onNavigateToEvent}
        onClose={onClose}
      />
    </div>
  );
}

/* ===========================================================================
   BackToTimelineCTA — Floating pill button on story page
   Slides in from right after 1s delay. Keyboard accessible.
   =========================================================================== */
function BackToTimelineCTA({ onClose }: { onClose: () => void }) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setVisible(true), 1000);
    return () => clearTimeout(timer);
  }, []);

  /* Also close on Escape key */
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

  return (
    <button
      className={`hist-back-to-timeline${visible ? " hist-back-to-timeline--visible" : ""}`}
      onClick={onClose}
      aria-label="Back to timeline"
      type="button"
    >
      <svg
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2.5"
        strokeLinecap="round"
        aria-hidden="true"
      >
        <path d="M19 12H5" />
        <path d="M12 19l-7-7 7-7" />
      </svg>
      <span>Timeline</span>
    </button>
  );
}

/* ===========================================================================
   FunFact — Ephemeral contextual fact positioned on the timeline track
   Fades in when near the viewport center, fades out when scrolled past.
   =========================================================================== */
function FunFact({
  text,
  position,
  totalWidth,
  containerRef,
}: {
  text: string;
  position: number;
  totalWidth: number;
  containerRef: React.RefObject<HTMLDivElement | null>;
}) {
  const factRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const el = factRef.current;
    const container = containerRef.current;
    if (!el || !container) return;

    /* Use IntersectionObserver with the scroll container as root */
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          setIsVisible(entry.isIntersecting);
        });
      },
      {
        root: container,
        rootMargin: "-20% 0px -20% 0px",
        threshold: 0,
      }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [containerRef]);

  return (
    <div
      ref={factRef}
      className={`hist-tl-fact${isVisible ? " hist-tl-fact--visible" : ""}`}
      style={{ left: `${position * 100}%` }}
      aria-hidden="true"
    >
      {text}
    </div>
  );
}

/* ===========================================================================
   TimelineCard — Above or below the track
   240px wide (desktop), full-width (mobile).
   Photo + title always visible. Hook + dots + CTA on hover (desktop).
   On mobile: title + year + small thumbnail, tap to open.
   Entrance stagger: cascades left-to-right via --card-index delay.
   Cinematographic: Dutch angle on catastrophic-above cards, weight
   differences for above (looming) vs below (receding).
   =========================================================================== */
function TimelineCard({
  event,
  index,
  side,
  onOpen,
  entranceReady,
  reducedMotion,
}: {
  event: HistoricalEvent;
  index: number;
  side: "above" | "below";
  onOpen: (event: HistoricalEvent) => void;
  entranceReady: boolean;
  reducedMotion: boolean;
}) {
  const hook =
    HOOKS[event.slug] ||
    event.contextNarrative.split(". ").slice(0, 2).join(". ") + ".";

  const cta =
    CTAS[event.slug] ||
    `Explore ${event.perspectives.length} accounts of ${event.title}`;

  const year = extractYear(event.dateSort, event.datePrimary);

  const handleClick = useCallback(() => {
    onOpen(event);
  }, [event, onOpen]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        onOpen(event);
      }
    },
    [event, onOpen]
  );

  const severityClass = `hist-tl-card--${event.severity}`;
  const entranceClass = entranceReady && !reducedMotion ? " hist-tl-card--entrance" : "";

  return (
    <article
      className={`hist-tl-card hist-tl-card--${side} ${severityClass}${entranceClass}`}
      data-slug={event.slug}
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onClick={handleClick}
      role="button"
      style={!reducedMotion ? { "--card-index": index } as React.CSSProperties : undefined}
    >
      {/* Photo with year badge */}
      <div className="hist-tl-card__photo">
        <PosterImage event={event} eager={index < 3} />
        <span className="hist-tl-card__year-badge" aria-hidden="true">
          {year}
        </span>
      </div>

      {/* Title */}
      <div className="hist-tl-card__body">
        <h3 className="hist-tl-card__title">{event.title}</h3>
      </div>

      {/* Expand on hover (desktop only via CSS) */}
      <div className="hist-tl-card__expand">
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
          onClick={(e) => {
            e.stopPropagation();
            handleClick();
          }}
          type="button"
        >
          <span className="hist-tl-card__cta-text">{cta}</span>
          <span className="hist-tl-card__cta-arrow" aria-hidden="true">
            &rarr;
          </span>
        </button>
      </div>
    </article>
  );
}
