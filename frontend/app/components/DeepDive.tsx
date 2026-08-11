"use client";

// Route-scoped CSS. verify.css carries the Claim Consensus / ComparativeView
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
import type { Story, StorySource, DeepDiveData, ThreeLensData, OpinionLabel, SigilData, DisputedClaim } from "../lib/types";
import { fetchDeepDiveData, fetchLastPipelineRun } from "../lib/supabase";
import { timeAgo, BASE_PATH } from "../lib/utils";
import { SITE_URL } from "../lib/siteMeta";
import { hapticLight, hapticMicro } from "../lib/haptics";
import { findHistoryContext } from "../lib/historyContext";
import Sigil from "./Sigil";
import NavBar from "./NavBar";
import DeepDiveSpectrum from "./DeepDiveSpectrum";
import BiasSnapshot from "./BiasSnapshot";
import type { DeepDiveSpectrumSource } from "./DeepDiveSpectrum";
import ComparativeView from "./ComparativeView";
import SpreadDisagreement from "./SpreadDisagreement";
import ClaimConsensusSection from "./ClaimConsensusSection";
import ClaimMark from "./ClaimMark";
import LazyOnView from "./LazyOnView";

/* ---------------------------------------------------------------------------
   DeepDive — Mobile full-page "next screen" (phones only).

   This is NOT a modal, backdrop, or bottom sheet. It fills the viewport as its
   own page and REPLACES the feed (HomeContent renders it instead of MobileFeed
   on the mobile branch). It mounts the Void News masthead (<NavBar/>) at the
   top exactly like /onair, pushes a history entry on open so the hardware Back
   button returns to the feed, and offers Story / Spread as two compact pages
   plus prev/next story walkers.

   Desktop uses InlineDeepDive (in-feed accordion) instead — this component is
   never rendered above 767px.
   --------------------------------------------------------------------------- */

// History is hidden pre-launch (the /history routes 301 away), so the archival
// cross-link must never render or link into a dead route. Flip HISTORY_HIDDEN to
// false to re-enable it when History returns.
const HISTORY_HIDDEN: boolean = true;

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
  /** Pipeline completed_at for the NavBar "as of" dateline. */
  editionBuiltAt?: string | null;
  /** Accepted for call-site compatibility (desktop FLIP origin). Unused here. */
  originRect?: DOMRect | null;
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
  const [showAllLenses, setShowAllLenses] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    setIsMobileLens(mq.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobileLens(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const renderAxis = (axis: typeof SIX_AXES[0], i: number) => {
    const score = sigilData[axis.key] as number;
    const dotCount = Math.max(1, Math.round((score / 100) * 5));
    const isActive = activeAxis === axis.id;
    return (
      <button
        key={axis.id}
        className={`dd-lens${isActive ? " dd-lens--active" : ""}${visible ? " dd-lens--visible" : ""}`}
        style={{ "--lens-delay": `${i * 40}ms` } as React.CSSProperties}
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
      {isMobileLens ? (
        <>
          <button
            className={`dd-bias-toggle text-meta${showAllLenses ? " dd-bias-toggle--open" : ""}`}
            onClick={() => { hapticLight(); setShowAllLenses(!showAllLenses); }}
            aria-expanded={showAllLenses}
            aria-controls="dd-lenses-collapsible"
          >
            <span className="dd-bias-toggle__label">
              {showAllLenses ? "Hide analysis" : "Bias Analysis"}
            </span>
            <span className="dd-bias-toggle__caret" aria-hidden="true">
              {showAllLenses ? "▾" : "▸"}
            </span>
          </button>

          <div
            id="dd-lenses-collapsible"
            className={`dd-lenses__collapsible${showAllLenses ? " dd-lenses__collapsible--open" : ""}`}
            aria-hidden={!showAllLenses}
          >
            <h3 className="dd-section-label text-meta dd-lenses__collapsible-label">Six Lenses</h3>
            <div className={`dd-lenses__grid${activeAxis ? " dd-lenses__grid--has-active" : ""}`}>
              {SIX_AXES.map((axis, i) => renderAxis(axis, i))}
            </div>
          </div>
        </>
      ) : (
        <>
          <h3 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-3)" }}>Six Lenses</h3>
          <div className={`dd-lenses__grid${activeAxis ? " dd-lenses__grid--has-active" : ""}`}>
            {SIX_AXES.map((axis, i) => renderAxis(axis, i))}
          </div>
        </>
      )}
      <a href={`${BASE_PATH}/sources/#methodology`} className="dd-lenses__link text-meta">
        How we score
      </a>
    </div>
  );
}

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

/* --- Main DeepDive component (mobile full-page) --------------------------- */

export default function DeepDive({
  story,
  onClose,
  onNavigate,
  storyIndex = -1,
  totalStories = 0,
  editionBuiltAt = null,
}: DeepDiveProps) {
  const [liveData, setLiveData] = useState<DeepDiveData | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [fetchError, setFetchError] = useState(false);
  const [retryCount, setRetryCount] = useState(0);
  const [analysisExpanded, setAnalysisExpanded] = useState(false);
  const [shareCopied, setShareCopied] = useState(false);
  const shareTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  /* Story / Spread pages. Default "story" so the summary is what readers see. */
  const [ledeView, setLedeView] = useState<"story" | "spread">("story");
  const segRef = useRef<HTMLDivElement>(null);

  /* NavBar "as of" dateline. Seeded from the prop (HomeContent already knows the
     pipeline time); fetches as a fallback so the masthead matches Home. */
  const [builtAt, setBuiltAt] = useState<string | null>(editionBuiltAt);
  useEffect(() => {
    if (builtAt) return;
    let alive = true;
    fetchLastPipelineRun().then((run) => {
      if (alive && run?.completed_at) setBuiltAt(run.completed_at);
    });
    return () => { alive = false; };
  }, [builtAt]);

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
        })),
    [sources],
  );

  /* Spread page makes sense only when there is a Sigil or scored sources. */
  const hasLedeSpectrum = Boolean(story.sigilData) || spectrumSources.length > 0;

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
    setLedeView("story");
    setAnalysisExpanded(false);
    setShareCopied(false);
    if (shareTimer.current) clearTimeout(shareTimer.current);
    window.scrollTo(0, 0);
  }, [story.id]);

  /* ---- History integration: push a state entry on open so the hardware /
     browser Back button returns to the feed instead of leaving the site. --- */
  useEffect(() => {
    window.history.pushState({ voidDeepDive: true }, "");
    const onPop = () => { onCloseRef.current(); };
    window.addEventListener("popstate", onPop);
    return () => window.removeEventListener("popstate", onPop);
    // mount-only: one entry per open (prev/next keeps the same entry).
  }, []);

  /* Back to feed — pop the pushed entry (fires popstate -> onClose). */
  const handleBack = useCallback(() => {
    hapticLight();
    window.history.back();
  }, []);

  /* Keyboard: Escape returns to feed, arrows walk stories. */
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        handleBack();
      } else if (onNavigate && (e.key === "ArrowLeft" || e.key === "ArrowRight")) {
        e.preventDefault();
        onNavigate(e.key === "ArrowLeft" ? "prev" : "next");
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [handleBack, onNavigate]);

  /* Segmented-control keyboard support (roving tabs). */
  const handleSegKey = useCallback((e: React.KeyboardEvent) => {
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight" && e.key !== "Home" && e.key !== "End") return;
    e.preventDefault();
    const next: "story" | "spread" =
      e.key === "Home" ? "story"
        : e.key === "End" ? "spread"
          : ledeView === "story" ? "spread" : "story";
    setLedeView(next);
    hapticMicro();
    const id = next === "story" ? "dd-seg-story" : "dd-seg-spread";
    segRef.current?.querySelector<HTMLElement>(`#${id}`)?.focus();
  }, [ledeView]);

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
      {/* Void News masthead — same top bar as Home / On Air. Search is omitted
          (the overlay searches the feed, which this page has replaced). */}
      <NavBar editionBuiltAt={builtAt} />

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
            hideCoverageBar={spectrumSources.length > 0}
          />
        )}

        {/* Compact Story / Spread segmented switch */}
        {hasLedeSpectrum && (
          <div
            className="dd-seg"
            role="tablist"
            aria-label="Story or bias spread"
            ref={segRef}
            onKeyDown={handleSegKey}
          >
            <button
              type="button"
              role="tab"
              id="dd-seg-story"
              aria-selected={ledeView === "story"}
              aria-controls="dd-panel-story"
              tabIndex={ledeView === "story" ? 0 : -1}
              className={`dd-seg__btn${ledeView === "story" ? " dd-seg__btn--active" : ""}`}
              onClick={() => { hapticMicro(); setLedeView("story"); }}
            >
              Story
            </button>
            <button
              type="button"
              role="tab"
              id="dd-seg-spread"
              aria-selected={ledeView === "spread"}
              aria-controls="dd-panel-spread"
              tabIndex={ledeView === "spread" ? 0 : -1}
              className={`dd-seg__btn${ledeView === "spread" ? " dd-seg__btn--active" : ""}`}
              onClick={() => { hapticMicro(); setLedeView("spread"); }}
            >
              Spread
            </button>
          </div>
        )}

        <div className="dd-page__content anim-dd-page">
          {/* ---- Story page: summary + claim consensus ---- */}
          <section
            id="dd-panel-story"
            role={hasLedeSpectrum ? "tabpanel" : undefined}
            aria-labelledby={hasLedeSpectrum ? "dd-seg-story" : undefined}
            hidden={hasLedeSpectrum && ledeView !== "story"}
            className="dd-page__panel"
          >
            <h2 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-2)" }}>The Story</h2>
            <p className="text-base dd-summary-text" style={{ lineHeight: 1.75, margin: 0 }}>
              {renderSummaryWithContradictions(story.summary, deepDive?.claimConsensus?.disputed_details)}
            </p>

            {deepDive?.claimConsensus && (
              <section className="dd-page__section" aria-label="Claim Consensus verification">
                <hr className="ink-rule" style={{ margin: "var(--space-5) 0 var(--space-4)" }} aria-hidden="true" />
                <LazyOnView rootMargin="300px 0px" minHeight={120}>
                  <ClaimConsensusSection consensus={deepDive.claimConsensus} />
                </LazyOnView>
              </section>
            )}

            <HistoryContextLink title={story.title} summary={story.summary} />
          </section>

          {/* ---- Spread page: Sigil + spectrum + sources roster + lenses ---- */}
          {hasLedeSpectrum && (
            <section
              id="dd-panel-spread"
              role="tabpanel"
              aria-labelledby="dd-seg-spread"
              hidden={ledeView !== "spread"}
              className="dd-page__panel"
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

              {/* Subtle inline loading — only while the spectrum sources are
                  genuinely still being fetched. Never a full-panel skeleton; the
                  Sigil above is already live from the story. */}
              {sourcesPending && (
                <p className="dd-page__loading text-meta" role="status">Gathering the full source list</p>
              )}

              {/* Agree / Dispute — the promoted centerpiece. What the sources
                  broadly agree on vs where they split, pulled up from the old
                  buried ComparativeView disclosure. Self-omits when empty. */}
              <SpreadDisagreement
                consensus={deepDive?.consensus}
                divergence={deepDive?.divergence}
              />

              {/* Six Lenses — full 6-axis bias breakdown. */}
              {story.sigilData && !story.sigilData.pending && (
                <section className="dd-page__section" aria-label="Six Lenses">
                  <hr className="ink-rule" style={{ margin: "var(--space-5) 0 var(--space-4)" }} aria-hidden="true" />
                  <SixLenses
                    sigilData={{ ...story.sigilData, agreement: Math.round(story.sigilData.agreement) }}
                    visible={true}
                  />
                </section>
              )}

              {/* Source Perspectives — progressive disclosure (lazy). */}
              {hasCrossLeanSources && !analysisExpanded && (
                <button
                  className="dd-read-more dd-analysis-trigger"
                  onClick={() => { hapticLight(); setAnalysisExpanded(true); }}
                >
                  Show source breakdown
                </button>
              )}
              {analysisExpanded && hasCrossLeanSources && (
                <section className="dd-page__section" aria-label="Source Perspectives" style={{ marginTop: "var(--space-4)" }}>
                  <hr className="ink-rule" style={{ marginBottom: "var(--space-4)" }} aria-hidden="true" />
                  <h3 className="dd-section-label text-meta" style={{ marginBottom: "var(--space-3)" }}>Source Perspectives</h3>
                  <LazyOnView rootMargin="400px 0px" minHeight={200}>
                    <ComparativeView
                      sources={sources}
                      consensusPoints={deepDive?.consensus}
                      divergencePoints={deepDive?.divergence}
                      hideInsights
                    />
                  </LazyOnView>
                </section>
              )}
            </section>
          )}

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
        </div>
      </main>
    </div>
  );
}
