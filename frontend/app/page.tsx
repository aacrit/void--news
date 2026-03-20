"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import type { Section, Category, Story, BiasScores, BiasSpread, ThreeLensData, OpinionLabel, SigilData } from "./lib/types";
import { supabase } from "./lib/supabase";
import LogoWordmark from "./components/LogoWordmark";
import LogoIcon from "./components/LogoIcon";
import NavBar, { type ViewMode } from "./components/NavBar";
import FilterBar from "./components/FilterBar";
import LeadStory from "./components/LeadStory";
import StoryCard from "./components/StoryCard";
import DeepDive from "./components/DeepDive";

import { timeAgo } from "./lib/utils";
import LoadingSkeleton from "./components/LoadingSkeleton";
import ErrorBoundary from "./components/ErrorBoundary";
import Footer from "./components/Footer";

function capitalize(s: string): string {
  if (!s) return s;
  const map: Record<string, string> = {
    politics: "Politics", economy: "Economy", tech: "Tech", technology: "Tech",
    health: "Health", environment: "Environment", conflict: "Conflict",
    science: "Science", culture: "Culture", sports: "Sports",
  };
  return map[s.toLowerCase()] || s.charAt(0).toUpperCase() + s.slice(1);
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
   Homepage — News Feed
   Desktop: broadsheet grid — lead story + asymmetric layout + dense compact
   Mobile: single-column tabloid stack
   --------------------------------------------------------------------------- */

function HomeContent() {
  const [stories, setStories] = useState<Story[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<Section>("world");
  const [activeCategory, setActiveCategory] = useState<"All" | Category>("All");
  const [viewMode, setViewMode] = useState<ViewMode>("facts");
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);
  const [showAllCompact, setShowAllCompact] = useState(false);

  const handleStoryClick = useCallback((story: Story) => {
    setSelectedStory(story);
  }, []);

  const handleDeepDiveClose = useCallback(() => {
    setSelectedStory(null);
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadFromSupabase() {
      try {
        // Query with enrichment columns first; fall back to base schema if
        // migrations 002/003 haven't been applied to the live database yet.
        const enrichedFields = `id,title,summary,category,section,content_type,importance_score,source_count,first_published,last_updated,divergence_score,headline_rank,coverage_velocity,bias_diversity,consensus_points,divergence_points`;
        const baseFields = `id,title,summary,category,section,importance_score,source_count,first_published,last_updated`;

        let worldRes, usRes;
        let usingEnriched = true;

        [worldRes, usRes] = await Promise.all([
          supabase
            .from("story_clusters")
            .select(enrichedFields)
            .eq("section", "world")
            .order("headline_rank", { ascending: false })
            .limit(100),
          supabase
            .from("story_clusters")
            .select(enrichedFields)
            .eq("section", "us")
            .order("headline_rank", { ascending: false })
            .limit(100),
        ]);

        // If enriched query failed (columns don't exist), fall back to base schema
        if (worldRes.error || usRes.error) {
          usingEnriched = false;
          [worldRes, usRes] = await Promise.all([
            supabase
              .from("story_clusters")
              .select(baseFields)
              .eq("section", "world")
              .order("first_published", { ascending: false })
              .limit(100),
            supabase
              .from("story_clusters")
              .select(baseFields)
              .eq("section", "us")
              .order("first_published", { ascending: false })
              .limit(100),
          ]);
        }

        if (controller.signal.aborted) return;

        const clusters = [
          ...(worldRes.data || []),
          ...(usRes.data || []),
        ];

        if (clusters.length === 0) {
          setIsLoading(false);
          return;
        }

        if (controller.signal.aborted) return;

        // Read bias data from pre-computed bias_diversity JSONB when available.
        // Falls back gracefully when enrichment columns don't exist yet.
        /* eslint-disable @typescript-eslint/no-explicit-any */
        const liveStories: Story[] = clusters.map(
          (cluster: any) => {
            const bd = usingEnriched ? cluster.bias_diversity : null;
            const hasBiasData = !!(bd && bd.avg_political_lean != null);

            const biasScores: BiasScores = hasBiasData
              ? {
                  politicalLean: bd.avg_political_lean ?? 50,
                  sensationalism: bd.avg_sensationalism ?? 30,
                  opinionFact: bd.avg_opinion_fact ?? 25,
                  factualRigor: bd.avg_factual_rigor ?? 75,
                  framing: bd.avg_framing ?? 40,
                }
              : {
                  politicalLean: 50,
                  sensationalism: 30,
                  opinionFact: 25,
                  factualRigor: 75,
                  framing: 40,
                };

            const biasSpread: BiasSpread | undefined = bd && bd.lean_spread != null
              ? {
                  leanSpread: bd.lean_spread ?? 0,
                  framingSpread: bd.framing_spread ?? 0,
                  leanRange: bd.lean_range ?? 0,
                  sensationalismSpread: bd.sensationalism_spread ?? 0,
                  opinionSpread: bd.opinion_spread ?? 0,
                  aggregateConfidence: bd.aggregate_confidence ?? 0,
                  analyzedCount: bd.analyzed_count ?? 0,
                }
              : undefined;

            const sourceCount = cluster.source_count || 1;
            const opinionLabel = (bd?.avg_opinion_label as OpinionLabel) ?? deriveOpinionLabel(biasScores.opinionFact);
            const lensData: ThreeLensData = {
              lean: biasScores.politicalLean,
              coverage: bd?.coverage_score ?? deriveCoverageScore(
                sourceCount, biasScores.factualRigor, biasSpread?.aggregateConfidence ?? 0.5,
              ),
              sourceCount,
              tierBreakdown: bd?.tier_breakdown,
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
              tierBreakdown: bd?.tier_breakdown,
              biasSpread,
              pending: !hasBiasData,
              opinionLabel,
            };

            // Parse consensus/divergence from JSONB columns
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
              section: (cluster.section || "world") as Section,
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
  }, []);

  const filteredStories = useMemo(() => {
    let filtered = stories.filter((s) => s.section === activeSection);
    // Facts/Opinion split: facts = opinionFact ≤ 50, opinion = opinionFact > 50
    if (viewMode === "facts") {
      filtered = filtered.filter((s) => s.biasScores.opinionFact <= 50);
    } else {
      filtered = filtered.filter((s) => s.biasScores.opinionFact > 50);
    }
    if (activeCategory !== "All") {
      filtered = filtered.filter((s) => s.category === activeCategory);
    }
    return filtered.sort((a, b) => b.headlineRank - a.headlineRank);
  }, [stories, activeSection, activeCategory, viewMode]);

  const leadStories = filteredStories.slice(0, 2);
  const mediumStories = filteredStories.slice(2, 5);
  const compactStories = filteredStories.slice(5);

  return (
    <div className="page-container">
      <NavBar
        activeSection={activeSection}
        onSectionChange={(s) => {
          setActiveSection(s);
          setActiveCategory("All");
          setShowAllCompact(false);
        }}
        viewMode={viewMode}
        onViewModeChange={(mode) => {
          setViewMode(mode);
          setActiveCategory("All");
          setShowAllCompact(false);
        }}
      />

      <main id="main-content" className="page-main">
        {/* Filter bar */}
        <FilterBar
          activeCategory={activeCategory}
          onCategoryChange={(cat) => { setActiveCategory(cat); setShowAllCompact(false); }}
        />

        {/* Live region for screen readers */}
        <div aria-live="polite" className="sr-only">
          {!isLoading && filteredStories.length > 0 &&
            `${filteredStories.length} stories loaded`}
          {!isLoading && stories.length > 0 && filteredStories.length === 0 &&
            "No stories match the current filter"}
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
              The printing press is rolling &mdash; 200 curated sources are being
              fetched, analyzed, and typeset. The {new Date().getUTCHours() < 17 ? "morning" : "evening"} edition will appear shortly.
            </p>
            <p className="edition-meta">
              Morning edition: 11:00 AM UTC &middot; Evening edition: 11:00 PM UTC
            </p>
          </div>
        )}

        {/* No stories in selected filter */}
        {!isLoading && !error && stories.length > 0 && filteredStories.length === 0 && (
          <div className="empty-state--inline">
            <p style={{
              fontFamily: "var(--font-structural)",
              fontSize: "var(--text-lg)",
              color: "var(--fg-tertiary)",
            }}>
              {viewMode === "opinion"
                ? "No opinion pieces in this edition."
                : "No stories in this category."}
            </p>
            {activeCategory !== "All" ? (
              <button
                onClick={() => setActiveCategory("All")}
                style={{
                  fontFamily: "var(--font-structural)",
                  fontSize: "var(--text-sm)",
                  color: "var(--fg-secondary)",
                  marginTop: "var(--space-3)",
                  textDecoration: "underline",
                  textUnderlineOffset: "3px",
                }}
              >
                View all stories
              </button>
            ) : viewMode === "opinion" ? (
              <button
                onClick={() => setViewMode("facts")}
                style={{
                  fontFamily: "var(--font-structural)",
                  fontSize: "var(--text-sm)",
                  color: "var(--fg-secondary)",
                  marginTop: "var(--space-3)",
                  textDecoration: "underline",
                  textUnderlineOffset: "3px",
                }}
              >
                Switch to Facts
              </button>
            ) : null}
          </div>
        )}

        {/* Lead section — two primary headlines side by side on desktop */}
        {!isLoading && leadStories.length > 0 && (
          <section aria-label="Lead stories" className="lead-section">
            {leadStories.map((story) => (
              <div key={story.id} className="lead-section__col">
                <LeadStory story={story} onStoryClick={handleStoryClick} />
              </div>
            ))}
          </section>
        )}

        {/* Medium stories — broadsheet grid on desktop */}
        {!isLoading && mediumStories.length > 0 && (
          <section aria-label="Top stories" className="grid-medium">
            {mediumStories.map((story, idx) => (
              <div key={story.id} className="grid-medium__item">
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
              <section aria-label="More stories" className="grid-compact">
                {visible.map((story, idx) => (
                  <div key={story.id} className="grid-compact__item">
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
              {activeSection === "world" ? "World" : "US"} Edition /{" "}
              {filteredStories.length} stories
            </span>
            <LogoWordmark height={14} />
          </div>
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

export default function Home() {
  return (
    <ErrorBoundary>
      <HomeContent />
    </ErrorBoundary>
  );
}
