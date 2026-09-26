"use client";

// Route-scoped CSS. verify.css carries the Claim Consensus / CoverageList
// styles; deep-dive-page.css adds the mobile full-page shell (masthead bar,
// compact segmented switch). Bundled with the lazy Deep Dive chunk.
import "../styles/verify.css";
import "../styles/deep-dive-page.css";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  ArrowLeft,
  CaretLeft,
  CaretRight,
  ShareNetwork,
} from "@phosphor-icons/react";
import type { Story, StorySource, DeepDiveData, ThreeLensData, OpinionLabel } from "../lib/types";
import { fetchDeepDiveData } from "../lib/supabase";
import { timeAgo } from "../lib/utils";
import { SITE_URL } from "../lib/siteMeta";
import { hapticLight } from "../lib/haptics";
import { findHistoryContext } from "../lib/historyContext";
import Sigil from "./Sigil";
import DeepDiveNext from "./DeepDiveNext";
import DeepDiveSummary from "./DeepDiveSummary";
import LeanLabelLegend from "./LeanLabelLegend";
import DeepDiveSpectrum from "./DeepDiveSpectrum";
import BiasSnapshot from "./BiasSnapshot";
import type { DeepDiveSpectrumSource } from "./DeepDiveSpectrum";
import CoverageList from "./CoverageList";
import SpreadDisagreement from "./SpreadDisagreement";
import ClaimConsensusSection from "./ClaimConsensusSection";
import LazyOnView from "./LazyOnView";

/* ---------------------------------------------------------------------------
   DeepDive — Mobile full-page "next screen" (phones only).

   This is NOT a modal, backdrop, or bottom sheet. It fills the viewport as its
   own page and REPLACES the feed (HomeContent renders it instead of MobileFeed
   on the mobile branch). It sits under the one masthead app/layout.tsx mounts,
   pushes a history entry on open so the hardware Back button returns to the
   feed, and offers prev/next story walkers.

   One scrollable page (2026-08-11): the old Story / Spread segmented switch was
   removed; the summary, spectrum, coverage meta, and source columns now stack in
   a single flow that mirrors the desktop InlineDeepDive order.

   Desktop uses InlineDeepDive (in-feed accordion) instead — this component is
   never rendered above 767px.
   --------------------------------------------------------------------------- */

// History shipped as a feature on 2026-09-19 (its launch-hiding 301s are gone),
// so the archival cross-link renders again. Set true only if the section is
// hidden again, and remove the nav links in the same commit.
const HISTORY_HIDDEN: boolean = false;

// The separate source roster is gone (2026-08-10): the DeepDiveSpectrum's
// positioned logos are the sole source display (tap/hover a logo for its name).

interface DeepDiveProps {
  story: Story;
  onClose: () => void;
  /** Navigate to previous/next story in the feed. */
  onNavigate?: (direction: "prev" | "next") => void;
  /** Current story index in the visible feed (for the counter). */
  storyIndex?: number;
  /** Total stories in the visible feed. */
  totalStories?: number;
  prevStory?: Story | null;
  nextStory?: Story | null;
  /** After the last story: walk back to the first. */
  onFirst?: () => void;
  /** Accepted for call-site compatibility; the masthead in app/layout.tsx owns the dateline. */
  editionBuiltAt?: string | null;
  /** Accepted for call-site compatibility (desktop FLIP origin). Unused here. */
  originRect?: DOMRect | null;
}

/* Six Lenses removed 2026-08-11 (CEO): the 6-axis breakdown was a secondary
   stat; the mobile Deep Dive stays clean (spectrum + agree/dispute carry the
   primary bias signal). */

/* --- History Context Link — subtle archival cross-link -------------------- */

function HistoryContextLink({ title, summary }: { title: string; summary: string }) {
  const match = findHistoryContext(title, summary);
  if (HISTORY_HIDDEN || !match) return null;

  const perspText = match.perspectiveCount > 0
    ? `See how this event is told from ${match.perspectiveCount} perspectives`
    : "Explore this event in the archive";

  return (
    <div className="dd-history-context">
      <hr className="ink-rule" style={{ margin: "0 0 var(--space-3) 0" }} aria-hidden="true" />
      <span className="dd-history-context__label text-meta" aria-hidden="true">Historical Context</span>
      <a
        href={match.href}
        className="dd-history-context__link"
        aria-label={`Historical context: ${match.title}`}
      >
        <span className="dd-history-context__arrow" aria-hidden="true">&rarr;</span>
        <span className="dd-history-context__title">{match.title}</span>
        <span className="dd-history-context__desc">{perspText}</span>
      </a>
    </div>
  );
}


/* --- Main DeepDive component (mobile full-page) --------------------------- */

export default function DeepDive({
  story,
  onClose,
  onNavigate,
  storyIndex = -1,
  totalStories = 0,
  prevStory = null,
  nextStory = null,
  onFirst,
}: DeepDiveProps) {
  const [liveData, setLiveData] = useState<DeepDiveData | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [shareCopied, setShareCopied] = useState(false);
  const shareTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Stable ref for onClose — used by the popstate listener without re-binding.
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  const deepDive: DeepDiveData | undefined = liveData ?? story.deepDive;
  const sources = useMemo(() => deepDive?.sources ?? [], [deepDive]);

  const spectrumSources: DeepDiveSpectrumSource[] = useMemo(
    () =>
      sources
        .filter((src) => src.biasScores != null)
        .map((src) => ({
          name: src.name,
          articleUrl: src.url,
          sourceUrl: src.url,
          tier: src.tier,
          politicalLean: src.biasScores?.politicalLean ?? 50,
          factualRigor: src.biasScores?.factualRigor,
          confidence: src.confidence,
          headline: src.articleTitle,
          leanUnscored: src.leanUnscored,
        })),
    [sources],
  );

  /* Spread page makes sense only when there is a Sigil or scored sources. */
  const hasLedeSpectrum = Boolean(story.sigilData) || spectrumSources.length > 0;


  /* Genuinely-waiting flag: the summary + Sigil are already on the story and
     render immediately; only the full source roster / spectrum are still being
     fetched. Drives the subtle inline loading line (never a full-panel skeleton,
     never blanks already-available content). */
  const sourcesPending = isLoadingData && sources.length === 0;

  /* ---- Fetch live cluster data from Supabase ---------------------------- */
  useEffect(() => {
    let cancelled = false;

    async function loadClusterData() {
      setIsLoadingData(true);
      setFetchError(false);
      try {
        const raw = await fetchDeepDiveData(story.id);
        if (cancelled || !raw || raw.length === 0) {
          setIsLoadingData(false);
          return;
        }

        const storySourceList: StorySource[] = [];
        for (const row of raw) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const article = row.article as any;
          if (!article) continue;

          const source = article.source;
          const biasRaw = article.bias_scores;
          const bias = Array.isArray(biasRaw)
            ? (biasRaw.length > 0 ? biasRaw[0] : null)
            : (biasRaw ?? null);

          const lean = (bias?.political_lean as number) ?? 50;
          const opinionVal = (bias?.opinion_fact as number) ?? 25;
          const rigor = (bias?.factual_rigor as number) ?? 75;

          let rationale: Record<string, unknown> | null = null;
          if (bias?.rationale && typeof bias.rationale === "object") {
            rationale = bias.rationale;
          }

          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const rawLean = rationale?.lean as any;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const rawOpinion = rationale?.opinion as any;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const rawCoverage = rationale?.coverage as any;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const rawSense = rationale?.sensationalism as any;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const rawFraming = rationale?.framing as any;
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const rawGemini = rationale?.gemini_reasoning as any;

          const mappedLean = rawLean ? {
            keywordScore: rawLean.keyword_score ?? rawLean.keywordScore ?? 0,
            framingShift: rawLean.framing_shift ?? rawLean.framingShift ?? 0,
            entityShift: rawLean.entity_shift ?? rawLean.entityShift ?? 0,
            sourceBaseline: rawLean.source_baseline ?? rawLean.sourceBaseline ?? 50,
            topLeftKeywords: rawLean.top_left_keywords ?? rawLean.topLeftKeywords ?? [],
            topRightKeywords: rawLean.top_right_keywords ?? rawLean.topRightKeywords ?? [],
            framingPhrasesFound: rawLean.framing_phrases_found ?? rawLean.framingPhrasesFound ?? [],
            entitySentiments: rawLean.entity_sentiments ?? rawLean.entitySentiments ?? {},
          } : undefined;

          const mappedOpinion = rawOpinion ? {
            pronounScore: rawOpinion.pronoun_score ?? rawOpinion.pronounScore ?? 0,
            subjectivityScore: rawOpinion.subjectivity_score ?? rawOpinion.subjectivityScore ?? 0,
            modalScore: rawOpinion.modal_score ?? rawOpinion.modalScore ?? 0,
            hedgingScore: rawOpinion.hedging_score ?? rawOpinion.hedgingScore ?? 0,
            attributionScore: rawOpinion.attribution_score ?? rawOpinion.attributionScore ?? 0,
            metadataScore: rawOpinion.metadata_score ?? rawOpinion.metadataScore ?? 0,
            rhetoricalScore: rawOpinion.rhetorical_score ?? rawOpinion.rhetoricalScore ?? 0,
            valueJudgmentScore: rawOpinion.value_judgment_score ?? rawOpinion.valueJudgmentScore ?? 0,
            classification: rawOpinion.classification ?? "Reporting",
            dominantSignals: rawOpinion.dominant_signals ?? rawOpinion.dominantSignals ?? [],
          } : undefined;

          const mappedCoverage = rawCoverage ? {
            factualRigor: rawCoverage.factual_rigor ?? rawCoverage.factualRigor ?? 0,
            namedSourcesCount: rawCoverage.named_sources_count ?? rawCoverage.namedSourcesCount ?? 0,
            orgCitationsCount: rawCoverage.org_citations_count ?? rawCoverage.orgCitationsCount ?? 0,
            dataPointsCount: rawCoverage.data_points_count ?? rawCoverage.dataPointsCount ?? 0,
            directQuotesCount: rawCoverage.direct_quotes_count ?? rawCoverage.directQuotesCount ?? 0,
            vagueSourcesCount: rawCoverage.vague_sources_count ?? rawCoverage.vagueSourcesCount ?? 0,
            specificityRatio: rawCoverage.specificity_ratio ?? rawCoverage.specificityRatio ?? 0,
          } : undefined;

          const mappedSense = rawSense ? {
            headlineScore: rawSense.headline_score ?? rawSense.headlineScore ?? 0,
            bodyScore: rawSense.body_score ?? rawSense.bodyScore ?? 0,
            clickbaitSignals: rawSense.clickbait_signals ?? rawSense.clickbaitSignals ?? 0,
            superlativeDensity: rawSense.superlative_density ?? rawSense.superlativeDensity ?? 0,
            urgencyDensity: rawSense.urgency_density ?? rawSense.urgencyDensity ?? 0,
            hyperboleDensity: rawSense.hyperbole_density ?? rawSense.hyperboleDensity ?? 0,
            measuredDensity: rawSense.measured_density ?? rawSense.measuredDensity ?? 0,
          } : undefined;

          const mappedFraming = rawFraming ? {
            connotationScore: rawFraming.connotation_score ?? rawFraming.connotationScore ?? 0,
            keywordEmphasisScore: rawFraming.keyword_emphasis_score ?? rawFraming.keywordEmphasisScore ?? 0,
            omissionScore: rawFraming.omission_score ?? rawFraming.omissionScore ?? 0,
            headlineBodyDivergence: rawFraming.headline_body_divergence ?? rawFraming.headlineBodyDivergence ?? 0,
            passiveVoiceScore: rawFraming.passive_voice_score ?? rawFraming.passiveVoiceScore ?? 0,
            hasClusterContext: rawFraming.has_cluster_context ?? rawFraming.hasClusterContext ?? false,
          } : undefined;

          const mappedGemini = rawGemini ? {
            political_lean: typeof rawGemini.political_lean === "string" ? rawGemini.political_lean : undefined,
            sensationalism: typeof rawGemini.sensationalism === "string" ? rawGemini.sensationalism : undefined,
            opinion_fact: typeof rawGemini.opinion_fact === "string" ? rawGemini.opinion_fact : undefined,
            factual_rigor: typeof rawGemini.factual_rigor === "string" ? rawGemini.factual_rigor : undefined,
            framing: typeof rawGemini.framing === "string" ? rawGemini.framing : undefined,
          } : undefined;

          let opinionLabel: OpinionLabel = "Reporting";
          if (opinionVal > 75) opinionLabel = "Editorial";
          else if (opinionVal > 50) opinionLabel = "Opinion";
          else if (opinionVal > 25) opinionLabel = "Analysis";

          const confidence = (bias?.confidence as number) ?? 0.5;
          const coverageScore = Math.round((rigor / 100) * 60 + confidence * 40);

          const lensData: ThreeLensData = {
            lean,
            coverage: coverageScore,
            sourceCount: 1,
            opinion: opinionVal,
            opinionLabel,
            leanRationale: mappedLean,
            opinionRationale: mappedOpinion,
            coverageRationale: mappedCoverage,
            sensationalismRationale: mappedSense,
            framingRationale: mappedFraming,
            geminiReasoning: mappedGemini,
          };

          storySourceList.push({
            name: (source?.name as string) ?? "Unknown",
            url: (article.url as string) ?? (source?.url as string) ?? "#",
            tier: ((source?.tier as string) as StorySource["tier"]) ?? "independent",
            biasScores: {
              politicalLean: lean,
              sensationalism: (bias?.sensationalism as number) ?? 30,
              opinionFact: opinionVal,
              factualRigor: rigor,
              framing: (bias?.framing as number) ?? 40,
            },
            lensData,
            confidence,
            articleTitle: (article.title as string) ?? undefined,
            articleSummary: (article.summary as string) ?? undefined,
            /* Carried, not acted on here: the spectrum is the one component
               that decides what it plots. The source still counts toward the
               roster and the tier breakdown, because it really did cover the
               story; only its position on the lean axis is withheld. */
            leanUnscored: bias?.lean_unscored === true,
          });
        }

        // Deduplicate: keep only the first article per source name.
        const seenSourceNames = new Set<string>();
        const dedupedSourceList = storySourceList.filter((s) => {
          const key = s.name.toLowerCase().trim();
          if (seenSourceNames.has(key)) return false;
          seenSourceNames.add(key);
          return true;
        });

        if (!cancelled && dedupedSourceList.length > 0) {
          const consensus = Array.isArray(story.deepDive?.consensus) ? story.deepDive.consensus : [];
          const divergenceData = Array.isArray(story.deepDive?.divergence) ? story.deepDive.divergence : [];

          setLiveData({
            consensus,
            divergence: divergenceData,
            sources: dedupedSourceList,
            claimConsensus: story.deepDive?.claimConsensus,
          });
        }
      } catch {
        if (!cancelled) setFetchError(true);
      } finally {
        if (!cancelled) setIsLoadingData(false);
      }
    }

    loadClusterData();
    return () => { cancelled = true; };
  }, [story.id, story.deepDive, retryCount]);

  /* ---- Reset transient page state when the parent walks to another story
     (prev/next does NOT remount — HomeContent renders this without a per-story
     key so the page persists and just re-fetches). ------------------------ */
  useEffect(() => {
    setShareCopied(false);
    if (shareTimer.current) clearTimeout(shareTimer.current);
    window.scrollTo(0, 0);
  }, [story.id]);

  /* History is owned by HomeContent (lib/deepDiveHistory): it pushed this
     story's permalink as the entry when the page opened, and its popstate
     listener closes the page. Back to feed therefore just goes back. */
  /* Back to feed — pop the pushed entry (fires popstate -> onClose). */
  const handleBack = useCallback(() => {
    hapticLight();
    onCloseRef.current();
  }, []);

  /* Keyboard: Escape returns to feed, arrows walk stories. */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      /* Arrows and J/K walk stories from HomeContent's one key handler. */
      if (e.key === "Escape" && !e.defaultPrevented) {
        e.preventDefault();
        handleBack();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [handleBack]);

  /* Share — native sheet, clipboard fallback with a brief toast. */
  const handleShare = useCallback(async () => {
    hapticLight();
    // Prefer the story's canonical standalone permalink so a shared link opens
    // the permanent /story page, not whatever route the reader is on.
    const url = story.permalink
      ? `${SITE_URL}${story.permalink}`
      : (typeof window !== "undefined" ? window.location.href : "");
    try {
      if (typeof navigator !== "undefined" && navigator.share) {
        await navigator.share({ title: story.title, url });
        return;
      }
    } catch {
      /* cancelled or unsupported — fall through to clipboard */
    }
    try {
      await navigator.clipboard.writeText(`${story.title}\n${url}`);
      setShareCopied(true);
      if (shareTimer.current) clearTimeout(shareTimer.current);
      shareTimer.current = setTimeout(() => setShareCopied(false), 2000);
    } catch {
      /* clipboard blocked — silent no-op */
    }
  }, [story.title, story.permalink]);

  useEffect(() => () => { if (shareTimer.current) clearTimeout(shareTimer.current); }, []);

  const sourceCount = sources.length > 0 ? sources.length : story.source.count;
  const hasNav = Boolean(onNavigate) && totalStories > 1;

  return (
    <div className="page-container">
      {/* The masthead is mounted once, in app/layout.tsx. Mounting a second
          NavBar here stacked two mastheads on the phone Deep Dive
          (headless sweep, 2026-09-21). */}
      <main id="main-content" className="dd-page" aria-label={`Deep dive: ${story.title}`}>
        {/* Top toolbar — Back to feed + prev/next + share. */}
        <div className="dd-page__bar">
          <button type="button" className="dd-page__back" onClick={handleBack} aria-label="Back to feed">
            <ArrowLeft size={18} weight="regular" aria-hidden="true" />
            <span className="dd-page__back-label">Back to feed</span>
          </button>

          <div className="dd-page__bar-right">
            {hasNav && (
              <div className="dd-page__nav">
                <button
                  type="button"
                  className="dd-page__nav-btn"
                  onClick={() => { hapticLight(); onNavigate!("prev"); }}
                  disabled={storyIndex <= 0}
                  aria-label="Previous story"
                >
                  <CaretLeft size={16} weight="bold" aria-hidden="true" />
                </button>
                <span className="dd-page__counter">{storyIndex + 1}/{totalStories}</span>
                <button
                  type="button"
                  className="dd-page__nav-btn"
                  onClick={() => { hapticLight(); onNavigate!("next"); }}
                  disabled={storyIndex >= totalStories - 1}
                  aria-label="Next story"
                >
                  <CaretRight size={16} weight="bold" aria-hidden="true" />
                </button>
              </div>
            )}
            <button type="button" className="dd-page__share" onClick={handleShare} aria-label="Share this story">
              <ShareNetwork size={18} weight="regular" aria-hidden="true" />
              {shareCopied && <span className="dd-page__share-toast" role="status">Link copied</span>}
            </button>
          </div>
        </div>

        {/* Headline + meta + primary bias snapshot */}
        <h1 className="dd-headline dd-page__headline">{story.title}</h1>
        <div className="deep-dive-meta">
          <span className="category-tag">{story.category}</span>
          <span className="dot-separator" aria-hidden="true" />
          <span className="dd-meta-sources text-data">
            {sourceCount} {sourceCount === 1 ? "source" : "sources"}
          </span>
          <span className="dot-separator" aria-hidden="true" />
          <span className="time-tag">{timeAgo(story.publishedAt)}</span>
        </div>

        {story.sigilData && !story.sigilData.pending && (
          <BiasSnapshot
            data={story.sigilData}
            sourceCount={sourceCount}
            variant="inline"
            /* Always hidden: the Spread spectrum below is the coverage view.
               Gating on spectrumSources (empty until the async fetch resolves)
               flashed the bar under the headline, then removed it. */
            hideCoverageBar={true}
          />
        )}

        {/* One scrollable flow (2026-08-11): the Story / Spread segmented switch
            was removed. Summary, spectrum, coverage meta, and source columns now
            stack in the same order as the desktop InlineDeepDive. */}
        <div className="dd-page__content anim-dd-page">
          {/* ---- The Story — summary in a reading-measure column ---- */}
          <section className="dd-page__panel" aria-label="The story">
            <h2 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-2)" }}>The Story</h2>
            <DeepDiveSummary
              summary={story.summary}
              disputed={deepDive?.claimConsensus?.disputed_details}
            />
          </section>

          {/* Subtle inline loading — only while the full source spread is still
              being fetched. The summary + Sigil above stay visible. */}
          {sourcesPending && (
            <p className="dd-page__loading text-meta" role="status">Gathering the full source list</p>
          )}

          {/* ---- The Spread — Sigil + source-lean spectrum ---- */}
          {hasLedeSpectrum && (
            <section className="dd-page__panel dd-page__section" aria-label="The spread">
              <hr className="ink-rule" style={{ margin: "var(--space-5) 0 var(--space-4)" }} aria-hidden="true" />
              <div className="dd-section-head">
                <h2 className="dd-section-label text-meta">The Spread</h2>
                <LeanLabelLegend />
              </div>

              {/* The Bench carries the shape's mark and word once sources are
                  placed; this Sigil stood above it and printed the same word a
                  second time ("Split", then "Split"). It stays only as the
                  fallback while no source can be placed. */}
              {story.sigilData && spectrumSources.length === 0 && (
                <div className="dd-analysis-block__sigil">
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

          {/* ---- Agree / Dispute — what the sources broadly agree on vs where
              they split. Self-omits when the pipeline supplied neither. ---- */}
          <SpreadDisagreement
            consensus={deepDive?.consensus}
            divergence={deepDive?.divergence}
          />

          {/* ---- The coverage: every source's article, open by default. ---- */}
          <CoverageList key={story.id} sources={sources} headingLevel={2} />

          {/* ---- Claim Consensus — cross-source verification (lazy) ---- */}
          {deepDive?.claimConsensus && (
            <section className="dd-page__section" aria-label="Claim Consensus verification">
              <hr className="ink-rule" style={{ margin: "var(--space-5) 0 var(--space-4)" }} aria-hidden="true" />
              <LazyOnView rootMargin="300px 0px" minHeight={120}>
                <ClaimConsensusSection consensus={deepDive.claimConsensus} />
              </LazyOnView>
            </section>
          )}

          {/* ---- Historical Context cross-link (only when keyword matches) ---- */}
          <HistoryContextLink title={story.title} summary={story.summary} />

          {/* Fetch error — retry (only when nothing loaded). */}
          {fetchError && !isLoadingData && sources.length === 0 && (
            <div className="dd-fetch-error">
              <p className="text-base empty-state__body" style={{ color: "var(--fg-muted)", lineHeight: 1.6 }}>
                Failed to load the full source list.
              </p>
              <button className="dd-read-more" onClick={() => setRetryCount((c) => c + 1)}>
                Retry
              </button>
            </div>
          )}

          {/* ---- The end: the next story by name, or the end of the edition. */}
          {onNavigate && storyIndex >= 0 && totalStories > 0 && (
            <DeepDiveNext
              position={storyIndex + 1}
              total={totalStories}
              prev={prevStory ? { title: prevStory.title } : null}
              next={nextStory ? { title: nextStory.title } : null}
              onNavigate={onNavigate}
              onFirst={onFirst}
            />
          )}
        </div>
      </main>
    </div>
  );
}
