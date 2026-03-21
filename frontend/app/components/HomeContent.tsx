"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import type { Edition, Category, Story, BiasScores, BiasSpread, ThreeLensData, OpinionLabel, SigilData } from "../lib/types";
import { EDITIONS } from "../lib/types";
import { supabase } from "../lib/supabase";
import LogoWordmark from "./LogoWordmark";
import LogoIcon from "./LogoIcon";
import NavBar, { type ViewMode } from "./NavBar";
import FilterBar from "./FilterBar";
import LeanFilter, { type LeanRange } from "./LeanFilter";
import LeadStory from "./LeadStory";
import StoryCard from "./StoryCard";
import DeepDive from "./DeepDive";
import OpEdPage from "./OpEdPage";
import ErrorBoundary from "./ErrorBoundary";

import LoadingSkeleton from "./LoadingSkeleton";
import Footer from "./Footer";

function capitalize(s: string): string {
  if (!s) return s;
  const map: Record<string, string> = {
    politics: "Politics", economy: "Economy", tech: "Tech", technology: "Tech",
    health: "Health", environment: "Environment", conflict: "Conflict",
    science: "Science", culture: "Culture", sports: "Sports",
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
  const [activeCategory, setActiveCategory] = useState<"All" | Category>("All");
  const [viewMode, setViewMode] = useState<ViewMode>("facts");
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);
  const [showAllCompact, setShowAllCompact] = useState(false);
  const [leanRange, setLeanRange] = useState<LeanRange | null>(null);

  const handleStoryClick = useCallback((story: Story) => {
    setSelectedStory(story);
  }, []);

  const handleDeepDiveClose = useCallback(() => {
    setSelectedStory(null);
  }, []);

  // Reset category filter and scroll to top when edition changes.
  // Lean filter is intentionally preserved — it's a universal preference
  // that persists until the user explicitly toggles it off.
  useEffect(() => {
    setActiveCategory("All");
    setShowAllCompact(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, [activeEdition]);

  useEffect(() => {
    const controller = new AbortController();

    async function loadFromSupabase() {
      setIsLoading(true);
      setError(null);

      try {
        const enrichedFields = `id,title,summary,category,section,sections,content_type,importance_score,source_count,first_published,last_updated,divergence_score,headline_rank,coverage_velocity,bias_diversity,consensus_points,divergence_points`;
        const baseFields = `id,title,summary,category,section,sections,importance_score,source_count,first_published,last_updated`;

        let res;
        let usingEnriched = true;

        // Fetch reporting + opinion separately so opinion pieces (fewer
        // sources, lower headline_rank) aren't crowded out of the top 100.
        const [reportingRes, opinionRes] = await Promise.all([
          supabase
            .from("story_clusters")
            .select(enrichedFields)
            .contains("sections", [activeEdition])
            .eq("content_type", "reporting")
            .order("headline_rank", { ascending: false })
            .limit(100),
          supabase
            .from("story_clusters")
            .select(enrichedFields)
            .contains("sections", [activeEdition])
            .eq("content_type", "opinion")
            .order("headline_rank", { ascending: false })
            .limit(50),
        ]);

        res = reportingRes;

        // If enriched query failed (columns don't exist), fall back to base schema
        if (res.error) {
          usingEnriched = false;
          res = await supabase
            .from("story_clusters")
            .select(baseFields)
            .contains("sections", [activeEdition])
            .order("first_published", { ascending: false })
            .limit(100);
        }

        if (controller.signal.aborted) return;

        // Merge reporting + opinion clusters
        const clusters = [
          ...(res.data || []),
          ...(!res.error && opinionRes.data ? opinionRes.data : []),
        ];

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

            const sourceCount = cluster.source_count || 1;
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
  }, [activeEdition]);

  const filteredStories = useMemo(() => {
    // In facts mode: show only reporting/facts clusters (opinionFact <= 50)
    // In opinion mode: OpEdPage handles its own data fetching — show nothing here
    let filtered = stories.filter((s) => s.biasScores.opinionFact <= 50);
    if (activeCategory !== "All") {
      filtered = filtered.filter((s) => s.category === activeCategory);
    }
    // Lean range filter — uses lensData.lean (cluster-level average political lean)
    if (leanRange !== null) {
      filtered = filtered.filter(
        (s) => s.lensData.lean >= leanRange.min && s.lensData.lean <= leanRange.max,
      );
    }
    return filtered.sort((a, b) => b.headlineRank - a.headlineRank);
  }, [stories, activeCategory, leanRange]);

  const leadStories = filteredStories.slice(0, 2);
  const mediumStories = filteredStories.slice(2, 5);
  const compactStories = filteredStories.slice(5);

  // Stable key that changes whenever the active filter changes.
  // Keying the <section> elements on this value causes React to unmount+remount
  // them, which replays the .anim-filter-card entrance animation on every filter
  // change — giving a "reshuffling" feel with no JS animation library.
  const filterKey = `${leanRange?.min ?? "x"}-${leanRange?.max ?? "x"}-${activeCategory}`;

  const editionMeta = EDITIONS.find((e) => e.slug === activeEdition) ?? EDITIONS[0];

  return (
    <div className="page-container">
      <NavBar
        activeEdition={activeEdition}
        viewMode={viewMode}
        onViewModeChange={(mode) => {
          setViewMode(mode);
          setActiveCategory("All");
          setShowAllCompact(false);
        }}
      />

      <main id="main-content" className="page-main">
        {/* Facts / Op-Ed toggle — mobile only (desktop lives in nav-tabs) */}
        <div className="view-mode-toggle--mobile" aria-hidden="false">
          <div
            className="view-mode-toggle"
            role="group"
            aria-label="Content type filter"
          >
            <button
              className={`view-mode-toggle__btn${viewMode === "facts" ? " view-mode-toggle__btn--active" : ""}`}
              onClick={() => { setViewMode("facts"); setActiveCategory("All"); setShowAllCompact(false); }}
              aria-pressed={viewMode === "facts"}
            >
              Facts
            </button>
            <button
              className={`view-mode-toggle__btn${viewMode === "opinion" ? " view-mode-toggle__btn--active" : ""}`}
              onClick={() => { setViewMode("opinion"); setActiveCategory("All"); setShowAllCompact(false); }}
              aria-pressed={viewMode === "opinion"}
            >
              Op-Ed
            </button>
          </div>
        </div>

        {/* Filter bar + Lean filter — ABOVE content in both modes */}
        <div className="filter-row">
          {viewMode === "facts" && (
            <FilterBar
              activeCategory={activeCategory}
              onCategoryChange={(cat) => { setActiveCategory(cat); setShowAllCompact(false); }}
            />
          )}
          <LeanFilter
            value={leanRange}
            onChange={(range) => { setLeanRange(range); setShowAllCompact(false); }}
          />
        </div>

        {/* Op-Ed page — renders its own data when in opinion mode */}
        {viewMode === "opinion" && (
          <OpEdPage edition={activeEdition} leanRange={leanRange} />
        )}

        {/* Facts mode — live region, loading, error, empty states, story grids */}
        {viewMode === "facts" && (
          <>
            {/* Live region for screen readers */}
            <div aria-live="polite" className="sr-only">
              {!isLoading && filteredStories.length > 0 &&
                `${filteredStories.length} stories loaded`}
              {!isLoading && stories.length > 0 && filteredStories.length === 0 &&
                leanRange !== null
                  ? "No stories match the current lean filter. Try widening the range."
                  : "No stories match the current filter"}
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
                  onClick={() => window.location.reload()}
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
                  {leanRange !== null
                    ? "No stories in this lean range."
                    : "No stories in this category."}
                </p>
                {leanRange !== null && (
                  <p className="lean-filter-empty__hint">
                    Try widening the range or clearing the filter.
                  </p>
                )}
                <div style={{ display: "flex", gap: "var(--space-4)", flexWrap: "wrap", justifyContent: "center" }}>
                  {leanRange !== null && (
                    <button
                      className="lean-filter-empty__action"
                      onClick={() => setLeanRange(null)}
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

            {/* Lead section — two primary headlines side by side on desktop */}
            {!isLoading && leadStories.length > 0 && (
              <section key={filterKey} aria-label="Lead stories" className="lead-section">
                {leadStories.map((story, i) => (
                  <div
                    key={story.id}
                    className="lead-section__col anim-filter-card"
                    style={{ animationDelay: `${i * 50}ms` }}
                  >
                    <LeadStory story={story} rank={i} onStoryClick={handleStoryClick} />
                  </div>
                ))}
              </section>
            )}

            {/* Medium stories — broadsheet grid on desktop */}
            {!isLoading && mediumStories.length > 0 && (
              <section key={`med-${filterKey}`} aria-label="Top stories" className="grid-medium">
                {mediumStories.map((story, idx) => (
                  <div
                    key={story.id}
                    className="grid-medium__item anim-filter-card"
                    style={{ animationDelay: `${idx * 50}ms` }}
                  >
                    <StoryCard story={story} index={idx + 1} onStoryClick={handleStoryClick} />
                  </div>
                ))}
              </section>
            )}

            {/* Compact stories — capped at 8 (2 desktop rows) with "More" */}
            {!isLoading && compactStories.length > 0 && (() => {
              const COMPACT_CAP = 8;
              const visible = showAllCompact ? compactStories : compactStories.slice(0, COMPACT_CAP);
              const hasMore = compactStories.length > COMPACT_CAP && !showAllCompact;
              return (
                <>
                  <section key={`cmp-${filterKey}`} aria-label="More stories" className="grid-compact">
                    {visible.map((story, idx) => (
                      <div
                        key={story.id}
                        className="grid-compact__item anim-filter-card"
                        style={{ animationDelay: `${idx * 50}ms` }}
                      >
                        <StoryCard
                          story={story}
                          index={idx + mediumStories.length + 1}
                          onStoryClick={handleStoryClick}
                        />
                      </div>
                    ))}
                  </section>
                  {hasMore && (
                    <div className="show-more">
                      <button
                        className="show-more__btn"
                        onClick={() => setShowAllCompact(true)}
                      >
                        More stories ({compactStories.length - COMPACT_CAP} remaining)
                      </button>
                    </div>
                  )}
                </>
              );
            })()}

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
        )}
      </main>

      {/* Footer */}
      {!isLoading && <Footer lastUpdated={lastUpdated} />}

      {/* Deep Dive panel */}
      {selectedStory && (
        <DeepDive story={selectedStory} onClose={handleDeepDiveClose} />
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
