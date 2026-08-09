"use client";

import React, { useState, useEffect, useMemo, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import type { Edition, Category, Story, BiasScores, BiasSpread, ThreeLensData, OpinionLabel, SigilData } from "../lib/types";
import { EDITIONS } from "../lib/types";
import { isUnscoredTilt } from "../lib/biasColors";
import { supabase, supabaseError } from "../lib/supabase";
import { cacheGet, cacheSet } from "../lib/feedCache";
import { cleanFeedSummary } from "../lib/summaryHygiene";
import { BASE_PATH } from "../lib/utils";
import LogoIcon from "./LogoIcon";
import LogoWordmark from "./LogoWordmark";
import NavBar from "./NavBar";
import LeadStory from "./LeadStory";
import StoryCard from "./StoryCard";
import { computeStoryFamilies } from "../lib/storyFamilies";
const DeepDiveOverlay = dynamic(() => import("./DeepDiveOverlay"), { ssr: false });
import ErrorBoundary from "./ErrorBoundary";

import LoadingSkeleton from "./LoadingSkeleton";
import Footer from "./Footer";
import { useDailyBrief } from "./DailyBrief";
import SkyboxBanner from "./SkyboxBanner";
// FloatingPlayer is now mounted globally in MobileNav (layout.tsx) so it renders
// on every route, including /weekly. It reads the global AudioProvider directly.
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
 *  page invites a one-click reveal of stories 31..50. */
const EDITION_FEED_DEFAULT = 30;

/** Total fetched from Supabase — main feed + headroom + buffer for the
 *  ≥3-source quality floor. Server-side ranker enforces topic diversity. */
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
  // Fires once: open a story's deep dive from a ?story=<id> deep link
  // (used by void --revolt "related coverage" cross-links).
  const deepLinkHandled = useRef(false);

  // Initial value MUST be false (matches SSR) — the matchMedia useEffect below
  // promotes it to true on mobile after mount. Reading data-viewport synchronously
  // here caused React #418 hydration mismatch on every iPhone-width route because
  // the layout.tsx inline script set data-viewport='mobile' before hydration, but
  // SSR rendered with isMobile=false. 1-frame flash on mobile is unavoidable for
  // SSG; the useEffect runs in the first paint commit cycle.
  const [isMobile, setIsMobile] = useState(false);

  // Search overlay state
  const [searchOpen, setSearchOpen] = useState(false);

  // Scroll-position preservation on Deep Dive open/close is owned by
  // DeepDiveOverlay (body scroll-lock + restore), so no local ref is needed.

  // 2026-06-02 single-feed: edition transition / whip-pan plumbing removed
  // (rev 46 collapse-editions). Only one feed exists, so the switch never fires.

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

  // The `rect` is retained in the signature for all callers (StoryCard,
  // MobileStoryCard, keyboard nav, deep link) but the overlay does not need it
  // for positioning — it is a centered modal / bottom sheet, not a FLIP morph.
  const handleStoryClick = useCallback((story: Story, _rect: DOMRect) => {
    void _rect;
    setSelectedStory(story);
  }, []);

  // Close the Deep Dive overlay. The overlay owns body scroll-lock and restores
  // the exact scroll position + returns focus to the triggering card on unmount,
  // so this only needs to clear the open story.
  const handleInlineCollapse = useCallback(() => {
    setSelectedStory(null);
  }, []);

  // Detect mobile for feed layout — responsive to viewport changes.
  // F5: keep React state AND the documentElement `data-viewport` attribute in
  // sync with the live viewport on every resize. The layout.tsx inline script
  // stamps data-viewport ONCE before first paint but never updates it, while the
  // feed CSS keys `.mf` (MobileFeed) vs `.feed-grid` (desktop) visibility off it
  // ([data-viewport="mobile"] .feed-grid { display:none } and the mirror rule).
  // A live resize across 767px flips this React branch (MobileFeed <-> desktop
  // grid) but left data-viewport stale, so CSS hid the newly-rendered feed and
  // every card vanished until a fresh navigation re-ran the inline script. The
  // loaded `stories` state survives the resize (deps are [activeEdition,
  // retryKey], so no refetch/remount), so syncing the attribute is all that is
  // needed to keep the cards on screen through the breakpoint switch.
  useEffect(() => {
    const mql = window.matchMedia("(max-width: 767px)");
    const sync = (matches: boolean) => {
      setIsMobile(matches);
      document.documentElement.setAttribute("data-viewport", matches ? "mobile" : "desktop");
      // Canvas-cap freeze workaround (measured on news.voidvision.org, 2026-08).
      // .page-main carries `filter: var(--cin-grade)`, which makes it a composited
      // layer whose COMPUTED STYLE Chromium restores STALE on a back/forward
      // navigation across the 767px breakpoint (load mobile, resize to desktop
      // while off-page, navigate back). The media-query cascade is never re-run
      // for this element, so its max-width stays frozen at the mobile value
      // (--canvas-max flips to 100% under 767px) and the whole canvas spills
      // edge-to-edge at desktop width. Reflow, class toggles, even display:none
      // do NOT clear the freeze; only writing the max-width property directly
      // re-resolves it. So re-assert the cap inline here, mirroring the CSS
      // literal in layout.css (.page-main). The value string flips across the
      // breakpoint, which guarantees style invalidation. This runs on mount, on
      // every breakpoint change, and on pageshow (see onPageShow below), covering
      // every restore path. The unfiltered .site-footer recomputes on its own, so
      // its pure-CSS cap in layout.css needs no nudge. NOTE: the base CSS cap
      // still owns first paint (no FOUC, correct with JS disabled); this only
      // corrects the post-restore frozen value on the one composited element.
      const pm = document.querySelector<HTMLElement>(".page-main");
      if (pm) pm.style.maxWidth = matches ? "100%" : "min(92vw, 1600px)";
    };
    sync(mql.matches);
    const handler = (e: MediaQueryListEvent) => sync(e.matches);
    mql.addEventListener("change", handler);
    // F6 (bfcache restore): the layout.tsx inline bootstrap stamps data-viewport
    // ONCE at first paint and the `change` handler above keeps it live on
    // resize, but NEITHER runs when the browser restores this page from the
    // back/forward cache (pageshow with persisted=true re-shows the frozen DOM
    // + JS heap without re-executing the head script or re-running effects). If
    // the viewport crossed the 767px breakpoint while the page sat in bfcache,
    // both the `data-viewport` attribute AND the frozen React `isMobile` state
    // are stale on restore. The feed CSS keys the whole layout off the attribute
    // ([data-viewport="mobile"] hides .skybox/.hero-slot/.feed-grid/.edition-line;
    // [data-viewport="desktop"] hides .mf), so a stale value renders the wrong
    // layout on back-nav: the desktop broadsheet display:none'd on a phone, or
    // the mobile feed forced full-bleed on desktop (the width cap appears lost).
    // Re-sync from the LIVE viewport on every pageshow, which fixes both the
    // attribute and the React state. Idempotent on a normal load (persisted=false).
    const onPageShow = () => sync(window.matchMedia("(max-width: 767px)").matches);
    window.addEventListener("pageshow", onPageShow);
    return () => {
      mql.removeEventListener("change", handler);
      window.removeEventListener("pageshow", onPageShow);
    };
  }, []);

  // Active desktop grid column count (matches responsive.css breakpoints:
  // 768->2, 1024->3, 1440->4; mobile is single-column). Used by F15 to balance
  // the collapsed grid so the last row never leaves a single-card orphan.
  const [gridColumns, setGridColumns] = useState(1);
  useEffect(() => {
    const q4 = window.matchMedia("(min-width: 1440px)");
    const q3 = window.matchMedia("(min-width: 1024px)");
    const q2 = window.matchMedia("(min-width: 768px)");
    const compute = () => setGridColumns(q4.matches ? 4 : q3.matches ? 3 : q2.matches ? 2 : 1);
    compute();
    q4.addEventListener("change", compute);
    q3.addEventListener("change", compute);
    q2.addEventListener("change", compute);
    return () => {
      q4.removeEventListener("change", compute);
      q3.removeEventListener("change", compute);
      q2.removeEventListener("change", compute);
    };
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
      // Belt-and-suspenders: drop any cached raw-excerpt summary so the card
      // shows its neutral pending line instead of scraped garbage.
      summary: cleanFeedSummary(
        typeof s.summary === "string" ? s.summary : String(s.summary ?? ""),
        typeof s.title === "string" ? s.title : "",
      ),
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

        /* eslint-disable @typescript-eslint/no-explicit-any */
        // One feed query with tiered field fallback: enriched -> enriched-minus-
        // is_international (older schema) -> base. Returns the PostgREST result
        // plus which field set won so downstream mapping knows what's present.
        const runFeedQuery = async (): Promise<{ res: any; enriched: boolean }> => {
          let enriched = true;
          let r: any = await supabase!
            .from("story_clusters")
            .select(enrichedFields)
            .contains("sections", [activeEdition])
            .order(rankColumn, { ascending: false })
            .limit(FETCH_LIMIT);
          if (r.error) {
            r = await supabase!
              .from("story_clusters")
              .select(enrichedFields.replace(",is_international", ""))
              .contains("sections", [activeEdition])
              .order(rankColumn, { ascending: false })
              .limit(FETCH_LIMIT);
          }
          if (r.error) {
            enriched = false;
            r = await supabase!
              .from("story_clusters")
              .select(baseFields)
              .contains("sections", [activeEdition])
              .order("first_published", { ascending: false })
              .limit(FETCH_LIMIT);
          }
          return { res: r, enriched };
        };

        // F1: the sole homepage feed query intermittently 500s (PostgREST) and,
        // when it does, previously blanked the page with no signal. Retry with
        // exponential backoff (400ms, 900ms) on error OR empty before giving up,
        // so a transient failure or a mid-write empty read self-heals. A genuine
        // empty (pipeline mid-run) simply exhausts the retries and falls through
        // to the "warming up" state below; a persistent error surfaces the
        // distinct failed state (visible editorial line + Retry button).
        const sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));
        const BACKOFF_MS = [400, 900];
        let res: any = null;
        let usingEnriched = true;
        for (let attempt = 0; attempt < 3; attempt++) {
          const out = await runFeedQuery();
          if (controller.signal.aborted) return;
          res = out.res;
          usingEnriched = out.enriched;
          const rowCount = res.error ? 0 : (res.data?.length ?? 0);
          if (!res.error && rowCount > 0) break;
          if (attempt < BACKOFF_MS.length) {
            await sleep(BACKOFF_MS[attempt]);
            if (controller.signal.aborted) return;
          }
        }
        /* eslint-enable @typescript-eslint/no-explicit-any */

        // Persistent failure after all retries — surface a visible, on-brand
        // failed state rather than a blank feed. If cached stories are already
        // on screen (repeat visitor), keep them and fail silently in the
        // background instead of replacing content with an error.
        if (!res || res.error) {
          if (!hasCachedData) {
            setError("Today's edition is taking a moment to load.");
          }
          setIsLoading(false);
          return;
        }

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
            // Guard against a raw scraped excerpt slipping onto a card: if the
            // summary fails the hygiene check it is blanked, and the card falls
            // back to its neutral "N sources reporting" pending line.
            const safeSummary = cleanFeedSummary(
              typeof cluster.summary === "string" ? cluster.summary : String(cluster.summary ?? ""),
              safeTitle,
            );

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

  // Deep link: ?story=<id> opens that story's inline deep dive once the feed
  // has loaded. Used by void --revolt to jump into a story's popout. No-ops
  // silently if the story isn't in the loaded feed.
  useEffect(() => {
    if (deepLinkHandled.current || typeof window === "undefined") return;
    if (filteredStories.length === 0) return;
    const id = new URL(window.location.href).searchParams.get("story");
    if (!id) { deepLinkHandled.current = true; return; }
    const story = filteredStories.find((s) => s.id === id);
    deepLinkHandled.current = true;
    if (!story) return;
    handleStoryClick(story, new DOMRect());
    requestAnimationFrame(() => {
      document.querySelector(`[data-story-id="${id}"]`)?.scrollIntoView({ block: "start" });
    });
    const url = new URL(window.location.href);
    url.searchParams.delete("story");
    window.history.replaceState({}, "", url.toString());
  }, [filteredStories, handleStoryClick]);

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

  // 2026-06-02 single-feed — the /world overflow split is gone; the homepage
  // now shows a single 50-story flow. The legacy world-overflow scaffolding
  // (WORLD_OVERFLOW_SIZE / worldOverflow / mainIds) was removed 2026-08-08.

  // v3 (2026-05-14): twin top stories — ranks 0 and 1 share the hero canvas
  // as co-equal "Top Story" leads. Grid below holds ranks 2..N where N is
  // the visible-window size (30 or 50).
  const twinLeads = mainStories.slice(0, 2);
  const gridStories = mainStories.slice(2);

  // F15: in the collapsed default view, avoid a single-card orphan on the last
  // grid row (which leaves 2 empty cells + a lopsided seam at 1024/3-col). When
  // the grid would end with exactly one card alone for the active column count,
  // hold that one card back until the reader expands the feed. Only a lone
  // orphan (remainder of 1) is trimmed; a 2-card tail reads as balanced and is
  // left intact. Never trims when expanded or on mobile (single column). This is
  // a prefix slice, so each card keeps its true index (rank = idx + 2).
  const displayGridStories = useMemo(() => {
    if (feedExpanded || isMobile || gridColumns < 2) return gridStories;
    if (gridStories.length % gridColumns === 1) return gridStories.slice(0, -1);
    return gridStories;
  }, [gridStories, feedExpanded, isMobile, gridColumns]);
  const orphanHeldBack = gridStories.length - displayGridStories.length;

  // Deep Dive is now presented as an overlay (DeepDiveOverlay) rendered once,
  // outside the feed, on both breakpoints. The feed no longer splits around an
  // open story, so the former inline-split bookkeeping was removed 2026-08-09.

  // Lead hero image removed 2026-05-13 — text-only newspaper composition.

  // Continuous-scroll set: the single 50-story feed. Keyboard nav (J/K) and
  // Deep Dive prev/next traverse this order; Search also operates on this set.
  const visibleStories = useMemo(
    () => [...mainStories],
    [mainStories],
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
        editionBuiltAt={lastUpdated}
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
        {/* Masthead tagline moved into the NavBar (2026-08-02). The former
            full-width ".home-flag" strip was removed so the feed starts higher
            on both mobile and desktop; "See through the void." now renders as
            an inline italic subline beside the wordmark in the top bar. */}

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
            {/* Live region for screen readers — announces the story count. */}
            <div aria-live="polite" className="sr-only">
              {!isLoading && mainStories.length > 0 &&
                `${mainStories.length} stories loaded. Press ? for keyboard shortcuts.`}
            </div>

            {/* Loading skeleton */}
            {isLoading && <LoadingSkeleton />}

            {/* Failed state (F1) — distinct from "genuinely empty" below. Shows
                only after the feed query exhausts its retries with a persistent
                error and no cached edition is on screen. On-brand editorial line
                plus a Retry that re-runs the fetch via retryKey. No blank page. */}
            {error && !isLoading && (
              <div className="empty-state" role="alert">
                <LogoIcon size={56} animation="idle" />
                <h2 className="text-xl" style={{ color: "var(--fg-primary)", marginBottom: "var(--space-3)" }}>
                  {error}
                </h2>
                <p className="text-base" style={{ color: "var(--fg-tertiary)", lineHeight: 1.6, marginBottom: "var(--space-4)" }}>
                  The wire hiccuped on its way to the page. One more try usually sets it right.
                </p>
                <button
                  className="btn-primary"
                  onClick={() => setRetryKey((k) => k + 1)}
                >
                  Retry
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
                  One edition a day. The next one is on its way.
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
                    /* Deep Dive is a global overlay now, not an inline split, so
                       the mobile feed never renders an inline block. */
                    selectedStory={null}
                    onInlineCollapse={handleInlineCollapse}
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

                  {/* Boundary line — marks where "about the day" (the brief) ends
                      and "the day" (the story feed) begins. */}
                  <div className="feed-start" aria-hidden="true">Today&rsquo;s Top Stories</div>

                  {/* Twin top stories — ranks 0 and 1, co-equal "Top Story"
                      leads side-by-side in a 50/50 split (vertical stack on
                      <1024px). Both wear the badge. v3 2026-05-14. Opening a
                      Deep Dive no longer reflows the feed — the grid stays put
                      under the overlay. */}
                  {twinLeads.length > 0 && (
                    <div key={filterKey} className="lead-twin hero-slot">
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
                  )}

                  {/* Grid below twin leads — ranks 2-49 (digest at 2-9, wire
                      at 10-49). Slot math: 8 digest + 40 wire = 48 grid cards,
                      plus 2 twin leads above = 50 total. */}
                  {gridStories.length > 0 && (
                    <section key={`grid-${filterKey}`} aria-label="Stories" className="feed-grid">
                      {displayGridStories.map((story, idx) => renderGridCard(story, idx))}
                    </section>
                  )}

                  {/* Expand-to-50 affordance — sits between the default
                      30-story window and the World section. Reader-controlled
                      disclosure of the remaining curated stories before the
                      international overflow. Hidden when already expanded
                      or when there's nothing more to reveal. */}
                  {!feedExpanded && (hiddenMainCount + orphanHeldBack) > 0 && (
                    <div className="feed-expand">
                      <button
                        type="button"
                        className="feed-expand__btn"
                        onClick={() => {
                          hapticLight();
                          setFeedExpanded(true);
                        }}
                        aria-label={`Show ${hiddenMainCount + orphanHeldBack} more stories`}
                      >
                        Show {hiddenMainCount + orphanHeldBack} more
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

      {/* Deep Dive — a focused overlay on both breakpoints: a centered card
           over a dimmed backdrop on desktop, a full-screen bottom sheet on
           mobile. Rendered once here (portaled to <body> by DeepDiveOverlay),
           outside the feed, so the grid never reflows underneath it. */}
      {selectedStory && (
        <DeepDiveOverlay
          key={selectedStory.id}
          story={selectedStory}
          onClose={handleInlineCollapse}
        />
      )}

      {/* Search overlay — Cmd+K. Search across main feed + World overflow. */}
      <SearchOverlay
        stories={visibleStories}
        onStorySelect={handleSearchSelect}
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
      />

      {/* Unified onboarding — DISABLED (2026-08-04). The auto-launching tour was
          distracting and the /about experience now covers the same ground. The
          UnifiedOnboarding component + onboarding.css are kept intact so it can
          be re-enabled later; here it is hard-gated to never auto-activate.
          Re-enable by restoring: active={!isLoading && stories.length > 0} */}
      <UnifiedOnboarding active={false} />

      {/* Keyboard shortcuts overlay — press ? to toggle */}
      <KeyboardShortcutsOverlay />

      {/* PWA install prompt — 2nd+ visit, above bottom nav */}
      <InstallPrompt />

      {/* FloatingPlayer moved to MobileNav (layout-level) so it is global across
          routes. dailyBriefState is still consumed above (SkyboxBanner etc.). */}
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
