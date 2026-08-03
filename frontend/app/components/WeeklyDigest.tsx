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
import SigilWordmark from "./SigilWordmark";

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

/* ── Image Caption ─────────────────────────────────────────────────────────
   Magazine attribution line rendered BELOW an image: an italic serif caption
   describing the picture, followed by a smaller mono credit. Renders
   caption + credit when a caption exists; falls back to credit-only; nothing
   when neither is present. The caption DATA is generated backend-side and may
   be absent — degrade cleanly. */
function ImgCaption({
  caption,
  credit,
}: {
  caption?: string | null;
  credit?: string | null;
}) {
  const cap = caption?.trim();
  const cr = credit?.trim();
  if (!cap && !cr) return null;
  return (
    <figcaption className="wk-img-caption">
      {cap && <span className="wk-img-caption__text">{cap}</span>}
      {cap && cr && <span className="wk-img-caption__sep" aria-hidden="true"> · </span>}
      {cr && <span className="wk-img-caption__credit">{cr}</span>}
    </figcaption>
  );
}

/* ── Full-Screen Cinematic Cover ───────────────────────────────────────────
   A newsstand cover that holds the full viewport on arrival: full-bleed cover
   image with a slow Ken-Burns push and a bottom-up scrim, VOID WEEKLY
   nameplate, issue line, cover headline, coverlines, and a scroll cue. After
   ~3.5s it auto-scrolls down to Page 1 — cancelled the moment the reader
   scrolls, taps, or keys (their intent wins). Honors prefers-reduced-motion:
   no auto-scroll, no Ken Burns. Degrades to a typographic cover on paper when
   no cover image is available. */
function CinematicCover({
  nameplate,
  issueLine,
  headline,
  coverlines,
  imageUrl,
  imageCaption,
  imageAttribution,
}: {
  nameplate: React.ReactNode;
  issueLine: string;
  headline: string;
  coverlines: string[];
  imageUrl?: string | null;
  imageCaption?: string | null;
  imageAttribution?: string | null;
}) {
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgError, setImgError] = useState(false);
  const hasImage = !!imageUrl && !imgError;

  const scrollToPageOne = () => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const target = document.getElementById("wk-page-1");
    target?.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
  };

  /* Auto-scroll to Page 1 after a linger, but never trap the reader: any
     wheel / touch / key / pointer intent cancels it, and it is skipped
     entirely under reduced-motion or if the reader has already scrolled. */
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let done = false;
    const cancel = () => {
      if (done) return;
      done = true;
      cleanup();
    };
    const opts = { passive: true } as AddEventListenerOptions;
    window.addEventListener("wheel", cancel, opts);
    window.addEventListener("touchstart", cancel, opts);
    window.addEventListener("pointerdown", cancel, opts);
    window.addEventListener("keydown", cancel);

    const timer = window.setTimeout(() => {
      if (done) return;
      done = true;
      // Only take over if the reader is still parked on the cover.
      if (window.scrollY < 12) {
        const target = document.getElementById("wk-page-1");
        target?.scrollIntoView({ behavior: "smooth", block: "start" });
      }
      cleanup();
    }, 3500);

    function cleanup() {
      window.clearTimeout(timer);
      window.removeEventListener("wheel", cancel, opts);
      window.removeEventListener("touchstart", cancel, opts);
      window.removeEventListener("pointerdown", cancel, opts);
      window.removeEventListener("keydown", cancel);
    }
    return cleanup;
  }, []);

  return (
    <section
      className={`wk-cover${hasImage ? " wk-cover--has-image" : " wk-cover--type"}`}
      aria-label="Cover"
    >
      {hasImage && (
        <div className="wk-cover__media" aria-hidden="true">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={imageUrl!}
            alt=""
            className={`wk-cover__img${imgLoaded ? " wk-cover__img--loaded" : ""}`}
            loading="eager"
            fetchPriority="high"
            decoding="async"
            onLoad={() => setImgLoaded(true)}
            onError={() => setImgError(true)}
          />
          <div className="wk-cover__scrim" />
        </div>
      )}

      <div className="wk-cover__furniture">
        <div className="wk-cover__top">
          <div className="wk-cover__nameplate">{nameplate}</div>
          <p className="wk-cover__issue">{issueLine}</p>
        </div>

        <div className="wk-cover__bottom">
          <h1 className="wk-cover__headline">{headline}</h1>

          {coverlines.length > 0 && (
            <div className="wk-cover__coverlines">
              <span className="wk-cover__coverlines-label">Also inside</span>
              <ul className="wk-cover__coverlines-list">
                {coverlines.map((line, i) => (
                  <li key={i} className="wk-cover__coverline">{line}</li>
                ))}
              </ul>
            </div>
          )}

          <button
            type="button"
            className="wk-cover__cue"
            onClick={scrollToPageOne}
            aria-label="Enter the issue"
          >
            <span className="wk-cover__kicker">See through the void</span>
            <svg
              className="wk-cover__chevron"
              viewBox="0 0 24 14"
              width="24"
              height="14"
              fill="none"
              aria-hidden="true"
            >
              <path d="M2 2 L12 12 L22 2" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          </button>
        </div>

        {(imageCaption || imageAttribution) && hasImage && (
          <div className="wk-cover__credit">
            <ImgCaption caption={imageCaption} credit={imageAttribution} />
          </div>
        )}
      </div>
    </section>
  );
}

/* ── Section Components ──────────────────────────────────────────────────── */

/* The large VOID WEEKLY nameplate now lives in the full-screen CinematicCover
   at the top of the issue; the compact sticky topbar carries a small copy for
   the rest of the page, so the old standalone <Masthead> was removed to avoid
   doubling the nameplate. */

/* --- B. Cover Hero --- */

function CoverHero({
  headline,
  imageUrl,
  imageAttribution,
  imageCaption,
}: {
  headline: string;
  imageUrl?: string | null;
  imageAttribution?: string | null;
  imageCaption?: string | null;
}) {
  const [imgLoaded, setImgLoaded] = useState(false);
  const [imgError, setImgError] = useState(false);

  return (
    <div className={`wk-cover-hero wk-cold-open--hero${imageUrl && !imgError ? " wk-cover-hero--has-image" : ""}`}>
      {imageUrl && !imgError && (
        <>
          <div className="wk-cover-hero__image-wrap">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={imageUrl}
              alt=""
              className={`wk-cover-hero__image${imgLoaded ? " wk-cover-hero__image--loaded" : ""}`}
              loading="eager"
              fetchPriority="high"
              decoding="async"
              onLoad={() => setImgLoaded(true)}
              onError={() => setImgError(true)}
            />
            <div className="wk-cover-hero__image-overlay" aria-hidden="true" />
          </div>
          <ImgCaption caption={imageCaption} credit={imageAttribution} />
        </>
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

/* Secondary cover-feature image (rendered above story subheads for si > 0).
   Mirrors the CoverHero fade-in / error-hide pattern. The wrapper carries an
   explicit aspect-ratio in CSS so there is zero layout shift while loading. */
function CoverFeatureImage({
  imageUrl,
  attribution,
  caption,
}: {
  imageUrl: string;
  attribution?: string;
  caption?: string;
}) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  if (error) return null;
  return (
    <figure className="wk-cover-body__figure">
      <div className="wk-cover-body__image-wrap">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={imageUrl}
          alt=""
          className={`wk-cover-body__image${loaded ? " wk-cover-body__image--loaded" : ""}`}
          loading="lazy"
          onLoad={() => setLoaded(true)}
          onError={() => setError(true)}
        />
      </div>
      <ImgCaption caption={caption} credit={attribution} />
    </figure>
  );
}

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
            {/* si === 0 image is already the big CoverHero up top; only render a
                body image for the 2nd+ feature to avoid duplicating the lead. */}
            {si > 0 && story.image_url && (
              <CoverFeatureImage
                imageUrl={story.image_url}
                attribution={story.image_attribution}
                caption={story.image_caption}
              />
            )}
            {/* Second cover feature's headline is a top-level section under the
                cover <h1>; keep it <h2> so heading levels never skip (a11y). */}
            {si > 0 && story.headline?.trim() && <h2 className="wk-cover-body__subhead">{story.headline}</h2>}
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

/* --- C2. void --Editorial (the single argued editorial, its own full-width
   section after the cover features) --- */

function SectionEditorial({
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
    <section
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-editorial-section wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-editorial-heading"
    >
      <h2 className="wk-section-label" id="wk-editorial-heading">Editorial</h2>
      <article className="wk-editorial">
        <span className="wk-editorial__lens">
          Through a {leanBadgeLabel(lean || "center").toLowerCase()} lens
        </span>
        {headline?.trim() && <h3 className="wk-editorial__headline">{headline}</h3>}
        <div className="wk-editorial__text">
          {paras.map((para, i) => (
            <p key={i}>{para}</p>
          ))}
        </div>
      </article>
    </section>
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
      id="wk-perspectives"
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-cover-anchor wk-opinions-section wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-opinions-heading"
    >
      <h2 className="wk-section-label" id="wk-opinions-heading">Perspectives</h2>
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
      id="wk-brief"
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-cover-anchor wk-brief-section wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-brief-heading"
    >
      <h2 className="wk-section-label" id="wk-brief-heading">Week in Brief</h2>
      <div className="wk-brief__list">
        {stories.map((story, i) => (
          <article
            key={i}
            className="wk-brief__item"
          >
            <div className="wk-brief__body">
              {story.headline?.trim() && <h3 className="wk-brief__headline">{story.headline}</h3>}
              <p className="wk-brief__summary">{story.summary}</p>
            </div>
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
      id="wk-contested"
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-cover-anchor wk-contested-section wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-contested-heading"
    >
      <h2 className="wk-section-label" id="wk-contested-heading">Most Contested</h2>
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
      id="wk-archive"
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-cover-anchor wk-archive wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-archive-heading"
    >
      <h2 className="wk-section-label" id="wk-archive-heading">Issue Archive</h2>
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

/* --- J. Editorial-rail furniture: "In This Issue" index + colophon --------
   These fill the cover-zone rail so a short editorial never leaves a blank
   gap beside the taller story column. */

interface RailIndexItem {
  href: string;
  label: string;
}

function RailIndex({ items }: { items: RailIndexItem[] }) {
  if (items.length === 0) return null;
  return (
    <nav className="wk-rail-index" aria-label="In this issue">
      <span className="wk-rail-index__label">In This Issue</span>
      <ul className="wk-rail-index__list">
        {items.map((item) => (
          <li key={item.href}>
            <a href={item.href} className="wk-rail-index__link">
              {item.label}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function RailColophon({
  issueNumber,
  weekRange,
  editionLabel,
}: {
  issueNumber: number;
  weekRange: string;
  editionLabel: string;
}) {
  return (
    <div className="wk-rail-colophon">
      <span className="wk-rail-colophon__mark">VOID WEEKLY</span>
      <span className="wk-rail-colophon__line">Issue #{issueNumber}</span>
      <span className="wk-rail-colophon__line">{weekRange}</span>
      <span className="wk-rail-colophon__line wk-rail-colophon__edition">{editionLabel} Edition</span>
    </div>
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

  /* ── Derived cover + rail data (guarded against a null digest) ── */
  const editionLabel = digest
    ? EDITIONS.find((e) => e.slug === digest.edition)?.label ?? "World"
    : "World";
  const weekRange = digest ? formatWeekRange(digest.week_start, digest.week_end) : "";
  const coverHeadline = digest
    ? digest.cover_headline || (digest.cover_text?.[0]?.headline ?? "")
    : "";

  /* Coverlines — "Also inside" teasers pulled from the OTHER cover-feature
     headlines and the top Week-in-Brief titles, excluding the lead headline,
     deduped, capped at three. */
  const coverlines: string[] = [];
  if (digest) {
    const norm = (s: string) => s.trim().toLowerCase();
    const seen = new Set<string>([norm(coverHeadline)]);
    const candidates = [
      ...(digest.cover_text ?? []).slice(1).map((s) => s.headline),
      ...(digest.recap_stories ?? []).map((s) => s.headline),
    ];
    for (const c of candidates) {
      const t = (c ?? "").trim();
      if (!t || seen.has(norm(t))) continue;
      seen.add(norm(t));
      coverlines.push(t);
      if (coverlines.length >= 3) break;
    }
  }

  /* "In This Issue" index — only the sections that actually exist this week. */
  const hasPerspectives = !!(
    digest?.opinion_left?.length ||
    digest?.opinion_center?.length ||
    digest?.opinion_right?.length
  );
  const hasBrief = !!digest?.recap_stories?.length;
  const hasContested = !!digest?.contested_stories?.length;
  const hasArchive = archive.length > 1;
  const indexItems: RailIndexItem[] = [];
  if (hasPerspectives) indexItems.push({ href: "#wk-perspectives", label: "Perspectives" });
  if (hasBrief) indexItems.push({ href: "#wk-brief", label: "Week in Brief" });
  if (hasContested) indexItems.push({ href: "#wk-contested", label: "Most Contested" });
  if (hasArchive) indexItems.push({ href: "#wk-archive", label: "Archive" });

  return (
    <div className="wk-page">
      {/* Full-screen cinematic cover — the first thing on arrival. Full-bleed
          (direct child of .wk-page so it escapes the .wk-main canvas width).
          The compact sticky topbar below only appears once the reader scrolls
          past the cover into Page 1, so the big nameplate is never doubled. */}
      {digest && !loading && (
        <CinematicCover
          nameplate={<SigilWordmark product="WEEKLY" height={44} accent="var(--palette-weekly)" />}
          issueLine={`Issue #${digest.issue_number} · ${weekRange}`}
          headline={coverHeadline}
          coverlines={coverlines}
          imageUrl={digest.cover_image_url}
          imageCaption={digest.cover_text?.[0]?.image_caption}
          imageAttribution={digest.cover_image_attribution}
        />
      )}

      {/* Page-1 scroll target: the auto-scroll and the cover scroll-cue land
          the reader here, at the boundary where the sticky topbar takes over. */}
      <div id="wk-page-1" className="wk-page-anchor" aria-hidden="true" />

      {/* Compact sticky topbar for the rest of the page: back to Void News, a
          small VOID WEEKLY, and the theme toggle. */}
      <div className="wk-topbar">
        <Link href="/" className="wk-back" aria-label="Back to Void News">
          <span className="wk-back__arrow" aria-hidden="true">&larr;</span>
          <LogoFull height={20} className="wk-back__logo" />
        </Link>
        <span className="wk-topbar__mark" aria-hidden="true">
          <SigilWordmark product="WEEKLY" height={16} accent="var(--palette-weekly)" />
        </span>
        <ThemeToggle />
      </div>

      <main
        ref={mainRef}
        id="main-content"
        className="wk-main"
      >
        {/* Large, static nameplate — server-rendered into the export HTML
            (digest is null at build) and kept until a real issue loads, so a
            genuine contentful element paints at FCP and anchors LCP across the
            loading AND empty/error states. It is gated on !digest (not on
            loading, which flips false fast on the empty-DB path and removed the
            anchor before LCP settled). When an issue loads, the CoverHero
            headline becomes the LCP. Without it, LCP fell to a tiny late text
            node (the site-wide experimental banner). */}
        {!digest && (
          <div className="wk-loading__flag" aria-hidden="true">
            Void News<span className="wk-loading__flag-cmd">&nbsp;Weekly</span>
          </div>
        )}

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
              Return to Void News
            </Link>
          </div>
        )}

        {digest && !loading && (
          <>
            {/* B + C. Cover zone — the top story (hero) and the cover features
                run in the main column; the argued Editorial is pinned in a right
                rail beside them, aligned to the top-story headline (magazine
                feel). The rail is a flex column that always fills the story
                column's height: sticky editorial + "In This Issue" index up
                top, a decorative flex-grow filler, then the colophon pinned at
                the bottom — so a short editorial never leaves a blank gap. Rail
                drops below on mobile. */}
            <div
              className={`wk-cover-zone${
                digest.opinion_text ? "" : " wk-cover-zone--no-rail"
              }`}
            >
              <div className="wk-cover-zone__main">
                <CoverHero
                  headline={coverHeadline}
                  imageUrl={digest.cover_image_url}
                  imageAttribution={digest.cover_image_attribution}
                  imageCaption={digest.cover_text?.[0]?.image_caption}
                />
                {digest.cover_text && digest.cover_text.length > 0 && (
                  <CoverBody stories={digest.cover_text} />
                )}
              </div>
              {digest.opinion_text && (
                <aside className="wk-cover-zone__rail">
                  <div className="wk-rail__sticky">
                    <SectionEditorial
                      headline={digest.opinion_headline}
                      text={digest.opinion_text}
                      lean={digest.opinion_lean}
                    />
                    <RailIndex items={indexItems} />
                  </div>
                  <div className="wk-rail-filler" aria-hidden="true">
                    <span className="wk-rail-filler__rule" />
                  </div>
                  <RailColophon
                    issueNumber={digest.issue_number}
                    weekRange={weekRange}
                    editionLabel={editionLabel}
                  />
                </aside>
              )}
            </div>

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
