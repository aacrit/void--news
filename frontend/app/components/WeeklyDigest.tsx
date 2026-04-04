"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import type {
  Edition,
  WeeklyDigestData,
  WeeklyCoverStory,
  WeeklyRecapStory,
  WeeklyOpinion,
  WeeklyBiasReportData,
} from "../lib/types";
import { EDITIONS } from "../lib/types";
import { fetchWeeklyDigest, fetchWeeklyArchive } from "../lib/supabase";
import { leanLabel as getLeanLabel, getLeanColor } from "../lib/biasColors";
import NavBar from "./NavBar";
import Footer from "./Footer";
import ScaleIcon from "./ScaleIcon";

/* ---------------------------------------------------------------------------
   WeeklyDigest — void --weekly
   Cinematic magazine-scroll layout. Single column, long-form reading.
   Slower, warmer, more editorial than the daily feed.
   Interactive timeline, count-up numbers, organic ink design, parallax.
   --------------------------------------------------------------------------- */

/* ── Organic Ink SVG Components ────────────────────────────────────────────── */

/** Hand-drawn horizontal rule — organic ink stroke with slight waviness */
function InkRule({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`wk-ink-rule ${className}`}
      viewBox="0 0 400 4"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d="M0 2 C20 0.5, 40 3.5, 80 2 S160 0.5, 200 2 S280 3.5, 320 2 S380 0.5, 400 2"
        stroke="currentColor"
        strokeWidth="1.2"
        fill="none"
        opacity="0.35"
      />
    </svg>
  );
}

/** Organic ink vertical track for timeline — slightly irregular vertical path */
function InkVerticalTrack() {
  return (
    <svg
      className="wk-timeline__ink-track"
      viewBox="0 0 4 400"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d="M2 0 C0.5 20, 3.5 40, 2 80 S0.5 160, 2 200 S3.5 280, 2 320 S0.5 380, 2 400"
        stroke="currentColor"
        strokeWidth="1.5"
        fill="none"
        opacity="0.25"
        strokeDasharray="8 4"
      />
    </svg>
  );
}

/** Organic ink horizontal track for desktop timeline */
function InkHorizontalTrack() {
  return (
    <svg
      className="wk-timeline__ink-track"
      viewBox="0 0 400 4"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d="M0 2 C20 0.5, 40 3.5, 80 2 S160 0.5, 200 2 S280 3.5, 320 2 S380 0.5, 400 2"
        stroke="currentColor"
        strokeWidth="1.5"
        fill="none"
        opacity="0.25"
        strokeDasharray="8 4"
      />
    </svg>
  );
}

/** Organic ink quotation mark — hand-drawn feel */
function InkQuoteMark() {
  return (
    <svg
      className="wk-ink-quote"
      viewBox="0 0 40 32"
      aria-hidden="true"
    >
      <path
        d="M6 24 C2 20, 1 14, 4 8 C6 4, 10 2, 14 2 C12 6, 10 10, 10 14 C14 14, 17 17, 17 21 C17 25, 14 28, 10 28 C8 28, 6.5 26, 6 24Z"
        fill="currentColor"
        opacity="0.5"
      />
      <path
        d="M26 24 C22 20, 21 14, 24 8 C26 4, 30 2, 34 2 C32 6, 30 10, 30 14 C34 14, 37 17, 37 21 C37 25, 34 28, 30 28 C28 28, 26.5 26, 26 24Z"
        fill="currentColor"
        opacity="0.5"
      />
    </svg>
  );
}

/** Organic ink left border — vertical wavey line for sidebar */
function InkLeftBorder() {
  return (
    <svg
      className="wk-ink-border"
      viewBox="0 0 4 200"
      preserveAspectRatio="none"
      aria-hidden="true"
    >
      <path
        d="M2 0 C0.5 10, 3.5 20, 2 40 S0.5 80, 2 100 S3.5 140, 2 160 S0.5 190, 2 200"
        stroke="currentColor"
        strokeWidth="2"
        fill="none"
        opacity="0.4"
      />
    </svg>
  );
}

/** Ink flourish ornament — plum diamond with radiating strokes, centered between sections */
function InkFlourish() {
  return (
    <div className="wk-flourish" aria-hidden="true">
      <svg
        className="wk-flourish__line"
        viewBox="0 0 80 2"
        preserveAspectRatio="none"
      >
        <path
          d="M0 1 C10 0.3, 20 1.7, 40 1 S60 0.3, 80 1"
          stroke="currentColor"
          strokeWidth="1"
          fill="none"
        />
      </svg>
      <svg
        className="wk-flourish__ornament"
        viewBox="0 0 20 20"
      >
        <path
          d="M10 2 L14 10 L10 18 L6 10 Z"
          fill="currentColor"
          opacity="0.6"
        />
        <path
          d="M2 10 C4 8, 6 9, 10 10 M10 10 C14 11, 16 12, 18 10"
          stroke="currentColor"
          strokeWidth="0.8"
          fill="none"
          opacity="0.35"
        />
        <path
          d="M10 2 C11 4, 9 6, 10 10 M10 10 C11 14, 9 16, 10 18"
          stroke="currentColor"
          strokeWidth="0.8"
          fill="none"
          opacity="0.35"
        />
      </svg>
      <svg
        className="wk-flourish__line"
        viewBox="0 0 80 2"
        preserveAspectRatio="none"
      >
        <path
          d="M0 1 C10 0.3, 20 1.7, 40 1 S60 0.3, 80 1"
          stroke="currentColor"
          strokeWidth="1"
          fill="none"
        />
      </svg>
    </div>
  );
}

/** Ink corner decoration — L-shaped organic brush strokes for hero section */
function InkCorner({ className = "" }: { className?: string }) {
  return (
    <svg
      className={`wk-cover__hero-corner ${className}`}
      viewBox="0 0 40 40"
      aria-hidden="true"
    >
      <path
        d="M2 38 C2 20, 3 10, 2 2"
        stroke="currentColor"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        opacity="0.5"
      />
      <path
        d="M2 2 C12 2, 22 3, 38 2"
        stroke="currentColor"
        strokeWidth="2"
        fill="none"
        strokeLinecap="round"
        opacity="0.5"
      />
      <circle
        cx="2"
        cy="2"
        r="2.5"
        fill="currentColor"
        opacity="0.4"
      />
    </svg>
  );
}

/* ── Formatting Helpers ────────────────────────────────────────────────────── */

function formatWeekRange(start: string, end: string): string {
  const s = new Date(start + "T00:00:00");
  const e = new Date(end + "T00:00:00");
  const sMonth = s.toLocaleDateString("en-US", { month: "long" });
  const eMonth = e.toLocaleDateString("en-US", { month: "long" });
  const sDay = s.getDate();
  const eDay = e.getDate();
  const eYear = e.getFullYear();

  if (sMonth === eMonth) {
    return `${sMonth} ${sDay}\u2009\u2013\u2009${eDay}, ${eYear}`;
  }
  return `${sMonth} ${sDay}\u2009\u2013\u2009${eMonth} ${eDay}, ${eYear}`;
}

function formatArchiveRange(start: string, end: string): string {
  const s = new Date(start + "T00:00:00");
  const e = new Date(end + "T00:00:00");
  return `${s.toLocaleDateString("en-US", { month: "short", day: "numeric" })}\u2013${e.toLocaleDateString("en-US", { month: "short", day: "numeric" })}`;
}

function leanBadgeClass(lean: string): string {
  const l = (lean || "center").toLowerCase().replace(/\s+/g, "-");
  return `wk-opinion__badge wk-opinion__badge--${l}`;
}

function leanBadgeLabel(lean: string): string {
  const map: Record<string, string> = {
    "left": "The Progressive",
    "center-left": "The Reformist",
    "center": "The Pragmatist",
    "center-right": "The Strategist",
    "right": "The Traditionalist",
    "far-left": "The Progressive",
    "far-right": "The Traditionalist",
  };
  return map[(lean || "center").toLowerCase()] ?? lean ?? "center";
}

function leanToScore(lean: string): number {
  const map: Record<string, number> = {
    "far-left": 10,
    "left": 28,
    "center-left": 40,
    "center": 50,
    "center-right": 60,
    "right": 73,
    "far-right": 90,
  };
  return map[(lean || "center").toLowerCase()] ?? 50;
}

/* ── Data Parsing ──────────────────────────────────────────────────────────── */

function parseCoverNumbers(
  raw: unknown
): { value: string; label: string }[] {
  if (!raw) return [];

  let arr: unknown[] = [];

  if (typeof raw === "string") {
    try {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) arr = parsed;
      else return [];
    } catch {
      return [];
    }
  } else if (Array.isArray(raw)) {
    arr = raw;
  } else {
    return [];
  }

  return arr
    .filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
    .map((item) => ({
      value: String(item.value ?? item.stat ?? ""),
      label: String(item.label ?? item.context ?? ""),
    }))
    .filter((n) => n.value !== "" && n.label !== "");
}

/* ── Scroll-Reveal Hook ────────────────────────────────────────────────────── */

/**
 * IntersectionObserver hook for scroll-triggered reveal animations.
 * Returns a ref to attach to the element and a boolean for visibility.
 */
function useScrollReveal(threshold = 0.15): [React.RefObject<HTMLElement | null>, boolean] {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // Check prefers-reduced-motion
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) {
      setVisible(true);
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.unobserve(el);
        }
      },
      { threshold }
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [threshold]);

  return [ref, visible];
}

/* ── Count-Up Animation Hook ───────────────────────────────────────────────── */

/**
 * Animates a number counting up from 0 to the target value when triggered.
 * Returns the current display value as a string.
 */
function useCountUp(
  targetStr: string,
  trigger: boolean,
  duration = 1200
): { displayValue: string; isCounting: boolean } {
  const [displayValue, setDisplayValue] = useState(targetStr);
  const [isCounting, setIsCounting] = useState(false);

  useEffect(() => {
    if (!trigger) return;

    // Extract numeric part from the value string
    const match = targetStr.match(/^([^0-9]*)([\d,.]+)(.*)$/);
    if (!match) {
      setDisplayValue(targetStr);
      return;
    }

    const prefix = match[1];
    const numStr = match[2];
    const suffix = match[3];
    const targetNum = parseFloat(numStr.replace(/,/g, ""));
    const hasCommas = numStr.includes(",");
    const hasDecimal = numStr.includes(".");
    const decimalPlaces = hasDecimal ? numStr.split(".")[1].length : 0;

    if (isNaN(targetNum) || targetNum === 0) {
      setDisplayValue(targetStr);
      return;
    }

    // Check prefers-reduced-motion
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) {
      setDisplayValue(targetStr);
      return;
    }

    setIsCounting(true);
    const startTime = performance.now();

    function animate(now: number) {
      const elapsed = now - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease-out: fast start, slow end
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = targetNum * eased;

      let formatted: string;
      if (hasDecimal) {
        formatted = current.toFixed(decimalPlaces);
      } else {
        formatted = Math.round(current).toString();
      }

      if (hasCommas) {
        const parts = formatted.split(".");
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
        formatted = parts.join(".");
      }

      setDisplayValue(`${prefix}${formatted}${suffix}`);

      if (progress < 1) {
        requestAnimationFrame(animate);
      } else {
        setDisplayValue(targetStr);
        setIsCounting(false);
      }
    }

    requestAnimationFrame(animate);
  }, [trigger, targetStr, duration]);

  return { displayValue, isCounting };
}

/* ── Parallax Hook ─────────────────────────────────────────────────────────── */

/**
 * Subtle parallax effect on scroll. Returns a ref and current transform offset.
 * Rate: how many pixels of offset per pixel of scroll (0.1 = subtle).
 */
function useParallax(rate = 0.08): [React.RefObject<HTMLElement | null>, number] {
  const ref = useRef<HTMLElement | null>(null);
  const [offset, setOffset] = useState(0);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    // Check prefers-reduced-motion
    const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReduced) return;

    // No parallax on mobile (performance)
    if (window.innerWidth < 768) return;

    let rafId: number;
    const handleScroll = () => {
      rafId = requestAnimationFrame(() => {
        const rect = el.getBoundingClientRect();
        const viewportCenter = window.innerHeight / 2;
        const elementCenter = rect.top + rect.height / 2;
        const delta = (elementCenter - viewportCenter) * rate;
        setOffset(delta);
      });
    };

    window.addEventListener("scroll", handleScroll, { passive: true });
    handleScroll();

    return () => {
      window.removeEventListener("scroll", handleScroll);
      cancelAnimationFrame(rafId);
    };
  }, [rate]);

  return [ref, offset];
}

/* ── Section Components ──────────────────────────────────────────────────── */

function Masthead({
  issueNumber,
  weekStart,
  weekEnd,
  edition,
}: {
  issueNumber: number;
  weekStart: string;
  weekEnd: string;
  edition: string;
}) {
  const editionLabel = EDITIONS.find((e) => e.slug === edition)?.label ?? "World";
  return (
    <header className="wk-masthead wk-cold-open--masthead">
      <InkRule className="wk-ink-rule--strong" />
      <div className="wk-masthead__brand">
        <ScaleIcon size={36} animation="idle" className="wk-masthead__icon" />
        <h1 className="wk-masthead__title">
          <svg
            className="wk-masthead__wordmark"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 360 40"
            fill="currentColor"
            role="img"
            aria-label="void --weekly"
          >
            <g transform="translate(0,2)">
              <polygon points="0,4 5.5,4 14,28 22.5,4 28,4 16.5,36 11.5,36" />
              <path
                d="M48 3.5 C61 3 62 10 61.5 20 C61 30 58 37 48 36.5 C38 37 35 30 34.5 20 C34 10 35 3 48 3.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
              />
              <rect x="69" y="2" width="5" height="5" rx="0.8" />
              <rect x="69.5" y="11" width="4" height="25" rx="0.5" />
              <path d="M82,20C82,10.5 87,3 94,3C97,3 100,4.5 102,7.5L102,0L107,0L107,36L102,36L102,32.5C100,35.5 97,37 94,37C87,37 82,29.5 82,20ZM88,20C88,27.5 90.8,32 95,32C98,32 100.5,29.5 102,26L102,14C100.5,10.5 98,8 95,8C90.8,8 88,12.5 88,20Z" />
              <rect x="122" y="17.5" width="10" height="3" rx="0.5" />
              <rect x="134" y="17.5" width="10" height="3" rx="0.5" />
              <path d="M156,12L159.5,12L164,29L168.5,14L171.5,14L176,29L180.5,12L184,12L177.5,36L174,36L169.5,21L165,36L161.5,36Z" />
              <path d="M190,23.5C190,17.5 193.5,11 200,11C206.5,11 209.5,17 209.5,23L209.5,24.5L193.5,24.5C193.8,29 196.5,33 200.5,33C203.5,33 205.5,31 206.8,29L209,30.5C207,33.5 204,36 200,36C194,36 190,30 190,23.5ZM193.5,22L206,22C205.5,17.5 203.5,14 200,14C196.5,14 194.2,17.5 193.5,22Z" />
              <path d="M216,23.5C216,17.5 219.5,11 226,11C232.5,11 235.5,17 235.5,23L235.5,24.5L219.5,24.5C219.8,29 222.5,33 226.5,33C229.5,33 231.5,31 232.8,29L235,30.5C233,33.5 230,36 226,36C220,36 216,30 216,23.5ZM219.5,22L232,22C231.5,17.5 229.5,14 226,14C222.5,14 220.2,17.5 219.5,22Z" />
              <path d="M242,0L245.2,0L245.2,22L254,12L258,12L250,21.5L259,36L255,36L248,24L245.2,27.5L245.2,36L242,36Z" />
              <rect x="264" y="0" width="3.2" height="36" rx="0.5" />
              <path d="M276,12L279.5,12L284.5,28L289.5,12L293,12L285,36L282.5,36L276.5,20Z" />
            </g>
          </svg>
        </h1>
      </div>
      <p className="wk-masthead__meta">
        Issue #{issueNumber}
        <span className="wk-masthead__sep">&mdash;</span>
        {formatWeekRange(weekStart, weekEnd)}
        <span className="wk-masthead__sep">&mdash;</span>
        <span className="wk-masthead__edition">{editionLabel} Edition</span>
      </p>
      <InkRule className="wk-ink-rule--strong" />
    </header>
  );
}

/* ── Interactive Numbers Sidebar ───────────────────────────────────────────── */

function NumberItem({
  value,
  label,
  visible,
  delay,
}: {
  value: string;
  label: string;
  visible: boolean;
  delay: number;
}) {
  const [triggerCount, setTriggerCount] = useState(false);
  const { displayValue, isCounting } = useCountUp(value, triggerCount, 1200 + delay);

  useEffect(() => {
    if (visible) {
      const timer = setTimeout(() => setTriggerCount(true), delay);
      return () => clearTimeout(timer);
    }
  }, [visible, delay]);

  return (
    <div className="wk-cover__number-item">
      <dt className={`wk-cover__number-value${isCounting ? " wk-number-counting" : ""}`}>
        {displayValue}
      </dt>
      <dd className="wk-cover__number-label">{label}</dd>
      <div className="wk-cover__number-tooltip" role="tooltip">
        {label}
      </div>
    </div>
  );
}

function NumbersSidebar({
  numbers,
}: {
  numbers: { value: string; label: string }[];
}) {
  const [sidebarRef, sidebarVisible] = useScrollReveal(0.3);

  if (numbers.length === 0) return null;

  return (
    <aside
      ref={sidebarRef as React.RefObject<HTMLElement>}
      className={`wk-cover__numbers wk-cold-open--numbers`}
      aria-label="This week in numbers"
    >
      <InkLeftBorder />
      <h4 className="wk-cover__numbers-title">This Week in Numbers</h4>
      <dl className="wk-cover__numbers-list">
        {numbers.map((n, k) => (
          <NumberItem
            key={k}
            value={n.value}
            label={n.label}
            visible={sidebarVisible}
            delay={k * 150}
          />
        ))}
      </dl>
    </aside>
  );
}

/* ── Interactive Timeline ──────────────────────────────────────────────────── */

function TimelineNode({
  entry,
  index,
}: {
  entry: Record<string, string>;
  index: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const dateText = entry.date || entry.day || "";
  const noteText = entry.event || entry.note || entry.development || "";

  // For expandable detail: show first sentence as summary, rest as detail
  const sentences = noteText.split(/(?<=[.!?])\s+/);
  const summary = sentences[0] || noteText;
  const detail = sentences.length > 1 ? sentences.slice(1).join(" ") : "";
  const hasDetail = detail.length > 0;

  return (
    <button
      className={`wk-timeline__node${expanded ? " wk-timeline__node--expanded" : ""}`}
      onClick={() => hasDetail && setExpanded(!expanded)}
      role="listitem"
      aria-expanded={hasDetail ? expanded : undefined}
      type="button"
      style={{ "--node-delay": `${index * 80}ms` } as React.CSSProperties}
    >
      <span className="wk-timeline__dot" aria-hidden="true" />
      <span className="wk-timeline__day">{dateText}</span>
      <span className="wk-timeline__note">{hasDetail ? summary : noteText}</span>
      {hasDetail && (
        <>
          <div className="wk-timeline__detail">
            <div className="wk-timeline__detail-inner">
              <p className="wk-timeline__detail-text">{detail}</p>
            </div>
          </div>
          <span className="wk-timeline__expand-hint">
            {expanded ? "Collapse" : "Expand"}
          </span>
        </>
      )}
    </button>
  );
}

function InteractiveTimeline({ timeline }: { timeline: Record<string, string>[] }) {
  const [isDesktop, setIsDesktop] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    setIsDesktop(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  if (!timeline || timeline.length === 0) return null;

  return (
    <div aria-labelledby="wk-timeline-heading">
      <h4 className="wk-timeline__heading" id="wk-timeline-heading">Key Events</h4>
      <div className="wk-timeline" role="list" aria-label="Key events">
        {isDesktop ? <InkHorizontalTrack /> : <InkVerticalTrack />}
        {timeline.map((entry, k) => (
          <TimelineNode key={k} entry={entry} index={k} />
        ))}
      </div>
    </div>
  );
}

/* ── Cover Story Card ──────────────────────────────────────────────────────── */

function CoverStoryCard({
  story,
  numbers,
  defaultExpanded,
  isFirst,
}: {
  story: WeeklyCoverStory;
  numbers: { value: string; label: string }[];
  defaultExpanded: boolean;
  isFirst: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const previewText = (story.text || "").slice(0, 200).replace(/\s+\S*$/, "");
  const [parallaxRef, parallaxOffset] = useParallax(0.06);

  const inner = (
    <article className="wk-cover__story">
      <h3
        ref={isFirst ? (parallaxRef as React.RefObject<HTMLHeadingElement>) : undefined}
        className={`wk-cover__headline${isFirst ? " wk-cold-open--headline" : ""}`}
        style={isFirst ? { transform: `translateY(${parallaxOffset}px)` } : undefined}
      >
        {story.headline}
      </h3>
      <div className={`wk-collapsible${expanded ? " wk-collapsible--open" : ""}`}>
        <div className="wk-collapsible__inner">
          {!expanded && (
            <div className="wk-cover__preview">
              <p>{previewText}...</p>
              <div className="wk-cover__preview-fade" aria-hidden="true" />
            </div>
          )}
          {expanded && (
            <>
              <div className={`wk-cover__body-wrap${isFirst ? " wk-cold-open--body" : ""}`}>
                <div className="wk-cover__text">
                  {(story.text || "").split("\n\n").filter(Boolean).map((para, j) => (
                    <p key={j}>{para}</p>
                  ))}
                </div>
                <NumbersSidebar numbers={numbers} />
              </div>
              <InteractiveTimeline
                timeline={story.timeline as Record<string, string>[] ?? []}
              />
            </>
          )}
        </div>
      </div>
      <button
        className="wk-toggle"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        type="button"
      >
        {expanded ? "Read less" : "Read more"}{" "}
        <span className="wk-toggle__chevron" aria-hidden="true">
          {expanded ? "\u25B2" : "\u25BC"}
        </span>
      </button>
    </article>
  );

  /* Wrap the first cover story in a hero treatment with ink corner flourishes */
  if (isFirst) {
    return (
      <div className="wk-cover__hero">
        <InkCorner className="wk-cover__hero-corner--tl" />
        <InkCorner className="wk-cover__hero-corner--br" />
        {inner}
      </div>
    );
  }

  return inner;
}

/* ── Cover Section ─────────────────────────────────────────────────────────── */

function CoverSection({
  stories,
  topLevelNumbers,
}: {
  stories: WeeklyCoverStory[];
  topLevelNumbers: unknown;
}) {
  const firstStory = stories[0];
  const secondaryStories = stories.slice(1);
  const firstNums = parseCoverNumbers(firstStory?.numbers);
  const firstNumbers = firstNums.length > 0
    ? firstNums
    : parseCoverNumbers(topLevelNumbers);

  return (
    <section className="wk-cover" aria-labelledby="wk-cover-heading">
      <h2 className="wk-section-label" id="wk-cover-heading" data-prefix="void --">The Cover</h2>
      {firstStory && (
        <CoverStoryCard
          story={firstStory}
          numbers={firstNumbers}
          defaultExpanded={true}
          isFirst={true}
        />
      )}
      {secondaryStories.length > 0 && (
        <>
          <InkRule />
          <div className="wk-cover__secondary">
            {secondaryStories.map((story, i) => {
              const storyNums = parseCoverNumbers(story.numbers);
              return (
                <CoverStoryCard
                  key={i}
                  story={story}
                  numbers={storyNums}
                  defaultExpanded={false}
                  isFirst={false}
                />
              );
            })}
          </div>
        </>
      )}
    </section>
  );
}

/* ── Opinion Card ──────────────────────────────────────────────────────────── */

function OpinionCard({ op }: { op: WeeklyOpinion }) {
  const [expanded, setExpanded] = useState(false);
  const safeText = op.text || "";
  const previewText = safeText.slice(0, 120).replace(/\s+\S*$/, "");
  const needsTruncation = safeText.length > 140;

  return (
    <article className="wk-opinion wk-reveal-child">
      <div className="wk-opinion__header">
        <span
          className={leanBadgeClass(op.lean)}
          style={{ "--lean-color": getLeanColor(leanToScore(op.lean)) } as React.CSSProperties}
        >
          {leanBadgeLabel(op.lean)}
        </span>
        {op.topic && (
          <span className="wk-opinion__topic">{op.topic}</span>
        )}
      </div>
      <h3 className="wk-opinion__headline">{op.headline}</h3>
      <div className={`wk-opinion__text${!expanded && needsTruncation ? " wk-opinion__text--clamped" : ""}`}>
        {expanded ? (
          (op.text || "").split("\n\n").filter(Boolean).map((para, j) => (
            <p key={j}>{para}</p>
          ))
        ) : (
          <p>{needsTruncation ? `${previewText}...` : op.text}</p>
        )}
        {!expanded && needsTruncation && (
          <div className="wk-opinion__text-fade" aria-hidden="true" />
        )}
      </div>
      {needsTruncation && (
        <button
          className="wk-toggle wk-toggle--inline"
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
          type="button"
        >
          {expanded ? "Read less" : "Read more"}{" "}
          <span className="wk-toggle__chevron" aria-hidden="true">
            {expanded ? "\u25B2" : "\u25BC"}
          </span>
        </button>
      )}
    </article>
  );
}

/* ── Collapsible Section with Scroll Reveal ────────────────────────────────── */

function CollapsibleSection({
  id,
  label,
  defaultOpen,
  children,
}: {
  id: string;
  label: string;
  defaultOpen: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const [sectionRef, sectionVisible] = useScrollReveal(0.1);

  return (
    <section
      ref={sectionRef as React.RefObject<HTMLElement>}
      className={`wk-collapsible-section wk-reveal${sectionVisible ? " wk-reveal--visible" : ""}`}
      aria-labelledby={id}
    >
      <button
        className="wk-section-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        type="button"
      >
        <h2 className="wk-section-label wk-section-label--toggle" id={id} data-prefix="void --">
          {label}
        </h2>
        <span className="wk-section-toggle__chevron" aria-hidden="true">
          {open ? "\u25B2" : "\u25BC"}
        </span>
      </button>
      <div className={`wk-section-body${open ? " wk-section-body--open" : ""}`}>
        <div className="wk-section-body__inner">
          {children}
        </div>
      </div>
    </section>
  );
}

/* ── Opinions Section ──────────────────────────────────────────────────────── */

function OpinionsSection({
  left,
  center,
  right,
}: {
  left: WeeklyOpinion[] | null;
  center: WeeklyOpinion[] | null;
  right: WeeklyOpinion[] | null;
}) {
  const all = [
    ...(left ?? []),
    ...(center ?? []),
    ...(right ?? []),
  ];
  if (all.length === 0) return null;

  return (
    <div className="wk-section--opinions">
      <CollapsibleSection id="wk-opinions-heading" label="The Opinions" defaultOpen={true}>
        <div className="wk-opinions__grid">
          {all.map((op, i) => (
            <OpinionCard key={i} op={op} />
          ))}
        </div>
      </CollapsibleSection>
    </div>
  );
}

/* ── Special Section ───────────────────────────────────────────────────────── */

function SpecialSection({
  story,
  sectionType,
}: {
  story: WeeklyRecapStory;
  sectionType: "tech" | "sports";
}) {
  const label = sectionType === "tech" ? "Tech Brief" : "Sports Page";
  const id = `wk-${sectionType}-heading`;
  const [ref, visible] = useScrollReveal(0.15);

  return (
    <section
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-special wk-special--${sectionType} wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby={id}
    >
      <h2 className="wk-section-label" id={id} data-prefix="void --">{label}</h2>
      <article className={`wk-special__card wk-special__card--${sectionType}`}>
        <h3 className="wk-special__headline">{story.headline}</h3>
        <p className="wk-special__summary">{story.summary}</p>
      </article>
    </section>
  );
}

/* ── Bias Report ───────────────────────────────────────────────────────────── */

function BiasReport({
  text,
  data,
}: {
  text: string | null;
  data: WeeklyBiasReportData | null;
}) {
  if (!text && !data) return null;

  // Pipeline stores aggregate stats under "stats"; type expects "aggregate".
  // Normalize field names defensively so both shapes work.
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const rawData = data as Record<string, any> | null;
  const agg = rawData?.aggregate ?? rawData?.stats ?? null;
  const rawPolarized = rawData?.most_polarized ?? [];
  // Pipeline items use { title, divergence }; type expects { headline, lean_spread, avg_lean }.
  const polarized = rawPolarized.map(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (item: any) => ({
      headline: item.headline ?? item.title ?? "",
      lean_spread: item.lean_spread ?? item.divergence ?? 0,
      avg_lean: item.avg_lean ?? 50,
    })
  );

  return (
    <CollapsibleSection id="wk-bias-heading" label="Bias Report" defaultOpen={true}>
      {agg && (
        <div className="wk-bias__aggregate">
          <div className="wk-bias__stat">
            <span className="wk-bias__stat-value">{agg.total_articles ?? agg.total_scored ?? 0}</span>
            <span className="wk-bias__stat-label">Articles Analyzed</span>
          </div>
          <div className="wk-bias__stat">
            <span className="wk-bias__stat-value">{(agg.avg_lean ?? 0).toFixed(1)}</span>
            <span className="wk-bias__stat-label">Avg. Lean</span>
            <span className="wk-bias__stat-note">{getLeanLabel(agg.avg_lean ?? 50)}</span>
          </div>
          <div className="wk-bias__stat">
            <span className="wk-bias__stat-value">{(agg.avg_rigor ?? 0).toFixed(1)}</span>
            <span className="wk-bias__stat-label">Avg. Rigor</span>
          </div>
          <div className="wk-bias__stat">
            <span className="wk-bias__stat-value">{(agg.avg_sensationalism ?? 0).toFixed(1)}</span>
            <span className="wk-bias__stat-label">Avg. Sensationalism</span>
          </div>
        </div>
      )}

      {polarized.length > 0 && (
        <div className="wk-bias__polarized">
          <h3 className="wk-bias__sub-heading">Most Polarized Stories</h3>
          {polarized.map((story: { headline: string; lean_spread: number; avg_lean: number }, i: number) => (
            <div key={i} className="wk-bias__bar-row">
              <span className="wk-bias__bar-label">{story.headline}</span>
              <div className="wk-bias__bar-track">
                <div
                  className="wk-bias__bar-fill"
                  style={{
                    width: `${Math.min(100, story.lean_spread)}%`,
                    backgroundColor: getLeanColor(story.avg_lean),
                  }}
                  aria-label={`Lean spread: ${story.lean_spread.toFixed(0)}`}
                />
                <span className="wk-bias__bar-value">
                  {story.lean_spread.toFixed(0)}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}

      {text && (
        <div className="wk-bias__text">
          {(text || "").split("\n\n").filter(Boolean).map((para, i) => (
            <p key={i}>{para}</p>
          ))}
        </div>
      )}
    </CollapsibleSection>
  );
}

/* ── Week in Brief ─────────────────────────────────────────────────────────── */

function WeekInBrief({ stories }: { stories: WeeklyRecapStory[] }) {
  if (stories.length === 0) return null;

  return (
    <CollapsibleSection id="wk-brief-heading" label="Week in Brief" defaultOpen={true}>
      <div className="wk-brief__list">
        {stories.map((story, i) => (
          <article key={i} className="wk-brief__item">
            <h3 className="wk-brief__headline">{story.headline}</h3>
            <p className="wk-brief__summary">{story.summary}</p>
          </article>
        ))}
      </div>
    </CollapsibleSection>
  );
}

/* ── Audio Player ──────────────────────────────────────────────────────────── */

function WeeklyAudioPlayer({
  audioUrl,
  durationSeconds,
}: {
  audioUrl: string;
  durationSeconds: number | null;
}) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(durationSeconds ?? 0);

  const handlePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) {
      audio.pause();
    } else {
      audio.play().catch(() => {});
    }
  }, [isPlaying]);

  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;
    const t = parseFloat(e.target.value);
    audio.currentTime = t;
    setCurrentTime(t);
  }, []);

  const formatTime = (s: number): string => {
    const mins = Math.floor(s / 60);
    const secs = Math.floor(s % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <CollapsibleSection
      id="wk-audio-heading"
      label="On Air"
      defaultOpen={true}
    >
      <div className="wk-audio__player">
        <audio
          ref={audioRef}
          src={audioUrl}
          preload="metadata"
          onLoadedMetadata={() => {
            if (audioRef.current) setDuration(audioRef.current.duration);
          }}
          onTimeUpdate={() => {
            if (audioRef.current) setCurrentTime(audioRef.current.currentTime);
          }}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
          onEnded={() => setIsPlaying(false)}
        />
        <button
          className={`wk-audio__play${isPlaying ? " wk-audio__play--active" : ""}`}
          onClick={handlePlayPause}
          aria-label={isPlaying ? "Pause" : "Play"}
          type="button"
        >
          {isPlaying ? (
            <svg width="14" height="16" viewBox="0 0 14 16" fill="currentColor" aria-hidden="true">
              <rect x="1" y="1" width="4" height="14" rx="1" />
              <rect x="9" y="1" width="4" height="14" rx="1" />
            </svg>
          ) : (
            <svg width="14" height="16" viewBox="0 0 14 16" fill="currentColor" aria-hidden="true">
              <path d="M2 1.5v13l11-6.5z" />
            </svg>
          )}
        </button>
        <div className="wk-audio__controls">
          <input
            type="range"
            className="wk-audio__scrubber"
            min={0}
            max={duration || 1}
            step={0.1}
            value={currentTime}
            onChange={handleSeek}
            aria-label="Seek"
          />
          <div className="wk-audio__time">
            <span>{formatTime(currentTime)}</span>
            <span>{formatTime(duration)}</span>
          </div>
        </div>
      </div>
    </CollapsibleSection>
  );
}

/* ── Issue Archive ─────────────────────────────────────────────────────────── */

interface ArchiveEntry {
  id: string;
  edition: string;
  week_start: string;
  week_end: string;
  issue_number: number;
  cover_headline: string;
  created_at: string;
}

function IssueArchive({
  entries,
  currentId,
}: {
  entries: ArchiveEntry[];
  currentId: string;
}) {
  const [ref, visible] = useScrollReveal(0.15);

  if (entries.length <= 1) return null;

  return (
    <section
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-archive wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-archive-heading"
    >
      <h2 className="wk-section-label" id="wk-archive-heading" data-prefix="void --">Issue Archive</h2>
      <div className="wk-archive__list">
        {entries.map((entry) => (
          <div
            key={entry.id}
            className={`wk-archive__item${entry.id === currentId ? " wk-archive__item--current" : ""}`}
          >
            <span className="wk-archive__issue">Issue #{entry.issue_number}</span>
            <span className="wk-archive__range">
              {formatArchiveRange(entry.week_start, entry.week_end)}
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ── Main Component ──────────────────────────────────────────────────────── */

interface WeeklyDigestProps {
  edition: Edition;
}

export default function WeeklyDigest({ edition }: WeeklyDigestProps) {
  const [digest, setDigest] = useState<WeeklyDigestData | null>(null);
  const [archive, setArchive] = useState<ArchiveEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mainRef = useRef<HTMLElement>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      fetchWeeklyDigest(edition),
      fetchWeeklyArchive(edition),
    ]).then(([digestData, archiveData]) => {
      if (cancelled) return;
      if (!digestData) {
        setError("No weekly digest available yet. Check back soon.");
      } else {
        setDigest(digestData as WeeklyDigestData);
      }
      setArchive(archiveData as ArchiveEntry[]);
      setLoading(false);
    }).catch(() => {
      if (!cancelled) {
        setError("Unable to load the weekly digest.");
        setLoading(false);
      }
    });

    return () => { cancelled = true; };
  }, [edition]);

  return (
    <div className="wk-page">
      <NavBar activeEdition={edition} />

      <main
        ref={mainRef}
        id="main-content"
        className="wk-main"
      >
        {loading && (
          <div className="wk-loading" aria-live="polite">
            <div className="wk-loading__bar" />
            <p className="wk-loading__text">Loading weekly digest...</p>
          </div>
        )}

        {error && !loading && (
          <div className="wk-empty" role="status">
            <p className="wk-empty__text">{error}</p>
            <Link href="/" className="wk-empty__link">
              Return to void --news
            </Link>
          </div>
        )}

        {digest && !loading && (
          <>
            <Masthead
              issueNumber={digest.issue_number}
              weekStart={digest.week_start}
              weekEnd={digest.week_end}
              edition={digest.edition}
            />

            {digest.cover_text && digest.cover_text.length > 0 && (
              <CoverSection
                stories={digest.cover_text}
                topLevelNumbers={digest.cover_numbers}
              />
            )}

            <InkFlourish />

            <OpinionsSection
              left={digest.opinion_left}
              center={digest.opinion_center}
              right={digest.opinion_right}
            />

            <InkFlourish />

            <div className="wk-section--cream">
              <BiasReport
                text={digest.bias_report_text}
                data={digest.bias_report_data}
              />
            </div>

            <InkRule />

            <WeekInBrief stories={digest?.recap_stories ?? []} />

            {digest.audio_url && (
              <>
                <InkRule />
                <WeeklyAudioPlayer
                  audioUrl={digest.audio_url}
                  durationSeconds={digest.audio_duration_seconds}
                />
              </>
            )}

            <InkRule />

            <IssueArchive
              entries={archive}
              currentId={digest.id}
            />
          </>
        )}
      </main>

      <Footer />
    </div>
  );
}
