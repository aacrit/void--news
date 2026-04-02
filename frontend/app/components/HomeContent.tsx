"use client";

import React, { useState, useEffect, useMemo, useCallback, useRef, Component, type ReactNode } from "react";
import dynamic from "next/dynamic";
import type { Edition, Category, Story, BiasScores, BiasSpread, ThreeLensData, OpinionLabel, SigilData, LeanChip } from "../lib/types";
import { EDITIONS, LEAN_RANGES } from "../lib/types";
import { supabase, supabaseError } from "../lib/supabase";
import { BASE_PATH } from "../lib/utils";
import LogoIcon from "./LogoIcon";
import LogoWordmark from "./LogoWordmark";
import NavBar from "./NavBar";
import LeadStory from "./LeadStory";
import StoryCard from "./StoryCard";
const DeepDive = dynamic(() => import("./DeepDive"), { ssr: false });
import ErrorBoundary from "./ErrorBoundary";

/* DeepDive-specific ErrorBoundary — shows dismissible error in the panel
   instead of crashing the entire feed. */
class DeepDiveErrorBoundary extends Component<
  { children: ReactNode; onClose: () => void },
  { hasError: boolean }
> {
  constructor(props: { children: ReactNode; onClose: () => void }) {
    super(props);
    this.state = { hasError: false };
  }
  static getDerivedStateFromError(): { hasError: boolean } {
    return { hasError: true };
  }
  render() {
    if (this.state.hasError) {
      return (
        <div className="deep-dive dd-error-boundary" role="dialog" aria-label="Error">
          <div className="dd-error-boundary__inner">
            <p className="text-base empty-state__body">
              Unable to load analysis for this story.
            </p>
            <button className="btn-primary" onClick={this.props.onClose}>Close</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

import LoadingSkeleton from "./LoadingSkeleton";
import Footer from "./Footer";
import { useDailyBrief } from "./DailyBrief";
import SkyboxBanner from "./SkyboxBanner";
const FloatingPlayer = dynamic(() => import("./FloatingPlayer"), { ssr: false });
import { hapticConfirm, hapticScrollEdge, hapticMedium, hapticLight, hapticMicro } from "../lib/haptics";
const UnifiedOnboarding = dynamic(() => import("./UnifiedOnboarding"), { ssr: false });
import { KeyboardShortcutsOverlay, useStoryKeyboardNav } from "./KeyboardShortcuts";
import InstallPrompt from "./InstallPrompt";
import MobileBottomNav from "./MobileBottomNav";
import MobileFeed from "./MobileFeed";
import SearchOverlay from "./SearchOverlay";

/** Map pipeline category slugs (both fine-grained and desk) to display names.
 *  Fine-grained slugs from old pipeline runs are merged to their desk names. */
function capitalize(s: string): string {
  if (!s) return s;
  const map: Record<string, string> = {
    // Desk slugs (current pipeline output)
    politics: "Politics", conflict: "Conflict", economy: "Economy",
    science: "Science", health: "Health", environment: "Environment",
    culture: "Culture",
    // Legacy fine-grained slugs (old data in DB) → desk names
    tech: "Science", technology: "Science", sports: "Culture",
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

const EDITION_STORAGE_KEY = "void-news-edition";
const VALID_EDITIONS: Edition[] = ["world", "us", "india"];

function HomeContentInner({ initialEdition = "world" }: HomeContentProps) {
  // Edition state: URL-driven routes (/us, /india) pass the correct edition.
  // At root URL (/), initialEdition is always "world" — check localStorage for
  // a saved preference so returning visitors see their last-used edition.
  const [activeEdition, setActiveEdition] = useState<Edition>(() => {
    if (typeof window === "undefined") return initialEdition;
    // Only apply localStorage override at root URL — explicit /us or /india
    // routes should always honor their URL-specified edition.
    const p = window.location.pathname.replace(/\/+$/, "");
    const isRootUrl = p === "" || p === BASE_PATH;
    if (isRootUrl && initialEdition === "world") {
      try {
        const saved = localStorage.getItem(EDITION_STORAGE_KEY);
        if (saved && VALID_EDITIONS.includes(saved as Edition)) {
          return saved as Edition;
        }
      } catch {
        // localStorage unavailable (private browsing, etc.) — fall through
      }
    }
    return initialEdition;
  });

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
  const [isMobile, setIsMobile] = useState(() =>
    typeof window !== "undefined" ? window.innerWidth < 768 : false
  );

  // Search overlay state
  const [searchOpen, setSearchOpen] = useState(false);

  // Scroll position before DeepDive opened — restored on close (F06)
  const scrollBeforeDeepDive = useRef<number>(0);

  // Whip pan direction — track previous edition index for direction-aware animation
  const EDITION_ORDER: Edition[] = ["world", "us", "india"];
  const prevEditionRef = useRef<Edition>(activeEdition);
  const [whipDirection, setWhipDirection] = useState<"right" | "left">("right");

  // --- Pull-to-Refresh (mobile only) ---
  const [pullOffset, setPullOffset] = useState(0);
  const [isPulling, setIsPulling] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const pullStartRef = useRef<{ y: number; scrollY: number } | null>(null);
  const pullResetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const PULL_THRESHOLD = 60; // px of visual displacement to trigger refresh

  const handlePullStart = useCallback((e: React.TouchEvent) => {
    if (!isMobile || isRefreshing || selectedStory) return;
    pullStartRef.current = {
      y: e.touches[0].clientY,
      scrollY: window.scrollY,
    };
  }, [isMobile, isRefreshing, selectedStory]);

  const handlePullMove = useCallback((e: React.TouchEvent) => {
    if (!pullStartRef.current || isRefreshing) return;
    // Only pull-to-refresh when at scroll top
    if (pullStartRef.current.scrollY > 5 && window.scrollY > 5) return;
    const deltaY = e.touches[0].clientY - pullStartRef.current.y;
    if (deltaY <= 0) { setPullOffset(0); return; }
    // Rubber-band resistance
    const offset = Math.min(deltaY * 0.4, 100);
    setPullOffset(offset);
    if (!isPulling && offset > 10) setIsPulling(true);
  }, [isRefreshing, isPulling]);

  const handlePullEnd = useCallback(() => {
    if (!isPulling) { pullStartRef.current = null; return; }
    if (pullOffset >= PULL_THRESHOLD) {
      // Trigger refresh
      hapticConfirm();
      setIsRefreshing(true);
      setPullOffset(40); // Hold at indicator position
      setRetryKey(k => k + 1);
      // Reset after data loads — clear any prior timer before scheduling a new one
      if (pullResetTimerRef.current !== null) clearTimeout(pullResetTimerRef.current);
      pullResetTimerRef.current = setTimeout(() => {
        pullResetTimerRef.current = null;
        setIsRefreshing(false);
        setPullOffset(0);
        setIsPulling(false);
      }, 1500);
    } else {
      // Cancel — spring back
      hapticLight();
      setPullOffset(0);
      setIsPulling(false);
    }
    pullStartRef.current = null;
  }, [isPulling, pullOffset]);

  // Cleanup pull-to-refresh reset timer on unmount to prevent state updates
  // on an unmounted component if the user navigates away mid-refresh.
  useEffect(() => {
    return () => {
      if (pullResetTimerRef.current !== null) clearTimeout(pullResetTimerRef.current);
    };
  }, []);

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

  // Detect mobile for feed layout — responsive to viewport changes
  useEffect(() => {
    const mql = window.matchMedia("(max-width: 767px)");
    setIsMobile(mql.matches);
    const handler = (e: MediaQueryListEvent) => setIsMobile(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, []);

  // Cmd+K / Ctrl+K to open search
  useEffect(() => {
    function handleCmdK(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setSearchOpen((v) => !v);
      }
    }
    document.addEventListener("keydown", handleCmdK);
    return () => document.removeEventListener("keydown", handleCmdK);
  }, []);

  // Reset category filter, close DeepDive, and scroll to top when edition changes.
  // Lean filter is intentionally preserved — it's a universal preference
  // that persists until the user explicitly toggles it off.
  // Whip pan direction: content exits left when navigating "right" in edition order.
  useEffect(() => {
    hapticConfirm();
    setSelectedStory(null);
    setOriginRect(null);
    setActiveCategory("All");
    setVisibleCount(BATCH_SIZE);
    window.scrollTo({ top: 0, behavior: "smooth" });

    // Compute whip pan direction based on edition order
    const prevIdx = EDITION_ORDER.indexOf(prevEditionRef.current);
    const nextIdx = EDITION_ORDER.indexOf(activeEdition);
    if (prevIdx !== nextIdx) {
      setWhipDirection(nextIdx > prevIdx ? "right" : "left");
    }
    prevEditionRef.current = activeEdition;
  }, [activeEdition]);

  // Persist edition preference to localStorage — returning visitors who land
  // on the root URL (/) will see their last-used edition instead of "world".
  // Also sync the URL so it always reflects the active edition.
  // Set data-edition on <html> so CSS edition color grades activate.
  useEffect(() => {
    try {
      localStorage.setItem(EDITION_STORAGE_KEY, activeEdition);
    } catch {
      // localStorage unavailable — no-op
    }
    // Sync URL without triggering a full page reload
    const path = activeEdition === "world" ? `${BASE_PATH}/` : `${BASE_PATH}/${activeEdition}/`;
    if (window.location.pathname !== path) {
      window.history.pushState({}, "", path);
    }
    // Set data-edition on <html> — enables per-edition cinematic color grades
    // (e.g., warmer sepia for India, cooler contrast for US) defined in CSS.
    document.documentElement.setAttribute("data-edition", activeEdition);
  }, [activeEdition]);

  useEffect(() => {
    const controller = new AbortController();

    // Stale-while-revalidate: show cached stories instantly on mount,
    // then fetch fresh data in background and swap when ready.
    try {
      const cached = localStorage.getItem(`void-stories-${activeEdition}`);
      if (cached && stories.length === 0) {
        const parsed = JSON.parse(cached) as Story[];
        if (parsed.length > 0) {
          setStories(parsed);
        }
      }
    } catch { /* localStorage unavailable */ }

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
        const enrichedFields = `id,title,summary,category,section,sections,importance_score,source_count,first_published,last_updated,divergence_score,headline_rank,coverage_velocity,bias_diversity,consensus_points,divergence_points,rank_world,rank_us,rank_india`;
        const baseFields = `id,title,summary,category,section,sections,importance_score,source_count,first_published,last_updated`;

        // Use per-edition rank column for ordering (cross-edition differentiation)
        const rankColumn = `rank_${activeEdition}` as "rank_world" | "rank_us" | "rank_india";

        let res;
        let usingEnriched = true;

        res = await supabase
          .from("story_clusters")
          .select(enrichedFields)
          .contains("sections", [activeEdition])
          .order(rankColumn, { ascending: false })
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
          // Try to restore cached stories so the user never sees an empty feed
          // (pipeline mid-run, transient DB gap, or retention cleanup).
          try {
            const cached = localStorage.getItem(`void-stories-${activeEdition}`);
            if (cached) {
              const parsed = JSON.parse(cached) as Story[];
              if (parsed.length > 0) {
                setStories(parsed);
                setIsLoading(false);
                return;
              }
            }
          } catch { /* localStorage unavailable */ }
          setStories([]);
          setIsLoading(false);
          return;
        }

        if (controller.signal.aborted) return;

        /* eslint-disable @typescript-eslint/no-explicit-any */
        const mappedStories: Story[] = clusters.map(
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
              importance: cluster[`rank_${activeEdition}`] || cluster.headline_rank || cluster.importance_score || 50,
              divergenceScore: cluster.divergence_score || 0,
              headlineRank: cluster[`rank_${activeEdition}`] || cluster.headline_rank || cluster.importance_score || 50,
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
        const divScores = mappedStories
          .map((s) => s.divergenceScore)
          .filter((d) => d > 0)
          .sort((a, b) => a - b);
        if (divScores.length >= 5) {
          const p10 = divScores[Math.floor(divScores.length * 0.1)];
          const p90 = divScores[Math.floor(divScores.length * 0.9)];
          for (const s of mappedStories) {
            if (s.divergenceScore > 0) {
              if (s.divergenceScore >= p90) {
                s.sigilData.divergenceFlag = "divergent";
              } else if (s.divergenceScore <= p10) {
                s.sigilData.divergenceFlag = "consensus";
              }
            }
          }
        }

        setStories(mappedStories);
        setIsLoading(false);

        // Cache stories so the feed is never empty during pipeline gaps
        try {
          localStorage.setItem(
            `void-stories-${activeEdition}`,
            JSON.stringify(mappedStories.slice(0, 50)),
          );
        } catch { /* quota exceeded or unavailable — no-op */ }

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

  // Story slicing — desktop broadsheet: lead(2) + medium(3) + compact(rest)
  const leadStories = filteredStories.slice(0, 2);
  const mediumStories = filteredStories.slice(2, 5);
  const compactStories = filteredStories.slice(5);
  const visibleCompact = compactStories.slice(0, visibleCount);

  // Pool size depends on feed layout
  const poolSize = isMobile
    ? filteredStories.length - 1
    : compactStories.length;
  const hasMore = poolSize > visibleCount && poolSize > 0;

  const loadMoreStories = useCallback(() => {
    hapticScrollEdge();
    setVisibleCount(prev => Math.min(prev + BATCH_SIZE, compactStories.length));
  }, [compactStories.length]);

  // Infinite scroll via IntersectionObserver on sentinel (desktop + mobile)
  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || !hasMore) return;

    const observer = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) loadMoreStories(); },
      { rootMargin: "200px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, loadMoreStories]);

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

  // Search: when a result is selected, open its Deep Dive
  const handleSearchSelect = useCallback((story: Story) => {
    setSearchOpen(false);
    handleStoryClick(story, new DOMRect());
  }, [handleStoryClick]);

  const editionMeta = EDITIONS.find((e) => e.slug === activeEdition) ?? EDITIONS[0];

  return (
    <div className="page-container" data-whip={whipDirection === "left" ? "left" : undefined}>
      <NavBar
        activeEdition={activeEdition}
        activeCategory={activeCategory}
        onCategoryChange={(cat) => { setActiveCategory(cat); setVisibleCount(BATCH_SIZE); }}
        activeLean={activeLean}
        onLeanChange={(lean) => { setActiveLean(lean); setVisibleCount(BATCH_SIZE); }}
        onSearchClick={() => setSearchOpen(true)}
        hasAudio={!!dailyBriefState.brief?.audio_url}
        isAudioPlaying={dailyBriefState.isPlaying}
        onOnairClick={() => {
          dailyBriefState.setPlayerVisible(true);
          if (!dailyBriefState.isPlaying) dailyBriefState.handlePlayPause();
        }}
      />

      <main
        id="main-content"
        className="page-main anim-cold-open-feed"
        onTouchStart={handlePullStart}
        onTouchMove={handlePullMove}
        onTouchEnd={handlePullEnd}
      >
        {/* Pull-to-refresh indicator (mobile) */}
        {(isPulling || isRefreshing) && (
          <div
            className="pull-to-refresh"
            style={{
              height: `${pullOffset}px`,
              opacity: Math.min(1, pullOffset / PULL_THRESHOLD),
              transition: isPulling ? "none" : "height 300ms cubic-bezier(0.2, 1, 0.3, 1), opacity 300ms ease-out",
            }}
          >
            <div
              className={`pull-to-refresh__spinner ${isRefreshing ? "pull-to-refresh__spinner--active" : ""}`}
              style={{
                transform: `rotate(${pullOffset * 3}deg)`,
                transition: isPulling ? "none" : "transform 300ms ease-out",
              }}
            >
              {isRefreshing ? "↻" : "↓"}
            </div>
            <span className="pull-to-refresh__text">
              {isRefreshing ? "Updating…" : pullOffset >= PULL_THRESHOLD ? "Release to refresh" : "Pull to refresh"}
            </span>
          </div>
        )}

        {/* Filters now integrated into NavBar — no separate filter row */}

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

            {/* News feed — mobile gets MobileFeed, desktop keeps broadsheet */}
            {!isLoading && stories.length > 0 && (
              isMobile ? (
                <MobileFeed
                  stories={filteredStories}
                  dailyBriefState={dailyBriefState}
                  onStoryClick={handleStoryClick}
                  filterKey={filterKey}
                  visibleCount={visibleCount}
                  hasMore={hasMore}
                  sentinelRef={sentinelRef}
                  kbdFocusIndex={kbdFocusIndex}
                  editionMeta={editionMeta}
                />
              ) : (
                <>
                  <div className="skybox" role="complementary" aria-label="void originals">
                    <SkyboxBanner state={dailyBriefState} />
                  </div>

                  {leadStories.length > 0 && (
                    <section key={filterKey} aria-label="Lead stories" className="lead-section anim-content-arrive">
                      {leadStories.map((story, i) => (
                        <div key={story.id} className="lead-section__col" style={{ animationDelay: `${Math.round(50 * Math.log2(i + 2))}ms` }}>
                          <div data-story-index={i}>
                            <LeadStory story={story} rank={i} onStoryClick={handleStoryClick} kbdFocused={kbdFocusIndex === i} />
                          </div>
                        </div>
                      ))}
                    </section>
                  )}

                  {mediumStories.length > 0 && (
                    <section key={`med-${filterKey}`} aria-label="Top stories" className="grid-medium">
                      {mediumStories.map((story, idx) => {
                        const gi = leadStories.length + idx;
                        return (
                          <div key={story.id} className="grid-medium__item" style={{ animationDelay: `${Math.round(50 * Math.log2(idx + 2))}ms` }}>
                            <StoryCard story={story} index={idx + 1} onStoryClick={handleStoryClick} globalIndex={gi} kbdFocused={kbdFocusIndex === gi} />
                          </div>
                        );
                      })}
                    </section>
                  )}

                  {compactStories.length > 0 && (
                    <>
                      <section key={`cmp-${filterKey}`} aria-label="More stories" className="grid-compact">
                        {visibleCompact.map((story, idx) => {
                          const gi = leadStories.length + mediumStories.length + idx;
                          return (
                            <div key={story.id} className="grid-compact__item" style={{ animationDelay: `${Math.round(50 * Math.log2((idx % BATCH_SIZE) + 2))}ms` }}>
                              <StoryCard
                                story={story}
                                index={idx + mediumStories.length + 1}
                                onStoryClick={handleStoryClick}
                                globalIndex={gi}
                                kbdFocused={kbdFocusIndex === gi}
                              />
                            </div>
                          );
                        })}
                      </section>

                      {hasMore && (
                        <div className="feed-sentinel" ref={sentinelRef} aria-hidden="true" />
                      )}
                    </>
                  )}

                  {filteredStories.length > 0 && (
                    <div className="edition-line">
                      <span className="edition-meta">
                        {editionMeta.label} Edition / {filteredStories.length} stories
                      </span>
                      <LogoWordmark height={14} />
                    </div>
                  )}
                </>
              )
            )}
        </>
      </main>

      {/* Footer */}
      {!isLoading && <Footer lastUpdated={lastUpdated} />}

      {/* Deep Dive panel — wrapped in its own ErrorBoundary so one bad
           cluster doesn't crash the entire feed */}
      {selectedStory && (
        <DeepDiveErrorBoundary onClose={handleDeepDiveClose}>
          <DeepDive
            story={selectedStory}
            onClose={handleDeepDiveClose}
            originRect={originRect}
            onNavigate={handleDeepDiveNav}
            storyIndex={filteredStories.findIndex((s) => s.id === selectedStory.id)}
            totalStories={filteredStories.length}
          />
        </DeepDiveErrorBoundary>
      )}

      {/* Search overlay — Cmd+K */}
      <SearchOverlay
        stories={filteredStories}
        onStorySelect={handleSearchSelect}
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
      />

      {/* Unified onboarding — carousel (concepts) then spotlight tour (real UI) */}
      <UnifiedOnboarding active={!isLoading && stories.length > 0} />

      {/* Keyboard shortcuts overlay — press ? to toggle */}
      <KeyboardShortcutsOverlay />

      {/* PWA install prompt — 2nd+ visit, above bottom nav */}
      <InstallPrompt />

      {/* Floating audio player — persistent, above all content */}
      {dailyBriefState.brief?.audio_url && (
        <audio ref={dailyBriefState.audioCallbackRef} src={dailyBriefState.brief.audio_url} preload="metadata" hidden />
      )}
      <FloatingPlayer state={dailyBriefState} />

      {/* Mobile bottom nav — single-row filters (thumb-reachable) */}
      {isMobile && (
        <MobileBottomNav
          activeEdition={activeEdition}
          onEditionChange={(edition) => { setActiveEdition(edition); setVisibleCount(BATCH_SIZE); }}
          activeLean={activeLean}
          onLeanChange={(lean) => { setActiveLean(lean); setVisibleCount(BATCH_SIZE); }}
          activeCategory={activeCategory}
          onCategoryChange={(cat) => { setActiveCategory(cat); setVisibleCount(BATCH_SIZE); }}
        />
      )}
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
