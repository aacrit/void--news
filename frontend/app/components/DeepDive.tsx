"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  ArrowLeft,
  X,
  Check,
  Warning,
} from "@phosphor-icons/react";
import type { Story, StorySource, DeepDiveData, ThreeLensData, OpinionLabel } from "../lib/types";
import { fetchDeepDiveData } from "../lib/supabase";
import { timeAgo } from "../lib/utils";
import Sigil from "./Sigil";
import LogoIcon from "./LogoIcon";
import { BiasInspectorInline } from "./BiasInspector";

/* ---------------------------------------------------------------------------
   DeepDive — Slide-in panel showing unified summary of a story cluster.
   Desktop (1024px+): 50% width panel sliding from the right.
   Mobile: full-screen modal sliding up from the bottom.
   --------------------------------------------------------------------------- */

interface DeepDiveProps {
  story: Story;
  onClose: () => void;
}

/* --- Favicon helper ------------------------------------------------------ */

function getDomain(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ""); }
  catch { return ""; }
}

function faviconUrl(articleUrl: string): string {
  const domain = getDomain(articleUrl);
  if (!domain) return "";
  return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
}

/* --- Lean label helper --------------------------------------------------- */

function leanLabel(lean: number): string {
  if (lean <= 20) return "Far Left";
  if (lean <= 35) return "Left";
  if (lean <= 45) return "Center-Left";
  if (lean <= 55) return "Center";
  if (lean <= 65) return "Center-Right";
  if (lean <= 80) return "Right";
  return "Far Right";
}

/* --- Main DeepDive component --------------------------------------------- */

export default function DeepDive({ story, onClose }: DeepDiveProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [contentVisible, setContentVisible] = useState(false);
  const [liveData, setLiveData] = useState<DeepDiveData | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [pressAnalysisOpen, setPressAnalysisOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const deepDive: DeepDiveData | undefined = liveData ?? story.deepDive;

  const sources = useMemo(() => deepDive?.sources ?? [], [deepDive]);

  /* ---- Compute lean spectrum: 1 above + 1 below track, overlap at 3+ ---- */
  const leanPositions = useMemo(() => {
    const items = sources
      .filter((src) => src.biasScores != null)
      .map((src, idx) => ({ src, idx, lean: src.biasScores?.politicalLean ?? 50 }))
      .sort((a, b) => a.lean - b.lean);

    // Alternate: first source at a lean position goes above, second below.
    // Third+ at the same lean position overlap on the below row.
    const positionCounts: Record<string, number> = {};
    return items.map((item) => {
      // Bucket by ~7% lean proximity
      const bucket = Math.round(item.lean / 7);
      const count = positionCounts[bucket] || 0;
      positionCounts[bucket] = count + 1;

      // 0 = above track, 1 = below track
      const side: "above" | "below" = count === 0 ? "above" : "below";
      const isOverflow = count >= 2; // 3rd+ source at same position
      return { ...item, side, isOverflow };
    });
  }, [sources]);

  /* ---- Detect desktop vs mobile for directional animation -------------- */
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    setIsDesktop(mq.matches);

    function handleChange(e: MediaQueryListEvent) {
      setIsDesktop(e.matches);
    }

    mq.addEventListener("change", handleChange);
    return () => mq.removeEventListener("change", handleChange);
  }, []);

  /* ---- Fetch live data from Supabase ----------------------------------- */
  useEffect(() => {
    let cancelled = false;

    async function loadClusterData() {
      setIsLoadingData(true);
      // Safety timeout: force-close spinner after 5s if fetch never resolves
      const safetyTimeout = setTimeout(() => {
        if (!cancelled) setIsLoadingData(false);
      }, 5000);
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
          // bias_scores may be object (one-to-one) or array (one-to-many)
          const biasRaw = article.bias_scores;
          const bias = Array.isArray(biasRaw)
            ? (biasRaw.length > 0 ? biasRaw[0] : null)
            : (biasRaw ?? null);

          const lean = (bias?.political_lean as number) ?? 50;
          const opinionVal = (bias?.opinion_fact as number) ?? 25;
          const rigor = (bias?.factual_rigor as number) ?? 75;

          // Parse rationale if available — pipeline stores snake_case keys,
          // frontend types use camelCase, so we map here.
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

          // Derive opinion label
          let opinionLabel: OpinionLabel = "Reporting";
          if (opinionVal > 75) opinionLabel = "Editorial";
          else if (opinionVal > 50) opinionLabel = "Opinion";
          else if (opinionVal > 25) opinionLabel = "Analysis";

          // Per-article coverage: based on rigor + confidence (no cluster source count)
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
          });
        }

        // Deduplicate: keep only the first article per source name.
        // Multiple articles from the same outlet in a cluster would otherwise
        // produce duplicate entries in the spectrum and source count display.
        const seenSourceNames = new Set<string>();
        const dedupedSourceList = storySourceList.filter((s) => {
          const key = s.name.toLowerCase().trim();
          if (seenSourceNames.has(key)) return false;
          seenSourceNames.add(key);
          return true;
        });

        if (!cancelled && dedupedSourceList.length > 0) {
          // Use pipeline-generated consensus/divergence from the cluster,
          // falling back only when no data has been computed yet.
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
          });
        }
      } catch {
        /* Silently fall back to mock deepDive data */
      } finally {
        clearTimeout(safetyTimeout);
        if (!cancelled) setIsLoadingData(false);
      }
    }

    loadClusterData();
    return () => { cancelled = true; };
  }, [story.id, story.deepDive]);

  /* ---- Open animation sequence ----------------------------------------- */
  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    requestAnimationFrame(() => {
      setIsVisible(true);
      setTimeout(() => setContentVisible(true), 200);
    });

    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, []);

  /* ---- Focus trap + Escape key ----------------------------------------- */
  useEffect(() => {
    if (!isVisible) return;
    panelRef.current?.focus();

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        handleClose();
        return;
      }

      if (e.key === "Tab" && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isVisible]);

  /* ---- Close with animation — sequenced: content fades first, then panel slides out */
  const handleClose = useCallback(() => {
    setContentVisible(false);
    // Content fades out over 150ms, then panel slides out
    setTimeout(() => {
      setIsVisible(false);
      setTimeout(() => {
        previousFocusRef.current?.focus();
        onClose();
      }, 400);
    }, 150);
  }, [onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        onClick={handleClose}
        className="deep-dive-backdrop"
        style={{
          opacity: isVisible ? 1 : 0,
          transition: "opacity 300ms var(--ease-out)",
        }}
      />

      {/* Panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Deep dive: ${story.title}`}
        tabIndex={-1}
        className="deep-dive-panel"
        style={{
          /* Desktop: slide from right (translateX). Mobile: slide from bottom (translateY).
             Both open and close use the same axis — symmetric animation.
             Spring easing gives physical weight to the panel. */
          transform: isVisible
            ? "translate(0, 0)"
            : isDesktop ? "translateX(100%)" : "translateY(100%)",
          transition: "transform 500ms var(--spring)",
        }}
      >
        {/* ---- Header --------------------------------------------------- */}
        <header className="deep-dive-panel__header">
          <div className="deep-dive-header-bar">
            <button onClick={handleClose} aria-label="Back to feed" className="deep-dive-back">
              <ArrowLeft size={18} weight="regular" aria-hidden="true" />
              <span className="deep-dive-back-label">Back to feed</span>
            </button>

            <button onClick={handleClose} aria-label="Close deep dive" className="deep-dive-close">
              <X size={20} weight="regular" aria-hidden="true" />
            </button>
          </div>

          <h2 className="text-xl" style={{ color: "var(--fg-primary)", marginTop: "var(--space-3)" }}>
            {story.title}
          </h2>

          <div className="deep-dive-meta">
            <span className="category-tag">{story.category}</span>
            <span className="dot-separator" aria-hidden="true" />
            <span className="time-tag" style={{ color: "var(--fg-tertiary)" }}>
              {sources.length > 0 ? sources.length : story.source.count} sources
            </span>
            <span className="dot-separator" aria-hidden="true" />
            <span className="time-tag">{timeAgo(story.publishedAt)}</span>
          </div>
        </header>

        {/* ---- Content (fades in after panel) ----------------------------- */}
        <div
          className="deep-dive-panel__content"
          style={{
            opacity: contentVisible ? 1 : 0,
            transition: "opacity 300ms var(--ease-out)",
          }}
        >
          {/* Loading indicator — analyzing animation while fetching deep dive data */}
          {isLoadingData && !deepDive && (
            <div style={{ padding: "var(--space-5) 0", display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-3)" }}>
              <LogoIcon size={32} animation="analyzing" />
              <span className="text-data" style={{ color: "var(--fg-tertiary)" }}>
                Analyzing coverage...
              </span>
            </div>
          )}

          {/* ---- Sigil — cluster-level bias indicator (first in content) ------- */}
          {story.sigilData && !story.sigilData.pending && (
            <div
              className={`anim-dd-section${contentVisible ? " anim-dd-section--visible" : ""}`}
              style={{ marginBottom: "var(--space-4)", transitionDelay: "50ms" }}
            >
              <Sigil data={story.sigilData} size="lg" />
            </div>
          )}

          {/* ---- Source lean spectrum ------------------------------------------- */}
          {sources.length > 0 && leanPositions.length > 0 && (
            <section aria-label="Source political lean" className={`anim-dd-section${contentVisible ? " anim-dd-section--visible" : ""}`} style={{ marginBottom: "var(--space-4)", transitionDelay: "100ms" }}>
              <div className="dd-spectrum">
                {/* Row above track */}
                <div className="dd-spectrum__row dd-spectrum__row--above">
                  {leanPositions.filter(p => p.side === "above").map(({ src, idx, lean, isOverflow }) => {
                    const favicon = src.url ? faviconUrl(src.url) : "";
                    return (
                      <a
                        key={`above-${src.name}-${idx}`}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={`${src.name} — ${leanLabel(lean)} (${lean})`}
                        aria-label={`${src.name}: ${leanLabel(lean)}`}
                        className={`dd-spectrum__dot${isOverflow ? " dd-spectrum__dot--overflow" : ""}`}
                        style={{ left: `${Math.max(3, Math.min(97, lean))}%` }}
                      >
                        {favicon ? (
                          <img src={favicon} alt="" width={18} height={18} style={{ borderRadius: 2 }} loading="lazy" />
                        ) : (
                          <span className="dd-spectrum__dot-initial">{src.name.charAt(0)}</span>
                        )}
                      </a>
                    );
                  })}
                </div>

                {/* Track with inline labels */}
                <div className="dd-spectrum__track">
                  <span className="dd-spectrum__inline-label dd-spectrum__inline-label--left">Left</span>
                  <span className="dd-spectrum__inline-label dd-spectrum__inline-label--center">Center</span>
                  <span className="dd-spectrum__inline-label dd-spectrum__inline-label--right">Right</span>
                </div>

                {/* Row below track */}
                <div className="dd-spectrum__row dd-spectrum__row--below">
                  {leanPositions.filter(p => p.side === "below").map(({ src, idx, lean, isOverflow }) => {
                    const favicon = src.url ? faviconUrl(src.url) : "";
                    return (
                      <a
                        key={`below-${src.name}-${idx}`}
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        title={`${src.name} — ${leanLabel(lean)} (${lean})`}
                        aria-label={`${src.name}: ${leanLabel(lean)}`}
                        className={`dd-spectrum__dot${isOverflow ? " dd-spectrum__dot--overflow" : ""}`}
                        style={{ left: `${Math.max(3, Math.min(97, lean))}%` }}
                      >
                        {favicon ? (
                          <img src={favicon} alt="" width={18} height={18} style={{ borderRadius: 2 }} loading="lazy" />
                        ) : (
                          <span className="dd-spectrum__dot-initial">{src.name.charAt(0)}</span>
                        )}
                      </a>
                    );
                  })}
                </div>
              </div>

              {/* Press Analysis inline expand — anchored below spectrum */}
              <button
                className="dd-press-trigger"
                onClick={() => setPressAnalysisOpen(v => !v)}
                aria-label={pressAnalysisOpen ? "Close press analysis" : "Open press analysis"}
                aria-expanded={pressAnalysisOpen}
              >
                <span>Press Analysis</span>
                <span
                  className={`dd-press-trigger__arrow${pressAnalysisOpen ? " dd-press-trigger__arrow--open" : ""}`}
                  aria-hidden="true"
                >
                  &#9658;
                </span>
              </button>

              {/* True dynamic-height expand: grid-template-rows 0fr → 1fr */}
              <div className={`dd-press-expand${pressAnalysisOpen ? " dd-press-expand--open" : ""}`}>
                <div className="dd-press-expand__inner">
                  <BiasInspectorInline sources={sources} />
                </div>
              </div>
            </section>
          )}

          {/* ---- Summary — flows as article lede, after spectrum -------------- */}
          <section aria-label="Story summary" className={`anim-dd-section${contentVisible ? " anim-dd-section--visible" : ""}`} style={{ marginBottom: "var(--space-5)", transitionDelay: "150ms" }}>
            <div className={`dd-collapsible${summaryExpanded ? " dd-collapsible--expanded" : ""}`}>
              <p className="text-base dd-summary-text" style={{ lineHeight: 1.75, margin: 0 }}>
                {story.summary}
              </p>
            </div>
            {story.summary && story.summary.length > 600 && !summaryExpanded && (
              <button className="dd-read-more" onClick={() => setSummaryExpanded(true)}>Read more</button>
            )}
          </section>

          {/* ---- Source perspectives: explicit Agreement / Divergence labels -- */}
          {deepDive && (
            (Array.isArray(deepDive.consensus) && deepDive.consensus.length > 0) ||
            (Array.isArray(deepDive.divergence) && deepDive.divergence.length > 0)
          ) && (
            <section aria-labelledby="dd-perspectives" className={`anim-dd-section${contentVisible ? " anim-dd-section--visible" : ""}`} style={{ marginBottom: "var(--space-5)", transitionDelay: "250ms" }}>
              <span id="dd-perspectives" className="dd-perspectives-label">Source Perspectives</span>

              {/* Agreement sub-section */}
              {deepDive && Array.isArray(deepDive.consensus) && deepDive.consensus.length > 0 && (
                <>
                  <span className="dd-perspectives-sublabel dd-perspectives-sublabel--agree">Agreement</span>
                  <ul className="dd-perspectives-list">
                    {deepDive.consensus.map((point, i) => (
                      <li key={`agree-${i}`} className="dd-perspectives-item dd-perspectives-item--agree">
                        <Check size={13} weight="bold" aria-hidden="true" className="dd-perspectives-item__icon" />
                        <span className="dd-perspectives-item__text">{point}</span>
                      </li>
                    ))}
                  </ul>
                </>
              )}

              {/* Divergence sub-section */}
              {deepDive && Array.isArray(deepDive.divergence) && deepDive.divergence.length > 0 && (
                <>
                  <span className="dd-perspectives-sublabel dd-perspectives-sublabel--diverge">Divergence</span>
                  <ul className="dd-perspectives-list">
                    {deepDive.divergence.map((point, i) => (
                      <li key={`diverge-${i}`} className="dd-perspectives-item dd-perspectives-item--diverge">
                        <Warning size={13} weight="bold" aria-hidden="true" className="dd-perspectives-item__icon" />
                        <span className="dd-perspectives-item__text">{point}</span>
                      </li>
                    ))}
                  </ul>
                </>
              )}
            </section>
          )}

          {/* No deep dive data at all */}
          {!deepDive && !isLoadingData && (
            <div style={{ padding: "var(--space-6) 0", textAlign: "center" }}>
              <p className="text-base" style={{ color: "var(--fg-tertiary)", lineHeight: 1.6 }}>
                Detailed coverage data is not yet available for this story.
                Check back after the next pipeline run.
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
