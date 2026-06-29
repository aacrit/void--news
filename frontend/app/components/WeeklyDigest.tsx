"use client";

import { useState, useEffect, useRef, useMemo } from "react";
import Link from "next/link";
import type {
  Edition,
  WeeklyDigestData,
  WeeklyCoverStory,
  WeeklyRecapStory,
  WeeklyOpinion,
  WeeklyContestedStory,
} from "../lib/types";
import { EDITIONS } from "../lib/types";
import { fetchWeeklyDigest, fetchWeeklyArchive } from "../lib/supabase";
import { AUDIO_ENABLED } from "../lib/audioGate";
import { useAudio, type EpisodeMeta } from "./AudioProvider";
import Footer from "./Footer";
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
    <div ref={ref as React.RefObject<HTMLDivElement>} className={visible ? "wk-reveal--visible" : ""}>
      <InkFlourish />
    </div>
  );
}

/* ── Formatting Helpers ────────────────────────────────────────────────────── */

/* Defensive: drop any embedded "TIMELINE" block the generator may have
   written into the cover essay (a heading line + bullet list). The timeline
   UI was removed, but older issues have it baked into cover_text. */
function stripTimelineFromText(text: string): string {
  const blocks = (text || "").split(/\n\n+/);
  const kept = blocks.filter((block) => {
    const lines = block.trim().split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length === 0) return false;
    const heading = lines[0].replace(/[*_#\s:]/g, "").toUpperCase();
    if (heading === "TIMELINE") return false;
    const allBullets = lines.every((l) => /^[*\-•]\s+/.test(l));
    if (allBullets) return false;
    return true;
  });
  return kept.join("\n\n");
}

/* Pick a single magazine-style pull-quote from a cover essay: the first
   self-contained sentence in a comfortable length band, drawn from existing
   text (no generation). Returns "" if nothing suitable. */
function pickPullQuote(text: string): string {
  const clean = stripTimelineFromText(text || "").replace(/\s+/g, " ").trim();
  const sentences = clean.split(/(?<=[.!?])\s+/).map((s) => s.trim()).filter(Boolean);
  const inBand = sentences.find((s) => s.length >= 70 && s.length <= 150);
  return inBand || sentences.find((s) => s.length >= 45 && s.length <= 200) || "";
}

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

/* Lean marker — same three labels the daily Opinion view uses
   (SkyboxBanner: Progressive / Pragmatic / Conservative). */
function leanBadgeLabel(lean: string): string {
  const l = (lean || "center").toLowerCase();
  if (l.includes("left")) return "Progressive";
  if (l.includes("right")) return "Conservative";
  return "Pragmatic";
}

/* Map a lean label to the shared bias color token — same blue/green/red
   tokens the daily Opinion view uses, applied with restraint (thin border +
   low-opacity badge) rather than a saturated fill. */
function leanToBiasVar(lean: string): string {
  const l = (lean || "center").toLowerCase();
  if (l.includes("left")) return "var(--bias-left)";
  if (l.includes("right")) return "var(--bias-right)";
  return "var(--bias-center)";
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
  imageUrl,
  imageAttribution,
}: {
  headline: string;
  imageUrl?: string | null;
  imageAttribution?: string | null;
}) {
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgError, setImgError] = useState(false);

  return (
    <div className={`wk-cover-hero wk-cold-open--hero${imageUrl && !imgError ? " wk-cover-hero--has-image" : ""}`}>
      {imageUrl && !imgError && (
        <div className="wk-cover-hero__image-wrap">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageUrl}
            alt=""
            className={`wk-cover-hero__image${imgLoaded ? " wk-cover-hero__image--loaded" : ""}`}
            loading="eager"
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgError(true)}
          />
          <div className="wk-cover-hero__image-overlay" aria-hidden="true" />
          {imageAttribution && (
            <span className="wk-cover-hero__image-credit">{imageAttribution}</span>
          )}
        </div>
      )}
      <div className="wk-cover-hero__content">
        {/* Cover hero is the page's primary headline — <h1> for SR + SEO.
            UAT 2026-05-13 P0-5: /weekly had no <h1>. */}
        <h1 className="wk-cover-hero__headline">{headline}</h1>
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

/* --- C. Cover Body --- */

function CoverBody({
  stories,
}: {
  stories: WeeklyCoverStory[];
}) {
  const [sectionRef, sectionVisible] = useScrollReveal(0.1);

  return (
    <section
      ref={sectionRef as React.RefObject<HTMLElement>}
      className={`wk-reveal${sectionVisible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-cover-heading"
    >
      {/* Show up to 2 cover stories */}
      {stories.slice(0, 2).map((story, si) => {
        const paras = stripTimelineFromText(story.text || "").split("\n\n").filter(Boolean);
        const pullQuote = pickPullQuote(story.text || "");
        return (
          <div key={si} className="wk-cover-body wk-cold-open--body">
            {si > 0 && <InkRule className="wk-ink-rule--strong" />}
            {si > 0 && story.headline?.trim() && <h3 className="wk-cover-body__subhead">{story.headline}</h3>}
            <div className="wk-cover-body__text">
              {paras.flatMap((para, j) => {
                const nodes = [<p key={`${si}-p-${j}`}>{para}</p>];
                // Pull-quote floats after the opening paragraph (magazine break).
                if (j === 0 && pullQuote && paras.length > 1) {
                  nodes.push(
                    <blockquote key={`${si}-pq`} className="wk-pullquote">
                      {pullQuote}
                    </blockquote>
                  );
                }
                return nodes;
              })}
            </div>
          </div>
        );
      })}
    </section>
  );
}

/* --- C2. void --Editorial (the single argued editorial, in the cover rail) --- */

function RailEditorial({
  headline,
  text,
  lean,
}: {
  headline: string | null;
  text: string;
  lean: string | null;
}) {
  const [ref, visible] = useScrollReveal(0.1);
  const paras = (text || "").split("\n\n").filter(Boolean);
  if (paras.length === 0) return null;
  return (
    <div
      ref={ref as React.RefObject<HTMLDivElement>}
      className={`wk-rail-editorial wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-label="Editorial"
    >
      <h2 className="wk-rail-editorial__label" data-prefix="void --">Editorial</h2>
      <span className="wk-rail-editorial__lens">
        Through a {leanBadgeLabel(lean || "center").toLowerCase()} lens
      </span>
      {headline?.trim() && <h3 className="wk-rail-editorial__headline">{headline}</h3>}
      <div className="wk-rail-editorial__text">
        {paras.map((para, i) => (
          <p key={i}>{para}</p>
        ))}
      </div>
    </div>
  );
}

/* --- D. Opinions --- */

function OpinionCard({ op }: { op: WeeklyOpinion }) {
  return (
    <article
      className="wk-opinion wk-reveal-child"
      style={{ "--lean-color": leanToBiasVar(op.lean) } as React.CSSProperties}
    >
      <div className="wk-opinion__header">
        <span className="wk-opinion__badge">
          {leanBadgeLabel(op.lean)}
        </span>
        {op.topic && (
          <span className="wk-opinion__topic">{op.topic}</span>
        )}
      </div>
      {op.headline?.trim() && <h3 className="wk-opinion__headline">{op.headline}</h3>}
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
            {story.headline?.trim() && <h3 className="wk-brief__headline">{story.headline}</h3>}
            <p className="wk-brief__summary">{story.summary}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

/* --- G. Most Contested This Week --- */

function ContestedSection({ stories }: { stories: WeeklyContestedStory[] }) {
  const [ref, visible] = useScrollReveal(0.1);

  const contestedStories = useMemo(() => {
    return [...stories]
      .filter((s) => s.claim_consensus && s.claim_consensus.disputed > 0)
      .sort((a, b) => a.claim_consensus.consensus_ratio - b.claim_consensus.consensus_ratio)
      .slice(0, 5);
  }, [stories]);

  if (contestedStories.length === 0) return null;

  return (
    <section
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-contested-section wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-contested-heading"
    >
      <h2 className="wk-section-label" id="wk-contested-heading" data-prefix="void --">Most Contested</h2>
      <div className="wk-contested__list">
        {contestedStories.map((story) => (
          <article key={story.id} className="wk-contested__item">
            <span className="wk-contested__mark" aria-hidden="true">&#x26A1;</span>
            <div className="wk-contested__body">
              {story.title?.trim() && <h3 className="wk-contested__headline">{story.title}</h3>}
              <p className="wk-contested__stat">
                Sources agreed: {story.claim_consensus.corroborated}/{story.claim_consensus.total_claims}
                {" "}({Math.round(story.claim_consensus.consensus_ratio * 100)}%)
              </p>
              {story.claim_consensus.consensus_summary && (
                <p className="wk-contested__summary">{story.claim_consensus.consensus_summary}</p>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

/* --- H. Audio — now plays through the shared void --onair player (recolored
       to the weekly red accent). The local <AudioBar> was removed; weekly audio
       is loaded into the global AudioProvider via playWeekly() in the main
       component, so it shares the daily transport, broadcast console, and
       playlist. --- */

/* --- I. Issue Archive --- */

interface ArchiveEntry {
  id: string;
  edition: string;
  week_start: string;
  week_end: string;
  issue_number: number;
  cover_headline: string;
  audio_url?: string | null;
  audio_duration_seconds?: number | null;
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
  const [digest, setDigest] = useState<WeeklyDigestData | null>(null);
  const [archive, setArchive] = useState<ArchiveEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mainRef = useRef<HTMLElement>(null);
  const { playWeekly } = useAudio();

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

  /* Load this issue's audio into the shared void --onair player (recolored to
     the weekly red accent). Previous playable issues from the archive become
     the "Previous issues" playlist. Does not auto-play. */
  useEffect(() => {
    if (!AUDIO_ENABLED || !digest?.audio_url) return;
    const archiveIssues: EpisodeMeta[] = archive
      .filter((issue) => !!issue.audio_url)
      .map((issue) => ({
        id: issue.id,
        edition: issue.edition,
        tldr_headline: issue.cover_headline,
        tldr_text: "",
        opinion_headline: null,
        opinion_text: null,
        opinion_lean: null,
        audio_url: issue.audio_url ?? null,
        audio_duration_seconds: issue.audio_duration_seconds ?? null,
        opinion_start_seconds: null,
        audio_voice_label: null,
        audio_voice: null,
        created_at: issue.created_at,
      }));
    playWeekly(digest, archiveIssues);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [digest?.id, archive]);

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
              imageUrl={digest.cover_image_url}
              imageAttribution={digest.cover_image_attribution}
            />

            {/* C. Cover zone — two features beside the italic Editor's Note rail */}
            {digest.cover_text && digest.cover_text.length > 0 && (
              <div className="wk-cover-zone">
                <div className="wk-cover-zone__main">
                  <CoverBody stories={digest.cover_text} />
                </div>
                <aside className="wk-cover-zone__aside" aria-label="Editorial">
                  {digest.opinion_text && (
                    <RailEditorial
                      headline={digest.opinion_headline}
                      text={digest.opinion_text}
                      lean={digest.opinion_lean}
                    />
                  )}
                </aside>
              </div>
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

            {/* F. Most Contested */}
            {digest.contested_stories && digest.contested_stories.length > 0 && (
              <>
                <RevealFlourish />
                <ContestedSection stories={digest.contested_stories} />
              </>
            )}

            {/* G. Audio now plays through the shared void --onair player
                (red-accented for weekly). Loaded via playWeekly() in an effect
                below — no inline player here. */}

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
    </div>
  );
}
