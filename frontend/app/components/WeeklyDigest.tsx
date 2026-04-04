"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import type {
  Edition,
  LeanChip,
  Category,
  WeeklyDigestData,
  WeeklyCoverStory,
  WeeklyRecapStory,
  WeeklyOpinion,
  WeeklyBiasReportData,
} from "../lib/types";
import { EDITIONS } from "../lib/types";
import { fetchWeeklyDigest, fetchWeeklyArchive } from "../lib/supabase";
import { leanLabel as getLeanLabel, getLeanColor } from "../lib/biasColors";
import Footer from "./Footer";
import MobileBottomNav from "./MobileBottomNav";
import ThemeToggle from "./ThemeToggle";
import LogoFull from "./LogoFull";

/* ---------------------------------------------------------------------------
   WeeklyDigest — void --weekly
   Dense broadsheet layout: 2-col / 3-col grids, no collapsibles.
   Deep red magazine palette. Everything visible, no "read more" toggles.
   --------------------------------------------------------------------------- */

/* ── Organic Ink SVG Components ────────────────────────────────────────────── */

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

/* ── Scroll-reveal wrapper for standalone InkFlourish ── */

function RevealFlourish() {
  const [ref, visible] = useScrollReveal(0.3);
  return (
    <div ref={ref as React.RefObject<HTMLDivElement>} className={`wk-reveal${visible ? " wk-reveal--visible" : ""}`}>
      <InkFlourish />
    </div>
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

function useScrollReveal(threshold = 0.15): [React.RefObject<HTMLElement | null>, boolean] {
  const ref = useRef<HTMLElement | null>(null);
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

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

function useCountUp(
  targetStr: string,
  trigger: boolean,
  duration = 1200
): { displayValue: string; isCounting: boolean } {
  const [displayValue, setDisplayValue] = useState(targetStr);
  const [isCounting, setIsCounting] = useState(false);

  useEffect(() => {
    if (!trigger) return;

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

/* ── Section Components ──────────────────────────────────────────────────── */

/* --- A. Masthead --- */

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
      <Link href="/" className="wk-masthead__home" aria-label="Return to void --news">
        <div className="wk-masthead__brand">
          {/* Full void logo with icon + "--weekly" wordmark */}
          <svg
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 380 40"
            fill="currentColor"
            role="img"
            aria-label="void --weekly"
            className="wk-masthead__logo"
          >
            {/* Icon — void circle + scale beam */}
            <g transform="translate(2,4) scale(0.83)" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M16 4 C24 3.5 25.5 7.5 25 13 C24.5 18.5 22.5 22 16 22 C9.5 22 7.5 18.5 7 13 C6.5 7.5 8 3.5 16 4" className="si-void" />
              <g className="si-beam--idle">
                <path d="M3 13 C10 12.2 22 13.8 29 13" />
                <line x1="5" y1="11" x2="5" y2="15" />
                <line x1="27" y1="11" x2="27" y2="15" />
              </g>
              <line x1="16" y1="22" x2="16" y2="29" />
              <path d="M12 29 C14 28.7 18 29.3 20 29" />
            </g>
            {/* "void" — bold serif */}
            <g transform="translate(36,2)">
              <polygon points="0,4 5.5,4 14,28 22.5,4 28,4 16.5,36 11.5,36" />
              <path d="M48 3.5 C61 3 62 10 61.5 20 C61 30 58 37 48 36.5 C38 37 35 30 34.5 20 C34 10 35 3 48 3.5" fill="none" stroke="currentColor" strokeWidth="2.2" />
              <rect x="69" y="2" width="5" height="5" rx="0.8" />
              <rect x="69.5" y="11" width="4" height="25" rx="0.5" />
              <path d="M82,20C82,10.5 87,3 94,3C97,3 100,4.5 102,7.5L102,0L107,0L107,36L102,36L102,32.5C100,35.5 97,37 94,37C87,37 82,29.5 82,20ZM88,20C88,27.5 90.8,32 95,32C98,32 100.5,29.5 102,26L102,14C100.5,10.5 98,8 95,8C90.8,8 88,12.5 88,20Z" />
              {/* "--weekly" — monospace letterforms */}
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
        </div>
      </Link>
      <p className="wk-masthead__meta">
        Issue #{issueNumber}
        <span className="wk-masthead__sep">&middot;</span>
        {formatWeekRange(weekStart, weekEnd)}
        <span className="wk-masthead__sep">&middot;</span>
        <span className="wk-masthead__edition">{editionLabel}</span>
      </p>
    </header>
  );
}

/* --- B. Cover Hero --- */

function CoverHero({
  headline,
}: {
  headline: string;
  issueNumber: number;
  sourceCount: number | null;
}) {
  return (
    <div className="wk-cover-hero wk-cold-open--hero">
      <div className="wk-cover-hero__content">
        <h2 className="wk-cover-hero__headline">{headline}</h2>
        <div className="wk-cover-hero__rule" aria-hidden="true">
          <svg viewBox="0 0 80 4" preserveAspectRatio="none">
            <path
              d="M0 2 C10 0.5, 20 3.5, 40 2 S60 0.5, 80 2"
              stroke="currentColor"
              strokeWidth="1.5"
              fill="none"
            />
          </svg>
        </div>
      </div>
    </div>
  );
}

/* --- C. Cover Body (text + numbers sidebar) --- */

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
    <div className="wk-cover-body__number-item">
      <dt className={`wk-cover-body__number-value${isCounting ? " wk-number-counting" : ""}`}>
        {displayValue}
      </dt>
      <dd className="wk-cover-body__number-label">{label}</dd>
    </div>
  );
}

function CoverBody({
  stories,
  topLevelNumbers,
}: {
  stories: WeeklyCoverStory[];
  topLevelNumbers: unknown;
}) {
  const [sectionRef, sectionVisible] = useScrollReveal(0.1);

  // Combine all cover story text
  const allText = stories
    .map((s) => s.text || "")
    .filter(Boolean);

  // Numbers: try first story's numbers, fall back to top-level
  const firstNums = parseCoverNumbers(stories[0]?.numbers);
  const numbers = firstNums.length > 0 ? firstNums : parseCoverNumbers(topLevelNumbers);

  // Timeline from first story
  const timeline = (stories[0]?.timeline ?? []) as Record<string, string>[];

  return (
    <section
      ref={sectionRef as React.RefObject<HTMLElement>}
      className={`wk-reveal${sectionVisible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-cover-heading"
    >
      {/* Show up to 2 cover stories */}
      {stories.slice(0, 2).map((story, si) => (
        <div key={si} className="wk-cover-body wk-cold-open--body">
          {si > 0 && <InkRule className="wk-ink-rule--strong" />}
          {si > 0 && <h3 className="wk-cover-body__subhead">{story.headline}</h3>}
          <div className="wk-cover-body__text">
            {(story.text || "").split("\n\n").filter(Boolean).map((para, j) => (
              <p key={`${si}-${j}`}>{para}</p>
            ))}
          </div>
        </div>
      ))}

      {/* Timeline — horizontal, full canvas width, below cover stories */}
      {timeline.length > 0 && (
        <div className="wk-timeline-section" aria-labelledby="wk-timeline-heading">
          <h3 className="wk-section-label" id="wk-timeline-heading">Timeline</h3>
          <div className="wk-timeline" role="list" aria-label="Key events">
            <InkHorizontalTrack />
            {timeline.map((entry, k) => (
              <TimelineNode key={k} entry={entry} index={k} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

/* --- D. Timeline --- */

function TimelineNode({
  entry,
  index,
}: {
  entry: Record<string, string>;
  index: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const dateText = entry.date || entry.day || "";
  const noteText = entry.title || entry.event || entry.note || entry.development || "";

  const sentences = noteText.split(/(?<=[.!?])\s+/);
  const summary = sentences[0] || noteText;
  const detail = sentences.length > 1 ? sentences.slice(1).join(" ") : "";
  const hasDetail = detail.length > 0;

  return (
    <div role="listitem">
      <button
        className={`wk-timeline__node${expanded ? " wk-timeline__node--expanded" : ""}`}
        onClick={() => hasDetail && setExpanded(!expanded)}
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
    </div>
  );
}

function TimelineSection({ timeline }: { timeline: Record<string, string>[] }) {
  const [isDesktop, setIsDesktop] = useState(false);
  const [ref, visible] = useScrollReveal(0.15);

  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
    setIsDesktop(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsDesktop(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  if (!timeline || timeline.length === 0) return null;

  return (
    <div
      ref={ref as React.RefObject<HTMLDivElement>}
      className={`wk-timeline-section wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-timeline-heading"
    >
      <h3 className="wk-section-label" id="wk-timeline-heading" data-prefix="void --">Timeline</h3>
      <div className="wk-timeline" role="list" aria-label="Key events">
        {isDesktop ? <InkHorizontalTrack /> : <InkVerticalTrack />}
        {timeline.map((entry, k) => (
          <TimelineNode key={k} entry={entry} index={k} />
        ))}
      </div>
    </div>
  );
}

/* --- E. Opinions --- */

function OpinionCard({ op }: { op: WeeklyOpinion }) {
  return (
    <article
      className="wk-opinion wk-reveal-child"
      style={{ "--lean-color": getLeanColor(leanToScore(op.lean)) } as React.CSSProperties}
    >
      <div className="wk-opinion__header">
        <span className="wk-opinion__badge">
          {leanBadgeLabel(op.lean)}
        </span>
        {op.topic && (
          <span className="wk-opinion__topic">{op.topic}</span>
        )}
      </div>
      <h3 className="wk-opinion__headline">{op.headline}</h3>
      <div className="wk-opinion__text">
        {(op.text || "").split("\n\n").filter(Boolean).map((para, j) => (
          <p key={j}>{para}</p>
        ))}
      </div>
    </article>
  );
}

function OpinionsSection({
  left,
  center,
  right,
}: {
  left: WeeklyOpinion[] | null;
  center: WeeklyOpinion[] | null;
  right: WeeklyOpinion[] | null;
}) {
  const [ref, visible] = useScrollReveal(0.1);
  // One per lean — pick the first from each bucket
  const picks: WeeklyOpinion[] = [];
  if (left && left.length > 0) picks.push(left[0]);
  if (center && center.length > 0) picks.push(center[0]);
  if (right && right.length > 0) picks.push(right[0]);
  if (picks.length === 0) return null;

  return (
    <section
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-opinions-section wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-opinions-heading"
    >
      <h2 className="wk-section-label" id="wk-opinions-heading" data-prefix="void --">Perspectives</h2>
      <div className="wk-opinions__grid">
        {picks.map((op, i) => (
          <OpinionCard key={i} op={op} />
        ))}
      </div>
    </section>
  );
}

/* --- F. Week in Brief --- */

function BriefList({ stories }: { stories: WeeklyRecapStory[] }) {
  const [ref, visible] = useScrollReveal(0.1);
  if (stories.length === 0) return null;

  return (
    <section
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-brief-section wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-brief-heading"
    >
      <h2 className="wk-section-label" id="wk-brief-heading" data-prefix="void --">Week in Brief</h2>
      <div className="wk-brief__list">
        {stories.map((story, i) => (
          <article key={i} className="wk-brief__item">
            <h3 className="wk-brief__headline">{story.headline}</h3>
            <p className="wk-brief__summary">{story.summary}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

/* --- G. Bias Report --- */

function BiasStats({
  text,
  data,
}: {
  text: string | null;
  data: WeeklyBiasReportData | null;
}) {
  const [ref, visible] = useScrollReveal(0.1);
  if (!text && !data) return null;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const rawData = data as Record<string, any> | null;
  const agg = rawData?.aggregate ?? rawData?.stats ?? null;
  const rawPolarized = rawData?.most_polarized ?? [];
  const polarized = rawPolarized.map(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (item: any) => ({
      headline: item.headline ?? item.title ?? "",
      lean_spread: item.lean_spread ?? item.divergence ?? 0,
      avg_lean: item.avg_lean ?? 50,
    })
  );

  return (
    <section
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-bias-section wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-bias-heading"
    >
      <h2 className="wk-section-label" id="wk-bias-heading" data-prefix="void --">Bias Report</h2>

      {agg && (
        <div className="wk-bias__aggregate">
          <div className="wk-bias__stat">
            <span className="wk-bias__stat-value">{agg.total_articles ?? agg.total_scored ?? 0}</span>
            <span className="wk-bias__stat-label">Articles</span>
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
            <span className="wk-bias__stat-label">Sensationalism</span>
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
    </section>
  );
}

/* --- H. Audio Player --- */

function AudioBar({
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
  const [audioError, setAudioError] = useState(false);

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
    <section className="wk-audio-section" aria-labelledby="wk-audio-heading">
      <h2 className="wk-section-label" id="wk-audio-heading" data-prefix="void --">On Air</h2>
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
          onError={() => setAudioError(true)}
        />
        <button
          className={`wk-audio__play${isPlaying ? " wk-audio__play--active" : ""}${audioError ? " wk-audio__play--disabled" : ""}`}
          onClick={handlePlayPause}
          aria-label={audioError ? "Audio unavailable" : isPlaying ? "Pause" : "Play"}
          type="button"
          disabled={audioError}
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
          {audioError ? (
            <span className="wk-audio__error">Audio unavailable</span>
          ) : (
            <>
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
            </>
          )}
        </div>
      </div>
    </section>
  );
}

/* --- I. Issue Archive --- */

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
            <span className="wk-archive__issue">#{entry.issue_number}</span>
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
  const router = useRouter();
  const [activeEdition, setActiveEdition] = useState<Edition>(edition);
  const [digest, setDigest] = useState<WeeklyDigestData | null>(null);
  const [archive, setArchive] = useState<ArchiveEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mainRef = useRef<HTMLElement>(null);
  const [isMobile, setIsMobile] = useState(false);

  // Unused by weekly but required by MobileBottomNav interface
  const [activeLean, setActiveLean] = useState<LeanChip>("All");
  const [activeCategory, setActiveCategory] = useState<"All" | Category>("All");

  // Sync edition state with prop (route changes re-mount with new prop)
  useEffect(() => {
    setActiveEdition(edition);
  }, [edition]);

  // Detect mobile for bottom nav
  useEffect(() => {
    const mql = window.matchMedia("(max-width: 767px)");
    setIsMobile(mql.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  // Handle edition change from MobileBottomNav
  const handleEditionChange = useCallback((ed: Edition) => {
    setActiveEdition(ed);
    router.push(ed === "world" ? "/weekly" : `/weekly/${ed}`);
  }, [router]);

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
      {/* Top bar: back to main + theme toggle */}
      <div className="wk-topbar">
        <Link href="/" className="wk-back" aria-label="Back to void --news">
          <span className="wk-back__arrow" aria-hidden="true">&larr;</span>
          <LogoFull height={20} className="wk-back__logo" />
        </Link>
        <ThemeToggle />
      </div>

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
            {/* A. Masthead */}
            <Masthead
              issueNumber={digest.issue_number}
              weekStart={digest.week_start}
              weekEnd={digest.week_end}
              edition={digest.edition}
            />

            {/* B. Cover Hero */}
            <CoverHero
              headline={digest.cover_headline || (digest.cover_text?.[0]?.headline ?? "")}
              issueNumber={digest.issue_number}
              sourceCount={digest.total_articles}
            />

            {/* C. Cover Body + Timeline sidebar */}
            {digest.cover_text && digest.cover_text.length > 0 && (
              <CoverBody
                stories={digest.cover_text}
                topLevelNumbers={digest.cover_numbers}
              />
            )}

            <RevealFlourish />

            {/* D. Opinions (1 per lean) */}
            <OpinionsSection
              left={digest.opinion_left}
              center={digest.opinion_center}
              right={digest.opinion_right}
            />

            <RevealFlourish />

            {/* E. Week in Brief */}
            <BriefList stories={digest?.recap_stories ?? []} />

            {/* F. Audio */}
            {digest.audio_url && (
              <>
                <InkRule />
                <AudioBar
                  audioUrl={digest.audio_url}
                  durationSeconds={digest.audio_duration_seconds}
                />
              </>
            )}

            <InkRule />

            {/* G. Archive */}
            <IssueArchive
              entries={archive}
              currentId={digest.id}
            />
          </>
        )}
      </main>

      <Footer />

      {/* Mobile bottom nav — filter buttons (editions moved to NavBar tabs) */}
      {isMobile && (
        <MobileBottomNav
          activeLean={activeLean}
          onLeanChange={setActiveLean}
          activeCategory={activeCategory}
          onCategoryChange={setActiveCategory}
        />
      )}
    </div>
  );
}
