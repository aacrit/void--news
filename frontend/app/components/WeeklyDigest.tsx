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
   Magazine-scroll layout. Single column, long-form reading experience.
   Slower, warmer, more editorial than the daily feed.
   --------------------------------------------------------------------------- */

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
  const l = lean.toLowerCase().replace(/\s+/g, "-");
  return `wk-opinion__badge wk-opinion__badge--${l}`;
}

function leanBadgeLabel(lean: string): string {
  // Map lean values to editorial voice persona names (matches daily brief pattern)
  const map: Record<string, string> = {
    "left": "The Progressive",
    "center-left": "The Reformist",
    "center": "The Pragmatist",
    "center-right": "The Strategist",
    "right": "The Traditionalist",
    "far-left": "The Progressive",
    "far-right": "The Traditionalist",
  };
  return map[lean.toLowerCase()] ?? lean;
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
  return map[lean.toLowerCase()] ?? 50;
}

/* ── Helpers ─────────────────────────────────────────────────────────────── */

/**
 * Normalize cover numbers from pipeline data.
 * Pipeline may send {stat, context} or {value, label} format,
 * and the data may be a JSON string (double-encoded) or already parsed.
 */
function parseCoverNumbers(
  raw: unknown
): { value: string; label: string }[] {
  if (!raw) return [];

  let arr: unknown[] = [];

  // Handle double-encoded JSON strings
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

  // Normalize each item: accept {stat, context} OR {value, label}
  return arr
    .filter((item): item is Record<string, unknown> => !!item && typeof item === "object")
    .map((item) => ({
      value: String(item.value ?? item.stat ?? ""),
      label: String(item.label ?? item.context ?? ""),
    }))
    .filter((n) => n.value !== "" && n.label !== "");
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
    <header className="wk-masthead">
      <div className="wk-masthead__rule" aria-hidden="true" />
      <div className="wk-masthead__brand">
        <ScaleIcon size={36} animation="idle" className="wk-masthead__icon" />
        <h1 className="wk-masthead__title">
          {/* "void" — bold serif letterforms with hollow O, matching LogoFull SVG */}
          <svg
            className="wk-masthead__wordmark"
            xmlns="http://www.w3.org/2000/svg"
            viewBox="0 0 360 40"
            fill="currentColor"
            role="img"
            aria-label="void --weekly"
          >
            <g transform="translate(0,2)">
              {/* "v" */}
              <polygon points="0,4 5.5,4 14,28 22.5,4 28,4 16.5,36 11.5,36" />
              {/* "o" — THE VOID: hollow outline */}
              <path
                d="M48 3.5 C61 3 62 10 61.5 20 C61 30 58 37 48 36.5 C38 37 35 30 34.5 20 C34 10 35 3 48 3.5"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
              />
              {/* "i" */}
              <rect x="69" y="2" width="5" height="5" rx="0.8" />
              <rect x="69.5" y="11" width="4" height="25" rx="0.5" />
              {/* "d" */}
              <path d="M82,20C82,10.5 87,3 94,3C97,3 100,4.5 102,7.5L102,0L107,0L107,36L102,36L102,32.5C100,35.5 97,37 94,37C87,37 82,29.5 82,20ZM88,20C88,27.5 90.8,32 95,32C98,32 100.5,29.5 102,26L102,14C100.5,10.5 98,8 95,8C90.8,8 88,12.5 88,20Z" />
              {/* "--weekly" — lighter monospace letterforms */}
              <rect x="122" y="17.5" width="10" height="3" rx="0.5" />
              <rect x="134" y="17.5" width="10" height="3" rx="0.5" />
              {/* "w" */}
              <path d="M156,12L159.5,12L164,29L168.5,14L171.5,14L176,29L180.5,12L184,12L177.5,36L174,36L169.5,21L165,36L161.5,36Z" />
              {/* "e" */}
              <path d="M190,23.5C190,17.5 193.5,11 200,11C206.5,11 209.5,17 209.5,23L209.5,24.5L193.5,24.5C193.8,29 196.5,33 200.5,33C203.5,33 205.5,31 206.8,29L209,30.5C207,33.5 204,36 200,36C194,36 190,30 190,23.5ZM193.5,22L206,22C205.5,17.5 203.5,14 200,14C196.5,14 194.2,17.5 193.5,22Z" />
              {/* "e" */}
              <path d="M216,23.5C216,17.5 219.5,11 226,11C232.5,11 235.5,17 235.5,23L235.5,24.5L219.5,24.5C219.8,29 222.5,33 226.5,33C229.5,33 231.5,31 232.8,29L235,30.5C233,33.5 230,36 226,36C220,36 216,30 216,23.5ZM219.5,22L232,22C231.5,17.5 229.5,14 226,14C222.5,14 220.2,17.5 219.5,22Z" />
              {/* "k" */}
              <path d="M242,0L245.2,0L245.2,22L254,12L258,12L250,21.5L259,36L255,36L248,24L245.2,27.5L245.2,36L242,36Z" />
              {/* "l" */}
              <rect x="264" y="0" width="3.2" height="36" rx="0.5" />
              {/* "y" */}
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
      <div className="wk-masthead__rule" aria-hidden="true" />
    </header>
  );
}

function CoverStoryCard({
  story,
  numbers,
  defaultExpanded,
}: {
  story: WeeklyCoverStory;
  numbers: { value: string; label: string }[];
  defaultExpanded: boolean;
}) {
  const [expanded, setExpanded] = useState(defaultExpanded);
  const previewText = story.text.slice(0, 200).replace(/\s+\S*$/, "");

  return (
    <article className="wk-cover__story">
      <h3 className="wk-cover__headline">{story.headline}</h3>
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
              <div className="wk-cover__body-wrap">
                <div className="wk-cover__text">
                  {story.text.split("\n\n").map((para, j) => (
                    <p key={j}>{para}</p>
                  ))}
                </div>
                {numbers.length > 0 && (
                  <aside className="wk-cover__numbers" aria-label="This week in numbers">
                    <h4 className="wk-cover__numbers-title">This Week in Numbers</h4>
                    <dl className="wk-cover__numbers-list">
                      {numbers.map((n, k) => (
                        <div key={k} className="wk-cover__number-item">
                          <dt className="wk-cover__number-value">{n.value}</dt>
                          <dd className="wk-cover__number-label">{n.label}</dd>
                        </div>
                      ))}
                    </dl>
                  </aside>
                )}
              </div>
              {story.timeline && story.timeline.length > 0 && (
                <div className="wk-timeline" role="list" aria-label="Key events">
                  <h4 className="wk-timeline__heading">Key Events</h4>
                  <div className="wk-timeline__track" aria-hidden="true" />
                  {story.timeline.map((entry, k) => (
                    <div key={k} className="wk-timeline__node" role="listitem">
                      <span className="wk-timeline__dot" aria-hidden="true" />
                      <span className="wk-timeline__day">{(entry as Record<string, string>).date || (entry as Record<string, string>).day || ""}</span>
                      <span className="wk-timeline__note">{(entry as Record<string, string>).event || (entry as Record<string, string>).note || (entry as Record<string, string>).development || ""}</span>
                    </div>
                  ))}
                </div>
              )}
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
}

function CoverSection({
  stories,
  topLevelNumbers,
}: {
  stories: WeeklyCoverStory[];
  topLevelNumbers: unknown;
}) {
  return (
    <section className="wk-cover" aria-labelledby="wk-cover-heading">
      <h2 className="wk-section-label" id="wk-cover-heading">The Cover</h2>
      {stories.map((story, i) => {
        const storyNums = parseCoverNumbers(story.numbers);
        const numbers = storyNums.length > 0
          ? storyNums
          : (i === 0 ? parseCoverNumbers(topLevelNumbers) : []);
        return (
          <div key={i}>
            <CoverStoryCard
              story={story}
              numbers={numbers}
              defaultExpanded={false}
            />
            {i < stories.length - 1 && (
              <hr className="wk-divider" aria-hidden="true" />
            )}
          </div>
        );
      })}
    </section>
  );
}

function OpinionCard({ op }: { op: WeeklyOpinion }) {
  const [expanded, setExpanded] = useState(false);
  const previewText = op.text.slice(0, 120).replace(/\s+\S*$/, "");
  const needsTruncation = op.text.length > 140;

  return (
    <article className="wk-opinion">
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
          op.text.split("\n\n").map((para, j) => (
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

  return (
    <section className="wk-collapsible-section" aria-labelledby={id}>
      <button
        className="wk-section-toggle"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        type="button"
      >
        <h2 className="wk-section-label wk-section-label--toggle" id={id}>
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
    <CollapsibleSection id="wk-opinions-heading" label="The Opinions" defaultOpen={true}>
      <div className="wk-opinions__grid">
        {all.map((op, i) => (
          <OpinionCard key={i} op={op} />
        ))}
      </div>
    </CollapsibleSection>
  );
}

function SpecialSection({
  story,
  sectionType,
}: {
  story: WeeklyRecapStory;
  sectionType: "tech" | "sports";
}) {
  const label = sectionType === "tech" ? "Tech Brief" : "Sports Page";
  const id = `wk-${sectionType}-heading`;

  return (
    <section className={`wk-special wk-special--${sectionType}`} aria-labelledby={id}>
      <h2 className="wk-section-label" id={id}>{label}</h2>
      <article className={`wk-special__card wk-special__card--${sectionType}`}>
        <h3 className="wk-special__headline">{story.headline}</h3>
        <p className="wk-special__summary">{story.summary}</p>
      </article>
    </section>
  );
}

function BiasReport({
  text,
  data,
}: {
  text: string | null;
  data: WeeklyBiasReportData | null;
}) {
  if (!text && !data) return null;

  const agg = data?.aggregate;
  const polarized = data?.most_polarized ?? [];

  return (
    <CollapsibleSection id="wk-bias-heading" label="Bias Report" defaultOpen={false}>
      {agg && (
        <div className="wk-bias__aggregate">
          <div className="wk-bias__stat">
            <span className="wk-bias__stat-value">{agg.total_articles}</span>
            <span className="wk-bias__stat-label">Articles Analyzed</span>
          </div>
          <div className="wk-bias__stat">
            <span className="wk-bias__stat-value">{agg.avg_lean.toFixed(1)}</span>
            <span className="wk-bias__stat-label">Avg. Lean</span>
            <span className="wk-bias__stat-note">{getLeanLabel(agg.avg_lean)}</span>
          </div>
          <div className="wk-bias__stat">
            <span className="wk-bias__stat-value">{agg.avg_rigor.toFixed(1)}</span>
            <span className="wk-bias__stat-label">Avg. Rigor</span>
          </div>
          <div className="wk-bias__stat">
            <span className="wk-bias__stat-value">{agg.avg_sensationalism.toFixed(1)}</span>
            <span className="wk-bias__stat-label">Avg. Sensationalism</span>
          </div>
        </div>
      )}

      {polarized.length > 0 && (
        <div className="wk-bias__polarized">
          <h3 className="wk-bias__sub-heading">Most Polarized Stories</h3>
          {polarized.map((story, i) => (
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
          {text.split("\n\n").map((para, i) => (
            <p key={i}>{para}</p>
          ))}
        </div>
      )}
    </CollapsibleSection>
  );
}

function WeekInBrief({ stories }: { stories: WeeklyRecapStory[] }) {
  const [expanded, setExpanded] = useState(false);
  if (stories.length === 0) return null;

  return (
    <CollapsibleSection id="wk-brief-heading" label="Week in Brief" defaultOpen={false}>
      <div className="wk-brief__list">
        {stories.map((story, i) => (
          <article key={i} className={`wk-brief__item${!expanded ? " wk-brief__item--compact" : ""}`}>
            <h3 className="wk-brief__headline">{story.headline}</h3>
            {expanded && (
              <p className="wk-brief__summary wk-brief__summary--full">{story.summary}</p>
            )}
          </article>
        ))}
      </div>
      <button
        className="wk-toggle wk-toggle--inline"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
        type="button"
      >
        {expanded ? "Headlines only" : "Show summaries"}{" "}
        <span className="wk-toggle__chevron" aria-hidden="true">
          {expanded ? "\u25B2" : "\u25BC"}
        </span>
      </button>
    </CollapsibleSection>
  );
}

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
      label="void --onair Weekly"
      defaultOpen={false}
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
  if (entries.length <= 1) return null;

  return (
    <section className="wk-archive" aria-labelledby="wk-archive-heading">
      <h2 className="wk-section-label" id="wk-archive-heading">Issue Archive</h2>
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

  // Separate recap stories into categories
  // All recap stories unified (tech/sports sections removed)

  return (
    <div className="wk-page">
      <NavBar activeEdition={edition} />

      <main
        ref={mainRef}
        id="main-content"
        className="wk-main"
        role="main"
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

            <OpinionsSection
              left={digest.opinion_left}
              center={digest.opinion_center}
              right={digest.opinion_right}
            />

            <BiasReport
              text={digest.bias_report_text}
              data={digest.bias_report_data}
            />

            <WeekInBrief stories={digest?.recap_stories ?? []} />

            {digest.audio_url && (
              <WeeklyAudioPlayer
                audioUrl={digest.audio_url}
                durationSeconds={digest.audio_duration_seconds}
              />
            )}

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
