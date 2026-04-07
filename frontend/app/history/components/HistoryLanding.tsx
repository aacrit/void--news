"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import Link from "next/link";
import type { HistoricalEvent, RedactedEvent, HistoryEra } from "../types";
import { ERAS } from "../types";
import { HOOKS, CTAS } from "../hooks";
/* CartographerStrip deferred — removed from timeline view, kept as component for future arc/map pages */

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

/* ── Side mapping: alternate above/below for even distribution ── */
function getCardSide(_event: HistoricalEvent, index: number): "above" | "below" {
  return index % 2 === 0 ? "above" : "below";
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
  const MIN_GAP_PX = 320; /* Must exceed card width (280px max) to prevent overlap */
  const minGapNorm = totalWidth > 0 ? MIN_GAP_PX / totalWidth : 0.08;
  const resolved = [...positions];
  const sides = events.map((e, i) => getCardSide(e, i));

  const aboveIndices = events.map((_, i) => i).filter((i) => sides[i] === "above");
  const belowIndices = events.map((_, i) => i).filter((i) => sides[i] === "below");

  for (const group of [aboveIndices, belowIndices]) {
    for (let pass = 0; pass < 12; pass++) {
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
/* ── Easter Egg: "The line remembers" — severity encodes the wobble ──
   The ink track is a seismograph of human suffering. Near catastrophic
   events the line shudders. Near peaceful events it calms. The wobble
   is not random — it carries the weight of what happened. */
const SEVERITY_WEIGHT: Record<string, number> = {
  catastrophic: 1.0, critical: 0.55, major: 0.2,
};

function generateInkPath(
  width: number,
  events: HistoricalEvent[],
  positions: number[]
): string {
  const segments = Math.max(20, Math.floor(width / 50));
  const step = width / segments;
  let d = `M0,4`;
  for (let i = 1; i <= segments; i++) {
    const x = i * step;
    const frac = x / width;

    /* Find severity intensity at this point */
    let intensity = 0.15;
    for (let e = 0; e < events.length; e++) {
      const dist = Math.abs(frac - (positions[e] || 0));
      const influence = Math.max(0, 1 - dist * 14);
      const w = SEVERITY_WEIGHT[events[e].severity] || 0.2;
      intensity = Math.max(intensity, w * influence);
    }

    const baseWobble = Math.sin(i * 1.7) * 1.2 + Math.cos(i * 2.3) * 0.8;
    const wobble = baseWobble * (0.12 + intensity * 1.5);
    d += ` S${(x - step * 0.3).toFixed(1)},${(4 + wobble).toFixed(2)} ${x.toFixed(1)},${(4 - wobble * 0.5).toFixed(2)}`;
  }
  return d;
}

/* ── Easter Egg: Dot size = death toll as % of world population ──
   Ancient catastrophes (Black Death: 25-50% of humanity) feel heavier
   than modern ones with larger absolute numbers but smaller relative impact. */
const WORLD_POP: [number, number][] = [
  [-3000, 14e6], [-500, 100e6], [0, 200e6], [500, 200e6], [1000, 310e6],
  [1200, 400e6], [1350, 370e6], [1500, 500e6], [1700, 600e6], [1800, 1e9],
  [1900, 1.6e9], [1940, 2.3e9], [1960, 3e9], [1980, 4.4e9], [1994, 5.6e9],
];

function worldPopAt(year: number): number {
  for (let i = WORLD_POP.length - 1; i >= 0; i--) {
    if (year >= WORLD_POP[i][0]) {
      if (i === WORLD_POP.length - 1) return WORLD_POP[i][1];
      const [y0, p0] = WORLD_POP[i];
      const [y1, p1] = WORLD_POP[i + 1];
      const t = (year - y0) / (y1 - y0);
      return p0 + t * (p1 - p0);
    }
  }
  return WORLD_POP[0][1];
}

function parseDeathToll(toll?: string): number {
  if (!toll || toll === "N/A") return 0;
  const mMatch = toll.match(/([\d,.]+)\s*(?:million|m)/i);
  if (mMatch) return parseFloat(mMatch[1].replace(/,/g, "")) * 1e6;
  const kMatch = toll.match(/([\d,.]+)\s*(?:thousand|k)/i);
  if (kMatch) return parseFloat(kMatch[1].replace(/,/g, "")) * 1e3;
  const nMatch = toll.match(/([\d,.]+)/);
  return nMatch ? parseFloat(nMatch[1].replace(/,/g, "")) : 0;
}

function dotScaleFromDeathToll(event: HistoricalEvent): number {
  const toll = parseDeathToll(event.deathToll);
  if (toll <= 0) return 1;
  const year = extractNumericYear(event.dateSort);
  const pop = worldPopAt(year);
  const pct = toll / pop; // fraction of world population
  // Log scale: 0.01% → 1.0, 1% → 1.3, 10% → 1.5, 50% → 1.7
  return 0.8 + Math.min(Math.log10(Math.max(pct, 1e-6) * 1e4 + 1) / 5, 0.9);
}

/* ===========================================================================
   PosterImage — Robust fallback chain
   heroImage -> media[0].url -> ... -> cinematic gradient
   =========================================================================== */
function PosterImage({ event, eager, year }: { event: HistoricalEvent; eager?: boolean; year?: string }) {
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
    return (
      <div className="hist-tl-card__photo-fallback" aria-hidden="true">
        {year && <span className="hist-tl-card__photo-fallback-year">{year}</span>}
      </div>
    );
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
  const [focusedIndex, setFocusedIndex] = useState(0);
  const [prevEra, setPrevEra] = useState<string | null>(null);
  const [eraFlashColor, setEraFlashColor] = useState<string | null>(null);
  const [entranceReady, setEntranceReady] = useState(false);
  const [scrollYear, setScrollYear] = useState<number | null>(null);
  const [isMobileVertical, setIsMobileVertical] = useState(false);
  const stationRefs = useRef<(HTMLDivElement | null)[]>([]);
  /* Globe view removed — kept simple */

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
    () => Math.max(100, sortedEvents.length * 420),
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

  /* ── Ink path — "The line remembers" ── */
  const inkPath = useMemo(
    () => generateInkPath(totalWidthVw, sortedEvents, positions),
    [totalWidthVw, sortedEvents, positions]
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
    const container = timelineRef.current;
    if (!container) return;

    const years = sortedEvents.map((e) => extractNumericYear(e.dateSort));

    const updateFocusedIndex = () => {
      let closest = 0;
      let closestDist = Infinity;
      let scrollFraction = 0;

      if (isMobileVertical) {
        /* Vertical mode: use scrollTop + station offsetTop */
        const viewCenter = container.scrollTop + container.clientHeight / 2;
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
        const totalH = container.scrollHeight;
        scrollFraction = totalH > 0 ? viewCenter / totalH : 0;
      } else {
        /* Horizontal mode: viewport CENTER for year ribbon sync */
        const viewCenter = container.scrollLeft + container.clientWidth / 2;
        const totalW = container.scrollWidth;
        for (let i = 0; i < positions.length; i++) {
          const cardX = positions[i] * totalW;
          const dist = Math.abs(cardX - viewCenter);
          if (dist < closestDist) {
            closestDist = dist;
            closest = i;
          }
        }
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
  }, [positions, sortedEvents, isMobileVertical]);

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
    if (reducedMotion) return;
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
  }, [reducedMotion, hasScrolled]);

  /* ── Momentum wheel: vertical scroll -> horizontal, snappier physics (desktop only) ── */
  useEffect(() => {
    if (isMobileVertical) return; /* Skip on mobile — native vertical scroll */
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
  }, [positions, isMobileVertical]);

  /* ── Edge scroll: mouse near left/right edge triggers auto-scroll (desktop) ── */
  useEffect(() => {
    if (reducedMotion) return;
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
  }, [reducedMotion]);

  /* ── Auto-scroll to 1945 on initial load ── */
  useEffect(() => {
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

  /* ── Preload hero images for focused card ± 2 neighbors ── */
  useEffect(() => {
    if (sortedEvents.length === 0) return;
    const preloadIndices = [focusedIndex - 2, focusedIndex - 1, focusedIndex, focusedIndex + 1, focusedIndex + 2];
    const links: HTMLLinkElement[] = [];
    for (const idx of preloadIndices) {
      if (idx < 0 || idx >= sortedEvents.length) continue;
      const url = sortedEvents[idx].heroImage;
      if (!url) continue;
      const existing = document.querySelector(`link[href="${url}"]`);
      if (existing) continue;
      const link = document.createElement("link");
      link.rel = "preload";
      link.as = "image";
      link.href = url;
      document.head.appendChild(link);
      links.push(link);
    }
    return () => { links.forEach((l) => l.remove()); };
  }, [focusedIndex, sortedEvents]);

  /* ── Easter Egg: Anniversary Vigil — events glow on their date ── */
  const anniversarySlugs = useMemo(() => {
    const today = new Date();
    const monthName = today.toLocaleString("en-US", { month: "long" }).toLowerCase();
    const day = today.getDate();
    return new Set(
      sortedEvents
        .filter((e) => {
          const dp = (e.datePrimary || "").toLowerCase();
          return dp.includes(monthName) && dp.includes(String(day));
        })
        .map((e) => e.slug)
    );
  }, [sortedEvents]);

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
      {/* ── TOP ZONE: Era header + year ribbon + era pills ── */}
      <div
        className={`hist-tl-top-zone ${hasScrolled ? "" : "hist-tl-top-zone--hidden"}`}
        style={{ "--era-color": eraCtx.color } as React.CSSProperties}
      >
        {/* Era header */}
        <div className="hist-tl-era-header" aria-live="polite" aria-atomic="true">
          <span className="hist-tl-era-header__label">{eraCtx.label}</span>
          <span className="hist-tl-era-header__desc">{eraCtx.description}</span>
        </div>

        {/* Year ribbon — ±4 years with focus/blur depth-of-field */}
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

        {/* Era pills */}
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
      </div>

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
            viewBox={`0 0 ${totalWidthVw} 8`}
            preserveAspectRatio="none"
            aria-hidden="true"
          >
            <title>The line remembers.</title>
            <path
              ref={inkPathRef}
              className="hist-tl-full__ink-path"
              d={inkPath}
              stroke="var(--hist-accent)"
              strokeWidth="3"
              fill="none"
              opacity="0.8"
            />
          </svg>

          {/* Cards + stems + dots */}
          {sortedEvents.map((event, i) => {
            const side = sides[i];
            const pct = positions[i] * 100;
            const isFocused = i === focusedIndex;
            const dist = Math.min(Math.abs(i - focusedIndex), 6);
            const isAnniversary = anniversarySlugs.has(event.slug);
            const dScale = dotScaleFromDeathToll(event);

            return (
              <div
                key={event.slug}
                ref={(el) => { stationRefs.current[i] = el; }}
                className={`hist-tl-full__station${isFocused ? " hist-tl-full__station--focused" : ""}${isAnniversary ? " hist-tl-full__station--anniversary" : ""}`}
                style={{
                  left: `${pct}%`,
                  "--card-dist": dist,
                  "--dot-scale": dScale,
                } as React.CSSProperties}
              >
                {/* Dot on track — size encodes death toll as % of world population */}
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
                  entranceReady={entranceReady}
                  reducedMotion={reducedMotion}
                  focused={isFocused}
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
  entranceReady,
  reducedMotion,
  focused,
}: {
  event: HistoricalEvent;
  index: number;
  side: "above" | "below";
  entranceReady: boolean;
  reducedMotion: boolean;
  focused: boolean;
}) {
  const hook =
    HOOKS[event.slug] ||
    (event.contextNarrative || event.title).split(". ").slice(0, 2).join(". ") + ".";

  const cta =
    CTAS[event.slug] ||
    `Explore ${event.perspectives.length} accounts of ${event.title}`;

  const year = extractYear(event.dateSort, event.datePrimary);

  const severityClass = `hist-tl-card--${event.severity}`;
  const entranceClass = entranceReady && !reducedMotion ? " hist-tl-card--entrance" : "";
  const focusedClass = focused && !reducedMotion ? " hist-tl-card--focused" : "";

  /* Easter Egg: Victor dominance → photo saturation.
     More victors = heavier sepia (further from truth).
     Balanced perspectives = more color fidelity. */
  const victorCount = event.perspectives.filter((p) => p.viewpointType === "victor").length;
  const victorDominance = event.perspectives.length > 0 ? victorCount / event.perspectives.length : 0.5;
  const photoSat = 0.55 + (1 - victorDominance) * 0.35;
  const photoSepia = 0.04 + victorDominance * 0.14;

  return (
    <Link
      href={`/history/${event.slug}`}
      className={`hist-tl-card hist-tl-card--${side} ${severityClass}${entranceClass}${focusedClass}`}
      data-slug={event.slug}
      aria-label={`${event.title} — ${event.datePrimary}`}
      style={{
        ...(reducedMotion ? {} : { "--card-index": index }),
        "--photo-sat": photoSat,
        "--photo-sepia": photoSepia,
      } as React.CSSProperties}
    >
      {/* Photo with year badge — saturation encodes victor dominance */}
      <div className="hist-tl-card__photo">
        <PosterImage event={event} eager={index < 3} year={year} />
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

        <span className="hist-tl-card__cta">
          <span className="hist-tl-card__cta-text">{cta}</span>
          <span className="hist-tl-card__cta-arrow" aria-hidden="true">
            &rarr;
          </span>
        </span>
      </div>
    </Link>
  );
}
