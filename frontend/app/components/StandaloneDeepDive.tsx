"use client";

// Route-scoped CSS. verify.css carries Claim Consensus + ComparativeView;
// deep-dive-page.css carries the dd-src-cols source-column vocabulary;
// story-page.css adds the standalone centered reading shell. spectrum.css is
// imported by DeepDiveSpectrum itself.
import "../styles/verify.css";
import "../styles/deep-dive-page.css";
import "../styles/story-page.css";

import { useCallback, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, ShareNetwork } from "@phosphor-icons/react";
import type { Story, StorySource } from "../lib/types";
import type { DeepDiveSpectrumSource } from "./DeepDiveSpectrum";
import { hapticLight } from "../lib/haptics";
import NavBar from "./NavBar";
import Sigil from "./Sigil";
import DeepDiveSpectrum from "./DeepDiveSpectrum";
import BiasSnapshot from "./BiasSnapshot";
import SixLenses from "./SixLenses";
import SummaryWithContradictions from "./SummaryWithContradictions";
import ClaimConsensusSection from "./ClaimConsensusSection";
import ComparativeView from "./ComparativeView";
import SourceLedger from "./SourceLedger";

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
}

export default function StandaloneDeepDive({
  story,
  spectrumSources,
  columnSources,
  hasBiasData,
  datelineLabel,
  shareUrl,
}: StandaloneDeepDiveProps) {
  const [shareCopied, setShareCopied] = useState(false);
  const shareTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const sourceCount = story.source.count;
  const hasSpread = hasBiasData || spectrumSources.length > 0;

  // Cross-lean sources gate the ComparativeView (Source Perspectives), exactly
  // as the live Deep Dive does.
  const hasCrossLeanSources = (() => {
    const buckets = new Set<string>();
    for (const src of columnSources) {
      const lean = src.biasScores?.politicalLean ?? 50;
      if (lean <= 40) buckets.add("left");
      else if (lean <= 60) buckets.add("center");
      else buckets.add("right");
      if (buckets.size >= 2) return true;
    }
    return false;
  })();

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
      {/* Void News masthead — same top bar as Home / On Air. An archived story
          is a permanent snapshot, so we show its edition DATE only and suppress
          the live "as of <time>" freshness signal (passing an empty timestamp;
          NavBar renders no time block when it is empty). */}
      <NavBar editionDateline={datelineLabel} editionTimestamp="" />

      <main
        id="main-content"
        className="story-page dd-page"
        aria-label={`Story: ${story.title}`}
      >
        <div className="story-page__inner">
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

          {/* ---- The Story — summary + claim consensus ---- */}
          <section className="story-page__section" aria-label="The story">
            <h2 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-2)" }}>The Story</h2>
            <p className="text-base dd-summary-text" style={{ lineHeight: 1.75, margin: 0 }}>
              <SummaryWithContradictions
                summary={story.summary}
                disputed={claimConsensus?.disputed_details}
              />
            </p>

            {claimConsensus && (
              <div className="story-page__block" aria-label="Claim Consensus verification">
                <hr className="ink-rule" style={{ margin: "var(--space-5) 0 var(--space-4)" }} aria-hidden="true" />
                <ClaimConsensusSection consensus={claimConsensus} />
              </div>
            )}
          </section>

          {/* ---- The Spread — Sigil + spectrum + source columns + lenses ---- */}
          {hasSpread && (
            <section className="story-page__section" aria-label="The spread">
              <hr className="ink-rule" style={{ margin: "var(--space-5) 0 var(--space-4)" }} aria-hidden="true" />
              <h2 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-3)" }}>The Spread</h2>

              {story.sigilData && (
                <div className="dd-analysis-block__sigil story-page__sigil">
                  <Sigil data={story.sigilData} size="xl" storyId={story.id} />
                </div>
              )}

              {spectrumSources.length > 0 && (
                <div className="dd-analysis-block__spectrum">
                  <DeepDiveSpectrum sources={spectrumSources} />
                </div>
              )}

              {columnSources.length > 0 && (
                <SourceLedger sources={columnSources} defaultOpen />
              )}
            </section>
          )}

          {/* ---- Six Lenses — full 6-axis bias breakdown ---- */}
          {story.sigilData && !story.sigilData.pending && (
            <section className="story-page__section" aria-label="Six Lenses">
              <hr className="ink-rule" style={{ margin: "var(--space-5) 0 var(--space-4)" }} aria-hidden="true" />
              <SixLenses
                sigilData={{ ...story.sigilData, agreement: Math.round(story.sigilData.agreement) }}
                visible={true}
              />
            </section>
          )}

          {/* ---- Source Perspectives — consensus/divergence + read-all-sides.
              Reuses ComparativeView, gated on cross-lean sources exactly like
              the live Deep Dive. Absent points are omitted (never fabricated). */}
          {hasCrossLeanSources && (
            <section className="story-page__section" aria-label="Source Perspectives">
              <hr className="ink-rule" style={{ margin: "var(--space-5) 0 var(--space-4)" }} aria-hidden="true" />
              <h2 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-3)" }}>Source Perspectives</h2>
              <ComparativeView
                sources={columnSources}
                consensusPoints={consensus}
                divergencePoints={divergence}
              />
            </section>
          )}
        </div>
      </main>
    </div>
  );
}
