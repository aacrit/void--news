"use client";

// Route-scoped CSS — verify.css carries the Claim Consensus / source-grid
// styles that ClaimConsensusSection + ComparativeView depend on. The rest of
// the Deep Dive vocabulary (.dd-lede*, .dd-headline, .dd-collapsible,
// .anim-dd-section, .dd-cascade-*) lives in the globally-imported
// components.css / animations.css / layout-zones.css. inline-dd.css adds the
// in-flow block chrome that the modal does not need.
import "../styles/verify.css";
import "../styles/inline-dd.css";

import { useState, useEffect, useCallback, useMemo } from "react";
import { ShareNetwork } from "@phosphor-icons/react";
import type {
  Story,
  StorySource,
  DeepDiveData,
  ThreeLensData,
  OpinionLabel,
} from "../lib/types";
import { fetchDeepDiveData } from "../lib/supabase";
import { timeAgo } from "../lib/utils";
import { leanToBucket, leanLabel } from "../lib/biasColors";
import { hapticLight } from "../lib/haptics";
import DeepDiveSpectrum from "./DeepDiveSpectrum";
import type { DeepDiveSpectrumSource } from "./DeepDiveSpectrum";
import BiasSnapshot from "./BiasSnapshot";
import ComparativeView from "./ComparativeView";
import ClaimConsensusSection from "./ClaimConsensusSection";
import SixLenses from "./SixLenses";
import SummaryWithContradictions from "./SummaryWithContradictions";
import { findHistoryContext } from "../lib/historyContext";
import LazyOnView from "./LazyOnView";

/* ---------------------------------------------------------------------------
   InlineDeepDive — Deep Dive CONTENT renderer.

   Renders only the Deep Dive content (masthead + sections). It is mounted
   inside DeepDiveOverlay, which owns ALL dialog behaviour: the portal, the
   backdrop, body scroll-lock, focus trap, Escape / backdrop / back-button
   dismissal, focus return, and the enter/exit motion. This component therefore
   does NOT manage positioning, scroll, focus, or Escape — it is presentational.

   (Historic note: this component used to expand as an in-flow accordion inside
   the feed grid on both breakpoints. That inline-expand was replaced by the
   centered-modal / bottom-sheet overlay; the accordion height tween + self
   scroll/focus/Escape were removed because the overlay owns them now.)

   The cascade classes (.anim-dd-section / .dd-cascade-*) fade the sections in
   just after mount (contentVisible flips true on the next frame); under
   prefers-reduced-motion they start visible so nothing animates.
   --------------------------------------------------------------------------- */

/* History is hidden for launch (nav links removed + /history 301s to home).
   While hidden, the Deep Dive archival cross-link must not render (it would
   promise perspectives and bounce the reader to the homepage). Flip to false
   when History ships again as a feature. */
const HISTORY_HIDDEN: boolean = true;

/* Human-readable outlet tier for the source roster chips. Never fabricates a
   tier — the caller passes the tier already present on the source data. */
function tierLabel(tier: string): string {
  if (tier === "us_major") return "US Major";
  if (tier === "international") return "International";
  return "Independent";
}

/* --- History Context Link — subtle archival cross-link (mirrors DeepDive) -- */
function HistoryContextLink({
  title,
  summary,
  visible,
}: {
  title: string;
  summary: string;
  visible: boolean;
}) {
  const match = findHistoryContext(title, summary);
  // History is HIDDEN for launch (2026-08-05): /history 301-redirects to the
  // homepage, so this archival cross-link would promise "N perspectives" and
  // then bounce the reader back to the feed. Gate it off entirely while History
  // is hidden (HISTORY_HIDDEN). The render path below stays intact and reachable
  // for when History returns — flip HISTORY_HIDDEN to false to re-enable.
  if (HISTORY_HIDDEN || !match) return null;

  const perspText =
    match.perspectiveCount > 0
      ? `See how this event is told from ${match.perspectiveCount} perspectives`
      : "Explore this event in the archive";

  return (
    <div
      className={`dd-history-context anim-dd-section dd-cascade-5${visible ? " anim-dd-section--visible" : ""}`}
    >
      <hr className="ink-rule" style={{ margin: "0 0 var(--space-3) 0" }} aria-hidden="true" />
      <span className="dd-history-context__label text-meta" aria-hidden="true">
        Historical Context
      </span>
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


interface InlineDeepDiveProps {
  story: Story;
  /** id applied to the headline so the overlay dialog can aria-labelledby it. */
  titleId?: string;
  /** Legacy prop — the overlay owns dismissal, so this is accepted but unused.
   *  Kept optional so existing (dormant) call sites still type-check. */
  onCollapse?: () => void;
}

export default function InlineDeepDive({ story, titleId }: InlineDeepDiveProps) {
  /* ---- Cascade flag — flips true on the next frame after mount so the
     .anim-dd-section sections fade in. Under reduced motion it starts true so
     the content is visible immediately with no transition. ---- */
  const prefersReduced =
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const [contentVisible, setContentVisible] = useState(prefersReduced);
  const [shareToast, setShareToast] = useState(false);

  /* ---- Live cluster data (copied pattern from DeepDive.tsx) ------------- */
  const [liveData, setLiveData] = useState<DeepDiveData | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  /* ---- Progressive disclosure: source breakdown (Perspectives + lazy) --- */
  const [analysisExpanded, setAnalysisExpanded] = useState(false);

  /* ---- Reset transient state when the parent swaps to a different story
     without unmounting (one-open-at-a-time, selecting another card). ----- */
  useEffect(() => {
    setAnalysisExpanded(false);
  }, [story.id]);

  const deepDive: DeepDiveData | undefined = liveData ?? story.deepDive;

  const sources = useMemo(() => deepDive?.sources ?? [], [deepDive]);

  /* ---- Map sources for the mini-spectrum component ---------------------- */
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
        })),
    [sources],
  );

  /* ---- Sources span 2+ lean buckets? (Source Perspectives gate) -------- */
  const hasCrossLeanSources = useMemo(() => {
    const buckets = new Set<string>();
    for (const src of sources) {
      const lean = src.biasScores?.politicalLean ?? 50;
      if (lean <= 40) buckets.add("left");
      else if (lean <= 60) buckets.add("center");
      else buckets.add("right");
      if (buckets.size >= 2) return true;
    }
    return false;
  }, [sources]);

  /* ---- Fetch live data from Supabase (copied pattern from DeepDive.tsx) - */
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
            // Default an untiered source to "independent" (the neutral floor),
            // not "us_major" — an unknown tier must not inflate credibility.
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
          // When the pipeline supplies no consensus/divergence points, leave
          // them empty so the section is omitted entirely. Asserting "Sources
          // broadly agree..." (or fabricating divergence) with no data behind it
          // misrepresents the coverage.
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

  /* ---- Content cascade — fade the sections in on the frame after mount.
     The overlay owns the panel enter motion; this only staggers the inner
     sections via the .anim-dd-section / .dd-cascade-* classes. Under reduced
     motion contentVisible starts true (initial state), so this is a no-op. */
  useEffect(() => {
    if (contentVisible) return;
    const id = requestAnimationFrame(() => setContentVisible(true));
    return () => cancelAnimationFrame(id);
    // mount only (remounts per story via the key in DeepDiveOverlay)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sourceCount = sources.length > 0 ? sources.length : story.source.count;

  /* Share — native share sheet, clipboard fallback with a brief toast. */
  const handleShare = useCallback(async () => {
    hapticLight();
    const url = typeof window !== "undefined" ? window.location.href : "";
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
      setShareToast(true);
      window.setTimeout(() => setShareToast(false), 2000);
    } catch {
      /* clipboard blocked — silent no-op */
    }
  }, [story.title]);

  return (
    <article className="inline-dd inline-dd--overlay" aria-label={`Deep dive: ${story.title}`}>
      {/* ---- Masthead: share toolbar, then headline. The overlay chrome owns
             the close affordance; this toolbar keeps only Share. -------------- */}
      <header className="inline-dd__header">
        <div className="inline-dd__toolbar">
          <button
            type="button"
            className="inline-dd__action"
            aria-label="Share this story"
            onClick={handleShare}
          >
            <ShareNetwork size={17} weight="regular" aria-hidden="true" />
          </button>
          {shareToast && (
            <span className="inline-dd__share-toast" role="status">Link copied</span>
          )}
        </div>

        <h2 id={titleId} className="inline-dd__headline">
          <span className="inline-dd__headline-text">{story.title}</span>
        </h2>

        <div className="deep-dive-meta inline-dd__meta">
          <span className="category-tag">{story.category}</span>
          <span className="dot-separator" aria-hidden="true" />
          <span className="dd-meta-sources text-data">
            {sourceCount} {sourceCount === 1 ? "source" : "sources"}
          </span>
          <span className="dot-separator" aria-hidden="true" />
          <span className="time-tag">{timeAgo(story.publishedAt)}</span>
        </div>

        {/* Inline bias snapshot — three primary axes right under the headline. */}
        {story.sigilData && !story.sigilData.pending && (
          <BiasSnapshot
            data={story.sigilData}
            sourceCount={sourceCount}
            variant="inline"
            /* The Spread section below plots the full L->R distribution via
               DeepDiveSpectrum (gated on spectrumSources.length > 0). When that
               renders, the small segmented LeanCoverageBar restates it, so hide
               it; keep it as the only coverage signal when the spectrum is
               absent (too few scored sources). */
            hideCoverageBar={spectrumSources.length > 0}
          />
        )}
      </header>

      {/* ---- Content ---------------------------------------------------- */}
      <div className="inline-dd__content">
        {/* Loading skeleton — structured placeholders while Supabase fetches. */}
        {isLoadingData && sources.length === 0 && (
          <div className="dd-loading-skeleton" role="status" aria-label="Loading analysis">
            <span className="dd-loading-skeleton__status text-meta" style={{ color: "var(--fg-muted)" }}>
              Loading analysis...
            </span>
            <div className="dd-loading-skeleton__section">
              <div className="shimmer-line dd-loading-skeleton__bar" />
            </div>
            <div className="dd-loading-skeleton__section">
              <div className="shimmer-line dd-loading-skeleton__line dd-loading-skeleton__line--short" />
              <div className="dd-loading-skeleton__perspectives">
                <div className="shimmer-line dd-loading-skeleton__perspective-card" />
                <div className="shimmer-line dd-loading-skeleton__perspective-card" />
                <div className="shimmer-line dd-loading-skeleton__perspective-card" />
              </div>
            </div>
          </div>
        )}

        {/* ---- The Story — summary in a reading-measure column ---- */}
        <section className={`inline-dd__story anim-dd-section dd-cascade-1${contentVisible ? " anim-dd-section--visible" : ""}`}>
          <h3 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-2)" }}>The Story</h3>
          <p className="text-base dd-summary-text" style={{ lineHeight: 1.75, margin: 0 }}>
            <SummaryWithContradictions
              summary={story.summary}
              disputed={deepDive?.claimConsensus?.disputed_details}
            />
          </p>
        </section>

        {/* ---- The Spread — source-lean spectrum as a full-width band ---- */}
        {spectrumSources.length > 0 && (
          <section
            aria-label="Source spectrum"
            className={`inline-dd__spread anim-dd-section dd-cascade-2${contentVisible ? " anim-dd-section--visible" : ""}`}
          >
            <hr className="ink-rule" style={{ marginBottom: "var(--space-4)" }} aria-hidden="true" />
            <h3 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-3)" }}>The Spread</h3>
            <div className="inline-dd__spectrum">
              <DeepDiveSpectrum sources={spectrumSources} />
            </div>
          </section>
        )}

        {/* ---- All Sources — complete, non-truncating chip roster ----------
             Every source that fed this cluster, as a wrapped pill grid (lean
             dot + name + tier). No "+N more" hidden truncation: the reader sees
             the full roster. Long names ellipsize inside a chip; the grid wraps
             and never causes page-level horizontal scroll. */}
        {sources.length > 0 && (
          <section
            aria-label="All sources"
            className={`inline-dd__sources anim-dd-section dd-cascade-3${contentVisible ? " anim-dd-section--visible" : ""}`}
          >
            <hr className="ink-rule" style={{ marginBottom: "var(--space-4)" }} aria-hidden="true" />
            <h3 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-3)" }}>
              Sources <span className="text-data inline-dd__sources-count">({sources.length})</span>
            </h3>
            <ul className="inline-dd__source-chips">
              {sources.map((src, i) => {
                const lean = src.biasScores?.politicalLean ?? 50;
                const bucket = leanToBucket(lean);
                const label = `${src.name}. ${leanLabel(lean)}. ${tierLabel(src.tier)}.`;
                const inner = (
                  <>
                    <span
                      className="inline-dd__source-dot"
                      data-lean={bucket}
                      aria-hidden="true"
                    />
                    <span className="inline-dd__source-name">{src.name}</span>
                    <span className="inline-dd__source-tier text-data" aria-hidden="true">
                      {tierLabel(src.tier)}
                    </span>
                  </>
                );
                return (
                  <li key={`${src.name}-${i}`} className="inline-dd__source-chip">
                    {src.url && src.url !== "#" ? (
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-dd__source-link"
                        aria-label={label}
                      >
                        {inner}
                      </a>
                    ) : (
                      <span className="inline-dd__source-link inline-dd__source-link--static" aria-label={label}>
                        {inner}
                      </span>
                    )}
                  </li>
                );
              })}
            </ul>
          </section>
        )}

        {/* ---- Six Lenses — 6-axis ink-stamp bias breakdown ---- */}
        {story.sigilData && !story.sigilData.pending && (
          <section
            className={`anim-dd-section dd-cascade-3${contentVisible ? " anim-dd-section--visible" : ""}`}
            aria-label="Six Lenses"
          >
            <hr className="ink-rule" style={{ marginBottom: "var(--space-4)" }} aria-hidden="true" />
            {/* Round agreement for display parity with the other integer axes
                (F14: the stored value can be fractional, e.g. 30.88). Display
                only — the underlying story.sigilData is left untouched. */}
            <SixLenses
              sigilData={{ ...story.sigilData, agreement: Math.round(story.sigilData.agreement) }}
              visible={contentVisible}
            />
          </section>
        )}

        {/* ---- Claim Consensus — cross-source verification (lazy) -------- */}
        {deepDive?.claimConsensus && (
          <section
            className={`anim-dd-section dd-cascade-3${contentVisible ? " anim-dd-section--visible" : ""}`}
            style={{ marginBottom: "var(--space-5)" }}
            aria-label="Claim Consensus verification"
          >
            <hr className="ink-rule" style={{ marginBottom: "var(--space-4)" }} aria-hidden="true" />
            <LazyOnView rootMargin="300px 0px" minHeight={120}>
              <ClaimConsensusSection consensus={deepDive.claimConsensus} />
            </LazyOnView>
          </section>
        )}

        {/* ---- Progressive disclosure trigger (Source Perspectives) ------ */}
        {hasCrossLeanSources && !analysisExpanded && (
          <button
            className={`dd-read-more dd-analysis-trigger anim-dd-section dd-cascade-trigger${contentVisible ? " anim-dd-section--visible" : ""}`}
            onClick={() => { hapticLight(); setAnalysisExpanded(true); }}
          >
            Show source breakdown
          </button>
        )}

        {/* ---- Source Perspectives (collapsed by default, lazy) --------- */}
        {analysisExpanded && hasCrossLeanSources && (
          <section
            aria-label="Source Perspectives"
            className={`anim-dd-section dd-cascade-3${contentVisible ? " anim-dd-section--visible" : ""}`}
            style={{ marginBottom: "var(--space-5)" }}
          >
            <hr className="ink-rule" style={{ marginBottom: "var(--space-4)" }} aria-hidden="true" />
            <h3 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-3)" }}>Source Perspectives</h3>
            <LazyOnView rootMargin="400px 0px" minHeight={200}>
              <ComparativeView
                sources={sources}
                consensusPoints={deepDive?.consensus}
                divergencePoints={deepDive?.divergence}
              />
            </LazyOnView>
          </section>
        )}

        {/* ---- Historical Context cross-link (only when keyword matches) -- */}
        <HistoryContextLink title={story.title} summary={story.summary} visible={contentVisible} />

        {/* Fetch error — retry UI */}
        {fetchError && !isLoadingData && sources.length === 0 && (
          <div className="dd-fetch-error">
            <p className="text-base empty-state__body" style={{ color: "var(--fg-muted)", lineHeight: 1.6 }}>
              Failed to load analysis.
            </p>
            <button className="dd-read-more" onClick={() => setRetryCount((c) => c + 1)}>
              Retry
            </button>
          </div>
        )}

        {/* No deep dive data at all (no error) */}
        {sources.length === 0 && !isLoadingData && !fetchError && (
          <div className="dd-empty-data">
            <p className="text-base empty-state__body--no-margin" style={{ lineHeight: 1.6 }}>
              Detailed coverage data is not yet available for this story.
              Check back after the next pipeline run.
            </p>
          </div>
        )}
      </div>
    </article>
  );
}
