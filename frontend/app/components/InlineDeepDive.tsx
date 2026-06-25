"use client";

// Route-scoped CSS — verify.css carries the Claim Consensus / source-grid
// styles that ClaimConsensusSection + ComparativeView depend on. The rest of
// the Deep Dive vocabulary (.dd-lede*, .dd-headline, .dd-collapsible,
// .anim-dd-section, .dd-cascade-*) lives in the globally-imported
// components.css / animations.css / layout-zones.css. inline-dd.css adds the
// in-flow block chrome that the modal does not need.
import "../styles/verify.css";
import "../styles/inline-dd.css";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { CaretUp } from "@phosphor-icons/react";
import type {
  Story,
  StorySource,
  DeepDiveData,
  ThreeLensData,
  OpinionLabel,
} from "../lib/types";
import { fetchDeepDiveData } from "../lib/supabase";
import { timeAgo } from "../lib/utils";
import { hapticLight } from "../lib/haptics";
import Sigil from "./Sigil";
import DeepDiveSpectrum from "./DeepDiveSpectrum";
import type { DeepDiveSpectrumSource } from "./DeepDiveSpectrum";
import BiasSnapshot from "./BiasSnapshot";
import ComparativeView from "./ComparativeView";
import ClaimConsensusSection from "./ClaimConsensusSection";
import { findHistoryContext } from "../lib/historyContext";
import LazyOnView from "./LazyOnView";

/* ---------------------------------------------------------------------------
   InlineDeepDive — Cinematic Inline Deep Dive (stage 1: STATIC).

   Renders the Deep Dive content as an in-flow, full-width block inside the
   feed instead of the DeepDive modal. NO fixed positioning, NO backdrop, NO
   body scroll lock, NO focus trap — it is just a block in the document flow
   that pushes later cards down.

   The data-fetch + derived-data pattern (liveData / spectrumSources /
   hasCrossLeanSources) and the lede block are intentionally duplicated from
   DeepDive.tsx so the legacy modal stays byte-identical. The shared
   sub-components (Sigil, DeepDiveSpectrum, BiasSnapshot, ComparativeView,
   ClaimConsensusSection) are reused directly.

   The cascade classes (.anim-dd-section / .dd-cascade-*) are wired now but
   driven statically (contentVisible = true on mount); the actual reveal
   choreography arrives in a later stage.
   --------------------------------------------------------------------------- */

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
  if (!match) return null;

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
  onCollapse: () => void;
}

export default function InlineDeepDive({ story, onCollapse }: InlineDeepDiveProps) {
  /* ---- Static cascade flag — true on mount (animation lands in a later stage) ---- */
  const [contentVisible, setContentVisible] = useState(true);

  /* ---- Live cluster data (copied pattern from DeepDive.tsx) ------------- */
  const [liveData, setLiveData] = useState<DeepDiveData | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);

  /* ---- Progressive disclosure: source breakdown (Perspectives + lazy) --- */
  const [analysisExpanded, setAnalysisExpanded] = useState(false);

  /* ---- Lede view tabs — phones only. Both panels render (hydration-safe);
     CSS hides the inactive one only <768px keyed on data-lede-view. ------- */
  const [ledeView, setLedeView] = useState<"story" | "spread">("story");
  const ledeTablistRef = useRef<HTMLDivElement>(null);

  /* ---- Summary collapsible (clamp + Read more) ------------------------- */
  const [summaryExpanded, setSummaryExpanded] = useState(() => {
    if (typeof window !== "undefined" && window.innerWidth < 1024) return true;
    return false;
  });
  const [summaryOverflows, setSummaryOverflows] = useState(false);
  const summaryInnerRef = useRef<HTMLDivElement>(null);

  /* Story-id-suffixed ids so multiple instances never collide on
     ids/aria targets. classNames stay intact for the shared CSS. */
  const tabStoryId = `idd-lede-tab-story-${story.id}`;
  const tabSpreadId = `idd-lede-tab-spread-${story.id}`;
  const panelStoryId = `idd-panel-story-${story.id}`;
  const panelSpreadId = `idd-panel-spectrum-${story.id}`;

  const handleLedeTabKey = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight" && e.key !== "Home" && e.key !== "End") return;
      e.preventDefault();
      const next: "story" | "spread" =
        e.key === "Home" ? "story"
          : e.key === "End" ? "spread"
            : ledeView === "story" ? "spread" : "story";
      setLedeView(next);
      hapticLight();
      const id = next === "story" ? tabStoryId : tabSpreadId;
      ledeTablistRef.current?.querySelector<HTMLElement>(`#${id}`)?.focus();
    },
    [ledeView, tabStoryId, tabSpreadId],
  );

  /* ---- Reset transient state when the parent swaps to a different story
     without unmounting (one-open-at-a-time, selecting another card). ----- */
  useEffect(() => {
    setLedeView("story");
    setAnalysisExpanded(false);
    setSummaryExpanded(typeof window !== "undefined" && window.innerWidth < 1024);
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

  /* Lede has a Sigil/Spectrum panel to pair with the summary — drives the
     phone tab bar + the second column. */
  const hasLedeSpectrum = Boolean(story.sigilData) || spectrumSources.length > 0;

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
            tier: ((source?.tier as string) as StorySource["tier"]) ?? "us_major",
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
          const rawConsensus = Array.isArray(story.deepDive?.consensus) ? story.deepDive.consensus : [];
          const rawDivergence = Array.isArray(story.deepDive?.divergence) ? story.deepDive.divergence : [];
          const consensus = rawConsensus.length > 0
            ? rawConsensus
            : ["Sources broadly agree on the key facts of this story"];
          const divergenceData = rawDivergence.length > 0
            ? rawDivergence
            : ["Some differences in framing and emphasis were detected across sources"];

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

  /* ---- Detect summary overflow — show "Read more" only when text clips --- */
  useEffect(() => {
    const el = summaryInnerRef.current;
    if (!el || summaryExpanded) return;

    const check = () => {
      setSummaryOverflows(el.scrollHeight > el.clientHeight + 2);
    };

    check();
    const ro = new ResizeObserver(check);
    ro.observe(el);
    return () => ro.disconnect();
  }, [summaryExpanded, story.summary, contentVisible]);

  // Static-stage no-op reference so the lint rule does not flag the setter as
  // unused; the real reveal choreography (setContentVisible(false) on enter,
  // then true) arrives in a later stage.
  void setContentVisible;

  const sourceCount = sources.length > 0 ? sources.length : story.source.count;

  return (
    <article className="inline-dd" aria-label={`Deep dive: ${story.title}`}>
      {/* ---- Masthead: headline IS the collapse toggle ------------------- */}
      <header className="inline-dd__header">
        <button
          type="button"
          className="inline-dd__headline"
          aria-expanded={true}
          aria-label={`Collapse deep dive: ${story.title}`}
          onClick={() => { hapticLight(); onCollapse(); }}
        >
          <span className="inline-dd__headline-text">{story.title}</span>
          <CaretUp size={18} weight="bold" className="inline-dd__caret" aria-hidden="true" />
        </button>

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

        {/* ---- Lede: Sigil/Spectrum + summary (mirrors DeepDive lede) ---- */}
        <div className="dd-lede" data-lede-view={ledeView}>
          {hasLedeSpectrum && (
            <div
              className="dd-lede__tabs"
              role="tablist"
              aria-label="Story or bias spread"
              ref={ledeTablistRef}
              onKeyDown={handleLedeTabKey}
            >
              <button
                type="button"
                role="tab"
                id={tabStoryId}
                aria-selected={ledeView === "story"}
                aria-controls={panelStoryId}
                tabIndex={ledeView === "story" ? 0 : -1}
                className={`dd-lede__tab${ledeView === "story" ? " dd-lede__tab--active" : ""}`}
                onClick={() => { hapticLight(); setLedeView("story"); }}
              >
                The Story
              </button>
              <button
                type="button"
                role="tab"
                id={tabSpreadId}
                aria-selected={ledeView === "spread"}
                aria-controls={panelSpreadId}
                tabIndex={ledeView === "spread" ? 0 : -1}
                className={`dd-lede__tab${ledeView === "spread" ? " dd-lede__tab--active" : ""}`}
                onClick={() => { hapticLight(); setLedeView("spread"); }}
              >
                The Spread
              </button>
            </div>
          )}

          {/* ---- Sigil + Spectrum (lede context) — first in DOM so the
               desktop float wraps the summary around and under it ---- */}
          {hasLedeSpectrum && (
            <section
              id={panelSpreadId}
              role="tabpanel"
              aria-labelledby={tabSpreadId}
              className={`dd-lede__spectrum anim-dd-section dd-cascade-2${contentVisible ? " anim-dd-section--visible" : ""}`}
            >
              {story.sigilData && (
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

          {/* ---- Summary (lede subject) ---- */}
          <section
            id={panelStoryId}
            role={hasLedeSpectrum ? "tabpanel" : undefined}
            aria-labelledby={hasLedeSpectrum ? tabStoryId : undefined}
            className={`dd-lede__story anim-dd-section dd-cascade-1${contentVisible ? " anim-dd-section--visible" : ""}`}
          >
            <h3 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-2)" }}>The Story</h3>
            <div className={`dd-collapsible${summaryExpanded ? " dd-collapsible--expanded" : ""}${!summaryOverflows && !summaryExpanded ? " dd-collapsible--fits" : ""}`}>
              <div className="dd-collapsible__inner" ref={summaryInnerRef}>
                <p className="text-base dd-summary-text" style={{ lineHeight: 1.75, margin: 0 }}>
                  {story.summary}
                </p>
              </div>
            </div>
            {summaryOverflows && !summaryExpanded && (
              <button className="dd-read-more" onClick={() => { hapticLight(); setSummaryExpanded(true); }}>Read more</button>
            )}
          </section>
        </div>

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
