"use client";

import React, { useState, useEffect, useMemo, useCallback, useRef, Component, type ReactNode } from "react";
import dynamic from "next/dynamic";
import type { Edition, Category, Story, BiasScores, BiasSpread, ThreeLensData, OpinionLabel, SigilData } from "../lib/types";
import { EDITIONS } from "../lib/types";
import { isUnscoredTilt } from "../lib/biasColors";
import { supabase, supabaseError } from "../lib/supabase";
import { cacheGet, cacheSet } from "../lib/feedCache";
import { BASE_PATH } from "../lib/utils";
import { AUDIO_ENABLED } from "../lib/audioGate";
import { getDeepDiveMode, type DeepDiveMode } from "../lib/deepDiveModeGate";
import LogoIcon from "./LogoIcon";
import LogoWordmark from "./LogoWordmark";
import NavBar from "./NavBar";
import LeadStory from "./LeadStory";
import StoryCard from "./StoryCard";
import { computeStoryFamilies } from "../lib/storyFamilies";
const DeepDive = dynamic(() => import("./DeepDive"), { ssr: false });
const InlineDeepDive = dynamic(() => import("./InlineDeepDive"), { ssr: false });
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
import { hapticConfirm, hapticLight } from "../lib/haptics";
const UnifiedOnboarding = dynamic(() => import("./UnifiedOnboarding"), { ssr: false });
import { useStoryKeyboardNav } from "./KeyboardShortcuts";
const KeyboardShortcutsOverlay = dynamic(() => import("./KeyboardShortcuts").then(m => ({ default: m.KeyboardShortcutsOverlay })), { ssr: false });
import InstallPrompt from "./InstallPrompt";
import MobileFeed from "./MobileFeed";
// WorldDivider removed 2026-06-02 — no overflow split in single-feed mode.
const SearchOverlay = dynamic(() => import("./SearchOverlay"), { ssr: false });

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

/* ---------------------------------------------------------------------------
   Editorial feed constants — newspaper-principle (same feed for all readers)
   --------------------------------------------------------------------------- */

/** Hard cap: maximum stories in the main edition feed when fully expanded. */
const EDITION_FEED_SIZE = 50;

/** Default visible window before the reader expands the feed. After 30 the
 *  page invites a one-click reveal of stories 31..50, then the World section. */
const EDITION_FEED_DEFAULT = 30;

/** Maximum World overflow stories appended after the main feed. */
const WORLD_OVERFLOW_SIZE = 30;

/** Total fetched from Supabase — main feed + headroom for overflow + buffer for
 *  the ≥3-source quality floor. Server-side ranker enforces topic diversity. */
const FETCH_LIMIT = 100;


interface HomeContentProps {
  initialEdition?: Edition;
}

/* ---------------------------------------------------------------------------
   HomeContent — News Feed
   Desktop: broadsheet grid — lead story + asymmetric layout + dense compact
   Mobile: single-column tabloid stack
   Edition is URL-driven: each edition has its own route.
   --------------------------------------------------------------------------- */

// 2026-06-02 single-feed — activeEdition collapsed to a constant.
// initialEdition prop kept for back-compat with /[edition]/page.tsx routes
// (which now redirect to /), but unused — the feed is always "world".
const activeEdition = "world" as const;

function HomeContentInner({ initialEdition: _initialEdition = "world" }: HomeContentProps) {
  void _initialEdition;

  const [stories, setStories] = useState<Story[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  // retryKey: incrementing triggers the data-fetch useEffect without a full
  // page reload — gives users a clean retry path from the error state.
  const [retryKey, setRetryKey] = useState(0);
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);
  const [originRect, setOriginRect] = useState<DOMRect | null>(null);

  // Deep Dive mode — "card" (legacy modal) or "inline" (in-feed expand).
  // MUST initialize to "card" so SSR + first client paint match (the query
  // override + env are resolved in the useEffect below, after mount). The
  // default `card` render path is byte-identical to before; only `inline`
  // branches diverge.
  const [deepDiveMode, setDeepDiveMode] = useState<DeepDiveMode>("card");
  useEffect(() => {
    setDeepDiveMode(getDeepDiveMode());
  }, []);

  // Initial value MUST be false (matches SSR) — the matchMedia useEffect below
  // promotes it to true on mobile after mount. Reading data-viewport synchronously
  // here caused React #418 hydration mismatch on every iPhone-width route because
  // the layout.tsx inline script set data-viewport='mobile' before hydration, but
  // SSR rendered with isMobile=false. 1-frame flash on mobile is unavoidable for
  // SSG; the useEffect runs in the first paint commit cycle.
  const [isMobile, setIsMobile] = useState(false);

  // Search overlay state
  const [searchOpen, setSearchOpen] = useState(false);

  // Scroll position before DeepDive opened — restored on close (F06)
  const scrollBeforeDeepDive = useRef<number>(0);

  // 2026-06-02 single-feed — edition transition / whip-pan state removed.
  // Constants kept so existing render paths compile without rewiring.
  const whipDirection = "right" as const;
  const isEditionSwitch = false;
  const editionTransition: null = null;

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
    // Rubber-band resistance — progressive (native iOS feel)
    const offset = Math.min(Math.pow(deltaY, 0.7), 100);
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

  // Cleanup timers on unmount to prevent state updates on unmounted component.
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

  // Inline-mode collapse — clear the open story and glide back to where the user
  // was when they opened it. The inline block is in the document flow, so removing
  // it changes scroll height; restore after the DOM updates (double rAF) so we
  // land on the original feed position instead of a clamped spot.
  const handleInlineCollapse = useCallback(() => {
    const restore = scrollBeforeDeepDive.current;
    setSelectedStory(null);
    setOriginRect(null);
    requestAnimationFrame(() =>
      requestAnimationFrame(() => window.scrollTo({ top: restore, behavior: "smooth" })),
    );
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

  // 2026-06-02 single-feed — edition switch effects removed (was whip pan,
  // cross-fade, localStorage, URL push, data-edition attribute). The page
  // is always "world" and the URL never changes from /.
  useEffect(() => {
    document.documentElement.setAttribute("data-edition", "world");
  }, []);

  // Scene 7: Practical light warmth propagation — when audio is playing,
  // the page-main receives a subtle warm sepia tint (motivated by the
  // OnAir "practical" light source). The CSS rule .page-main--audio-playing
  // applies sepia(0.01) layered on top of the existing color grade.
  useEffect(() => {
    const el = document.querySelector('.page-main');
    if (!el) return;
    if (dailyBriefState.isPlaying) {
      el.classList.add('page-main--audio-playing');
    } else {
      el.classList.remove('page-main--audio-playing');
    }
  }, [dailyBriefState.isPlaying]);

  // Coerce cached Story fields to strings — localStorage may contain stale
  // data from before JSONB coercion was added, triggering React #310.
  function sanitizeStory(s: Story): Story {
    return {
      ...s,
      title: typeof s.title === "string" ? s.title : String(s.title ?? ""),
      summary: typeof s.summary === "string" ? s.summary : String(s.summary ?? ""),
      category: (typeof s.category === "string" ? s.category : "Politics") as Category,
      deepDive: s.deepDive ? {
        ...s.deepDive,
        consensus: Array.isArray(s.deepDive.consensus)
          ? s.deepDive.consensus.map((p: unknown) => typeof p === "string" ? p : String(p ?? ""))
          : [],
        divergence: Array.isArray(s.deepDive.divergence)
          ? s.deepDive.divergence.map((p: unknown) => typeof p === "string" ? p : String(p ?? ""))
          : [],
      } : undefined,
    };
  }

  useEffect(() => {
    const controller = new AbortController();

    // Stale-while-revalidate via IndexedDB: show cached stories instantly
    // on repeat visits (no loading skeleton), then fetch fresh data in
    // background and silently swap when ready.
    let hasCachedData = false;

    async function loadCachedStories() {
      const cacheKey = `feed-${activeEdition}`;
      const cached = await cacheGet<Story[]>(cacheKey);
      if (cached && cached.data.length > 0 && !controller.signal.aborted) {
        setStories(cached.data.map(sanitizeStory));
        setIsLoading(false);
        hasCachedData = true;
      }
    }

    async function loadFromSupabase() {
      // Only show loading skeleton when there is no cached data to display.
      // On repeat visits, cached stories are already rendered — skeleton would
      // flash over visible content.
      if (!hasCachedData) {
        setIsLoading(true);
      }
      setError(null);

      // Guard: if Supabase client is unavailable, surface a user-friendly error
      // rather than throwing a TypeError on the first .from() call.
      if (!supabase) {
        setError(supabaseError ?? "Unable to connect to data source.");
        setIsLoading(false);
        return;
      }

      try {
        // is_international is added by the 2026-05-15 pipeline upgrade. Older
        // schemas don't have the column — the enriched-fields select will fail
        // and we fall back to base, which silently treats every story as
        // non-international (no World overflow rendered).
        // 2026-05-24 v2 — added is_headline + headline_confidence (migration 059).
        // Used to render the HEADLINE badge and to prioritize sort on /world.
        const enrichedFields = `id,title,summary,category,section,sections,importance_score,source_count,first_published,last_updated,divergence_score,headline_rank,coverage_velocity,bias_diversity,consensus_points,divergence_points,rank_world,claim_consensus,cached_image_url,is_international,is_headline,headline_confidence`;
        const baseFields = `id,title,summary,category,section,sections,importance_score,source_count,first_published,last_updated`;

        // Single daily feed — rank_world is the sole rank column (the other
        // per-edition rank columns were dropped by migration 061).
        const rankColumn = "rank_world" as const;

        let res;
        let usingEnriched = true;

        res = await supabase
          .from("story_clusters")
          .select(enrichedFields)
          .contains("sections", [activeEdition])
          .order(rankColumn, { ascending: false })
          .limit(FETCH_LIMIT);

        // If enriched query failed (columns don't exist — e.g. is_international
        // missing on older schema), retry with the smaller enriched set minus
        // is_international before bottoming out at base.
        if (res.error) {
          res = await supabase
            .from("story_clusters")
            .select(enrichedFields.replace(",is_international", ""))
            .contains("sections", [activeEdition])
            .order(rankColumn, { ascending: false })
            .limit(FETCH_LIMIT);
        }
        if (res.error) {
          usingEnriched = false;
          res = await supabase
            .from("story_clusters")
            .select(baseFields)
            .contains("sections", [activeEdition])
            .order("first_published", { ascending: false })
            .limit(FETCH_LIMIT);
        }

        if (controller.signal.aborted) return;

        const clusters = res.data || [];

        if (clusters.length === 0) {
          // When Supabase returns empty (pipeline mid-run, transient DB gap),
          // keep showing any cached data already on screen rather than blanking.
          if (!hasCachedData) {
            // Last resort: try IndexedDB for any previously cached feed
            const cached = await cacheGet<Story[]>(`feed-${activeEdition}`);
            if (cached && cached.data.length > 0) {
              setStories(cached.data.map(sanitizeStory));
              setIsLoading(false);
              return;
            }
            setStories([]);
          }
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
                  polarization: safeNum(bd, "polarization", 0),
                  leanLeftCount: safeNum(bd, "lean_left_count", 0),
                  leanCenterCount: safeNum(bd, "lean_center_count", 0),
                  leanRightCount: safeNum(bd, "lean_right_count", 0),
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
            const claimCon = cluster.claim_consensus;
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
              unscored: hasBiasData && isUnscoredTilt(
                biasScores.politicalLean,
                sourceCount,
                biasSpread?.leanSpread ?? 0,
                biasSpread?.leanRange ?? 0,
                biasSpread?.aggregateConfidence ?? 0,
              ),
              opinionLabel,
              consensusCorroborated: claimCon?.corroborated,
              consensusTotal: claimCon?.total_claims,
            };

            const rawConsensus = usingEnriched ? cluster.consensus_points : null;
            const rawDivergence = usingEnriched ? cluster.divergence_points : null;
            const consensusPoints: string[] = Array.isArray(rawConsensus)
              ? rawConsensus.map((p: unknown) => typeof p === "string" ? p : String(p ?? ""))
              : [];
            const divergencePoints: string[] = Array.isArray(rawDivergence)
              ? rawDivergence.map((p: unknown) => typeof p === "string" ? p : String(p ?? ""))
              : [];

            // Defensive: coerce title/summary to string — JSONB fields or
            // corrupted data can return objects, crashing React (#310).
            const safeTitle = typeof cluster.title === "string" ? cluster.title : String(cluster.title ?? "");
            const safeSummary = typeof cluster.summary === "string" ? cluster.summary : String(cluster.summary ?? "");

            return {
              id: cluster.id,
              title: safeTitle,
              summary: safeSummary,
              source: {
                name: "Multiple Sources",
                count: sourceCount,
              },
              category: capitalize(typeof cluster.category === "string" ? cluster.category : "politics") as Category,
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
              importance: cluster.rank_world || cluster.headline_rank || cluster.importance_score || 50,
              divergenceScore: cluster.divergence_score || 0,
              headlineRank: cluster.rank_world || cluster.headline_rank || cluster.importance_score || 50,
              coverageVelocity: cluster.coverage_velocity || 0,
              deepDive: consensusPoints.length > 0 || divergencePoints.length > 0 || cluster.claim_consensus
                ? {
                    consensus: consensusPoints,
                    divergence: divergencePoints,
                    sources: [],
                    claimConsensus: cluster.claim_consensus || undefined,
                  }
                : undefined,
              cachedImageUrl: cluster.cached_image_url ?? null,
              // is_international flag: true when the story belongs to the World
              // overflow section. Defensive Boolean cast — older schemas without
              // the column return undefined → falsy, no overflow rendered.
              // Cast through unknown to bypass Story interface (extra field).
              is_international: Boolean(cluster.is_international),
            } as unknown as Story;
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

        // Persist to IndexedDB for instant render on next visit. Cache the
        // full fetched set so the World overflow renders instantly too.
        cacheSet(`feed-${activeEdition}`, mappedStories.slice(0, FETCH_LIMIT), activeEdition);

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

    // Load cached data first (instant), then revalidate from Supabase.
    // Sequential: cache read must complete before Supabase fetch starts
    // so we know whether to show the loading skeleton.
    loadCachedStories().then(() => loadFromSupabase());
    return () => controller.abort();
  }, [activeEdition, retryKey]);

  // Defensive strip of legacy ?lean=&cat= params from old shareable links.
  // Filters were removed in 2026-05-15 redesign — these params no longer
  // do anything, so clean them out of the URL on mount.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    let changed = false;
    for (const key of ["lean", "cat"]) {
      if (url.searchParams.has(key)) {
        url.searchParams.delete(key);
        changed = true;
      }
    }
    if (changed) window.history.replaceState({}, "", url.toString());
  }, []);

  const filteredStories = useMemo(() => {
    // Quality floor: hide clusters with fewer than 3 sources.
    // Single-source wire regurgitations and 2-source duds are low-signal.
    // Three sources = minimum 2 independent editorial decisions to cover a story.
    // Server-side ranker enforces topic diversity and rank order — no
    // client-side filtering or category cap. Pure curation.
    return stories.filter((s) => (s.sigilData?.sourceCount ?? s.source?.count ?? 0) >= 3);
  }, [stories]);

  // Main feed = top 50 by rank. World overflow = remaining international
  // stories not already in the main feed, capped at 30. Defensive Boolean
  // cast on is_international handles missing-column case (older schemas
  // produce no overflow, page renders cleanly without the divider).
  // Full main pool (capped at 50). Visible window starts at 30 and expands
  // to 50 on reader request. Server-side ranker is the editorial source of
  // truth; no client-side reordering.
  const mainPool = useMemo(
    () => filteredStories.slice(0, EDITION_FEED_SIZE),
    [filteredStories],
  );

  // Reader-controlled disclosure: default to 30, click "Show 20 more" to
  // reveal 31..50 BEFORE the World section. Pure curation principle —
  // editor sorts; reader paces. Resets to collapsed on edition switch.
  const [feedExpanded, setFeedExpanded] = useState(false);
  useEffect(() => {
    setFeedExpanded(false);
  }, [activeEdition]);

  const mainStories = useMemo(
    () => mainPool.slice(0, feedExpanded ? EDITION_FEED_SIZE : EDITION_FEED_DEFAULT),
    [mainPool, feedExpanded],
  );

  /* Same-Story Cluster Family detection. When two or more top-10 cards
     are angles on the same event (Beijing summit, Iran ceasefire collapse),
     compute the family relationship from stemmed-title Jaccard and pass
     it down so StoryCard can render a "Related: N angles" chip. Catches
     the rare cases where the hardened clustering engine (rev 44) keeps
     legitimately-related sub-stories apart. */
  const storyFamilies = useMemo(
    () => computeStoryFamilies(mainStories, { topN: 10, jaccardFloor: 0.30 }),
    [mainStories],
  );
  const hiddenMainCount = mainPool.length - mainStories.length;

  const mainIds = useMemo(
    () => new Set(mainPool.map((s) => s.id)),
    [mainPool],
  );
  // 2026-06-02 single-feed — worldOverflow collapsed to an empty array.
  // The /world overflow split is gone; the homepage now shows a single
  // 50-story flow. Variable kept so downstream consumers (visibleStories,
  // aria announcements) don't need rewiring.
  const worldOverflow: Story[] = useMemo(() => [], []);
  void mainIds;
  void WORLD_OVERFLOW_SIZE;

  // v3 (2026-05-14): twin top stories — ranks 0 and 1 share the hero canvas
  // as co-equal "Top Story" leads. Grid below holds ranks 2..N where N is
  // the visible-window size (30 or 50).
  const twinLeads = mainStories.slice(0, 2);
  const gridStories = mainStories.slice(2);

  // --- Inline Deep Dive split (inline mode only) ---------------------------
  // When deepDiveMode === "inline" and a story is open, the feed splits around
  // it so the expanded block renders full-width in the document flow. These
  // values stay inert in "card" mode (inlineActive is false), so the card
  // render path is byte-identical.
  const inlineActive = deepDiveMode === "inline" && selectedStory != null;
  // Index of the open story within mainStories: 0/1 = twin lead, >=2 = grid.
  const inlineIndex = inlineActive
    ? mainStories.findIndex((s) => s.id === selectedStory!.id)
    : -1;
  // Open story is one of the two twin leads (replaces the whole twin block).
  const inlineInLead = inlineActive && inlineIndex >= 0 && inlineIndex < 2;
  // Open story is in the grid — split position within gridStories.
  const inlineGridSplit = inlineActive && inlineIndex >= 2 ? inlineIndex - 2 : -1;

  // Lead hero image removed 2026-05-13 — text-only newspaper composition.

  // Continuous-scroll set: main feed + World overflow. Keyboard nav (J/K) and
  // Deep Dive prev/next traverse this combined order so the divider doesn't
  // interrupt navigation. Search also operates on this set.
  const visibleStories = useMemo(
    () => [...mainStories, ...worldOverflow],
    [mainStories, worldOverflow],
  );

  // Stable key per edition — when activeEdition changes the grid replays its
  // entrance animation. Filters are gone, so the key only varies by edition.
  const filterKey = activeEdition;

  // Keyboard navigation — J/K to move through stories, Enter to open Deep Dive
  const kbdSelectStory = useCallback((index: number) => {
    if (index >= 0 && index < visibleStories.length) {
      handleStoryClick(visibleStories[index], new DOMRect());
    }
  }, [visibleStories, handleStoryClick]);

  const kbdFocusIndex = useStoryKeyboardNav(
    visibleStories,
    kbdSelectStory,
    !!selectedStory,
  );

  // Single grid-card renderer — shared by the unsplit grid and both halves of
  // the inline split so the index-derived props (globalIndex, variant, family,
  // keyboard focus) stay identical regardless of which path renders the card.
  // `idx` is the card's position within gridStories (rank = idx + 2). Declared
  // after kbdFocusIndex since it closes over it.
  const renderGridCard = useCallback(
    (story: Story, idx: number) => {
      const gi = 2 + idx;
      const variant: "digest" | "wire" = idx < 8 ? "digest" : "wire";
      const family = storyFamilies.get(story.id);
      return (
        <div key={story.id} className="feed-grid__item">
          <StoryCard
            story={story}
            index={idx + 2}
            onStoryClick={handleStoryClick}
            globalIndex={gi}
            kbdFocused={kbdFocusIndex === gi}
            variant={variant}
            family={family}
          />
        </div>
      );
    },
    [storyFamilies, handleStoryClick, kbdFocusIndex],
  );

  // Inter-story navigation within Deep Dive — traverses main + overflow.
  const handleDeepDiveNav = useCallback((direction: "prev" | "next") => {
    if (!selectedStory) return;
    const idx = visibleStories.findIndex((s) => s.id === selectedStory.id);
    if (idx < 0) return;
    const newIdx = direction === "prev" ? idx - 1 : idx + 1;
    if (newIdx >= 0 && newIdx < visibleStories.length) {
      setSelectedStory(visibleStories[newIdx]);
    }
  }, [selectedStory, visibleStories]);

  // Search: when a result is selected, open its Deep Dive
  const handleSearchSelect = useCallback((story: Story) => {
    setSearchOpen(false);
    handleStoryClick(story, new DOMRect());
  }, [handleStoryClick]);

  const editionMeta = EDITIONS.find((e) => e.slug === activeEdition) ?? EDITIONS[0];

  return (
    <div className="page-container">
      <NavBar
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
        className="page-main"
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
              transition: isPulling ? "none" : "height 300ms var(--spring-snappy), opacity 300ms ease-out",
            }}
          >
            <div className="pull-to-refresh__spinner">
              <LogoIcon size={24} animation={isRefreshing ? "analyzing" : "idle"} />
            </div>
          </div>
        )}

        {/* Filters now integrated into NavBar — no separate filter row */}

        {/* Live region, loading, error, empty states, story grids */}
        <>
            {/* Live region for screen readers — announces story count + World section */}
            <div aria-live="polite" className="sr-only">
              {!isLoading && mainStories.length > 0 &&
                `${mainStories.length} stories loaded.${worldOverflow.length > 0 ? ` World section follows with ${worldOverflow.length} international stories.` : ""} Press ? for keyboard shortcuts.`}
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
                  No stories yet. The pipeline is still collecting and analyzing
                  sources. The next update will appear shortly.
                </p>
                <p className="edition-meta">
                  Editions: 7 AM &middot; 2 PM &middot; 8 PM Chicago
                </p>
              </div>
            )}

            {/* News feed — mobile gets MobileFeed, desktop keeps broadsheet */}
            {!isLoading && stories.length > 0 && (
              isMobile ? (
                <>
                  <MobileFeed
                    stories={mainStories}
                    dailyBriefState={dailyBriefState}
                    onStoryClick={handleStoryClick}
                    filterKey={filterKey}
                    kbdFocusIndex={kbdFocusIndex}
                    editionMeta={editionMeta}
                    selectedStory={selectedStory}
                    onInlineCollapse={handleInlineCollapse}
                    transitionClass={editionTransition === "out" ? "anim-edition-out" : editionTransition === "in" ? "anim-edition-in" : undefined}
                  />

                  {/* World overflow — international stories that didn't make
                      the homepage cut. Rendered inline as one continuous scroll
                      below the main feed; kbdFocusIndex offset by mainStories.length. */}
                  {/* World overflow removed 2026-06-02 single-feed. */}
                </>
              ) : (
                <>
                  <div className="skybox">
                    <SkyboxBanner state={dailyBriefState} />
                  </div>

                  {/* Twin top stories — ranks 0 and 1, co-equal "Top Story"
                      leads side-by-side in a 50/50 split (vertical stack on
                      <1024px). Both wear the badge. v3 2026-05-14.
                      Inline mode: when one of the twin leads is open, the whole
                      twin block is replaced by the full-width InlineDeepDive. */}
                  {inlineInLead ? (
                    <InlineDeepDive key={selectedStory!.id} story={selectedStory!} onCollapse={handleInlineCollapse} />
                  ) : (
                    twinLeads.length > 0 && (
                      <div key={filterKey} className={`lead-twin hero-slot${isEditionSwitch ? " anim-content-arrive" : ""}${inlineActive ? " lead-twin--recede" : ""}`}>
                        {twinLeads.map((story, idx) => (
                          <LeadStory
                            key={story.id}
                            story={story}
                            rank={idx}
                            twin={twinLeads.length === 2}
                            onStoryClick={handleStoryClick}
                            kbdFocused={kbdFocusIndex === idx}
                          />
                        ))}
                      </div>
                    )
                  )}

                  {/* Grid below twin leads — ranks 2-49 (digest at 2-9, wire
                      at 10-49). Slot math: 8 digest + 40 wire = 48 grid cards,
                      plus 2 twin leads above = 50 total.
                      Inline mode: when a grid card is open, the grid is split
                      into two sub-grids with the full-width InlineDeepDive
                      between them (one <section> each avoids the empty-cell gap
                      that grid-column:1/-1 would leave). The original grid index
                      is preserved on each card so variant + globalIndex math is
                      identical to the unsplit grid. */}
                  {gridStories.length > 0 && (
                    inlineGridSplit >= 0 ? (
                      <React.Fragment key={`grid-split-${filterKey}`}>
                        {inlineGridSplit > 0 && (
                          <section aria-label="Stories" className="feed-grid feed-grid--recede">
                            {gridStories.slice(0, inlineGridSplit).map((story, idx) =>
                              renderGridCard(story, idx),
                            )}
                          </section>
                        )}
                        <InlineDeepDive key={selectedStory!.id} story={selectedStory!} onCollapse={handleInlineCollapse} />
                        {inlineGridSplit < gridStories.length - 1 && (
                          <section aria-label="Stories" className="feed-grid feed-grid--recede">
                            {gridStories.slice(inlineGridSplit + 1).map((story, sIdx) =>
                              renderGridCard(story, inlineGridSplit + 1 + sIdx),
                            )}
                          </section>
                        )}
                      </React.Fragment>
                    ) : (
                      <section key={`grid-${filterKey}`} aria-label="Stories" className={`feed-grid${isEditionSwitch ? " anim-content-arrive" : ""}${inlineActive ? " feed-grid--recede" : ""}`}>
                        {gridStories.map((story, idx) => renderGridCard(story, idx))}
                      </section>
                    )
                  )}

                  {/* Expand-to-50 affordance — sits between the default
                      30-story window and the World section. Reader-controlled
                      disclosure of the remaining curated stories before the
                      international overflow. Hidden when already expanded
                      or when there's nothing more to reveal. */}
                  {!feedExpanded && hiddenMainCount > 0 && (
                    <div className="feed-expand">
                      <button
                        type="button"
                        className="feed-expand__btn"
                        onClick={() => {
                          hapticLight();
                          setFeedExpanded(true);
                        }}
                        aria-label={`Show ${hiddenMainCount} more stories`}
                      >
                        Show {hiddenMainCount} more
                      </button>
                    </div>
                  )}

                  {/* World overflow removed 2026-06-02 single-feed. */}

                  {visibleStories.length > 0 && (
                    <div className="edition-line">
                      <span className="edition-meta">
                        {mainStories.length} stories
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

      {/* Deep Dive panel (card mode) — wrapped in its own ErrorBoundary so one
           bad cluster doesn't crash the entire feed. The modal is NOT mounted
           on the desktop broadsheet in inline mode (InlineDeepDive renders
           in-feed instead) and is NO LONGER mounted on mobile (MobileFeed now
           expands InlineDeepDive in place — see its split-render path). This
           leaves the modal only for desktop `?dd=card`; it is slated for full
           removal in a later phase. */}
      {deepDiveMode === "card" && selectedStory && (
        <DeepDiveErrorBoundary onClose={handleDeepDiveClose}>
          <DeepDive
            story={selectedStory}
            onClose={handleDeepDiveClose}
            originRect={originRect}
            onNavigate={handleDeepDiveNav}
            storyIndex={visibleStories.findIndex((s) => s.id === selectedStory.id)}
            totalStories={visibleStories.length}
          />
        </DeepDiveErrorBoundary>
      )}

      {/* Search overlay — Cmd+K. Search across main feed + World overflow. */}
      <SearchOverlay
        stories={visibleStories}
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

      {/* Floating audio player — gated by AUDIO_DISABLED flag (void --onair
          parking lot). When flipped on, AudioProvider in layout.tsx owns
          the underlying audio element. */}
      {AUDIO_ENABLED && <FloatingPlayer state={dailyBriefState} />}
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
