"use client";

// Route-scoped CSS — verify.css carries the Claim Consensus / source-grid
// styles that ClaimConsensusSection + ComparativeView depend on. The rest of
// the Deep Dive vocabulary (.dd-lede*, .dd-headline, .dd-collapsible,
// .anim-dd-section, .dd-cascade-*) lives in the globally-imported
// components.css / animations.css / layout-zones.css. inline-dd.css adds the
// in-flow block chrome that the modal does not need.
import "../styles/verify.css";
import "../styles/inline-dd.css";

import { useState, useEffect, useLayoutEffect, useRef, useCallback, useMemo } from "react";
import { X, ShareNetwork } from "@phosphor-icons/react";
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
  /* ---- Cascade flag — flips true just after the accordion starts opening so
     the .anim-dd-section sections L-cut in (see the mount effect below). ---- */
  const [contentVisible, setContentVisible] = useState(false);
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

  /* ---- Accordion expand on mount + L-cut content cascade -----------------
     The block grows from 0 to its natural height (cards below slide down via
     normal flow), then releases to height:auto so later/lazy content and hover
     overflow (spectrum tooltips, Sigil popup) are not clipped. The
     .anim-dd-section sections fade in just after the grow starts (an L-cut).
     prefers-reduced-motion: skip the height tween and reveal instantly. */
  const articleRef = useRef<HTMLElement>(null);
  const headlineRef = useRef<HTMLButtonElement>(null);

  /* Scroll the open story's headline to just under the sticky nav. Driven from
     the accordion effect (once the block has reached full height) so a story low
     in the feed has enough body below it to actually reach the top — a mount-time
     scrollIntoView (height 0) clamped short and left lower stories mis-seated. */
  const scrollHeadlineToTop = useCallback((behavior: ScrollBehavior) => {
    const el = articleRef.current;
    if (!el) return;
    const top = el.getBoundingClientRect().top + window.scrollY - 64; // nav (~53) + gap
    window.scrollTo({ top: Math.max(0, top), behavior });
  }, []);

  useLayoutEffect(() => {
    const el = articleRef.current;
    if (!el) return;
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) {
      setContentVisible(true);
      scrollHeadlineToTop("auto");
      return;
    }
    const natural = el.scrollHeight;
    el.style.overflow = "hidden";
    el.style.height = "0px";
    void el.offsetHeight; // commit the 0 start before transitioning
    el.style.transition = "height 600ms var(--ease-cinematic)";
    el.style.height = `${natural}px`;
    scrollHeadlineToTop("smooth"); // best-effort start (may clamp low in the feed)

    const release = () => {
      el.style.height = "auto";
      el.style.overflow = "";
      el.style.transition = "";
      scrollHeadlineToTop("smooth"); // authoritative: full height now, so it seats at the top
    };
    const onEnd = (e: TransitionEvent) => {
      if (e.target === el && e.propertyName === "height") {
        el.removeEventListener("transitionend", onEnd);
        release();
      }
    };
    el.addEventListener("transitionend", onEnd);
    const fallback = window.setTimeout(release, 680); // safety if transitionend misses
    const cascade = window.setTimeout(() => setContentVisible(true), 150);
    return () => {
      el.removeEventListener("transitionend", onEnd);
      window.clearTimeout(fallback);
      window.clearTimeout(cascade);
    };
    // mount-only; remounts per story via the key in HomeContent
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /* Collapse: reverse the accordion to 0, then unmount via onCollapse. */
  const collapsingRef = useRef(false);
  const handleCollapse = useCallback(() => {
    hapticLight();
    const el = articleRef.current;
    const reduce =
      typeof window !== "undefined" &&
      window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!el || reduce) {
      onCollapse();
      return;
    }
    if (collapsingRef.current) return;
    collapsingRef.current = true;
    const current = el.scrollHeight;
    el.style.height = `${current}px`;
    el.style.overflow = "hidden";
    void el.offsetHeight;
    el.style.transition =
      "height 480ms var(--ease-cinematic), opacity 420ms var(--ease-cinematic)";
    el.style.height = "0px";
    el.style.opacity = "0";
    let done = false;
    const finish = () => {
      if (done) return;
      done = true;
      onCollapse();
    };
    const onEnd = (e: TransitionEvent) => {
      if (e.target === el && e.propertyName === "height") finish();
    };
    el.addEventListener("transitionend", onEnd);
    window.setTimeout(finish, 560); // safety if transitionend misses
  }, [onCollapse]);

  /* Esc collapses the inline block (parity with the modal's Escape-to-close). */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        handleCollapse();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [handleCollapse]);

  /* Move focus into the block on open so keyboard + screen-reader users land on
     the expanded content. Scroll is owned by the accordion effect above. */
  useEffect(() => {
    headlineRef.current?.focus({ preventScroll: true });
    // mount only (remounts per story via the key in HomeContent)
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
    <article ref={articleRef} className="inline-dd" aria-label={`Deep dive: ${story.title}`}>
      {/* ---- Masthead: share + close toolbar, then headline (also a toggle) -- */}
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
          <button
            type="button"
            className="inline-dd__action"
            aria-label={`Close deep dive: ${story.title}`}
            onClick={handleCollapse}
          >
            <X size={17} weight="bold" aria-hidden="true" />
          </button>
          {shareToast && (
            <span className="inline-dd__share-toast" role="status">Link copied</span>
          )}
        </div>

        <button
          ref={headlineRef}
          type="button"
          className="inline-dd__headline"
          aria-expanded={true}
          aria-label={`Collapse deep dive: ${story.title}`}
          onClick={handleCollapse}
        >
          <span className="inline-dd__headline-text">{story.title}</span>
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

        {/* ---- Six Lenses — 6-axis ink-stamp bias breakdown ---- */}
        {story.sigilData && !story.sigilData.pending && (
          <section
            className={`anim-dd-section dd-cascade-3${contentVisible ? " anim-dd-section--visible" : ""}`}
            aria-label="Six Lenses"
          >
            <hr className="ink-rule" style={{ marginBottom: "var(--space-4)" }} aria-hidden="true" />
            <SixLenses sigilData={story.sigilData} visible={contentVisible} />
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
