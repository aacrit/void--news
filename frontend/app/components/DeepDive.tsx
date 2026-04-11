"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  ArrowLeft,
  CaretLeft,
  CaretRight,
  X,
} from "@phosphor-icons/react";
import type { Story, StorySource, DeepDiveData, ThreeLensData, OpinionLabel, SigilData, DisputedClaim } from "../lib/types";
import { fetchDeepDiveData } from "../lib/supabase";
import { timeAgo, BASE_PATH } from "../lib/utils";
import { hapticMedium, hapticLight, hapticMicro } from "../lib/haptics";
import { generateShareCardImage, generateSquareCardImage, generateStoryCardImage } from "../lib/shareCardRenderer";
import { findHistoryContext } from "../lib/historyContext";
import Sigil from "./Sigil";
import LogoIcon from "./LogoIcon";
import DeepDiveSpectrum from "./DeepDiveSpectrum";
import type { DeepDiveSpectrumSource } from "./DeepDiveSpectrum";
import ComparativeView from "./ComparativeView";
import ClaimConsensusSection from "./ClaimConsensusSection";
import ClaimMark from "./ClaimMark";

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

/* --- Six Lenses — ink-stamp 6-axis bias scores --------------------------- */

const SIX_AXES: { id: string; name: string; key: keyof SigilData }[] = [
  { id: "lean",           name: "Political Lean",  key: "politicalLean" },
  { id: "sensationalism", name: "Sensationalism",   key: "sensationalism" },
  { id: "opinion",        name: "Opinion",           key: "opinionFact" },
  { id: "rigor",          name: "Factual Rigor",     key: "factualRigor" },
  { id: "framing",        name: "Framing",           key: "framing" },
  { id: "tracking",       name: "Agreement",         key: "agreement" },
];

function SixLenses({ sigilData, visible }: { sigilData: SigilData; visible: boolean }) {
  const [activeAxis, setActiveAxis] = useState<string | null>(null);
  const [isMobileLens, setIsMobileLens] = useState(false);
  const [showSecondary, setShowSecondary] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobileLens(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobileLens(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  /* Priority order per memory rule: lean is hero, rigor second, opinion third */
  const PRIMARY_IDS = new Set(["lean", "rigor", "opinion"]);
  const primaryAxes = SIX_AXES.filter(a => PRIMARY_IDS.has(a.id));
  const secondaryAxes = SIX_AXES.filter(a => !PRIMARY_IDS.has(a.id));

  const renderAxis = (axis: typeof SIX_AXES[0], i: number) => {
    const score = sigilData[axis.key] as number;
    const dotCount = Math.max(1, Math.round((score / 100) * 5));
    const isActive = activeAxis === axis.id;
    return (
      <button
        key={axis.id}
        className={`dd-lens${isActive ? " dd-lens--active" : ""}${visible ? " dd-lens--visible" : ""}`}
        style={{ "--lens-delay": `${450 + i * 50}ms` } as React.CSSProperties}
        onClick={() => { hapticMicro(); setActiveAxis(isActive ? null : axis.id); }}
        aria-expanded={isActive}
        aria-label={`${axis.name}: ${score} out of 100`}
      >
        <span className="dd-lens__score">{score}</span>
        <span className="dd-lens__dots" aria-hidden="true">
          {Array.from({ length: 5 }, (_, di) => (
            <span key={di} className={`dd-lens__pip${di < dotCount ? " dd-lens__pip--filled" : ""}`} />
          ))}
        </span>
        <span className="dd-lens__name">{axis.name}</span>
      </button>
    );
  };

  return (
    <div className="dd-lenses">
      <h3 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-3)" }}>Six Lenses</h3>
      {isMobileLens ? (
        <>
          <div className={`dd-lenses__grid${activeAxis ? " dd-lenses__grid--has-active" : ""}`}>
            {primaryAxes.map((axis, i) => renderAxis(axis, i))}
          </div>
          <div
            className="dd-lenses__secondary"
            style={{
              maxHeight: showSecondary ? "300px" : "0",
              overflow: "hidden",
              transition: "max-height 300ms var(--ease-out)",
            }}
          >
            <div className={`dd-lenses__grid${activeAxis ? " dd-lenses__grid--has-active" : ""}`}>
              {secondaryAxes.map((axis, i) => renderAxis(axis, i + 3))}
            </div>
          </div>
          <button
            className="dd-lenses__expand text-meta"
            onClick={() => { hapticMicro(); setShowSecondary(!showSecondary); }}
            aria-expanded={showSecondary}
          >
            {showSecondary ? "Show less" : `${secondaryAxes.length} more axes`}
          </button>
        </>
      ) : (
        <div className={`dd-lenses__grid${activeAxis ? " dd-lenses__grid--has-active" : ""}`}>
          {SIX_AXES.map((axis, i) => renderAxis(axis, i))}
        </div>
      )}
      <a href={`${BASE_PATH}/sources/#methodology`} className="dd-lenses__link text-meta">
        How we score
      </a>
    </div>
  );
}

/* --- History Context Link — subtle archival cross-link -------------------- */

function HistoryContextLink({ title, summary, visible }: { title: string; summary: string; visible: boolean }) {
  const match = findHistoryContext(title, summary);
  if (!match) return null;

  const perspText = match.perspectiveCount > 0
    ? `See how this event is told from ${match.perspectiveCount} perspectives`
    : "Explore this event in the archive";

  return (
    <div className={`dd-history-context anim-dd-section dd-cascade-5${visible ? " anim-dd-section--visible" : ""}`}>
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

/* --- Inline contradiction highlight helper -------------------------------- */

function renderSummaryWithContradictions(
  summary: string,
  disputedDetails?: DisputedClaim[],
): React.ReactNode {
  if (!disputedDetails?.length || !summary) return summary;

  const targets: { phrase: string; dispute: DisputedClaim }[] = [];
  for (const d of disputedDetails) {
    for (const version of [d.version_a, d.version_b]) {
      if (!version) continue;
      const phrases = version.split(/[.!?]+/).map((s) => s.trim()).filter((s) => s.length >= 12);
      for (const phrase of phrases) {
        if (summary.toLowerCase().includes(phrase.toLowerCase())) {
          targets.push({ phrase, dispute: d });
        }
      }
    }
    if (d.topic && d.topic.length >= 8 && summary.toLowerCase().includes(d.topic.toLowerCase())) {
      if (!targets.some((t) => t.dispute === d)) {
        targets.push({ phrase: d.topic, dispute: d });
      }
    }
  }

  if (targets.length === 0) return summary;

  const matches: { start: number; end: number; dispute: DisputedClaim; text: string }[] = [];
  const lower = summary.toLowerCase();
  for (const { phrase, dispute } of targets) {
    const idx = lower.indexOf(phrase.toLowerCase());
    if (idx >= 0) {
      const overlaps = matches.some(
        (m) => (idx >= m.start && idx < m.end) || (idx + phrase.length > m.start && idx + phrase.length <= m.end),
      );
      if (!overlaps) {
        matches.push({ start: idx, end: idx + phrase.length, dispute, text: summary.slice(idx, idx + phrase.length) });
      }
    }
  }

  if (matches.length === 0) return summary;
  matches.sort((a, b) => a.start - b.start);

  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  for (let i = 0; i < matches.length; i++) {
    const m = matches[i];
    if (cursor < m.start) nodes.push(summary.slice(cursor, m.start));
    nodes.push(<ClaimMark key={`cm-${i}`} text={m.text} disputed={m.dispute} />);
    cursor = m.end;
  }
  if (cursor < summary.length) nodes.push(summary.slice(cursor));
  return <>{nodes}</>;
}

/* --- Main DeepDive component --------------------------------------------- */

export default function DeepDive({ story, onClose, originRect, onNavigate, storyIndex = -1, totalStories = 0 }: DeepDiveProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [contentVisible, setContentVisible] = useState(false);
  const [liveData, setLiveData] = useState<DeepDiveData | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const [summaryExpanded, setSummaryExpanded] = useState(() => {
    if (typeof window !== "undefined" && window.innerWidth < 1024) return true;
    return false;
  });
  const [analysisExpanded, setAnalysisExpanded] = useState(false);
  const [summaryOverflows, setSummaryOverflows] = useState(false);
  const summaryInnerRef = useRef<HTMLDivElement>(null);
  // Tabs removed — Deep Dive is now a single continuous scroll view
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
  const touchStartRef = useRef<{ x: number; y: number; time: number; scrollTop: number; direction: "none" | "vertical" | "horizontal"; hapticFired: boolean } | null>(null);

  /** Cross-fade opacity for horizontal story swipe navigation */
  const [swipeNavOpacity, setSwipeNavOpacity] = useState(1);

  /* ---- Hero image state -------------------------------------------------- */
  const [heroImageUrl, setHeroImageUrl] = useState<string | null>(null);
  const [heroImgLoaded, setHeroImgLoaded] = useState(false);
  const [heroImgError, setHeroImgError] = useState(false);

  /* ---- Share button state ------------------------------------------------ */
  const [shareCopied, setShareCopied] = useState(false);
  const [shareToastText, setShareToastText] = useState("Link copied");
  const shareCopiedTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* Reset swipe gesture state when the parent navigates to a different story
     without unmounting this component (handleDeepDiveNav changes story prop). */
  useEffect(() => {
    setIsDismissing(false);
    setIsDragging(false);
    setDragOffset(0);
    setShareCopied(false);
    setHeroImageUrl(null);
    setHeroImgLoaded(false);
    setHeroImgError(false);
    touchStartRef.current = null;
    if (shareCopiedTimer.current) clearTimeout(shareCopiedTimer.current);
  }, [story.id]);

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
      }, 4000);
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

        // Extract best hero image from cluster articles (prefer highest-tier source)
        {
          const tierRank: Record<string, number> = { us_major: 3, international: 2, independent: 1 };
          let bestImg: { url: string; rank: number } | null = null;
          for (const row of raw!) {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const a = row.article as any;
            if (!a?.image_url) continue;
            const url = a.image_url as string;
            if (url.startsWith('data:') || url.length < 20 || /logo|icon|favicon|pixel|spacer|tracker|1x1|blank|placeholder|default-og|brand/i.test(url)) continue;
            const tier = (a.source?.tier as string) ?? "independent";
            const rank = tierRank[tier] ?? 0;
            if (!bestImg || rank > bestImg.rank) bestImg = { url, rank };
          }
          if (!cancelled) {
            setHeroImageUrl(bestImg?.url ?? null);
            setHeroImgLoaded(false);
            setHeroImgError(false);
          }
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

    // Global state: allows CSS to disable expensive backdrop-filters on
    // elements hidden behind the Deep Dive overlay (mobile GPU budget).
    document.documentElement.classList.add('deep-dive-active');

    // Feed recession: page-main scales down 0.3%, creating physical depth
    // — the feed recedes as the Deep Dive approaches the viewer.
    const pageMain = document.querySelector('.page-main');
    pageMain?.classList.remove('page-main--deep-dive-closing');
    pageMain?.classList.add('page-main--deep-dive-open');

    hapticMedium();
    const isDesktopForMorph = window.innerWidth >= 1024;
    const hasMorph = originRect && originRect.width > 0 && panelRef.current && isDesktopForMorph;

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
        const MORPH_SCALE_MIN = 0.15;
        const scaleX = Math.max(MORPH_SCALE_MIN, originRect.width / finalRect.width);
        const scaleY = Math.max(MORPH_SCALE_MIN, originRect.height / finalRect.height);
        const dx = (originRect.left + originRect.width / 2) - (finalRect.left + finalRect.width / 2);
        const dy = (originRect.top + originRect.height / 2) - (finalRect.top + finalRect.height / 2);

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
        // Double rAF guarantees the browser paints the snap frame before
        // the transition begins. The first rAF commits the snap to the DOM,
        // the browser paints it, then the second rAF starts the spring.
        // This is more reliable than setTimeout(0) which can fire before
        // the browser paints, collapsing snap + transition into one frame.
        requestAnimationFrame(() => {
          setMorphStyle({
            transform: finalTransform,
            borderRadius: isDesktopNow ? "16px" : "16px 16px 0 0",
            opacity: 1,
            boxShadow: "var(--shadow-cinematic-lifted)",
            transition: [
              "transform 380ms var(--spring-bouncy)",
              "border-radius 200ms cubic-bezier(0.16, 1, 0.3, 1)",
              "opacity 200ms cubic-bezier(0.16, 1, 0.3, 1)",
              "box-shadow 250ms cubic-bezier(0.16, 1, 0.3, 1)",
            ].join(", "),
          });

          // L-cut: content cascades in while morph is still settling.
          setTimeout(() => setContentVisible(true), isDesktopNow ? 180 : 120);

          // Clear morph style after transition settles
          setTimeout(() => {
            setMorphStyle(null);
            panelRef.current?.setAttribute('data-settled', '');
          }, 320);
        });
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
      // Remove feed recession + global state classes
      document.documentElement.classList.remove('deep-dive-active');
      const pm = document.querySelector('.page-main');
      pm?.classList.remove('page-main--deep-dive-open', 'page-main--deep-dive-closing');
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

  /* ---- Share handler ------------------------------------------------------ */
  const handleShare = useCallback(async () => {
    hapticLight();
    const url = typeof window !== "undefined" ? window.location.href : "";

    /** Show a transient toast under the share button. */
    const showToast = (msg: string) => {
      setShareToastText(msg);
      setShareCopied(true);
      if (shareCopiedTimer.current) clearTimeout(shareCopiedTimer.current);
      shareCopiedTimer.current = setTimeout(() => setShareCopied(false), 2400);
    };

    /* 1. Generate Evidence Card — 9:16 story card (primary), fallback to square/OG */
    const isMobileShare = typeof window !== "undefined" && window.innerWidth < 768;
    const deepDiveSources = (liveData?.sources ?? story.deepDive?.sources) || [];
    let blob: Blob | null = null;
    try {
      blob = await generateStoryCardImage(story, deepDiveSources, url);
    } catch {
      // 9:16 card failed — fall back to legacy formats
      try {
        blob = isMobileShare
          ? await generateSquareCardImage(story)
          : await generateShareCardImage(story);
      } catch {
        // Canvas rendering failed — fall back to URL-only sharing below
      }
    }

    /* 2a. Mobile with file-sharing support: share card image + URL */
    if (blob && typeof navigator !== "undefined" && navigator.share && navigator.canShare) {
      const file = new File([blob], "void-news-evidence-card.png", { type: "image/png" });
      const shareData = { files: [file], title: story.title, url };
      try {
        if (navigator.canShare(shareData)) {
          await navigator.share(shareData);
          return; // OS share sheet handled feedback
        }
      } catch {
        // User cancelled or share failed — fall through to download
      }
    }

    /* 2b. Mobile without file support: share URL via native sheet */
    if (!blob && typeof navigator !== "undefined" && navigator.share) {
      try {
        await navigator.share({ url, title: story.title });
        return;
      } catch {
        // User cancelled — fall through
      }
    }

    /* 3. Desktop (or file-share not supported): download the PNG */
    if (blob) {
      try {
        const blobUrl = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = blobUrl;
        a.download = "void-news-evidence-card.png";
        a.style.display = "none";
        document.body.appendChild(a);
        a.click();
        // Cleanup after a tick so the download starts
        setTimeout(() => {
          document.body.removeChild(a);
          URL.revokeObjectURL(blobUrl);
        }, 100);
        // Also copy URL to clipboard for easy pasting
        try { await navigator.clipboard.writeText(url); } catch { /* ok */ }
        showToast("Card saved");
        return;
      } catch {
        // Download failed — fall through to clipboard-only
      }
    }

    /* 4. Last resort: copy URL to clipboard */
    try {
      await navigator.clipboard.writeText(url);
      showToast("Link copied");
    } catch {
      // Clipboard API not available — silent fail
    }
  }, [story]);

  /* ---- Close — reverse FLIP morph (panel shrinks back into the card) ---- */
  const handleClose = useCallback(() => {
    hapticLight();
    // Remove settled state — hides studio reflection ::before immediately
    panelRef.current?.removeAttribute('data-settled');
    // Phase 1: Content fades out quickly
    setContentVisible(false);

    // Feed recession: swap open → closing (scale returns with snappy spring)
    const pageMain = document.querySelector('.page-main');
    pageMain?.classList.remove('page-main--deep-dive-open');
    pageMain?.classList.add('page-main--deep-dive-closing');

    // Backdrop rack-out: blur clears (feed refocuses) via CSS animation
    const backdrop = document.querySelector('.deep-dive-backdrop');
    backdrop?.classList.add('deep-dive-backdrop--closing');

    /* ═══ SCENE 5: REVERSE SHOT — Panel collapses back into its card ═══
       Find the actual card in the DOM at close time rather than relying on
       the stale originRect from open time. This handles arrow-key navigation
       between stories (story changes but originRect still pointed at the
       original card) and any layout shifts.

       The panel stays fully opaque until the final 80ms — the viewer's eye
       tracks the panel all the way back into the card, then it vanishes
       into the card surface like a match cut in reverse. */

    // Fresh rect: query the DOM for the current story's card element.
    // Falls back to originRect (still valid when body is position:fixed),
    // then to null (graceful center-close fallback).
    const cardEl = document.querySelector(`[data-story-id="${story.id}"]`);
    const targetRect = cardEl ? cardEl.getBoundingClientRect() : (originRect?.width ? originRect : null);

    if (targetRect && targetRect.width > 0 && panelRef.current) {
      const panel = panelRef.current;
      if (!panel) { previousFocusRef.current?.focus(); onClose(); return; }

      const currentRect = panel.getBoundingClientRect();
      const MORPH_SCALE_MIN = 0.15;
      const scaleX = Math.max(MORPH_SCALE_MIN, targetRect.width / currentRect.width);
      const scaleY = Math.max(MORPH_SCALE_MIN, targetRect.height / currentRect.height);
      const dx = (targetRect.left + targetRect.width / 2) - (currentRect.left + currentRect.width / 2);
      const dy = (targetRect.top + targetRect.height / 2) - (currentRect.top + currentRect.height / 2);

      const isDesktopNow = window.innerWidth >= 1024;
      const closeTransform = isDesktopNow
        ? `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px)) scale(${scaleX}, ${scaleY})`
        : `translate(${dx}px, ${dy}px) scale(${scaleX}, ${scaleY})`;

      // Reverse match cut — panel physically returns to the card.
      // 320ms with smooth deceleration: fast departure, gentle arrival.
      // Opacity holds for first 220ms then fades in final 100ms.
      setMorphStyle({
        transform: closeTransform,
        borderRadius: "8px",
        opacity: 0,
        boxShadow: "var(--shadow-e0)",
        transition: [
          "transform 320ms cubic-bezier(0.32, 0.72, 0, 1)",
          "border-radius 240ms cubic-bezier(0.32, 0.72, 0, 1)",
          "opacity 100ms cubic-bezier(0.16, 1, 0.3, 1) 220ms",
          "box-shadow 280ms cubic-bezier(0.32, 0.72, 0, 1)",
        ].join(", "),
      });

      // L-cut — backdrop fades early so feed sharpens while panel mid-flight
      setTimeout(() => setIsVisible(false), 100);

      // Cleanup — after panel has visually merged with the card
      setTimeout(() => {
        pageMain?.classList.remove('page-main--deep-dive-closing');
        previousFocusRef.current?.focus();
        onClose();
      }, 350);
    } else {
      /* ═══ FALLBACK: fast slide-out ═══ */
      setIsVisible(false);
      setTimeout(() => {
        pageMain?.classList.remove('page-main--deep-dive-closing');
        previousFocusRef.current?.focus();
        onClose();
      }, 300);
    }
  }, [onClose, originRect, story.id]);

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
      hapticFired: false,
    };
  }, [isDesktop]);

  const handleTouchMove = useCallback((e: React.TouchEvent) => {
    if (isDesktop || !touchStartRef.current) return;

    const touch = e.touches[0];
    const deltaX = touch.clientX - touchStartRef.current.x;
    const deltaY = touch.clientY - touchStartRef.current.y;
    const absX = Math.abs(deltaX);
    const absY = Math.abs(deltaY);

    // Determine direction on first significant movement (20px dead zone)
    if (touchStartRef.current.direction === "none" && (absX > 20 || absY > 20)) {
      touchStartRef.current.direction = absX > absY * 2 ? "horizontal" : "vertical";
    }

    // --- Horizontal swipe (story navigation) ---
    if (touchStartRef.current.direction === "horizontal" && onNavigateRef.current) {
      // Haptic detent at threshold crossing (once per gesture)
      if (absX > 60 && !touchStartRef.current.hapticFired) {
        hapticMicro();
        touchStartRef.current.hapticFired = true;
      }
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
             Desktop: subtle appear in place. Mobile: slide from bottom.
             Close animation (spring-snappy 350ms) is kept as-is. */
          transform: isVisible
            ? isDesktop
              ? "translate(-50%, -50%) scale(1)"
              : `translateY(${dragOffset}px)`
            : isDesktop
              ? "translate(-50%, -50%) scale(0.98)"
              : "translateY(100%)",
          opacity: isVisible ? 1 : 0,
          boxShadow: isVisible ? "var(--shadow-cinematic-dramatic)" : "none",
          transition: isDragging
            ? "none"
            : isDismissing
              ? "transform 280ms cubic-bezier(0.2, 1, 0.3, 1)"
              : !isVisible
                ? "transform 350ms var(--spring-snappy), opacity 180ms cubic-bezier(0.16, 1, 0.3, 1) 150ms, box-shadow 180ms cubic-bezier(0.16, 1, 0.3, 1)"
                : contentVisible
                  ? "none"
                  : "transform 220ms ease-out, opacity 180ms ease-out, box-shadow 220ms ease-out",
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
            {/* Static story counter — mobile only, replaces swipe hint as persistent affordance */}
            {!isDesktop && totalStories > 1 && (
              <span className="dd-story-counter" aria-label={`Story ${storyIndex + 1} of ${totalStories}`}>
                {storyIndex + 1} / {totalStories}
              </span>
            )}

            {/* Share button */}
            <button onClick={handleShare} aria-label="Share this story" className="deep-dive-share">
              {shareCopied ? (
                /* Checkmark icon — confirms clipboard copy */
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                  <path d="M4 9.5L7.5 13L14 5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ) : (
                /* Share icon — arrow up from box */
                <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                  <path d="M6 7L9 4L12 7" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                  <path d="M9 4V12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
                  <path d="M4 11V14H14V11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              )}
              {shareCopied && <span className="dd-share-toast">{shareToastText}</span>}
            </button>
            {/* Accessible announcement for screen readers */}
            <div aria-live="polite" className="sr-only">
              {shareCopied ? shareToastText : ""}
            </div>

            <button onClick={handleClose} aria-label="Close deep dive" className="deep-dive-close">
              <X size={20} weight="regular" aria-hidden="true" />
            </button>
          </div>

          {/* Hero image — cinematic front-page photograph */}
          {heroImageUrl && !heroImgError && (
            <div className={`dd-hero-image${heroImgLoaded ? " dd-hero-image--loaded" : ""}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={heroImageUrl}
                alt=""
                className="dd-hero-image__img"
                loading="eager"
                onLoad={() => setHeroImgLoaded(true)}
                onError={() => setHeroImgError(true)}
              />
              <div className="dd-hero-image__grade" aria-hidden="true" />
            </div>
          )}

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
              className={`dd-analysis-block anim-dd-section dd-cascade-1${contentVisible ? " anim-dd-section--visible" : ""}`}
              style={{ marginBottom: "var(--space-6)" }}
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

          <hr className="ink-rule" style={{ margin: "0 0 var(--space-4) 0" }} aria-hidden="true" />

          {/* ---- Summary ---- */}
          <section className={`anim-dd-section dd-cascade-2${contentVisible ? " anim-dd-section--visible" : ""}`} style={{ marginBottom: "var(--space-5)" }}>
            <h3 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-2)" }}>The Story</h3>
            <div className={`dd-collapsible${summaryExpanded ? " dd-collapsible--expanded" : ""}${!summaryOverflows && !summaryExpanded ? " dd-collapsible--fits" : ""}`}>
              <div className="dd-collapsible__inner" ref={summaryInnerRef}>
                <p className="text-base dd-summary-text" style={{ lineHeight: 1.75, margin: 0 }}>
                  {renderSummaryWithContradictions(story.summary, deepDive?.claimConsensus?.disputed_details)}
                </p>
              </div>
            </div>
            {summaryOverflows && !summaryExpanded && (
              <button className="dd-read-more" onClick={() => { hapticLight(); setSummaryExpanded(true); }}>Read more</button>
            )}
          </section>

          {/* ---- Progressive disclosure trigger ---- */}
          {(hasCrossLeanSources || (story.sigilData && !story.sigilData.pending)) && !analysisExpanded && (
            <button
              className={`dd-read-more dd-analysis-trigger anim-dd-section dd-cascade-trigger${contentVisible ? " anim-dd-section--visible" : ""}`}
              onClick={() => { hapticLight(); setAnalysisExpanded(true); }}
            >
              Show full analysis
            </button>
          )}

          {/* ---- Source Perspectives (collapsed by default) ---- */}
          {analysisExpanded && hasCrossLeanSources && (
            <section id="dd-panel-perspectives" aria-label="Source Perspectives" className={`anim-dd-section dd-cascade-3${contentVisible ? " anim-dd-section--visible" : ""}`} style={{ marginBottom: "var(--space-5)" }}>
              <hr className="ink-rule" style={{ marginBottom: "var(--space-4)" }} aria-hidden="true" />
              <h3 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-3)" }}>Source Perspectives</h3>
              <ComparativeView
                sources={sources}
                consensusPoints={deepDive?.consensus}
                divergencePoints={deepDive?.divergence}
              />
            </section>
          )}

          {/* ---- Claim Consensus — cross-source verification (collapsed by default) ---- */}
          {analysisExpanded && deepDive?.claimConsensus && (
            <section
              className={`anim-dd-section dd-cascade-3${contentVisible ? " anim-dd-section--visible" : ""}`}
              style={{ marginBottom: "var(--space-5)" }}
              aria-label="Claim Consensus verification"
            >
              <hr className="ink-rule" style={{ marginBottom: "var(--space-4)" }} aria-hidden="true" />
              <ClaimConsensusSection consensus={deepDive.claimConsensus} />
            </section>
          )}

          {/* ---- Six Lenses — ink stamp bias scores (collapsed by default) ---- */}
          {analysisExpanded && story.sigilData && !story.sigilData.pending && (
            <section
              className={`anim-dd-section dd-cascade-4${contentVisible ? " anim-dd-section--visible" : ""}`}
              style={{ marginBottom: "var(--space-4)" }}
              aria-label="Six Lenses bias analysis"
            >
              <hr className="ink-rule" style={{ marginBottom: "var(--space-4)" }} aria-hidden="true" />
              <SixLenses sigilData={story.sigilData} visible={contentVisible} />
            </section>
          )}

          {/* ---- Historical Context cross-link (only when keyword matches) ---- */}
          <HistoryContextLink title={story.title} summary={story.summary} visible={contentVisible} />

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

        {/* Mobile sticky footer — "Read All Sides" CTA */}
        {!isDesktop && sources.length > 0 && hasCrossLeanSources && (
          <div className="dd-cta-footer">
            <button
              className="dd-read-more dd-cta-footer__btn"
              onClick={() => {
                hapticLight();
                if (!analysisExpanded) setAnalysisExpanded(true);
                const perspectives = document.getElementById("dd-panel-perspectives");
                if (perspectives) {
                  perspectives.scrollIntoView({ behavior: "smooth", block: "start" });
                }
              }}
            >
              Read All Sides &mdash; {sources.length} sources
            </button>
          </div>
        )}
      </div>
    </>
  );
}
