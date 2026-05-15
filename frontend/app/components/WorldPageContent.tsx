"use client";

import { useEffect, useMemo, useState, useCallback, Component, type ReactNode } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import type { Story, BiasScores, BiasSpread, ThreeLensData, OpinionLabel, SigilData, Edition, Category } from "../lib/types";
import { isUnscoredTilt } from "../lib/biasColors";
import { supabase, supabaseError } from "../lib/supabase";
import NavBar from "./NavBar";
import StoryCard from "./StoryCard";
import LoadingSkeleton from "./LoadingSkeleton";
import Footer from "./Footer";
import LogoWordmark from "./LogoWordmark";
import LogoIcon from "./LogoIcon";
import WorldDivider from "./WorldDivider";
import ErrorBoundary from "./ErrorBoundary";
const DeepDive = dynamic(() => import("./DeepDive"), { ssr: false });
const SearchOverlay = dynamic(() => import("./SearchOverlay"), { ssr: false });

/* ---------------------------------------------------------------------------
   WorldPageContent — client component for /world.

   Fetches the same ~100 clusters as HomeContent, applies the ≥3-source quality
   floor, then renders ONLY the World overflow (international stories ranked
   beyond the homepage's top 50). No lead, no brief, no skybox — just the
   divider + a wire grid + the standard nav/footer chrome.

   Defensive: when is_international column is missing (older schemas), the
   overflow is empty and the page shows a graceful empty state.
   --------------------------------------------------------------------------- */

const EDITION_FEED_SIZE = 50;
const WORLD_OVERFLOW_SIZE = 30;
const FETCH_LIMIT = 100;

class WorldDeepDiveErrorBoundary extends Component<
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
            <p className="text-base empty-state__body">Unable to load analysis for this story.</p>
            <button className="btn-primary" onClick={this.props.onClose}>Close</button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

function capitalize(s: string): string {
  if (!s) return s;
  const map: Record<string, string> = {
    politics: "Politics", conflict: "Conflict", economy: "Economy",
    science: "Science", health: "Health", environment: "Environment",
    culture: "Culture",
    tech: "Science", technology: "Science", sports: "Culture",
  };
  return map[s.toLowerCase()] || s.charAt(0).toUpperCase() + s.slice(1);
}

function parseBiasDiversity(raw: unknown): Record<string, unknown> | null {
  if (raw == null) return null;
  if (typeof raw !== "object" || Array.isArray(raw)) return null;
  return raw as Record<string, unknown>;
}

function safeNum(bd: Record<string, unknown>, key: string, fallback: number): number {
  const v = bd[key];
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  return fallback;
}

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

function WorldPageContentInner() {
  const [stories, setStories] = useState<Story[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);
  const [originRect, setOriginRect] = useState<DOMRect | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setIsLoading(true);
      setError(null);

      if (!supabase) {
        setError(supabaseError ?? "Unable to connect to data source.");
        setIsLoading(false);
        return;
      }

      try {
        const enrichedFields = `id,title,summary,category,section,sections,importance_score,source_count,first_published,last_updated,divergence_score,headline_rank,coverage_velocity,bias_diversity,consensus_points,divergence_points,rank_world,rank_us,rank_europe,rank_south_asia,claim_consensus,cached_image_url,is_international`;
        const fallbackFields = enrichedFields.replace(",is_international", "");

        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        let res: any = await supabase
          .from("story_clusters")
          .select(enrichedFields)
          .contains("sections", ["world"])
          .order("rank_world", { ascending: false })
          .limit(FETCH_LIMIT);

        // Fall back if is_international column doesn't exist yet
        if (res.error) {
          res = await supabase
            .from("story_clusters")
            .select(fallbackFields)
            .contains("sections", ["world"])
            .order("rank_world", { ascending: false })
            .limit(FETCH_LIMIT);
        }

        if (controller.signal.aborted) return;

        const clusters = res.data || [];

        /* eslint-disable @typescript-eslint/no-explicit-any */
        const mappedStories: Story[] = clusters.map((cluster: any) => {
          const bd = parseBiasDiversity(cluster.bias_diversity);
          const hasBiasData = !!(bd && bd["avg_political_lean"] != null);

          const biasScores: BiasScores = hasBiasData
            ? {
                politicalLean: safeNum(bd!, "avg_political_lean", 50),
                sensationalism: safeNum(bd!, "avg_sensationalism", 30),
                opinionFact: safeNum(bd!, "avg_opinion_fact", 25),
                factualRigor: safeNum(bd!, "avg_factual_rigor", 75),
                framing: safeNum(bd!, "avg_framing", 40),
              }
            : { politicalLean: 50, sensationalism: 30, opinionFact: 25, factualRigor: 75, framing: 40 };

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

          const sourceCount = cluster.source_count ?? 0;
          const opinionLabel = (bd?.["avg_opinion_label"] as OpinionLabel) ?? deriveOpinionLabel(biasScores.opinionFact);
          const lensData: ThreeLensData = {
            lean: biasScores.politicalLean,
            coverage: bd
              ? safeNum(bd, "coverage_score", deriveCoverageScore(sourceCount, biasScores.factualRigor, biasSpread?.aggregateConfidence ?? 0.5))
              : deriveCoverageScore(sourceCount, biasScores.factualRigor, 0.5),
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

          const safeTitle = typeof cluster.title === "string" ? cluster.title : String(cluster.title ?? "");
          const safeSummary = typeof cluster.summary === "string" ? cluster.summary : String(cluster.summary ?? "");

          return {
            id: cluster.id,
            title: safeTitle,
            summary: safeSummary,
            source: { name: "Multiple Sources", count: sourceCount },
            category: capitalize(typeof cluster.category === "string" ? cluster.category : "politics") as Category,
            publishedAt: cluster.first_published || cluster.last_updated || new Date().toISOString(),
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
            cachedImageUrl: cluster.cached_image_url ?? null,
            is_international: Boolean(cluster.is_international),
          } as unknown as Story;
        });
        /* eslint-enable @typescript-eslint/no-explicit-any */

        setStories(mappedStories);
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

    load();
    return () => controller.abort();
  }, [retryKey]);

  // Same slicing logic as HomeContent: ≥3-source floor, top-50 main set, then
  // overflow = international stories not in main, capped at 30.
  const filteredStories = useMemo(
    () => stories.filter((s) => (s.sigilData?.sourceCount ?? s.source?.count ?? 0) >= 3),
    [stories],
  );
  const mainIds = useMemo(
    () => new Set(filteredStories.slice(0, EDITION_FEED_SIZE).map((s) => s.id)),
    [filteredStories],
  );
  const worldOverflow = useMemo(
    () =>
      filteredStories
        .filter((s) => !mainIds.has(s.id) && Boolean((s as Story & { is_international?: boolean }).is_international))
        .slice(0, WORLD_OVERFLOW_SIZE),
    [filteredStories, mainIds],
  );

  const handleStoryClick = useCallback((story: Story, rect: DOMRect) => {
    setOriginRect(rect.width > 0 ? rect : null);
    setSelectedStory(story);
  }, []);

  const handleDeepDiveClose = useCallback(() => {
    setSelectedStory(null);
    setOriginRect(null);
  }, []);

  const handleSearchSelect = useCallback((story: Story) => {
    setSearchOpen(false);
    handleStoryClick(story, new DOMRect());
  }, [handleStoryClick]);

  const handleDeepDiveNav = useCallback((direction: "prev" | "next") => {
    if (!selectedStory) return;
    const idx = worldOverflow.findIndex((s) => s.id === selectedStory.id);
    if (idx < 0) return;
    const newIdx = direction === "prev" ? idx - 1 : idx + 1;
    if (newIdx >= 0 && newIdx < worldOverflow.length) {
      setSelectedStory(worldOverflow[newIdx]);
    }
  }, [selectedStory, worldOverflow]);

  return (
    <div className="page-container">
      <NavBar
        activeEdition="world"
        onSearchClick={() => setSearchOpen(true)}
      />

      <main id="main-content" className="page-main">
        <div aria-live="polite" className="sr-only">
          {!isLoading && worldOverflow.length > 0 &&
            `${worldOverflow.length} international stories loaded.`}
        </div>

        {isLoading && <LoadingSkeleton />}

        {error && !isLoading && (
          <div className="empty-state">
            <h2 className="text-xl" style={{ color: "var(--fg-primary)", marginBottom: "var(--space-3)" }}>
              Unable to load stories
            </h2>
            <p className="text-base" style={{ color: "var(--fg-tertiary)", marginBottom: "var(--space-4)" }}>
              {error}
            </p>
            <button className="btn-primary" onClick={() => setRetryKey((k) => k + 1)}>
              Try again
            </button>
          </div>
        )}

        {!isLoading && !error && stories.length === 0 && (
          <div className="empty-state">
            <LogoIcon size={56} animation="analyzing" />
            <h2 className="text-xl" style={{ color: "var(--fg-primary)", marginBottom: "var(--space-3)" }}>
              The Presses Are Warming Up
            </h2>
            <p className="text-base" style={{ color: "var(--fg-tertiary)", lineHeight: 1.6 }}>
              No stories yet. The pipeline is still collecting and analyzing sources.
            </p>
          </div>
        )}

        {!isLoading && !error && stories.length > 0 && worldOverflow.length === 0 && (
          <div className="empty-state">
            <h2 className="text-xl" style={{ color: "var(--fg-primary)", marginBottom: "var(--space-3)" }}>
              No World overflow today
            </h2>
            <p className="text-base" style={{ color: "var(--fg-tertiary)", lineHeight: 1.6, marginBottom: "var(--space-4)" }}>
              Every international story made the homepage cut. Check back after the next pipeline run.
            </p>
            <Link className="btn-primary" href="/">Back to homepage</Link>
          </div>
        )}

        {!isLoading && worldOverflow.length > 0 && (
          <section aria-label="World — international stories" className="world-section world-section--standalone">
            <WorldDivider count={worldOverflow.length} />
            <div className="feed-grid world-section__grid">
              {worldOverflow.map((story, idx) => (
                <div key={story.id} className="feed-grid__item">
                  <StoryCard
                    story={story}
                    index={idx}
                    onStoryClick={handleStoryClick}
                    globalIndex={idx}
                    variant="wire"
                  />
                </div>
              ))}
            </div>

            <div className="edition-line">
              <span className="edition-meta">
                {worldOverflow.length} international stories
              </span>
              <LogoWordmark height={14} />
            </div>
          </section>
        )}
      </main>

      {!isLoading && <Footer lastUpdated={lastUpdated} />}

      {selectedStory && (
        <WorldDeepDiveErrorBoundary onClose={handleDeepDiveClose}>
          <DeepDive
            story={selectedStory}
            onClose={handleDeepDiveClose}
            originRect={originRect}
            onNavigate={handleDeepDiveNav}
            storyIndex={worldOverflow.findIndex((s) => s.id === selectedStory.id)}
            totalStories={worldOverflow.length}
          />
        </WorldDeepDiveErrorBoundary>
      )}

      <SearchOverlay
        stories={worldOverflow}
        onStorySelect={handleSearchSelect}
        isOpen={searchOpen}
        onClose={() => setSearchOpen(false)}
      />
    </div>
  );
}

export default function WorldPageContent() {
  return (
    <ErrorBoundary>
      <WorldPageContentInner />
    </ErrorBoundary>
  );
}
