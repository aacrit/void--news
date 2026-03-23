"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
import type { Edition, Category, Story, BiasScores, BiasSpread, ThreeLensData, OpinionLabel, SigilData } from "../lib/types";
import { EDITIONS } from "../lib/types";
import { supabase, supabaseError } from "../lib/supabase";
import LogoWordmark from "./LogoWordmark";
import LogoIcon from "./LogoIcon";
import NavBar from "./NavBar";
import FilterBar, { type LeanChip, LEAN_RANGES } from "./FilterBar";
import LeadStory from "./LeadStory";
import StoryCard from "./StoryCard";
import DeepDive from "./DeepDive";
import ErrorBoundary from "./ErrorBoundary";

/* ---------------------------------------------------------------------------
   VisibleCard — defers anim-filter-card until the element enters the viewport.

   Uses a pooled IntersectionObserver (shared across all VisibleCards) to avoid
   creating 100+ observers on long feeds. The observer is created once and
   elements register/unregister via a WeakMap callback.
   --------------------------------------------------------------------------- */

// Pooled observer — single instance shared by all VisibleCard components
const observerCallbacks = new WeakMap<Element, () => void>();
let sharedObserver: IntersectionObserver | null = null;

function getSharedObserver(): IntersectionObserver {
  if (sharedObserver) return sharedObserver;
  sharedObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) {
          const cb = observerCallbacks.get(entry.target);
          if (cb) {
            cb();
            observerCallbacks.delete(entry.target);
            sharedObserver?.unobserve(entry.target);
          }
        }
      }
    },
    { rootMargin: "100px" },
  );
  return sharedObserver;
}

interface VisibleCardProps {
  className?: string;
  style?: React.CSSProperties;
  children: React.ReactNode;
}

function VisibleCard({ className = "", style, children }: VisibleCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    // If already in the viewport on mount (e.g. filter re-render), mark
    // immediately without waiting for the observer callback.
    const rect = el.getBoundingClientRect();
    if (rect.top < window.innerHeight + 100) {
      setInView(true);
      return;
    }
    const observer = getSharedObserver();
    observerCallbacks.set(el, () => setInView(true));
    observer.observe(el);
    return () => {
      observerCallbacks.delete(el);
      observer.unobserve(el);
    };
  }, []);

  return (
    <div
      ref={ref}
      className={`${className}${inView ? " anim-filter-card" : ""}`}
      style={style}
    >
      {children}
    </div>
  );
}

import LoadingSkeleton from "./LoadingSkeleton";
import Footer from "./Footer";
import { useDailyBrief, DailyBriefText } from "./DailyBrief";
import { hapticConfirm, hapticScrollEdge } from "../lib/haptics";
import BiasLensOnboarding from "./BiasLensOnboarding";
import { KeyboardShortcutsOverlay, useStoryKeyboardNav } from "./KeyboardShortcuts";

/** Map pipeline category slugs (both fine-grained and desk) to display names.
 *  Fine-grained slugs from old pipeline runs are merged to their desk names. */
function capitalize(s: string): string {
  if (!s) return s;
  const map: Record<string, string> = {
    // Desk slugs (current pipeline output)
    politics: "Politics", economy: "Economy", science: "Science",
    health: "Health", culture: "Culture",
    // Legacy fine-grained slugs (old data in DB) → merged desk names
    conflict: "Politics", tech: "Science", technology: "Science",
    environment: "Health", sports: "Culture",
  };
  return map[s.toLowerCase()] || s.charAt(0).toUpperCase() + s.slice(1);
}

/**
 * Runtime guard for bias_diversity JSONB from Supabase.
 * Returns null if the value is not a plain object — guards against malformed
 * JSONB (strings, arrays, unexpected types) that would cause property-access
 * errors downstream. Accepts null/undefined as a valid "no data" signal.
 */
function parseBiasDiversity(raw: unknown): Record<string, unknown> | null {
  if (raw == null) return null;
  if (typeof raw !== "object" || Array.isArray(raw)) return null;
  return raw as Record<string, unknown>;
}

/**
 * Safely coerce a bias_diversity field value to number, returning fallback
 * if the field is missing, null, not a number, or NaN.
 */
function safeNum(bd: Record<string, unknown>, key: string, fallback: number): number {
  const v = bd[key];
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  return fallback;
}

/**
 * Safely extract tier_breakdown as Record<string, number> — only keeps
 * entries where the value is a finite number.
 */
function safeTierBreakdown(bd: Record<string, unknown>): Record<string, number> | undefined {
  const raw = bd["tier_breakdown"];
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return undefined;
  const result: Record<string, number> = {};
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof v === "number" && Number.isFinite(v)) result[k] = v;
  }
  return Object.keys(result).length > 0 ? result : undefined;
}

function deriveOpinionLabel(score: number): OpinionLabel {
  if (score <= 25) return "Reporting";
  if (score <= 50) return "Analysis";
  if (score <= 75) return "Opinion";
  return "Editorial";
}

function deriveCoverageScore(sourceCount: number, factualRigor: number, confidence: number): number {
  const sourceNorm = Math.min(1.0, sourceCount / 10.0);
  const rigorNorm = factualRigor / 100.0;
  const confNorm = Math.min(1.0, confidence);
  return Math.round((sourceNorm * 0.35 + 0.2 + confNorm * 0.20 + rigorNorm * 0.25) * 100);
}

interface HomeContentProps {
  initialEdition?: Edition;
}

/* ---------------------------------------------------------------------------
   HomeContent — News Feed
   Desktop: broadsheet grid — lead story + asymmetric layout + dense compact
   Mobile: single-column tabloid stack
   Edition is URL-driven: each edition has its own route.
   --------------------------------------------------------------------------- */

function HomeContentInner({ initialEdition = "world" }: HomeContentProps) {
  const activeEdition: Edition = initialEdition;

  const [stories, setStories] = useState<Story[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  // retryKey: incrementing triggers the data-fetch useEffect without a full
  // page reload — gives users a clean retry path from the error state.
  const [retryKey, setRetryKey] = useState(0);
  // Read initial filter state from URL params (bookmarkable/shareable)
  const [activeCategory, setActiveCategory] = useState<"All" | Category>(() => {
    if (typeof window === "undefined") return "All";
    const params = new URLSearchParams(window.location.search);
    const cat = params.get("cat");
    if (cat && ["Politics", "Economy", "Science", "Health", "Culture"].includes(cat)) return cat as Category;
    return "All";
  });
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);
  const [originRect, setOriginRect] = useState<DOMRect | null>(null);
  const [activeLean, setActiveLean] = useState<LeanChip>(() => {
    if (typeof window === "undefined") return "All";
    const params = new URLSearchParams(window.location.search);
    const lean = params.get("lean");
    if (lean && ["Left", "Center", "Right"].includes(lean)) return lean as LeanChip;
    return "All";
  });

  // Batch reveal for compact stories — no hard cap, progressive loading
  const BATCH_SIZE = 8;
  const [visibleCount, setVisibleCount] = useState(BATCH_SIZE);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [isMobile, setIsMobile] = useState(false);

  // Scroll position before DeepDive opened — restored on close (F06)
  const scrollBeforeDeepDive = useRef<number>(0);

  // Daily Brief state — shared between text + onair player
  // while DailyBriefText renders in the content area
  const dailyBriefState = useDailyBrief(activeEdition);

  const handleStoryClick = useCallback((story: Story, rect: DOMRect) => {
    // Only use the rect for the FLIP morph when it has real dimensions.
    // DOMRect() with no args gives a zeroed rect (keyboard nav fallback).
    scrollBeforeDeepDive.current = window.scrollY;
    setOriginRect(rect.width > 0 ? rect : null);
    setSelectedStory(story);
  }, []);

  const handleDeepDiveClose = useCallback(() => {
    setSelectedStory(null);
    setOriginRect(null);
    window.scrollTo(0, scrollBeforeDeepDive.current);
  }, []);

  // Detect mobile for infinite scroll vs editorial link
  useEffect(() => {
    setIsMobile(window.matchMedia("(max-width: 767px)").matches);
  }, []);

  // Reset category filter, close DeepDive, and scroll to top when edition changes.
  // Lean filter is intentionally preserved — it's a universal preference
  // that persists until the user explicitly toggles it off.
  useEffect(() => {
    hapticConfirm();
    setSelectedStory(null);
    setOriginRect(null);
    setActiveCategory("All");
    setVisibleCount(BATCH_SIZE);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [activeEdition]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadFromSupabase() {
      setIsLoading(true);
      setError(null);

      // Guard: if Supabase client is unavailable, surface a user-friendly error
      // rather than throwing a TypeError on the first .from() call.
      if (!supabase) {
        setError(supabaseError ?? "Unable to connect to data source.");
        setIsLoading(false);
        return;
      }

      try {
        const enrichedFields = `id,title,summary,category,section,sections,importance_score,source_count,first_published,last_updated,divergence_score,headline_rank,coverage_velocity,bias_diversity,consensus_points,divergence_points`;
        const baseFields = `id,title,summary,category,section,sections,importance_score,source_count,first_published,last_updated`;

        let res;
        let usingEnriched = true;

        res = await supabase
          .from("story_clusters")
          .select(enrichedFields)
          .contains("sections", [activeEdition])
          .order("headline_rank", { ascending: false })
          .limit(500);

        // If enriched query failed (columns don't exist), fall back to base schema
        if (res.error) {
          usingEnriched = false;
          res = await supabase
            .from("story_clusters")
            .select(baseFields)
            .contains("sections", [activeEdition])
            .order("first_published", { ascending: false })
            .limit(500);
        }

        if (controller.signal.aborted) return;

        const clusters = res.data || [];

        if (clusters.length === 0) {
          setStories([]);
          setIsLoading(false);
          return;
        }

        if (controller.signal.aborted) return;

        /* eslint-disable @typescript-eslint/no-explicit-any */
        const liveStories: Story[] = clusters.map(
          (cluster: any) => {
            // M002: Runtime-validate bias_diversity JSONB before any property access.
            // parseBiasDiversity returns null for strings, arrays, or non-plain-objects.
            const bd = usingEnriched ? parseBiasDiversity(cluster.bias_diversity) : null;
            const hasBiasData = !!(bd && bd["avg_political_lean"] != null);

            const biasScores: BiasScores = hasBiasData
              ? {
                  politicalLean: safeNum(bd!, "avg_political_lean", 50),
                  sensationalism: safeNum(bd!, "avg_sensationalism", 30),
                  opinionFact: safeNum(bd!, "avg_opinion_fact", 25),
                  factualRigor: safeNum(bd!, "avg_factual_rigor", 75),
                  framing: safeNum(bd!, "avg_framing", 40),
                }
              : {
                  politicalLean: 50,
                  sensationalism: 30,
                  opinionFact: 25,
                  factualRigor: 75,
                  framing: 40,
                };

            const biasSpread: BiasSpread | undefined = bd && bd["lean_spread"] != null
              ? {
                  leanSpread: safeNum(bd, "lean_spread", 0),
                  framingSpread: safeNum(bd, "framing_spread", 0),
                  leanRange: safeNum(bd, "lean_range", 0),
                  sensationalismSpread: safeNum(bd, "sensationalism_spread", 0),
                  opinionSpread: safeNum(bd, "opinion_spread", 0),
                  aggregateConfidence: safeNum(bd, "aggregate_confidence", 0),
                  analyzedCount: safeNum(bd, "analyzed_count", 0),
                }
              : undefined;

            // Use nullish coalescing so a genuine 0 is preserved rather than
            // defaulting to 1. The pending flag on lensData/sigilData already
            // handles the no-bias-data display state.
            const sourceCount = cluster.source_count ?? 0;
            const opinionLabel = (bd?.["avg_opinion_label"] as OpinionLabel) ?? deriveOpinionLabel(biasScores.opinionFact);
            const lensData: ThreeLensData = {
              lean: biasScores.politicalLean,
              coverage: bd ? safeNum(bd, "coverage_score", deriveCoverageScore(
                sourceCount, biasScores.factualRigor, biasSpread?.aggregateConfidence ?? 0.5,
              )) : deriveCoverageScore(sourceCount, biasScores.factualRigor, 0.5),
              sourceCount,
              tierBreakdown: bd ? safeTierBreakdown(bd) : undefined,
              opinion: biasScores.opinionFact,
              opinionLabel,
              pending: !hasBiasData,
            };
            const sigilData: SigilData = {
              politicalLean: biasScores.politicalLean,
              sensationalism: biasScores.sensationalism,
              opinionFact: biasScores.opinionFact,
              factualRigor: biasScores.factualRigor,
              framing: biasScores.framing,
              agreement: cluster.divergence_score || 0,
              sourceCount,
              tierBreakdown: bd ? safeTierBreakdown(bd) : undefined,
              biasSpread,
              pending: !hasBiasData,
              opinionLabel,
            };

            const rawConsensus = usingEnriched ? cluster.consensus_points : null;
            const rawDivergence = usingEnriched ? cluster.divergence_points : null;
            const consensusPoints: string[] = Array.isArray(rawConsensus)
              ? rawConsensus
              : [];
            const divergencePoints: string[] = Array.isArray(rawDivergence)
              ? rawDivergence
              : [];

            return {
              id: cluster.id,
              title: cluster.title,
              summary: cluster.summary || "",
              source: {
                name: "Multiple Sources",
                count: sourceCount,
              },
              category: capitalize(cluster.category || "politics") as Category,
              publishedAt:
                cluster.first_published ||
                cluster.last_updated ||
                new Date().toISOString(),
              biasScores,
              biasSpread,
              lensData,
              sigilData,
              section: (cluster.section || "world") as Edition,
              sections: (cluster.sections || [cluster.section || "world"]) as Edition[],
              importance: cluster.headline_rank || cluster.importance_score || 50,
              divergenceScore: cluster.divergence_score || 0,
              headlineRank: cluster.headline_rank || cluster.importance_score || 50,
              coverageVelocity: cluster.coverage_velocity || 0,
              deepDive: consensusPoints.length > 0 || divergencePoints.length > 0
                ? {
                    consensus: consensusPoints,
                    divergence: divergencePoints,
                    sources: [],
                  }
                : undefined,
            };
          }
        );

        // Compute divergence percentiles (p10/p90) and flag top/bottom 10%
        const divScores = liveStories
          .map((s) => s.divergenceScore)
          .filter((d) => d > 0)
          .sort((a, b) => a - b);
        if (divScores.length >= 5) {
          const p10 = divScores[Math.floor(divScores.length * 0.1)];
          const p90 = divScores[Math.floor(divScores.length * 0.9)];
          for (const s of liveStories) {
            if (s.divergenceScore > 0) {
              if (s.divergenceScore >= p90) {
                s.sigilData.divergenceFlag = "divergent";
              } else if (s.divergenceScore <= p10) {
                s.sigilData.divergenceFlag = "consensus";
              }
            }
          }
        }

        setStories(liveStories);
        setIsLoading(false);

        const { data: run } = await supabase
          .from("pipeline_runs")
          .select("completed_at")
          .eq("status", "completed")
          .order("completed_at", { ascending: false })
          .limit(1)
          .single();

        if (!controller.signal.aborted && run?.completed_at) {
          setLastUpdated(run.completed_at);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : "Failed to load stories");
          setIsLoading(false);
        }
      }
    }

    loadFromSupabase();
    return () => controller.abort();
  }, [activeEdition, retryKey]);

  // Sync filter state to URL params for bookmarkability
  useEffect(() => {
    if (typeof window === "undefined") return;
    const params = new URLSearchParams(window.location.search);
    if (activeLean !== "All") params.set("lean", activeLean);
    else params.delete("lean");
    if (activeCategory !== "All") params.set("cat", activeCategory);
    else params.delete("cat");
    const qs = params.toString();
    const url = qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
    window.history.replaceState(null, "", url);
  }, [activeLean, activeCategory]);

  const filteredStories = useMemo(() => {
    let filtered = stories;
    if (activeCategory !== "All") {
      filtered = filtered.filter((s) => s.category === activeCategory);
    }
    // Lean chip filter — uses lensData.lean (cluster-level average political lean)
    const leanRange = LEAN_RANGES[activeLean];
    if (leanRange) {
      filtered = filtered.filter(
        (s) => s.lensData.lean >= leanRange.min && s.lensData.lean <= leanRange.max,
      );
    }
    return filtered.sort((a, b) => b.headlineRank - a.headlineRank);
  }, [stories, activeCategory, activeLean]);

  const leadStories = filteredStories.slice(0, 2);
  const mediumStories = filteredStories.slice(2, 5);
  const compactStories = filteredStories.slice(5);

  // Progressive batch reveal — no hard cap
  const visibleCompact = compactStories.slice(0, visibleCount);
  const remainingCount = compactStories.length - visibleCount;
  const hasMore = remainingCount > 0;

  const loadMoreStories = useCallback(() => {
    hapticScrollEdge();
    setVisibleCount(prev => Math.min(prev + BATCH_SIZE, compactStories.length));
  }, [compactStories.length]);

  // Mobile: infinite scroll via IntersectionObserver on sentinel
  useEffect(() => {
    if (!isMobile) return;
    const sentinel = sentinelRef.current;
    if (!sentinel || !hasMore) return;

    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) loadMoreStories(); },
      { rootMargin: "200px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [isMobile, hasMore, loadMoreStories]);

  // Stable key that changes whenever the active filter changes.
  // Keying the <section> elements on this value causes React to unmount+remount
  // them, which replays the .anim-filter-card entrance animation on every filter
  // change — giving a "reshuffling" feel with no JS animation library.
  const filterKey = `${activeLean}-${activeCategory}`;

  // Keyboard navigation — J/K to move through stories, Enter to open Deep Dive
  const kbdSelectStory = useCallback((index: number) => {
    if (index >= 0 && index < filteredStories.length) {
      handleStoryClick(filteredStories[index], new DOMRect());
    }
  }, [filteredStories, handleStoryClick]);

  const kbdFocusIndex = useStoryKeyboardNav(
    filteredStories,
    kbdSelectStory,
    !!selectedStory,
  );

  // Inter-story navigation within Deep Dive
  const handleDeepDiveNav = useCallback((direction: "prev" | "next") => {
    if (!selectedStory) return;
    const idx = filteredStories.findIndex((s) => s.id === selectedStory.id);
    if (idx < 0) return;
    const newIdx = direction === "prev" ? idx - 1 : idx + 1;
    if (newIdx >= 0 && newIdx < filteredStories.length) {
      setSelectedStory(filteredStories[newIdx]);
    }
  }, [selectedStory, filteredStories]);

  const editionMeta = EDITIONS.find((e) => e.slug === activeEdition) ?? EDITIONS[0];

  return (
    <div className="page-container">
      <NavBar
        activeEdition={activeEdition}
      />

      <main id="main-content" className="page-main">
        {/* Filter bar row — category chips + lean chips + On Air CTA */}
        <div className="filter-row">
          <FilterBar
            activeCategory={activeCategory}
            onCategoryChange={(cat) => { setActiveCategory(cat); setVisibleCount(BATCH_SIZE); }}
            activeLean={activeLean}
            onLeanChange={(lean) => { setActiveLean(lean); setVisibleCount(BATCH_SIZE); }}
            activeEdition={activeEdition}
          />
        </div>

        {/* Live region, loading, error, empty states, story grids */}
        <>
            {/* Live region for screen readers — announces filter changes and story count */}
            <div aria-live="polite" className="sr-only">
              {!isLoading && filteredStories.length > 0 &&
                `${filteredStories.length} stories loaded for ${activeEdition} edition${activeCategory !== "All" ? `, filtered by ${activeCategory}` : ""}${activeLean !== "All" ? `, ${activeLean} perspective` : ""}. Press ? for keyboard shortcuts.`}
              {!isLoading && stories.length > 0 && filteredStories.length === 0 &&
                "No stories match the current filter. Try clearing your filters."}
            </div>

            {/* Loading skeleton */}
            {isLoading && <LoadingSkeleton />}

            {/* Error state */}
            {error && !isLoading && (
              <div className="empty-state">
                <h2 className="text-xl" style={{ color: "var(--fg-primary)", marginBottom: "var(--space-3)" }}>
                  Unable to load stories
                </h2>
                <p className="text-base" style={{ color: "var(--fg-tertiary)", marginBottom: "var(--space-4)" }}>
                  {error}
                </p>
                <button
                  className="btn-primary"
                  onClick={() => setRetryKey((k) => k + 1)}
                >
                  Try again
                </button>
              </div>
            )}

            {/* Empty state — no data from pipeline yet */}
            {!isLoading && !error && stories.length === 0 && (
              <div className="empty-state">
                <LogoIcon size={56} animation="analyzing" />
                <h2 className="text-xl" style={{ color: "var(--fg-primary)", marginBottom: "var(--space-3)" }}>
                  The Presses Are Warming Up
                </h2>
                <p className="text-base" style={{ color: "var(--fg-tertiary)", lineHeight: 1.6, marginBottom: "var(--space-4)" }}>
                  No stories yet for the {editionMeta.label} edition &mdash; the pipeline is still
                  collecting and analyzing {editionMeta.sourceCount}.
                  The {new Date().getUTCHours() < 17 ? "morning" : "evening"} edition will appear shortly.
                </p>
                <p className="edition-meta">
                  Morning edition: 11:00 AM UTC &middot; Evening edition: 11:00 PM UTC
                </p>
              </div>
            )}

            {/* No stories in selected filter(s) */}
            {!isLoading && !error && stories.length > 0 && filteredStories.length === 0 && (
              <div className="lean-filter-empty">
                <p className="lean-filter-empty__text">
                  No stories match this filter.
                </p>
                <div style={{ display: "flex", gap: "var(--space-4)", flexWrap: "wrap", justifyContent: "center" }}>
                  {activeLean !== "All" && (
                    <button
                      className="lean-filter-empty__action"
                      onClick={() => setActiveLean("All")}
                    >
                      Clear lean filter
                    </button>
                  )}
                  {activeCategory !== "All" && (
                    <button
                      className="lean-filter-empty__action"
                      onClick={() => setActiveCategory("All")}
                    >
                      View all categories
                    </button>
                  )}
                </div>
              </div>
            )}

            {/* 1. Lead section — two primary headlines side by side on desktop */}
            {!isLoading && leadStories.length > 0 && (
              <section key={filterKey} aria-label="Lead stories" className="lead-section anim-content-arrive">
                {leadStories.map((story, i) => (
                  <VisibleCard
                    key={story.id}
                    className="lead-section__col"
                    style={{ animationDelay: `${Math.round(50 * Math.log2(i + 2))}ms` }}
                  >
                    <LeadStory story={story} rank={i} onStoryClick={handleStoryClick} />
                  </VisibleCard>
                ))}
              </section>
            )}

            {/* 2. Daily Brief — TL;DR editorial box, below lead headlines */}
            {!isLoading && stories.length > 0 && (
              <DailyBriefText state={dailyBriefState} />
            )}

            {/* Medium stories — broadsheet grid on desktop */}
            {!isLoading && mediumStories.length > 0 && (
              <section key={`med-${filterKey}`} aria-label="Top stories" className="grid-medium">
                {mediumStories.map((story, idx) => {
                  const gi = leadStories.length + idx;
                  return (
                    <VisibleCard
                      key={story.id}
                      className="grid-medium__item"
                      style={{ animationDelay: `${Math.round(50 * Math.log2(idx + 2))}ms` }}
                    >
                      <StoryCard story={story} index={idx + 1} onStoryClick={handleStoryClick} globalIndex={gi} kbdFocused={kbdFocusIndex === gi} />
                    </VisibleCard>
                  );
                })}
              </section>
            )}

            {/* Compact stories — progressive batch reveal, no hard cap */}
            {!isLoading && compactStories.length > 0 && (
              <>
                <section key={`cmp-${filterKey}`} aria-label="More stories" className="grid-compact">
                  {visibleCompact.map((story, idx) => {
                    const gi = leadStories.length + mediumStories.length + idx;
                    return (
                      <VisibleCard
                        key={story.id}
                        className="grid-compact__item"
                        style={{ animationDelay: `${Math.round(50 * Math.log2((idx % BATCH_SIZE) + 2))}ms` }}
                      >
                        <StoryCard
                          story={story}
                          index={idx + mediumStories.length + 1}
                          onStoryClick={handleStoryClick}
                          globalIndex={gi}
                          kbdFocused={kbdFocusIndex === gi}
                        />
                      </VisibleCard>
                    );
                  })}
                </section>

                {/* Feed continuation — gradient fade + editorial link (desktop) / sentinel (mobile) */}
                {hasMore && (
                  <div className="feed-continuation" ref={sentinelRef}>
                    <div className="feed-continuation__fade" aria-hidden="true" />
                    {!isMobile && (
                      <button
                        className="feed-continuation__link"
                        onClick={loadMoreStories}
                        aria-label="Show more stories"
                      >
                        Continue reading
                      </button>
                    )}
                  </div>
                )}
              </>
            )}

            {/* Edition line — newspaper tradition */}
            {!isLoading && filteredStories.length > 0 && (
              <div className="edition-line">
                <span className="edition-meta">
                  {editionMeta.label} Edition /{" "}
                  {filteredStories.length} stories
                </span>
                <LogoWordmark height={14} />
              </div>
            )}
        </>
      </main>

      {/* Footer */}
      {!isLoading && <Footer lastUpdated={lastUpdated} />}

      {/* Deep Dive panel */}
      {selectedStory && (
        <DeepDive
          story={selectedStory}
          onClose={handleDeepDiveClose}
          originRect={originRect}
          onNavigate={handleDeepDiveNav}
          storyIndex={filteredStories.findIndex((s) => s.id === selectedStory.id)}
          totalStories={filteredStories.length}
        />
      )}

      {/* BiasLens onboarding — first-visit 3-slide carousel */}
      <BiasLensOnboarding />

      {/* Keyboard shortcuts overlay — press ? to toggle */}
      <KeyboardShortcutsOverlay />
    </div>
  );
}

export default function HomeContent({ initialEdition = "world" }: HomeContentProps) {
  return (
    <ErrorBoundary>
      <HomeContentInner initialEdition={initialEdition} />
    </ErrorBoundary>
  );
}
