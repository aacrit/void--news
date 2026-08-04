"use client";

import { useState, useEffect, useRef, useMemo, useCallback } from "react";
import Link from "next/link";
import type { HistoricalEvent, Perspective, MediaItem, ConnectionType } from "../types";
import { HOOKS, CTAS } from "../hooks";
import { ARC_FEATURES } from "../arc-features";
import { useAudio } from "../../components/AudioProvider";
import ReelScrubber, { type ScrubNode } from "./ReelScrubber";
import PerspectiveFrame from "./PerspectiveFrame";
import PerspectiveReader from "./PerspectiveReader";
import Lightbox from "./Lightbox";
import MediaGallery from "./MediaGallery";

/* Floor-based clock so a float duration reads "4:30", not "4:30.3000001". */
function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/* ===========================================================================
   "By the Numbers" — stat derivation
   Every value is derived from the existing fact strings; no data is invented.
   Each stat leads with a big, abbreviated magnitude (3.5 million -> "3.5M",
   ~21,000 -> "~21K", 46 years -> "46 yrs"); the full detail rides in a
   fine-print qualifier line below it. Prose-led or number-less strings fall
   back to a legible "text" cell so nothing renders as a giant wall of words.
   =========================================================================== */

type StatVariant = "figure" | "text";
interface StatCell {
  key: string;
  label: string;
  value: string;   // the large display string
  fine?: string;   // fine-print qualifier
  variant: StatVariant;
}

/* Em / en dashes are banned in written output; normalize to commas. */
function tidy(s: string): string {
  return s
    .replace(/[—–]/g, ", ")
    .replace(/\s*\(/g, ", ")
    .replace(/\)/g, "")
    .replace(/,\s*,/g, ",")
    .replace(/\s+/g, " ")
    .replace(/\s+([,;:.])/g, "$1")
    .replace(/^[\s,;:.]+/, "")
    .trim();
}

function truncate(s: string, max: number): string {
  if (s.length <= max) return s;
  const cut = s.slice(0, max);
  const sp = cut.lastIndexOf(" ");
  return (sp > max * 0.6 ? cut.slice(0, sp) : cut).replace(/[\s,;:.]+$/, "") + "…";
}

/* Round to at most one decimal, dropping a trailing ".0". */
function shortNum(x: number): string {
  const r = Math.round(x * 10) / 10;
  return Number.isInteger(r) ? String(r) : r.toFixed(1);
}

function compact(n: number): string {
  const a = Math.abs(n);
  if (a >= 1e9) return shortNum(n / 1e9) + "B";
  if (a >= 1e6) return shortNum(n / 1e6) + "M";
  if (a >= 1e3) return shortNum(n / 1e3) + "K";
  return String(Math.round(n));
}

function scaleOf(word?: string): number {
  if (!word) return 1;
  const w = word.toLowerCase();
  if (w.startsWith("bill") || w === "bn") return 1e9;
  if (w.startsWith("mill")) return 1e6;
  if (w.startsWith("thou")) return 1e3;
  return 1;
}

function abbrevOne(numStr: string, scaleWord?: string): string {
  const n = parseFloat(numStr.replace(/,/g, ""));
  if (!isFinite(n)) return numStr;
  return compact(n * scaleOf(scaleWord));
}

/* Merge a range so a shared magnitude suffix isn't repeated: "75M"+"200M" -> "75-200M". */
function mergeRange(a: string, b: string, prefix: string): string {
  const sa = /[KMB]$/.exec(a);
  const sb = /[KMB]$/.exec(b);
  if (sa && sb && sa[0] === sb[0]) return `${prefix}${a.slice(0, -1)}-${b}`;
  return `${prefix}${a}-${b}`;
}

const _NUM = "\\d[\\d,]*(?:\\.\\d+)?";
const _SCALE = "(?:thousand|million|billion|bn)";
const _APPROX = /^(?:~|≈|about|around|approx(?:imately)?|over|nearly|est(?:imated)?|roughly|up to)\s*/i;

/* Pull a leading (or scale-qualified) magnitude out of a messy fact string.
   Returns null when no usable number is present (caller renders a text cell). */
function deriveMagnitude(raw: string): { value: string; fine: string } | null {
  let s = raw.trim();
  let prefix = "";
  const am = _APPROX.exec(s);
  if (am) { prefix = "~"; s = s.slice(am[0].length); }

  const rangeAnchored = new RegExp(`^(${_NUM})\\s*(${_SCALE})?\\s*(?:[-–—]|to)\\s*(${_NUM})\\s*(${_SCALE})?`, "i");
  const singleAnchored = new RegExp(`^(${_NUM})\\s*(${_SCALE})?`, "i");
  const rangeAnywhere = new RegExp(`(${_NUM})\\s*(${_SCALE})?\\s*(?:[-–—]|to)\\s*(${_NUM})\\s*(${_SCALE})`, "i");
  const singleAnywhere = new RegExp(`(${_NUM})\\s*(${_SCALE})`, "i");

  let m: RegExpExecArray | null;
  let value = "";
  let matchEnd = -1;

  if ((m = rangeAnchored.exec(s))) {
    const shared = m[4] || m[2];
    value = mergeRange(abbrevOne(m[1], m[2] || shared), abbrevOne(m[3], m[4] || shared), prefix);
    matchEnd = m[0].length;
  } else if (/^\d/.test(s) && (m = singleAnchored.exec(s))) {
    value = prefix + abbrevOne(m[1], m[2]);
    matchEnd = m[0].length;
  } else if ((m = rangeAnywhere.exec(s))) {
    const shared = m[4] || m[2];
    value = mergeRange(abbrevOne(m[1], m[2] || shared), abbrevOne(m[3], m[4] || shared), "");
  } else if ((m = singleAnywhere.exec(s))) {
    value = abbrevOne(m[1], m[2]);
  } else {
    return null;
  }

  const rest = matchEnd >= 0 ? s.slice(matchEnd) : s.replace(m[0], " ");
  const fine = truncate(
    tidy(rest).replace(/^(?:people|persons|killed|dead|deaths|of)\s+/i, ""),
    58
  );
  return { value, fine };
}

/* The Span cell: a duration count leads ("46 yrs"); the year range is fine print.
   Falls back to a bare year range or the raw date when no count is present. */
function deriveSpan(raw: string): { value: string; fine: string } {
  const s = raw.trim();
  const dur = /(\d[\d,.]*)\s*(year|yr|day|month|week|decade|centur)/i.exec(s);
  const yrRange = /(\d{1,4})\s*(BCE|BC|CE|AD)?\s*[-–—]\s*(\d{1,4})\s*(BCE|BC|CE|AD)?/i.exec(s);
  const paren = /\(([^)]+)\)/.exec(s);

  const yrText = yrRange
    ? tidy(`${yrRange[1]}${yrRange[2] ? " " + yrRange[2] : ""}-${yrRange[3]}${yrRange[4] ? " " + yrRange[4] : ""}`)
    : "";

  if (dur) {
    const u = dur[2].toLowerCase();
    const unit = /year|yr/.test(u) ? "yrs"
      : /day/.test(u) ? "days"
      : /month/.test(u) ? "mos"
      : /week/.test(u) ? "wks"
      : /decade/.test(u) ? "decades"
      : "centuries";
    const fine = yrText || (paren ? truncate(tidy(paren[1]), 32) : "");
    return { value: `${dur[1]} ${unit}`, fine };
  }
  if (yrRange) {
    return { value: yrText, fine: paren ? truncate(tidy(paren[1]), 32) : "" };
  }
  const singleYr = /\d{1,4}\s*(?:BCE|BC|CE|AD)\b|\d{3,4}/i.exec(s);
  if (singleYr) {
    return { value: singleYr[0].trim(), fine: paren ? truncate(tidy(paren[1]), 32) : "" };
  }
  return { value: truncate(tidy(s), 20), fine: "" };
}

function figureOrText(key: string, label: string, raw: string): StatCell {
  const m = deriveMagnitude(raw);
  if (m) return { key, label, value: m.value, fine: m.fine, variant: "figure" };
  return { key, label, value: truncate(tidy(raw), 40), variant: "text" };
}

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
  const { playHistory } = useAudio();
  const reelRef = useRef<HTMLDivElement>(null);
  const galleryRef = useRef<HTMLElement>(null);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const [fraction, setFraction] = useState(0);
  const [reader, setReader] = useState<Perspective | null>(null);
  const [evidenceIndex, setEvidenceIndex] = useState<number | null>(null);
  const [isVertical, setIsVertical] = useState(false);

  /* One-time "scroll/swipe to explore" cue on the first frame. Dismissed on the
     reader's first scroll / arrow-key / node interaction. */
  const [cueVisible, setCueVisible] = useState(true);
  const cueDismissedRef = useRef(false);
  const dismissCue = useCallback(() => {
    if (cueDismissedRef.current) return;
    cueDismissedRef.current = true;
    setCueVisible(false);
  }, []);

  /* The reel only hijacks the vertical wheel while it is the engaged (hovered /
     focused) region, so the page scrolls normally everywhere else. */
  const reelEngagedRef = useRef(false);

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

  /* "By the Numbers" — numbers-forward stat cells derived from the fact strings */
  const stats = useMemo<StatCell[]>(() => {
    const cells: StatCell[] = [];
    const dateRaw = event.dateRange || event.datePrimary;
    if (dateRaw) {
      const span = deriveSpan(dateRaw);
      cells.push({ key: "span", label: "Span", value: span.value, fine: span.fine, variant: "figure" });
    }
    if (event.deathToll && event.deathToll !== "N/A") {
      cells.push(figureOrText("killed", "Killed", event.deathToll));
    }
    if (event.displaced && event.displaced !== "N/A") {
      cells.push(figureOrText("displaced", "Displaced", event.displaced));
    }
    if (event.location) {
      cells.push({ key: "place", label: "Place", value: event.location, variant: "text" });
    }
    return cells;
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

      /* First real scroll retires the discovery cue */
      if ((isVertical ? el.scrollTop : el.scrollLeft) > 8) dismissCue();

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
  }, [isVertical, frameCount, dismissCue]);

  /* Desktop: translate vertical wheel into horizontal scrubbing, releasing to
     the page at the left edge so the reader can scroll back up to the hero. */
  useEffect(() => {
    const el = reelRef.current;
    if (!el || isVertical) return;

    const onWheel = (e: WheelEvent) => {
      /* Only scrub while the reel is the engaged region AND has snapped to fill
         the viewport — otherwise let the page finish scrolling the hero away. */
      if (!reelEngagedRef.current) return;
      if (el.getBoundingClientRect().top > 2) return;
      const delta = Math.abs(e.deltaY) > Math.abs(e.deltaX) ? e.deltaY : e.deltaX;
      const max = el.scrollWidth - el.clientWidth;
      const atLeft = el.scrollLeft <= 0;
      const atRight = el.scrollLeft >= max - 1;
      if ((atLeft && delta < 0) || (atRight && delta > 0)) return; // release cleanly at the edges
      e.preventDefault();
      el.scrollLeft += delta;
    };

    const onEnter = () => { reelEngagedRef.current = true; };
    const onLeave = () => { reelEngagedRef.current = false; };

    el.addEventListener("wheel", onWheel, { passive: false });
    el.addEventListener("pointerenter", onEnter);
    el.addEventListener("pointerleave", onLeave);
    el.addEventListener("focusin", onEnter);
    el.addEventListener("focusout", onLeave);
    return () => {
      el.removeEventListener("wheel", onWheel);
      el.removeEventListener("pointerenter", onEnter);
      el.removeEventListener("pointerleave", onLeave);
      el.removeEventListener("focusin", onEnter);
      el.removeEventListener("focusout", onLeave);
    };
  }, [isVertical]);

  const goToFrame = useCallback((i: number) => {
    dismissCue();
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
  }, [dismissCue]);

  const onReelKey = useCallback(
    (e: React.KeyboardEvent) => {
      dismissCue();
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
    [focusedIndex, frameCount, goToFrame, dismissCue]
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
                onClick={() =>
                  playHistory({
                    id: event.id,
                    title: event.title,
                    subtitle: event.subtitle,
                    audioUrl: event.audioUrl!,
                    durationSeconds: event.audioDuration ?? 0,
                  })
                }
                aria-label={`Listen to ${event.title}, ${event.perspectives.length} perspectives`}
              >
                <svg width="12" height="14" viewBox="0 0 12 14" fill="currentColor" aria-hidden="true" className="hist-hero-listen__icon">
                  <path d="M1 1.5v11l10-5.5z" />
                </svg>
                <span className="hist-hero-listen__label">Listen</span>
                <span className="hist-hero-listen__meta">{event.perspectives.length} perspectives · {formatClock(event.audioDuration ?? 0)}</span>
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

      {/* ── AUDIO — plays through the shared void --onair player. The hero
             "Listen" button calls playHistory(), which loads this event into the
             global FloatingPlayer (collapsed pill → side panel), exactly like
             News and Weekly. The old inline HistoryAudioCue was retired. ── */}

      {/* ── BY THE NUMBERS — numbers-forward stat strip below the hero.
             The hero's lower third is already dense (title / subtitle / Listen /
             scroll-hint), so the stats live as a full-width "film-poster" band
             immediately below it: big abbreviated magnitudes over an archival
             plate, with the year / detail as fine print. ── */}
      <section className="hist-numbers" aria-label="Key facts, by the numbers">
        <p className="hist-numbers__eyebrow">By the Numbers</p>
        <dl className="hist-numbers__grid" data-count={stats.length}>
          {stats.map((s) => (
            <div key={s.key} className={`hist-stat hist-stat--${s.variant}`}>
              <dt className="hist-stat__label">{s.label}</dt>
              <dd className="hist-stat__body">
                <span className="hist-stat__value">{s.value}</span>
                {s.fine && <span className="hist-stat__fine">{s.fine}</span>}
              </dd>
            </div>
          ))}
        </dl>
        {(cast || event.media.length > 0) && (
          <div className="hist-numbers__foot">
            {cast && (
              <p className="hist-numbers__cast">
                <span className="hist-numbers__cast-label">Key figures</span>
                <span className="hist-numbers__cast-names">{cast}</span>
              </p>
            )}
            {event.media.length > 0 && (
              <button
                type="button"
                className="hist-numbers__gallery"
                onClick={() =>
                  galleryRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
                }
              >
                Gallery <span className="hist-numbers__gallery-count">{event.media.length}</span>
              </button>
            )}
          </div>
        )}
      </section>

      {/* ── LEAD-IN — the vertical scroll flows into the horizontal reel ── */}
      <div className="hist-reel-leadin" aria-hidden="true">
        <span className="hist-reel-leadin__label">{perspectives.length} perspectives ahead</span>
        <span className="hist-reel-leadin__chevron" />
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

        {/* One-time discovery cue on the first frame */}
        {cueVisible && (
          <div
            className={`hist-reel__cue${isVertical ? " hist-reel__cue--vertical" : ""}`}
            aria-hidden="true"
          >
            <span className="hist-reel__cue-text">
              {isVertical ? "Swipe" : "Scroll"} to explore {perspectives.length} accounts
            </span>
            <span className="hist-reel__cue-chevron" />
          </div>
        )}

        {/* Desktop prev / next chevrons — hidden at the ends */}
        {!isVertical && (
          <>
            {focusedIndex > 0 && (
              <button
                type="button"
                className="hist-reel__nav-btn hist-reel__nav-btn--prev"
                onClick={() => goToFrame(focusedIndex - 1)}
                aria-label="Previous account"
              >
                &larr;
              </button>
            )}
            {focusedIndex < frameCount - 1 && (
              <button
                type="button"
                className="hist-reel__nav-btn hist-reel__nav-btn--next"
                onClick={() => goToFrame(focusedIndex + 1)}
                aria-label="Next account"
              >
                &rarr;
              </button>
            )}
          </>
        )}

        <ReelScrubber
          nodes={scrubNodes}
          activeIndex={focusedIndex}
          fraction={fraction}
          onSelect={goToFrame}
        />
      </section>

      {/* ── GALLERY — the archival evidence, promoted from the facts pill ── */}
      {event.media.length > 0 && (
        <section className="hist-gallery-section" id="gallery" ref={galleryRef}>
          <div className="hist-gallery-section__head">
            <h2 className="hist-gallery-section__title">Gallery</h2>
            <span className="hist-gallery-section__count">{event.media.length} items</span>
          </div>
          <MediaGallery media={event.media} onSelect={setEvidenceIndex} />
        </section>
      )}

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
