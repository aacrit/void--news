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

/* ── Timeline Arcs — thematic threads connecting events across centuries ── */
interface TimelineArc {
  slug: string;
  title: string;
  subtitle: string;
  color: string;
  /** Event slugs this arc threads through, in chronological order */
  connectedSlugs: string[];
}

const TIMELINE_ARCS: TimelineArc[] = [
  {
    slug: "capitalism-and-communism",
    title: "Capitalism & Communism",
    subtitle: "The 175-year argument over who owns the future",
    color: "#B44C00", /* burnt amber — economic arc */
    connectedSlugs: [
      "french-revolution",       // 1789 — proto-socialist ideals
      "haitian-revolution",      // 1804 — slave revolt, economic liberation
      "opium-wars",              // 1839 — imperial capitalism, forced markets
      "meiji-restoration",       // 1868 — capitalist industrialization
      "scramble-for-africa",     // 1884 — colonial extractive capitalism
      "congo-free-state",        // 1885 — rubber capitalism, forced labor
      "armenian-genocide",       // 1915 — WWI, imperial collapse
      "holodomor",               // 1932 — Soviet forced collectivization
      "hiroshima-nagasaki",      // 1945 — WWII end, Cold War starts
      "partition-of-india",      // 1947 — decolonization, economic partition
      "cambodian-genocide",      // 1975 — communist Khmer Rouge
      "tiananmen-square",        // 1989 — communist state vs. reform
      "fall-of-berlin-wall",     // 1989 — end of communist Eastern Europe
    ],
  },
];

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

/* ── Density-adaptive spacing ──
   Sparse periods (ancient → medieval, 2500-year gaps) compress via log scale.
   Dense periods (1900-1950, 5-10 year gaps) get near-linear space.
   Result: less scrolling through empty centuries, more room where events cluster. */
function computePositions(events: HistoricalEvent[]): number[] {
  if (events.length === 0) return [];
  if (events.length === 1) return [0.5];

  const years = events.map((e) => extractNumericYear(e.dateSort));
  const DENSE_THRESHOLD = 60; // Gaps under 60 years: near-linear
  const LOG_SCALE = 25; // Controls compression intensity for large gaps

  // Compute gaps between consecutive events
  const gaps: number[] = [];
  for (let i = 1; i < years.length; i++) {
    gaps.push(Math.max(1, years[i] - years[i - 1]));
  }

  // Compress: linear for dense, log for sparse
  const compressed = gaps.map((gap) => {
    if (gap <= DENSE_THRESHOLD) return gap;
    return DENSE_THRESHOLD + Math.log2(gap / DENSE_THRESHOLD) * LOG_SCALE;
  });

  // Build cumulative positions normalized to [0.05, 0.95]
  const total = compressed.reduce((a, b) => a + b, 0);
  if (total === 0) return events.map(() => 0.5);

  const positions = [0.05];
  let cumulative = 0;
  for (const g of compressed) {
    cumulative += g;
    positions.push(0.05 + (cumulative / total) * 0.9);
  }
  return positions;
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

  // Clamp all positions to [0.03, 0.97] so they stay within the ink path
  const maxPos = Math.max(...resolved);
  if (maxPos > 0.97) {
    const scale = 0.94 / (maxPos - resolved[0]);
    for (let i = 0; i < resolved.length; i++) {
      resolved[i] = 0.03 + (resolved[i] - resolved[0]) * scale;
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
  const [scrollYear, setScrollYear] = useState<number | null>(null);
  const [isMobileVertical, setIsMobileVertical] = useState(false);
  const stationRefs = useRef<(HTMLDivElement | null)[]>([]);
  const flipRectRef = useRef<DOMRect | null>(null);
  const flipImageRef = useRef<string | null>(null);
  const [flipAnimating, setFlipAnimating] = useState(false);

  /* ── Detect vertical (mobile) timeline mode ── */
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobileVertical(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobileVertical(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

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

  /* ── Arc lanes: resolve connected slugs to positions ── */
  const arcLanes = useMemo(() => {
    return TIMELINE_ARCS.map((arc) => {
      const nodes: { index: number; position: number; slug: string; title: string }[] = [];
      for (const slug of arc.connectedSlugs) {
        const idx = sortedEvents.findIndex((e) => e.slug === slug);
        if (idx !== -1) {
          nodes.push({
            index: idx,
            position: positions[idx],
            slug,
            title: sortedEvents[idx].title,
          });
        }
      }
      if (nodes.length < 2) return null;
      const startPct = nodes[0].position * 100;
      const endPct = nodes[nodes.length - 1].position * 100;
      return { ...arc, nodes, startPct, endPct };
    }).filter(Boolean) as (TimelineArc & {
      nodes: { index: number; position: number; slug: string; title: string }[];
      startPct: number;
      endPct: number;
    })[];
  }, [sortedEvents, positions]);

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

  /* ── Focused index + rolling year — works for both horizontal (desktop) and vertical (mobile) ── */
  useEffect(() => {
    if (activeEvent) return;
    const container = timelineRef.current;
    if (!container) return;

    const years = sortedEvents.map((e) => extractNumericYear(e.dateSort));

    const updateFocusedIndex = () => {
      let closest = 0;
      let closestDist = Infinity;
      let scrollFraction = 0;

      if (isMobileVertical) {
        /* Vertical mode: use scrollTop + station offsetTop */
        const viewCenter = container.scrollTop + container.clientHeight / 3;
        for (let i = 0; i < stationRefs.current.length; i++) {
          const el = stationRefs.current[i];
          if (!el) continue;
          const stationCenter = el.offsetTop + el.offsetHeight / 2;
          const dist = Math.abs(stationCenter - viewCenter);
          if (dist < closestDist) {
            closestDist = dist;
            closest = i;
          }
        }
        /* Scroll fraction for year interpolation */
        const totalH = container.scrollHeight;
        const viewCenterFull = container.scrollTop + container.clientHeight / 2;
        scrollFraction = totalH > 0 ? viewCenterFull / totalH : 0;
      } else {
        /* Horizontal mode: use scrollLeft (original logic) */
        const scrollCenter = container.scrollLeft + container.clientWidth / 3;
        const totalW = container.scrollWidth;
        for (let i = 0; i < positions.length; i++) {
          const cardX = positions[i] * totalW;
          const dist = Math.abs(cardX - scrollCenter);
          if (dist < closestDist) {
            closestDist = dist;
            closest = i;
          }
        }
        const viewCenter = container.scrollLeft + container.clientWidth / 2;
        scrollFraction = totalW > 0 ? viewCenter / totalW : 0;
      }

      setFocusedIndex(closest);

      /* Rolling year: interpolate from scroll fraction */
      let leftIdx = 0;
      let rightIdx = positions.length - 1;
      for (let i = 0; i < positions.length - 1; i++) {
        if (positions[i] <= scrollFraction && positions[i + 1] >= scrollFraction) {
          leftIdx = i;
          rightIdx = i + 1;
          break;
        }
      }
      if (scrollFraction <= positions[0]) {
        setScrollYear(years[0]);
      } else if (scrollFraction >= positions[positions.length - 1]) {
        setScrollYear(years[years.length - 1]);
      } else {
        const leftPos = positions[leftIdx];
        const rightPos = positions[rightIdx];
        const t = rightPos > leftPos ? (scrollFraction - leftPos) / (rightPos - leftPos) : 0;
        setScrollYear(Math.round(years[leftIdx] + t * (years[rightIdx] - years[leftIdx])));
      }
    };

    container.addEventListener("scroll", updateFocusedIndex, { passive: true });
    updateFocusedIndex();
    return () => container.removeEventListener("scroll", updateFocusedIndex);
  }, [activeEvent, positions, sortedEvents, isMobileVertical]);

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

  /* ── Fun facts: position using same adaptive algorithm as events ── */
  const funFactPositions = useMemo(() => {
    if (sortedEvents.length < 2 || positions.length < 2) return [];
    const years = sortedEvents.map((e) => extractNumericYear(e.dateSort));
    const minYear = Math.min(...years);
    const maxYear = Math.max(...years);

    return FUN_FACTS.map((fact) => {
      const midYear = (fact.yearStart + fact.yearEnd) / 2;
      if (midYear < minYear || midYear > maxYear) return null;
      // Interpolate position from flanking events
      let leftIdx = 0;
      for (let i = 0; i < years.length - 1; i++) {
        if (years[i] <= midYear && years[i + 1] >= midYear) {
          leftIdx = i;
          break;
        }
        if (i === years.length - 2) leftIdx = i;
      }
      const rightIdx = Math.min(leftIdx + 1, years.length - 1);
      const yearSpan = years[rightIdx] - years[leftIdx];
      const t = yearSpan > 0 ? (midYear - years[leftIdx]) / yearSpan : 0.5;
      const position = positions[leftIdx] + t * (positions[rightIdx] - positions[leftIdx]);
      return { ...fact, position };
    }).filter(Boolean) as (typeof FUN_FACTS[0] & { position: number })[];
  }, [sortedEvents, positions]);

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

  /* ── Momentum wheel: vertical scroll -> horizontal, snappier physics (desktop only) ── */
  useEffect(() => {
    if (activeEvent || isMobileVertical) return; /* Skip on mobile — native vertical scroll */
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
  }, [activeEvent, positions, isMobileVertical]);

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
    if (isMobileVertical) {
      /* Mobile: scroll vertically to station element */
      const station = stationRefs.current[closest];
      if (station) {
        station.scrollIntoView({ block: "center", behavior: "instant" as ScrollBehavior });
      }
    } else {
      /* Desktop: scroll horizontally by position fraction */
      const totalW = container.scrollWidth;
      const targetLeft = positions[closest] * totalW - container.clientWidth / 3;
      container.scrollTo({ left: Math.max(0, targetLeft), behavior: "instant" as ScrollBehavior });
    }
    setFocusedIndex(closest);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sortedEvents.length, isMobileVertical]); /* Run once after events load + orientation known */

  /* ── URL management ── */
  const openStory = useCallback((event: HistoricalEvent) => {
    /* Remember which card index was opened */
    const idx = sortedEvents.findIndex((e) => e.slug === event.slug);
    if (idx !== -1) activeEventIndexRef.current = idx;

    /* FLIP: Capture card rect for morph animation */
    const cardEl = document.querySelector(`[data-slug="${event.slug}"]`) as HTMLElement | null;
    if (cardEl && !reducedMotion) {
      flipRectRef.current = cardEl.getBoundingClientRect();
      flipImageRef.current = event.heroImage || event.media[0]?.url || null;
      setFlipAnimating(true);
    }

    setActiveEvent(event);
    window.history.pushState(
      { historyInline: true, slug: event.slug },
      "",
      `/history/${event.slug}`
    );
  }, [sortedEvents, reducedMotion]);

  const closeStory = useCallback(() => {
    setActiveEvent(null);
    window.history.pushState({}, "", "/history");
    /* Scroll timeline back to the card the user was viewing */
    requestAnimationFrame(() => {
      const idx = activeEventIndexRef.current;
      const station = stationRefs.current[idx];
      if (station) {
        station.scrollIntoView({
          block: isMobileVertical ? "center" : "nearest",
          inline: isMobileVertical ? "nearest" : "center",
          behavior: "instant" as ScrollBehavior,
        });
      }
    });
  }, [isMobileVertical]);

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

  /* ── State B: Story active — floating Back CTA + FLIP morph + inline story ── */
  if (activeEvent) {
    return (
      <div className="hist-tl-wrapper hist-tl-wrapper--story-active">
        {/* FLIP morph overlay — animates card rect → full screen */}
        {flipAnimating && flipRectRef.current && (
          <FlipMorphOverlay
            rect={flipRectRef.current}
            imageUrl={flipImageRef.current}
            onComplete={() => setFlipAnimating(false)}
          />
        )}

        {/* Floating Back to Timeline CTA — slides in after 1s */}
        <BackToTimelineCTA onClose={closeStory} />

        {/* Inline story — L-cut: content fades in during morph */}
        <div className={`hist-inline-story-wrap${flipAnimating ? " hist-inline-story-wrap--entering" : ""}`}>
          <StoryContainer
            event={activeEvent}
            allEvents={sortedEvents}
            onNavigateToEvent={navigateToEvent}
            onClose={closeStory}
          />
        </div>
      </div>
    );
  }

  /* ── Current era context for header ── */
  const eraCtx = ERA_CONTEXT[currentEra] || ERA_CONTEXT.contemporary;

  /* ── Year ribbon: ±4 neighboring event years with distance for blur ── */
  const yearRibbon = useMemo(() => {
    if (sortedEvents.length === 0 || focusedIndex < 0) return [];
    const ribbon: { year: string; distance: number; index: number }[] = [];
    for (let d = -4; d <= 4; d++) {
      const idx = focusedIndex + d;
      if (idx < 0 || idx >= sortedEvents.length) continue;
      const y = extractYear(sortedEvents[idx].dateSort, sortedEvents[idx].datePrimary);
      ribbon.push({ year: y, distance: Math.abs(d), index: idx });
    }
    return ribbon;
  }, [sortedEvents, focusedIndex]);

  /* ── State A: Full timeline ── */
  return (
    <div className="hist-tl-wrapper">
      {/* ── TOP ZONE: Era header + year ribbon + era pills (all fixed) ── */}

      {/* Era header — updates as user scrolls */}
      <div
        className={`hist-tl-era-header ${hasScrolled ? "" : "hist-tl-era-header--hidden"}`}
        aria-live="polite"
        aria-atomic="true"
        style={{ "--era-color": eraCtx.color } as React.CSSProperties}
      >
        <div className="hist-tl-era-header__label">{eraCtx.label}</div>
        <div className="hist-tl-era-header__desc">{eraCtx.description}</div>
      </div>

      {/* Year ribbon — scrolling ±4 years with focus/blur */}
      {hasScrolled && (
        <div className="hist-tl-year-ribbon" aria-hidden="true">
          {yearRibbon.map((item) => (
            <button
              key={item.index}
              className={`hist-tl-year-ribbon__year${item.distance === 0 ? " hist-tl-year-ribbon__year--focused" : ""}`}
              style={{ "--yr-dist": item.distance } as React.CSSProperties}
              onClick={() => {
                const station = stationRefs.current[item.index];
                if (station) {
                  station.scrollIntoView({
                    block: isMobileVertical ? "center" : "nearest",
                    inline: isMobileVertical ? "nearest" : "center",
                    behavior: "smooth",
                  });
                }
              }}
              type="button"
            >
              {item.year}
            </button>
          ))}
        </div>
      )}

      {/* Era selection pills — ink-styled quick jump */}
      {hasScrolled && (
        <nav className="hist-tl-era-pills" role="navigation" aria-label="Era navigation">
          {eraGroups.map((era) => {
            const isActive = currentEra === era.id;
            return (
              <button
                key={era.id}
                className={`hist-tl-era-pill${isActive ? " hist-tl-era-pill--active" : ""}`}
                onClick={() => {
                  const station = stationRefs.current[era.firstIndex];
                  if (station) {
                    station.scrollIntoView({
                      block: isMobileVertical ? "center" : "nearest",
                      inline: isMobileVertical ? "nearest" : "center",
                      behavior: "smooth",
                    });
                  }
                }}
                type="button"
              >
                {ERA_CONTEXT[era.id]?.label || era.label}
              </button>
            );
          })}
        </nav>
      )}

      {/* Mission Brief -- fades on first scroll */}
      <div
        className={`hist-tl-brief ${hasScrolled ? "hist-tl-brief--hidden" : ""}`}
        aria-hidden={hasScrolled}
      >
        <p className="hist-tl-brief__text">
          One event. Every side. Decide for yourself.
        </p>
        <span className="hist-tl-brief__hint">
          {isMobileVertical ? "scroll through time" : "\u2190 scroll through time \u2192"}
        </span>
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
        style={eraFlashColor ? { "--era-flash-color": `color-mix(in srgb, ${eraFlashColor} 18%, transparent)` } as React.CSSProperties : undefined}
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

          {/* Arc lanes — thematic threads connecting events */}
          {arcLanes.map((arc) => (
            <div
              key={arc.slug}
              className="hist-tl-arc-lane"
              style={{
                left: `${arc.startPct}%`,
                width: `${arc.endPct - arc.startPct}%`,
                "--arc-color": arc.color,
              } as React.CSSProperties}
            >
              {/* Arc thread line */}
              <div className="hist-tl-arc-lane__thread" aria-hidden="true" />

              {/* Arc label at start */}
              <div className="hist-tl-arc-lane__label">
                <span className="hist-tl-arc-lane__title">{arc.title}</span>
                <span className="hist-tl-arc-lane__subtitle">{arc.subtitle}</span>
              </div>

              {/* Nodes at each connected event */}
              {arc.nodes.map((node) => {
                const laneWidth = arc.endPct - arc.startPct;
                const nodePct = laneWidth > 0
                  ? ((node.position * 100 - arc.startPct) / laneWidth) * 100
                  : 0;
                return (
                  <div
                    key={node.slug}
                    className="hist-tl-arc-lane__node"
                    style={{ left: `${nodePct}%` }}
                    title={node.title}
                  >
                    <div className="hist-tl-arc-lane__node-dot" />
                  </div>
                );
              })}
            </div>
          ))}

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
                ref={(el) => { stationRefs.current[i] = el; }}
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
   FlipMorphOverlay — FLIP animation from card rect to full viewport
   Creates a clone at the card's position, animates it to fill the screen,
   then fades out to reveal the actual EventDetail underneath (L-cut).
   =========================================================================== */
function FlipMorphOverlay({
  rect,
  imageUrl,
  onComplete,
}: {
  rect: DOMRect;
  imageUrl: string | null;
  onComplete: () => void;
}) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = overlayRef.current;
    if (!el) { onComplete(); return; }

    /* Start at card position, animate to full viewport */
    const animation = el.animate(
      [
        {
          top: `${rect.top}px`,
          left: `${rect.left}px`,
          width: `${rect.width}px`,
          height: `${rect.height}px`,
          borderRadius: "2px",
          opacity: 1,
        },
        {
          top: "0px",
          left: "0px",
          width: "100vw",
          height: "100vh",
          borderRadius: "0px",
          opacity: 1,
        },
      ],
      {
        duration: 500,
        easing: "cubic-bezier(0.16, 1, 0.3, 1)", /* document-settle */
        fill: "forwards",
      }
    );

    /* After morph completes, fade out to reveal EventDetail */
    animation.onfinish = () => {
      const fadeOut = el.animate(
        [{ opacity: 1 }, { opacity: 0 }],
        { duration: 300, easing: "ease-out", fill: "forwards" }
      );
      fadeOut.onfinish = onComplete;
    };

    return () => { animation.cancel(); };
  }, [rect, onComplete]);

  return (
    <div
      ref={overlayRef}
      className="hist-flip-morph"
      aria-hidden="true"
      style={{
        position: "fixed",
        top: rect.top,
        left: rect.left,
        width: rect.width,
        height: rect.height,
        zIndex: 60,
        overflow: "hidden",
        backgroundSize: "cover",
        backgroundPosition: "center",
        backgroundColor: "var(--hist-paper-deep)",
        backgroundImage: imageUrl ? `url(${imageUrl})` : undefined,
        filter: "contrast(1.05) saturate(0.75) sepia(0.12)",
        pointerEvents: "none",
      }}
    />
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
