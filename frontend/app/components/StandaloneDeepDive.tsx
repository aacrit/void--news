"use client";

// Route-scoped CSS. verify.css carries Claim Consensus + CoverageList;
// deep-dive-page.css carries the dd-src-cols source-column vocabulary;
// story-page.css adds the standalone centered reading shell. spectrum.css is
// imported by DeepDiveSpectrum itself.
import "../styles/verify.css";
import "../styles/deep-dive-page.css";
import "../styles/story-page.css";

import { useCallback, useRef, useState } from "react";
import Link from "next/link";
import PrintMast from "./PrintMast";
import { ArrowLeft, ShareNetwork } from "@phosphor-icons/react";
import type { Story, StorySource } from "../lib/types";
import type { DeepDiveSpectrumSource } from "./DeepDiveSpectrum";
import { hapticLight } from "../lib/haptics";
import NavBar from "./NavBar";
import Sigil from "./Sigil";
import DeepDiveSpectrum from "./DeepDiveSpectrum";
import BiasSnapshot from "./BiasSnapshot";
import DeepDiveSummary from "./DeepDiveSummary";
import ClaimConsensusSection from "./ClaimConsensusSection";
import CoverageList from "./CoverageList";
import DeepDiveNext from "./DeepDiveNext";
import LeanLabelLegend from "./LeanLabelLegend";
import SpreadDisagreement from "./SpreadDisagreement";

/* ---------------------------------------------------------------------------
   StandaloneDeepDive — the shareable /story/[id] page.

   A real PAGE (not the in-feed overlay): the Void News masthead on top, a
   centered max-width reading view on desktop, full-page on mobile. Seeded
   ENTIRELY from build-time archive data passed as props — NO client-side data
   fetch, no useEffect data loading. Every timestamp is preformatted at build
   (datelineLabel) so first paint is deterministic (no Date.now/new Date in
   render, no React #418).

   A shared last-week story must never try to inline into today's feed, so the
   only navigation back into the app is an explicit "Go to today's feed" link.
   --------------------------------------------------------------------------- */

interface StandaloneDeepDiveProps {
  story: Story;
  /** Sources that carry a real lean — feed the spectrum. */
  spectrumSources: DeepDiveSpectrumSource[];
  /** All distinct sources for the Left/Center/Right roster columns. */
  columnSources: StorySource[];
  /** True when the archive row carries real bias diversity data. */
  hasBiasData: boolean;
  /** NavBar edition build time (ISO). Drives the masthead "as of" dateline. */
  builtAt: string | null;
  /** Preformatted, deterministic dateline (e.g. "Aug 8, 2026"). */
  datelineLabel: string;
  /** Canonical absolute URL to copy on Share. */
  shareUrl: string;
  /** Where this story sits in its own edition, for the ending. */
  editionNav?: {
    position: number;
    total: number;
    prev: { title: string; href: string } | null;
    next: { title: string; href: string } | null;
    editionLabel?: string;
  } | null;
}

export default function StandaloneDeepDive({
  story,
  spectrumSources,
  columnSources,
  hasBiasData,
  datelineLabel,
  shareUrl,
  editionNav = null,
}: StandaloneDeepDiveProps) {
  const [shareCopied, setShareCopied] = useState(false);
  const shareTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // One count for the meta line and the coverage list: the rows the list
  // shows, falling back to the stored count only when no rows are carried.
  const sourceCount = columnSources.length > 0 ? columnSources.length : story.source.count;
  const hasSpread = hasBiasData || spectrumSources.length > 0;


  const consensus = story.deepDive?.consensus;
  const divergence = story.deepDive?.divergence;
  const claimConsensus = story.deepDive?.claimConsensus;

  /* Share — copies the CANONICAL permalink (not window.location), so a shared
     link always points at this permanent page. Native sheet, clipboard toast
     fallback. */
  const handleShare = useCallback(async () => {
    hapticLight();
    try {
      if (typeof navigator !== "undefined" && navigator.share) {
        await navigator.share({ title: story.title, url: shareUrl });
        return;
      }
    } catch {
      /* cancelled or unsupported — fall through to clipboard */
    }
    try {
      await navigator.clipboard.writeText(`${story.title}\n${shareUrl}`);
      setShareCopied(true);
      if (shareTimer.current) clearTimeout(shareTimer.current);
      shareTimer.current = setTimeout(() => setShareCopied(false), 2000);
    } catch {
      /* clipboard blocked — silent no-op */
    }
  }, [story.title, shareUrl]);

  return (
    <div className="page-container">
      {/* The masthead is mounted once in the root layout and shows the current
          edition; the story's own printed-on date is carried in the page body. */}
      <main
        id="main-content"
        className="story-page dd-page"
        aria-label={`Story: ${story.title}`}
      >
        <div className="story-page__inner">
          <PrintMast path={story.permalink ?? `/story/${story.id}/`} />
          {/* Top toolbar — Go to today's feed + Share. A shared archive story
              must never inline into today's feed, so this is an explicit link. */}
          <div className="dd-page__bar">
            <Link href="/" className="dd-page__back">
              <ArrowLeft size={18} weight="regular" aria-hidden="true" />
              <span className="dd-page__back-label">Go to today&apos;s feed</span>
            </Link>

            <div className="dd-page__bar-right">
              <button
                type="button"
                className="dd-page__share"
                onClick={handleShare}
                aria-label="Share this story"
              >
                <ShareNetwork size={18} weight="regular" aria-hidden="true" />
                {shareCopied && (
                  <span className="dd-page__share-toast" role="status">Link copied</span>
                )}
              </button>
            </div>
          </div>

          {/* Headline + meta + primary bias snapshot */}
          <h1 className="dd-headline story-page__headline">{story.title}</h1>
          <div className="deep-dive-meta">
            <span className="category-tag">{story.category}</span>
            <span className="dot-separator" aria-hidden="true" />
            <span className="dd-meta-sources text-data">
              {sourceCount} {sourceCount === 1 ? "source" : "sources"}
            </span>
            <span className="dot-separator" aria-hidden="true" />
            <span className="time-tag">{datelineLabel}</span>
          </div>

          {story.sigilData && !story.sigilData.pending && (
            <BiasSnapshot
              data={story.sigilData}
              sourceCount={sourceCount}
              variant="inline"
              hideCoverageBar={spectrumSources.length > 0}
            />
          )}

          {/* ---- The Story, with what the sources agree on and where they
              split as its sidebar (beside it when the page is wide). ---- */}
          <div className="dd-lede-grid">
          <section className="story-page__section" aria-label="The story">
            <h2 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-2)" }}>The Story</h2>
            <DeepDiveSummary
              summary={story.summary}
              disputed={claimConsensus?.disputed_details}
            />

            {claimConsensus && (
              <div className="story-page__block" aria-label="Claim Consensus verification">
                <hr className="ink-rule" style={{ margin: "var(--space-5) 0 var(--space-4)" }} aria-hidden="true" />
                <ClaimConsensusSection consensus={claimConsensus} />
              </div>
            )}
          </section>
          <SpreadDisagreement consensus={consensus} divergence={divergence} />
          </div>

          {/* ---- The Spread — Sigil + spectrum. The spectrum's positioned logos
              ARE the source display now (hover a logo for its name); the
              separate source roster was removed. ---- */}
          {hasSpread && (
            <section className="story-page__section" aria-label="The spread">
              <hr className="ink-rule" style={{ margin: "var(--space-5) 0 var(--space-4)" }} aria-hidden="true" />
              <div className="dd-section-head">
                <h2 className="dd-section-label text-meta">The Spread</h2>
                <LeanLabelLegend />
              </div>

              {/* The Bench carries the mark and word once sources are placed;
                  the Sigil is only the fallback (as in the feed shells). */}
              {story.sigilData && spectrumSources.length === 0 && (
                <div className="dd-analysis-block__sigil story-page__sigil">
                  <Sigil data={story.sigilData} size="xl" storyId={story.id} />
                </div>
              )}

              {spectrumSources.length > 0 && (
                <div className="dd-analysis-block__spectrum">
                  <DeepDiveSpectrum sources={spectrumSources} />
                </div>
              )}
            </section>
          )}

          {/* Six Lenses callout removed 2026-08-11 (CEO) — kept clean; the
              spectrum + agree/dispute panel carry the primary bias signal. */}

          {/* ---- The coverage: every source, open, on the Bench's seven rungs. */}
          <CoverageList sources={columnSources} headingLevel={2} />

          {/* ---- The end: the next story in this story's own edition. ---- */}
          {editionNav && (
            <DeepDiveNext
              position={editionNav.position}
              total={editionNav.total}
              prev={editionNav.prev}
              next={editionNav.next}
              editionLabel={editionNav.editionLabel}
            />
          )}
        </div>
      </main>
    </div>
  );
}
