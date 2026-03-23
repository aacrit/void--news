"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  ArrowLeft,
  CaretLeft,
  CaretRight,
  X,
} from "@phosphor-icons/react";
import type { Story, StorySource, DeepDiveData, ThreeLensData, OpinionLabel } from "../lib/types";
import { fetchDeepDiveData } from "../lib/supabase";
import { timeAgo } from "../lib/utils";
import { hapticMedium, hapticLight } from "../lib/haptics";
import Sigil from "./Sigil";
import LogoIcon from "./LogoIcon";
import { BiasInspectorInline } from "./BiasInspector";
import DeepDiveSpectrum from "./DeepDiveSpectrum";
import type { DeepDiveSpectrumSource } from "./DeepDiveSpectrum";
import ComparativeView from "./ComparativeView";

/* ---------------------------------------------------------------------------
   DeepDive — Slide-in panel showing unified summary of a story cluster.
   Desktop (1024px+): 50% width panel sliding from the right.
   Mobile: full-screen modal sliding up from the bottom.
   --------------------------------------------------------------------------- */

// Press Analysis arrow bounce plays once per session — after the user has seen
// it, repeating the animation on every panel open is visual noise.
let hasSeenPressHint = false;

interface DeepDiveProps {
  story: Story;
  onClose: () => void;
  /** Card's DOMRect at click time — drives FLIP morph. Null = slide-in fallback. */
  originRect?: DOMRect | null;
  /** Navigate to previous/next story in the feed */
  onNavigate?: (direction: "prev" | "next") => void;
  /** Current story index in filtered list (for counter display) */
  storyIndex?: number;
  /** Total stories in filtered list */
  totalStories?: number;
}

/* --- Main DeepDive component --------------------------------------------- */

export default function DeepDive({ story, onClose, originRect, onNavigate, storyIndex = -1, totalStories = 0 }: DeepDiveProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [contentVisible, setContentVisible] = useState(false);
  const [liveData, setLiveData] = useState<DeepDiveData | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [summaryOverflows, setSummaryOverflows] = useState(false);
  const summaryInnerRef = useRef<HTMLDivElement>(null);
  const [pressAnalysisOpen, setPressAnalysisOpen] = useState(false);
  const [comparativeOpen, setComparativeOpen] = useState(false);
  /** Null = normal slide-in style (isVisible-driven). Object = FLIP morph phase. */
  const [morphStyle, setMorphStyle] = useState<React.CSSProperties | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  // Stable ref for onNavigate — avoids stale closure in keyboard handler
  // without adding it to the useEffect deps (which would re-focus the panel).
  const onNavigateRef = useRef(onNavigate);
  onNavigateRef.current = onNavigate;

  const deepDive: DeepDiveData | undefined = liveData ?? story.deepDive;

  const sources = useMemo(() => deepDive?.sources ?? [], [deepDive]);

  /* ---- Map sources for mini-spectrum component ---- */
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
    [sources]
  );

  /* ---- Trust score helper — for trust badge computation ---- */
  // tierScore + factualRigor * 0.4 + confidence * 0.2 (0–100 scale)
  function computeTrustScore(src: StorySource): number {
    const tierScore = src.tier === "us_major" ? 60 : src.tier === "international" ? 50 : 40;
    const rigor = src.biasScores?.factualRigor ?? 50;
    const conf = (src.confidence ?? 0.5) * 100;
    return Math.round(tierScore * 0.4 + rigor * 0.4 + conf * 0.2);
  }

  /* ---- Check if sources span 2+ lean buckets (for Read All Sides button) ---- */
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

  /* ---- Detect desktop vs mobile for animation choreography ------------- */
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)");
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
            articleTitle: (article.title as string) ?? undefined,
            articleSummary: (article.summary as string) ?? undefined,
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
        if (!cancelled) setIsLoadingData(false);
      }
    }

    loadClusterData();
    return () => { cancelled = true; };
  }, [story.id, story.deepDive]);

  /* ---- Open animation — FLIP morph or slide-in fallback ----------------- */
  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement;

    // iOS Safari ignores overflow:hidden on body — position:fixed is required
    // to actually prevent background scroll. Save scrollY so we can restore it.
    const scrollY = window.scrollY;
    const originalOverflow = document.body.style.overflow;
    const originalPosition = document.body.style.position;
    const originalWidth = document.body.style.width;
    const originalTop = document.body.style.top;

    document.body.style.overflow = "hidden";
    document.body.style.position = "fixed";
    document.body.style.width = "100%";
    document.body.style.top = `-${scrollY}px`;

    hapticMedium();
    const hasMorph = originRect && originRect.width > 0 && panelRef.current;

    if (hasMorph) {
      /* ═══ FLIP MORPH: card expands into panel ═══
         Choreography:
         1. Backdrop blur fades in (feed goes soft behind the card)
         2. Panel appears at the card's exact rect
         3. Panel morphs from card → final panel rect (spring physics)
         4. Content cascades in after morph settles

         The panel is position:fixed with opacity:0 in CSS. We need to
         measure its final rect. We briefly make it visible but off-screen
         via the morphStyle override, then compute the inverse transform. */

      const isDesktopNow = window.innerWidth >= 768;

      // Step 1: Backdrop blur starts immediately
      setIsVisible(true);

      // Step 2: Measure the panel's final position
      // The panel is already in the DOM at its final CSS position (inset:0 or
      // right:0 on desktop). We read that rect, then position it at the card.
      requestAnimationFrame(() => {
        const panel = panelRef.current;
        if (!panel) return;

        // Temporarily make panel visible at final position to measure
        panel.style.opacity = "1";
        panel.style.transform = "none";
        const finalRect = panel.getBoundingClientRect();

        if (finalRect.width === 0) {
          // Can't measure — fall through to slide
          const delay = isDesktopNow ? 120 : 30;
          setTimeout(() => setContentVisible(true), delay);
          return;
        }

        // Compute inverse transform: final → card origin
        const scaleX = originRect.width / finalRect.width;
        const scaleY = originRect.height / finalRect.height;
        const dx = (originRect.left + originRect.width / 2) - (finalRect.left + finalRect.width / 2);
        const dy = (originRect.top + originRect.height / 2) - (finalRect.top + finalRect.height / 2);

        // Step 3: Snap panel to card position (no transition)
        setMorphStyle({
          transform: `translate(${dx}px, ${dy}px) scale(${scaleX}, ${scaleY})`,
          borderRadius: "8px",
          opacity: 1,
          boxShadow: "var(--shadow-e0)",
          transition: "none",
        });

        // Step 4: On next paint, animate from card → final (CINEMATIC + SMOOTH)
        // Slow spring — panel expands with weight and settles gracefully.
        // Shadow trails behind (cinematic shadow lag: 80ms delay).
        requestAnimationFrame(() => {
          setMorphStyle({
            transform: "translate(0, 0) scale(1, 1)",
            borderRadius: isDesktopNow ? "16px" : "16px 16px 0 0",
            opacity: 1,
            boxShadow: "var(--shadow-e3)",
            transition: [
              "transform 650ms cubic-bezier(0.16, 1, 0.3, 1)",
              "border-radius 400ms cubic-bezier(0.16, 1, 0.3, 1)",
              "box-shadow 550ms cubic-bezier(0.16, 1, 0.3, 1) 80ms",
            ].join(", "),
          });

          // Step 5: Content starts cascading AFTER morph mostly settles (~70%)
          setTimeout(() => setContentVisible(true), isDesktopNow ? 400 : 250);

          // Clear morph style after spring fully settles
          setTimeout(() => setMorphStyle(null), 700);
        });
      });
    } else {
      /* ═══ FALLBACK: directional slide-in (keyboard nav, no rect) ═══ */
      requestAnimationFrame(() => {
        setIsVisible(true);
        const delay = window.innerWidth >= 768 ? 350 : 200;
        setTimeout(() => setContentVisible(true), delay);
      });
    }

    return () => {
      document.body.style.overflow = originalOverflow;
      document.body.style.position = originalPosition;
      document.body.style.width = originalWidth;
      document.body.style.top = originalTop;
      // Restore scroll position that was frozen by position:fixed
      window.scrollTo(0, scrollY);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

      // Arrow keys for inter-story navigation (read from ref to avoid stale closure)
      if (onNavigateRef.current && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
        e.preventDefault();
        onNavigateRef.current(e.key === "ArrowLeft" ? "prev" : "next");
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

  /* ---- Detect summary overflow — show "Read more" only when text is clipped ---- */
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

  /* ---- Close — reverse FLIP morph (panel shrinks back into the card) ---- */
  const handleClose = useCallback(() => {
    hapticLight();
    // Phase 1: Content fades out quickly
    setContentVisible(false);

    if (originRect && originRect.width > 0 && panelRef.current) {
      /* ═══ REVERSE MORPH: panel collapses back into the card ═══
         Choreography:
         1. Content fades out (100ms)
         2. Panel morphs from current rect → card origin (500ms spring)
         3. Panel fades to transparent as it nears the card
         4. Backdrop blur fades out — article becomes clear again
         5. onClose fires, DOM unmounts */
      setTimeout(() => {
        const panel = panelRef.current;
        if (!panel) { previousFocusRef.current?.focus(); onClose(); return; }

        const currentRect = panel.getBoundingClientRect();
        const scaleX = originRect.width / currentRect.width;
        const scaleY = originRect.height / currentRect.height;
        const dx = (originRect.left + originRect.width / 2) - (currentRect.left + currentRect.width / 2);
        const dy = (originRect.top + originRect.height / 2) - (currentRect.top + currentRect.height / 2);

        // Phase 2: Panel morphs back to card rect (cinematic reverse)
        setMorphStyle({
          transform: `translate(${dx}px, ${dy}px) scale(${scaleX}, ${scaleY})`,
          borderRadius: "8px",
          opacity: 0,
          boxShadow: "none",
          transition: [
            "transform 550ms cubic-bezier(0.16, 1, 0.3, 1)",
            "border-radius 300ms cubic-bezier(0.16, 1, 0.3, 1)",
            "opacity 250ms cubic-bezier(0.16, 1, 0.3, 1) 250ms",
            "box-shadow 200ms cubic-bezier(0.16, 1, 0.3, 1)",
          ].join(", "),
        });

        // Phase 3: Backdrop fades as panel shrinks (delayed for cinematic overlap)
        setTimeout(() => setIsVisible(false), 220);

        // Phase 4: Cleanup
        setTimeout(() => {
          previousFocusRef.current?.focus();
          onClose();
        }, 550);
      }, 180); // Content fades 150ms, pause, then morph begins
    } else {
      /* ═══ FALLBACK: cinematic slide-out ═══ */
      setTimeout(() => {
        setIsVisible(false);
        setTimeout(() => {
          previousFocusRef.current?.focus();
          onClose();
        }, 550);
      }, 180);
    }
  }, [onClose, originRect]);

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        onClick={handleClose}
        className="deep-dive-backdrop"
        style={{
          opacity: isVisible ? 1 : 0,
          transition: "opacity 450ms cubic-bezier(0.16, 1, 0.3, 1)",
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
        style={morphStyle ?? {
          /* Default open/close when no FLIP morph is active.
             Desktop: cinematic scale + translateY from center.
             Mobile: slide from bottom — bottom sheet.
             Slow, weighted spring — the panel has physical mass. */
          transform: isVisible
            ? isDesktop ? "translate(-50%, -50%) scale(1)" : "translateY(0)"
            : isDesktop ? "translate(-50%, -50%) scale(0.88) translateY(30px)" : "translateY(100%)",
          opacity: isVisible ? 1 : 0,
          boxShadow: isVisible ? "var(--shadow-e3)" : "none",
          transition: isVisible
            ? "transform 650ms cubic-bezier(0.16, 1, 0.3, 1), opacity 0ms, box-shadow 500ms cubic-bezier(0.16, 1, 0.3, 1) 120ms"
            : "transform 550ms cubic-bezier(0.16, 1, 0.3, 1), opacity 0ms 550ms, box-shadow 250ms cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      >
        {/* Mobile drag indicator — pill handle at top of bottom sheet */}
        <div className="dd-drag-indicator" aria-hidden="true" />

        {/* ---- Header --------------------------------------------------- */}
        <header className="deep-dive-panel__header">
          <div className="deep-dive-header-bar">
            <button onClick={handleClose} aria-label="Back to feed" className="deep-dive-back">
              <ArrowLeft size={18} weight="regular" aria-hidden="true" />
              <span className="deep-dive-back-label">Back to feed</span>
            </button>

            {/* Inter-story navigation */}
            {onNavigate && totalStories > 1 && (
              <div className="dd-story-nav">
                <button
                  className="dd-story-nav__btn"
                  onClick={() => { hapticLight(); onNavigate("prev"); }}
                  disabled={storyIndex <= 0}
                  aria-label="Previous story"
                >
                  <CaretLeft size={14} weight="bold" />
                </button>
                <span className="dd-story-nav__counter">
                  {storyIndex + 1}/{totalStories}
                </span>
                <button
                  className="dd-story-nav__btn"
                  onClick={() => { hapticLight(); onNavigate("next"); }}
                  disabled={storyIndex >= totalStories - 1}
                  aria-label="Next story"
                >
                  <CaretRight size={14} weight="bold" />
                </button>
              </div>
            )}

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

        {/* ---- Content (fades in after panel, fades out faster on close) ---- */}
        <div
          className="deep-dive-panel__content"
          style={{
            opacity: contentVisible ? 1 : 0,
            transition: `opacity ${contentVisible ? 450 : 150}ms cubic-bezier(0.16, 1, 0.3, 1)`,
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

          {/* ---- Skeleton Spectrum — shown while loading, if story has bias data ---- */}
          {isLoadingData && !deepDive && story.biasScores && (
            <div className="dd-skeleton-spectrum" aria-hidden="true">
              <div className="dd-skeleton-spectrum__bar" />
              <div className="dd-skeleton-spectrum__indicator"
                style={{ left: `${Math.max(4, Math.min(96, story.biasScores.politicalLean))}%` }}
              />
              <p className="dd-skeleton-spectrum__label text-data">Loading source data...</p>
            </div>
          )}

          {/* ---- Compact action bar: [Sigil | Spectrum | All Sides ▸ | Scoring ▸] -- */}
          {(story.sigilData || spectrumSources.length > 0) && (
            <div
              className={`dd-action-bar anim-dd-section${contentVisible ? " anim-dd-section--visible" : ""}`}
              style={{ marginBottom: "var(--space-4)", transitionDelay: "0ms" }}
            >
              {/* Sigil — xl, left anchor */}
              {story.sigilData && (
                <div className="dd-action-bar__sigil">
                  <Sigil data={story.sigilData} size="xl" />
                </div>
              )}

              {/* Spectrum — fills remaining space */}
              {spectrumSources.length > 0 && (
                <div className="dd-action-bar__spectrum">
                  <DeepDiveSpectrum sources={spectrumSources} />
                </div>
              )}

              {/* Action buttons */}
              <div className="dd-action-bar__buttons">
                {hasCrossLeanSources && (
                  <button
                    className={`dd-action-btn${comparativeOpen ? " dd-action-btn--active" : ""}`}
                    onClick={() => { hapticLight(); setComparativeOpen(v => !v); }}
                    aria-expanded={comparativeOpen}
                    aria-controls="dd-comparative-panel"
                    aria-label={comparativeOpen ? "Close All Sides view" : "Open All Sides view"}
                  >
                    <span>All Sides</span>
                    <span
                      className={`dd-press-trigger__arrow${comparativeOpen ? " dd-press-trigger__arrow--open" : ""}`}
                      aria-hidden="true"
                    >
                      &#9658;
                    </span>
                  </button>
                )}

                {spectrumSources.length > 0 && (
                  <button
                    className={`dd-action-btn${pressAnalysisOpen ? " dd-action-btn--active" : ""}`}
                    onClick={() => { hapticLight(); setPressAnalysisOpen(v => !v); hasSeenPressHint = true; }}
                    aria-label={pressAnalysisOpen ? "Close scoring breakdown" : "Open scoring breakdown"}
                    aria-expanded={pressAnalysisOpen}
                    aria-controls="dd-press-expand-panel"
                  >
                    <span>Scoring</span>
                    <span
                      className={`dd-press-trigger__arrow${pressAnalysisOpen ? " dd-press-trigger__arrow--open" : ""}${hasSeenPressHint ? " dd-press-trigger__arrow--no-bounce" : ""}`}
                      aria-hidden="true"
                    >
                      &#9658;
                    </span>
                  </button>
                )}
              </div>
            </div>
          )}

          {/* ---- Expand panels: All Sides + Scoring (below action bar) --------- */}
          {hasCrossLeanSources && (
            <div
              id="dd-comparative-panel"
              className={`dd-press-expand${comparativeOpen ? " dd-press-expand--open" : ""}`}
              style={{ width: "100%", marginBottom: comparativeOpen ? "var(--space-4)" : 0 }}
            >
              <div className="dd-press-expand__inner">
                <ComparativeView
                  sources={sources}
                  consensusPoints={deepDive?.consensus}
                  divergencePoints={deepDive?.divergence}
                />
              </div>
            </div>
          )}

          {spectrumSources.length > 0 && (
            <div
              id="dd-press-expand-panel"
              className={`dd-press-expand${pressAnalysisOpen ? " dd-press-expand--open" : ""}`}
              style={{ width: "100%", marginBottom: pressAnalysisOpen ? "var(--space-4)" : 0 }}
            >
              <div className="dd-press-expand__inner">
                <BiasInspectorInline sources={sources} />
              </div>
            </div>
          )}

          {/* ---- Summary — flows as article lede, after action bar -------------- */}
          <section aria-label="Story summary" className={`anim-dd-section${contentVisible ? " anim-dd-section--visible" : ""}`} style={{ marginBottom: "var(--space-5)", transitionDelay: "40ms" }}>
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
