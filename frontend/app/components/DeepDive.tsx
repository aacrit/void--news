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
   DeepDive — Centered popup overlay showing unified summary of a story cluster.
   Desktop (1024px+): centered modal (75vw, max-width 920px–1080px, 80vh) with
   cinematic shadow and backdrop blur.
   Mobile: full-screen modal sliding up from the bottom.
   --------------------------------------------------------------------------- */

// Press Analysis arrow bounce plays once per session — after the user has seen
// it, repeating the animation on every popup open is visual noise.
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
  const [fetchError, setFetchError] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const [summaryExpanded, setSummaryExpanded] = useState(false);
  const [summaryOverflows, setSummaryOverflows] = useState(false);
  const summaryInnerRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<"summary" | "allsides" | "scoring">("summary");
  /** Null = normal slide-in style (isVisible-driven). Object = FLIP morph phase. */
  const [morphStyle, setMorphStyle] = useState<React.CSSProperties | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);
  // Stable ref for onNavigate — avoids stale closure in keyboard handler
  // without adding it to the useEffect deps (which would re-focus the panel).
  const onNavigateRef = useRef(onNavigate);
  onNavigateRef.current = onNavigate;

  /* ---- Swipe gesture state (mobile only) -------------------------------- */
  const [dragOffset, setDragOffset] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [isDismissing, setIsDismissing] = useState(false);
  const touchStartRef = useRef<{ x: number; y: number; time: number; scrollTop: number; direction: "none" | "vertical" | "horizontal" } | null>(null);

  /* Reset swipe gesture state when the parent navigates to a different story
     without unmounting this component (handleDeepDiveNav changes story prop). */
  useEffect(() => {
    setIsDismissing(false);
    setIsDragging(false);
    setDragOffset(0);
    touchStartRef.current = null;
  }, [story.id]);
  /** Cross-fade opacity for horizontal story swipe navigation */
  const [swipeNavOpacity, setSwipeNavOpacity] = useState(1);

  /* ---- One-time swipe hint (mobile only) -------------------------------- */
  const [showSwipeHint, setShowSwipeHint] = useState(false);

  useEffect(() => {
    if (isDesktop || !isVisible || !onNavigate || totalStories <= 1) return;
    try {
      if (sessionStorage.getItem("dd-swipe-hint-seen")) return;
    } catch { return; }

    let hideTimer: ReturnType<typeof setTimeout> | null = null;
    const showTimer = setTimeout(() => {
      setShowSwipeHint(true);
      hideTimer = setTimeout(() => {
        setShowSwipeHint(false);
        try { sessionStorage.setItem("dd-swipe-hint-seen", "1"); } catch { /* ignore */ }
      }, 2000);
    }, 500);
    return () => {
      clearTimeout(showTimer);
      if (hideTimer) clearTimeout(hideTimer);
    };
  }, [isDesktop, isVisible, onNavigate, totalStories]);

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
    const mq = window.matchMedia("(min-width: 1024px)");
    setIsDesktop(mq.matches);

    function handleChange(e: MediaQueryListEvent) {
      setIsDesktop(e.matches);
    }

    mq.addEventListener("change", handleChange);
    return () => mq.removeEventListener("change", handleChange);
  }, []);

  /* ---- Retry counter — incrementing triggers re-fetch ------------------- */
  const [retryCount, setRetryCount] = useState(0);

  /* ---- Fetch live data from Supabase ----------------------------------- */
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
        if (!cancelled) setFetchError(true);
      } finally {
        if (!cancelled) setIsLoadingData(false);
      }
    }

    loadClusterData();
    return () => { cancelled = true; };
  }, [story.id, story.deepDive, retryCount]);

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
      /* ═══ SCENE 4: MATCH CUT — Card expands into Deep Dive panel ═══
         Cinematic reference: Kubrick match cuts (2001 bone → satellite).
         The headline maintains visual continuity from its card position
         to its panel position — the viewer's eye never loses the subject.

         Choreography (L-cut timing — content begins before morph settles):
         1. Backdrop blur fades in → feed goes shallow DoF (Deakins chiaroscuro)
         2. Panel snaps to card's exact rect (first frame of the match cut)
         3. Panel morphs card → final rect via spring-bouncy (500ms)
            - Shadow depth increases during morph (dolly in: approaching)
            - Border-radius transitions (card edge → panel edge)
            - Box-shadow ramps from e0 → cinematic-dramatic
         4. Content cascades in at ~40% morph completion (L-cut: new scene
            audio starts before old scene visual completes)
         5. Studio reflection ::before fades in after panel settles

         The L-cut offset (content at 180ms into a 500ms morph = 36%) is
         motivated: the viewer needs to see the content "behind" the panel
         before the panel finishes its physical movement. This creates the
         sensation that the Deep Dive was always there — the camera merely
         revealed it. */

      const isDesktopNow = window.innerWidth >= 1024;

      // Step 1: Backdrop blur starts immediately
      setIsVisible(true);

      // Step 2: Measure the panel's final position
      // The panel is already in the DOM at its final CSS position (inset:0 or
      // right:0 on desktop). We read that rect, then position it at the card.
      requestAnimationFrame(() => {
        const panel = panelRef.current;
        if (!panel) return;

        // On desktop the panel is centered via left:50%;top:50% + translate(-50%,-50%).
        // We must measure with that centering transform applied to get the true final rect.
        const centeringTransform = isDesktopNow ? "translate(-50%, -50%)" : "none";
        panel.style.opacity = "1";
        panel.style.transform = centeringTransform;
        const finalRect = panel.getBoundingClientRect();

        if (finalRect.width === 0) {
          const delay = isDesktopNow ? 120 : 30;
          setTimeout(() => setContentVisible(true), delay);
          return;
        }

        // Compute inverse transform: final → card origin
        // On desktop, offsets are relative to the centered position (translate(-50%,-50%))
        // Clamp minimum scale to prevent tiny-card-to-large-panel morphs from
        // starting at an invisible scale (e.g., a narrow card on mobile).
        const MORPH_SCALE_MIN = 0.15;
        const scaleX = Math.max(MORPH_SCALE_MIN, originRect.width / finalRect.width);
        const scaleY = Math.max(MORPH_SCALE_MIN, originRect.height / finalRect.height);
        const dx = (originRect.left + originRect.width / 2) - (finalRect.left + finalRect.width / 2);
        const dy = (originRect.top + originRect.height / 2) - (finalRect.top + finalRect.height / 2);

        // Desktop: offsets are additive to the centering transform
        const snapTransform = isDesktopNow
          ? `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px)) scale(${scaleX}, ${scaleY})`
          : `translate(${dx}px, ${dy}px) scale(${scaleX}, ${scaleY})`;
        const finalTransform = isDesktopNow
          ? "translate(-50%, -50%) scale(1, 1)"
          : "translate(0, 0) scale(1, 1)";

        // Step 3: Snap panel to card position (no transition)
        setMorphStyle({
          transform: snapTransform,
          borderRadius: "8px",
          opacity: 1,
          boxShadow: "var(--shadow-e0)",
          transition: "none",
        });

        // Step 4: Match cut morph — card position → final panel position.
        // setTimeout(0) guarantees the snap frame paints before the
        // transition begins — more reliable than nested rAF on 90/120Hz.
        //
        // The spring-bouncy easing (500ms) provides the dramatic overshoot
        // that makes the panel feel like it has physical mass — it arrives
        // with momentum, overshoots slightly, then settles into position.
        // This is the Spielberg "motivated camera" approach: the camera
        // movement has weight and inertia.
        //
        // Shadow ramps from e0 → cinematic-lifted (maximum depth) with
        // a 60ms delay — shadows lag matter, consistent with the card
        // hover dolly-in physics throughout the system.
        setTimeout(() => {
          setMorphStyle({
            transform: finalTransform,
            borderRadius: isDesktopNow ? "16px" : "16px 16px 0 0",
            opacity: 1,
            boxShadow: "var(--shadow-cinematic-lifted)",
            transition: [
              "transform 500ms var(--spring-bouncy)",
              "border-radius 350ms var(--spring-bouncy)",
              "box-shadow 400ms cubic-bezier(0.16, 1, 0.3, 1) 60ms",
            ].join(", "),
          });

          // L-cut: content cascades in while morph is still settling.
          // At 180ms (36% of 500ms morph), the panel is mid-spring —
          // this overlap creates the cinematic sensation that the content
          // was always there and the camera merely revealed it.
          setTimeout(() => setContentVisible(true), isDesktopNow ? 180 : 120);

          // Clear morph style after spring fully settles
          setTimeout(() => {
            setMorphStyle(null);
            // Signal CSS that the panel has settled — enables studio
            // reflection ::before fade-in (the key light catching the
            // top edge of the panel, like a glass refraction artifact).
            panelRef.current?.setAttribute('data-settled', '');
          }, 550);
        }, 0);
      });
    } else {
      /* ═══ FALLBACK: directional slide-in (keyboard nav, no rect) ═══ */
      requestAnimationFrame(() => {
        setIsVisible(true);
        const delay = window.innerWidth >= 768 ? 200 : 120;
        setTimeout(() => {
          setContentVisible(true);
          panelRef.current?.setAttribute('data-settled', '');
        }, delay);
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
    // Remove settled state — hides studio reflection ::before immediately
    panelRef.current?.removeAttribute('data-settled');
    // Phase 1: Content fades out quickly
    setContentVisible(false);

    if (originRect && originRect.width > 0 && panelRef.current) {
      /* ═══ SCENE 5: REVERSE SHOT — Panel collapses back to card ═══
         Cinematic reference: The reverse shot in conversation editing.
         After the close-up (Deep Dive), cut back to the wide (feed).

         Asymmetric timing is critical here:
         - Open: bouncy, dramatic, 500ms (the reveal is the spectacle)
         - Close: snappy, decisive, 380ms (returning is editorial efficiency)

         This asymmetry mirrors real film editing: establishing shots are
         held longer, reaction shots are cut quicker. The viewer has
         already absorbed the Deep Dive content; the close should feel
         like a confident editorial decision, not a slow retreat.

         Choreography:
         1. Content fades out (100ms) — J-cut: content exits first
         2. Panel morphs panel rect → card origin (380ms spring-snappy)
         3. Panel fades to transparent as it approaches the card
         4. Backdrop blur fades out at 80ms — L-cut: feed refocuses
            before panel physically reaches the card. This creates the
            sensation that the world behind is already sharp by the time
            the viewer's attention returns to it.
         5. onClose fires, DOM unmounts */
      setTimeout(() => {
        const panel = panelRef.current;
        if (!panel) { previousFocusRef.current?.focus(); onClose(); return; }

        const currentRect = panel.getBoundingClientRect();
        const MORPH_SCALE_MIN = 0.15;
        const scaleX = Math.max(MORPH_SCALE_MIN, originRect.width / currentRect.width);
        const scaleY = Math.max(MORPH_SCALE_MIN, originRect.height / currentRect.height);
        const dx = (originRect.left + originRect.width / 2) - (currentRect.left + currentRect.width / 2);
        const dy = (originRect.top + originRect.height / 2) - (currentRect.top + currentRect.height / 2);

        const isDesktopNow = window.innerWidth >= 1024;
        const closeTransform = isDesktopNow
          ? `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px)) scale(${scaleX}, ${scaleY})`
          : `translate(${dx}px, ${dy}px) scale(${scaleX}, ${scaleY})`;

        // Phase 2: Reverse shot morph — spring-snappy for decisive close.
        // 380ms (vs 500ms open) = 24% faster. The close is a cut-back,
        // not a reveal. Shadow collapses to nothing (dolly out: receding).
        setMorphStyle({
          transform: closeTransform,
          borderRadius: "8px",
          opacity: 0,
          boxShadow: "none",
          transition: [
            "transform 380ms var(--spring-snappy)",
            "border-radius 250ms var(--spring-snappy)",
            "opacity 200ms cubic-bezier(0.16, 1, 0.3, 1) 150ms",
            "box-shadow 150ms cubic-bezier(0.16, 1, 0.3, 1)",
          ].join(", "),
        });

        // Phase 3: L-cut — backdrop fades early so the feed is already
        // sharp before the panel reaches the card. The viewer's peripheral
        // vision registers the returning world before their foveal attention
        // leaves the closing panel.
        setTimeout(() => setIsVisible(false), 80);

        // Phase 4: Cleanup — fast dismissal matches editorial pace
        setTimeout(() => {
          previousFocusRef.current?.focus();
          onClose();
        }, 400);
      }, 100); // J-cut: content fades 100ms before morph begins
    } else {
      /* ═══ FALLBACK: fast slide-out ═══ */
      setTimeout(() => {
        setIsVisible(false);
        setTimeout(() => {
          previousFocusRef.current?.focus();
          onClose();
        }, 400);
      }, 100);
    }
  }, [onClose, originRect]);

  /* ---- Swipe-to-dismiss touch handlers (mobile only) -------------------- */

  const handleTouchStart = useCallback((e: React.TouchEvent) => {
    if (isDesktop) return;
    const panel = panelRef.current;
    if (!panel) return;

    const touch = e.touches[0];
    const scrollTop = panel.scrollTop;

    touchStartRef.current = {
      x: touch.clientX,
      y: touch.clientY,
      time: Date.now(),
      scrollTop,
      direction: "none",
    };
  }, [isDesktop]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (isDesktop || !touchStartRef.current) return;

    const touch = e.touches[0];
    const deltaX = touch.clientX - touchStartRef.current.x;
    const deltaY = touch.clientY - touchStartRef.current.y;
    const absX = Math.abs(deltaX);
    const absY = Math.abs(deltaY);

    // Determine direction on first significant movement
    if (touchStartRef.current.direction === "none" && (absX > 10 || absY > 10)) {
      touchStartRef.current.direction = absX > absY * 1.5 ? "horizontal" : "vertical";
    }

    // --- Horizontal swipe (story navigation) ---
    if (touchStartRef.current.direction === "horizontal" && onNavigateRef.current) {
      // Don't interfere with vertical scroll
      return;
    }

    // --- Vertical swipe (dismiss) ---
    if (touchStartRef.current.direction !== "vertical") return;
    if (deltaY <= 0) return;

    // Guard: if user started scrolling from mid-content, don't intercept
    const target = e.target as Node;
    const dragIndicator = panelRef.current?.querySelector(".dd-drag-indicator");
    const isOnDragIndicator = dragIndicator?.contains(target) ?? false;
    if (touchStartRef.current.scrollTop > 5 && !isOnDragIndicator) return;

    // Prevent page scroll while we're handling the drag
    e.preventDefault();

    // Rubber-band resistance — dampened feel
    const offset = deltaY * 0.6;
    setDragOffset(offset);
    setIsDragging(true);
  }, [isDesktop]);

  const handleTouchEnd = useCallback((e: React.TouchEvent) => {
    if (isDesktop || !touchStartRef.current) return;

    const start = touchStartRef.current;
    const touch = e.changedTouches[0];
    touchStartRef.current = null;

    // --- Horizontal swipe end → navigate stories ---
    if (start.direction === "horizontal" && onNavigateRef.current) {
      const deltaX = touch.clientX - start.x;
      const elapsed = Date.now() - start.time;
      const velocity = elapsed > 0 ? Math.abs(deltaX) / elapsed : 0;

      if (Math.abs(deltaX) > 60 || velocity > 0.3) {
        const dir = deltaX < 0 ? "next" : "prev";
        hapticLight();
        // Cross-fade content
        setSwipeNavOpacity(0);
        setTimeout(() => {
          onNavigateRef.current?.(dir);
          setSwipeNavOpacity(1);
        }, 150);
        return;
      }
    }

    // --- Vertical swipe end → dismiss ---
    if (!isDragging) return;

    const elapsed = Date.now() - start.time;
    const velocity = elapsed > 0 ? dragOffset / elapsed : 0;
    const shouldDismiss = dragOffset > 120 || velocity > 0.5;

    if (shouldDismiss) {
      hapticMedium();
      setIsDismissing(true);
      setIsDragging(false);
      setDragOffset(window.innerHeight);
      setTimeout(() => {
        previousFocusRef.current?.focus();
        onClose();
      }, 300);
    } else {
      setIsDragging(false);
      setDragOffset(0);
    }
  }, [isDesktop, isDragging, dragOffset, onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        onClick={handleClose}
        className="deep-dive-backdrop"
        style={{
          opacity: isVisible ? Math.max(0, 1 - dragOffset / 400) : 0,
          transition: isDragging
            ? "none"
            : isVisible
              ? "opacity 300ms cubic-bezier(0.16, 1, 0.3, 1)"
              : "opacity 250ms cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      />

      {/* Panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Deep dive: ${story.title}`}
        tabIndex={-1}
        className={`deep-dive-panel${isDragging ? " deep-dive-panel--dragging" : ""}`}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={handleTouchEnd}
        style={morphStyle ?? {
          /* Default open/close when no FLIP morph is active.
             Desktop: spring scale + translateY from center.
             Mobile: spring slide from bottom — bottom sheet. */
          transform: isVisible
            ? isDesktop
              ? "translate(-50%, -50%) scale(1)"
              : `translateY(${dragOffset}px)`
            : isDesktop
              ? "translate(-50%, -50%) scale(0.95) translateY(12px)"
              : "translateY(100%)",
          opacity: isVisible ? 1 : 0,
          boxShadow: isVisible ? "var(--shadow-cinematic-dramatic)" : "none",
          transition: isDragging
            ? "none"
            : isDismissing
              ? "transform 280ms cubic-bezier(0.2, 1, 0.3, 1)"
              : isVisible
                ? "transform 520ms var(--spring-bouncy), opacity 180ms cubic-bezier(0.16, 1, 0.3, 1), box-shadow 450ms cubic-bezier(0.16, 1, 0.3, 1) 60ms"
                : "transform 350ms var(--spring-snappy), opacity 180ms cubic-bezier(0.16, 1, 0.3, 1) 150ms, box-shadow 180ms cubic-bezier(0.16, 1, 0.3, 1)",
        }}
      >
        {/* Mobile drag indicator — pill handle at top of bottom sheet */}
        <div className={`dd-drag-indicator${isDragging ? " dd-drag-indicator--grabbed" : ""}`} aria-hidden="true" />

        {/* ---- Header --------------------------------------------------- */}
        <header className="deep-dive-panel__header">
          <div className="deep-dive-header-bar">
            <button onClick={handleClose} aria-label="Back to feed" className="deep-dive-back">
              <ArrowLeft size={18} weight="regular" aria-hidden="true" />
              <span className="deep-dive-back-label">Back to feed</span>
            </button>
            <span className="dd-brand-label" aria-hidden="true">void --deep-dive</span>

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
                {/* One-time swipe hint for mobile users */}
                {showSwipeHint && (
                  <span
                    className="dd-swipe-hint"
                    style={{
                      opacity: showSwipeHint ? 1 : 0,
                      transition: "opacity 300ms ease-out",
                    }}
                    aria-hidden="true"
                  >
                    swipe for next story
                  </span>
                )}
              </div>
            )}

            <button onClick={handleClose} aria-label="Close deep dive" className="deep-dive-close">
              <X size={20} weight="regular" aria-hidden="true" />
            </button>
          </div>

          <h2 className="dd-headline">
            {story.title}
          </h2>

          <div className="deep-dive-meta">
            <span className="category-tag">{story.category}</span>
            <span className="dot-separator" aria-hidden="true" />
            <span className="dd-meta-sources text-data">
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
            opacity: contentVisible ? swipeNavOpacity : 0,
            transition: `opacity ${swipeNavOpacity < 1 ? 120 : contentVisible ? 450 : 150}ms cubic-bezier(0.16, 1, 0.3, 1)`,
          }}
        >
          {/* Loading skeleton — structured placeholders while Supabase fetches data.
               Check sources.length rather than !deepDive because the homepage query
               populates deepDive with an empty sources array. */}
          {isLoadingData && sources.length === 0 && (
            <div className="dd-loading-skeleton" role="status" aria-label="Loading analysis">
              <span className="dd-loading-skeleton__status text-meta" style={{ color: "var(--fg-muted)" }}>
                Loading analysis...
              </span>

              {/* Spectrum bar placeholder */}
              <div className="dd-loading-skeleton__section">
                <div className="shimmer-line dd-loading-skeleton__bar" />
              </div>

              {/* Source perspective placeholders */}
              <div className="dd-loading-skeleton__section">
                <div className="shimmer-line dd-loading-skeleton__line dd-loading-skeleton__line--short" />
                <div className="dd-loading-skeleton__perspectives">
                  <div className="shimmer-line dd-loading-skeleton__perspective-card" />
                  <div className="shimmer-line dd-loading-skeleton__perspective-card" />
                  <div className="shimmer-line dd-loading-skeleton__perspective-card" />
                </div>
              </div>

              {/* Bias inspector score placeholders */}
              <div className="dd-loading-skeleton__section">
                <div className="shimmer-line dd-loading-skeleton__line dd-loading-skeleton__line--short" />
                <div className="dd-loading-skeleton__scores">
                  <div className="shimmer-line dd-loading-skeleton__score" />
                  <div className="shimmer-line dd-loading-skeleton__score" />
                  <div className="shimmer-line dd-loading-skeleton__score" />
                  <div className="shimmer-line dd-loading-skeleton__score" />
                </div>
              </div>
            </div>
          )}

          {/* ---- Sigil (stacked: icon above, lean+underline below) + full-width Spectrum ---- */}
          {(story.sigilData || spectrumSources.length > 0) && (
            <div
              className={`dd-analysis-block anim-dd-section${contentVisible ? " anim-dd-section--visible" : ""}`}
              style={{ marginBottom: "var(--space-4)", transitionDelay: "150ms" }}
            >
              {story.sigilData && (
                <div className="dd-analysis-block__sigil">
                  <Sigil data={story.sigilData} size="xl" />
                </div>
              )}
              {spectrumSources.length > 0 && (
                <div className="dd-analysis-block__spectrum">
                  <DeepDiveSpectrum sources={spectrumSources} />
                </div>
              )}
            </div>
          )}

          {/* ---- Tab bar (hidden when only Summary tab exists) ---- */}
          {(hasCrossLeanSources || spectrumSources.length > 0) && (
            <nav
              className={`dd-tabs anim-dd-section${contentVisible ? " anim-dd-section--visible" : ""}`}
              role="tablist"
              aria-label="Deep dive sections"
              style={{ transitionDelay: "250ms" }}
            >
              <button
                id="dd-tab-summary"
                role="tab"
                aria-selected={activeTab === "summary"}
                aria-controls="dd-panel-summary"
                className={`dd-tab${activeTab === "summary" ? " dd-tab--active" : ""}`}
                onClick={() => { hapticLight(); setActiveTab("summary"); }}
              >
                Summary
              </button>
              {hasCrossLeanSources && (
                <button
                  id="dd-tab-allsides"
                  role="tab"
                  aria-selected={activeTab === "allsides"}
                  aria-controls="dd-panel-allsides"
                  className={`dd-tab${activeTab === "allsides" ? " dd-tab--active" : ""}`}
                  onClick={() => { hapticLight(); setActiveTab("allsides"); }}
                >
                  All Sides
                </button>
              )}
              {spectrumSources.length > 0 && (
                <button
                  id="dd-tab-scoring"
                  role="tab"
                  aria-selected={activeTab === "scoring"}
                  aria-controls="dd-panel-scoring"
                  className={`dd-tab${activeTab === "scoring" ? " dd-tab--active" : ""}`}
                  onClick={() => { hapticLight(); setActiveTab("scoring"); }}
                >
                  Scoring
                </button>
              )}
            </nav>
          )}

          {/* ---- Tab panels ---- */}
          {activeTab === "summary" && (
            <section id="dd-panel-summary" role="tabpanel" aria-labelledby="dd-tab-summary" className={`anim-dd-section${contentVisible ? " anim-dd-section--visible" : ""}`} style={{ marginBottom: "var(--space-5)", transitionDelay: "350ms" }}>
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
          )}

          {activeTab === "allsides" && hasCrossLeanSources && (
            <section id="dd-panel-allsides" role="tabpanel" aria-labelledby="dd-tab-allsides" className={`anim-dd-section${contentVisible ? " anim-dd-section--visible" : ""}`} style={{ marginBottom: "var(--space-5)", transitionDelay: "350ms" }}>
              <ComparativeView
                sources={sources}
                consensusPoints={deepDive?.consensus}
                divergencePoints={deepDive?.divergence}
              />
            </section>
          )}

          {activeTab === "scoring" && spectrumSources.length > 0 && (
            <section id="dd-panel-scoring" role="tabpanel" aria-labelledby="dd-tab-scoring" className={`anim-dd-section${contentVisible ? " anim-dd-section--visible" : ""}`} style={{ marginBottom: "var(--space-5)", transitionDelay: "350ms" }}>
              <BiasInspectorInline sources={sources} />
            </section>
          )}

          {/* Fetch error — retry UI */}
          {fetchError && !isLoadingData && sources.length === 0 && (
            <div className="dd-fetch-error">
              <p className="text-base empty-state__body" style={{ color: "var(--fg-muted)", lineHeight: 1.6 }}>
                Failed to load analysis.
              </p>
              <button
                className="dd-read-more"
                onClick={() => setRetryCount((c) => c + 1)}
              >
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
      </div>
    </>
  );
}
