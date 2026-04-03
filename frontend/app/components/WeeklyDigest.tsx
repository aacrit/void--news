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
  // Normalize lean values from data to display labels
  const map: Record<string, string> = {
    "left": "Left",
    "center-left": "Center-Left",
    "center": "Center",
    "center-right": "Center-Right",
    "right": "Right",
    "far-left": "Far Left",
    "far-right": "Far Right",
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
      <h1 className="wk-masthead__title">void --weekly</h1>
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

function CoverSection({ stories }: { stories: WeeklyCoverStory[] }) {
  return (
    <section className="wk-cover" aria-labelledby="wk-cover-heading">
      <h2 className="wk-section-label" id="wk-cover-heading">The Cover</h2>
      {stories.map((story, i) => (
        <article key={i} className="wk-cover__story">
          <h3 className="wk-cover__headline">{story.headline}</h3>
          <div className="wk-cover__body-wrap">
            <div className="wk-cover__text">
              {story.text.split("\n\n").map((para, j) => (
                <p key={j}>{para}</p>
              ))}
            </div>
            {story.numbers && story.numbers.length > 0 && (
              <aside className="wk-cover__numbers" aria-label="This week in numbers">
                <h4 className="wk-cover__numbers-title">This Week in Numbers</h4>
                <dl className="wk-cover__numbers-list">
                  {story.numbers.map((n, k) => (
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
            <div className="wk-timeline" role="list" aria-label="Timeline">
              <div className="wk-timeline__track" aria-hidden="true" />
              {story.timeline.map((day, k) => (
                <div key={k} className="wk-timeline__node" role="listitem">
                  <span className="wk-timeline__dot" aria-hidden="true" />
                  <span className="wk-timeline__day">{day.day}</span>
                  <span className="wk-timeline__note">{day.note}</span>
                </div>
              ))}
            </div>
          )}
          {i < stories.length - 1 && (
            <hr className="wk-divider" aria-hidden="true" />
          )}
        </article>
      ))}
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
    <section className="wk-opinions" aria-labelledby="wk-opinions-heading">
      <h2 className="wk-section-label" id="wk-opinions-heading">The Opinions</h2>
      <div className="wk-opinions__grid">
        {all.map((op, i) => (
          <article key={i} className="wk-opinion">
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
            <div className="wk-opinion__text">
              {op.text.split("\n\n").map((para, j) => (
                <p key={j}>{para}</p>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
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
    <section className="wk-bias" aria-labelledby="wk-bias-heading">
      <h2 className="wk-section-label" id="wk-bias-heading">Bias Report</h2>

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
    </section>
  );
}

function WeekInBrief({ stories }: { stories: WeeklyRecapStory[] }) {
  if (stories.length === 0) return null;

  return (
    <section className="wk-brief" aria-labelledby="wk-brief-heading">
      <h2 className="wk-section-label" id="wk-brief-heading">Week in Brief</h2>
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
    <section className="wk-audio" aria-labelledby="wk-audio-heading">
      <h2 className="wk-section-label" id="wk-audio-heading">
        <span className="wk-audio__brand">void --onair</span> Weekly
      </h2>
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
    </section>
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
  const techStory = digest?.recap_stories?.find(
    (s) => s.section?.toLowerCase() === "tech"
  );
  const sportsStory = digest?.recap_stories?.find(
    (s) => s.section?.toLowerCase() === "sports"
  );
  const otherStories = (digest?.recap_stories ?? []).filter(
    (s) => s.section?.toLowerCase() !== "tech" && s.section?.toLowerCase() !== "sports"
  );

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
              <CoverSection stories={digest.cover_text} />
            )}

            <OpinionsSection
              left={digest.opinion_left}
              center={digest.opinion_center}
              right={digest.opinion_right}
            />

            {techStory && (
              <SpecialSection story={techStory} sectionType="tech" />
            )}

            {sportsStory && (
              <SpecialSection story={sportsStory} sectionType="sports" />
            )}

            <BiasReport
              text={digest.bias_report_text}
              data={digest.bias_report_data}
            />

            <WeekInBrief stories={otherStories} />

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
