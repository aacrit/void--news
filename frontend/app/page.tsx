"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import type { Section, Category, Story, BiasScores, BiasSpread } from "./lib/types";
import { supabase } from "./lib/supabase";
import NavBar from "./components/NavBar";
import FilterBar from "./components/FilterBar";
import LeadStory from "./components/LeadStory";
import StoryCard from "./components/StoryCard";
import DeepDive from "./components/DeepDive";
import RefreshButton from "./components/RefreshButton";
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
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);

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
        const selectFields = `id,title,summary,category,section,importance_score,source_count,first_published,last_updated,divergence_score,headline_rank,coverage_velocity,bias_diversity`;

        const [worldRes, usRes] = await Promise.all([
          supabase
            .from("story_clusters")
            .select(selectFields)
            .eq("section", "world")
            .order("headline_rank", { ascending: false })
            .limit(100),
          supabase
            .from("story_clusters")
            .select(selectFields)
            .eq("section", "us")
            .order("headline_rank", { ascending: false })
            .limit(100),
        ]);

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

        // Read bias data directly from pre-computed bias_diversity JSONB column.
        // This eliminates an expensive cluster_bias_summary view query with
        // a large IN() clause on every page load. The view is retained for
        // Deep Dive and pipeline use only.
        const liveStories: Story[] = clusters.map(
          (cluster: {
            id: string;
            title: string;
            summary: string | null;
            category: string | null;
            section: string | null;
            importance_score: number | null;
            source_count: number | null;
            first_published: string | null;
            last_updated: string | null;
            divergence_score: number | null;
            headline_rank: number | null;
            coverage_velocity: number | null;
            bias_diversity: Record<string, number> | null;
          }) => {
            const bd = cluster.bias_diversity;

            const biasScores: BiasScores = bd && bd.avg_political_lean != null
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

            return {
              id: cluster.id,
              title: cluster.title,
              summary: cluster.summary || "",
              source: {
                name: "Multiple Sources",
                count: cluster.source_count || 1,
              },
              category: capitalize(cluster.category || "politics") as Category,
              publishedAt:
                cluster.first_published ||
                cluster.last_updated ||
                new Date().toISOString(),
              biasScores,
              biasSpread,
              section: (cluster.section || "world") as Section,
              importance: cluster.headline_rank || cluster.importance_score || 50,
              divergenceScore: cluster.divergence_score || 0,
              headlineRank: cluster.headline_rank || cluster.importance_score || 50,
              coverageVelocity: cluster.coverage_velocity || 0,
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
    if (activeCategory !== "All") {
      filtered = filtered.filter((s) => s.category === activeCategory);
    }
    return filtered.sort((a, b) => b.headlineRank - a.headlineRank);
  }, [stories, activeSection, activeCategory]);

  const leadStory = filteredStories[0];
  const mediumStories = filteredStories.slice(1, 4);
  const compactStories = filteredStories.slice(4);

  return (
    <div className="page-container">
      <NavBar
        activeSection={activeSection}
        onSectionChange={(s) => {
          setActiveSection(s);
          setActiveCategory("All");
        }}
      />

      <main id="main-content" className="page-main">
        {/* Section title — newspaper tradition */}
        <div className="section-header">
          <h1 className="section-header__title">
            {activeSection === "world" ? "World News" : "US News"}
          </h1>
          <div className="section-header__actions">
            <RefreshButton externalLastUpdated={lastUpdated} />
          </div>
        </div>

        {/* Filter bar */}
        <FilterBar
          activeCategory={activeCategory}
          onCategoryChange={setActiveCategory}
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
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none" className="empty-icon" aria-hidden="true">
              <rect x="8" y="12" width="48" height="40" rx="1" stroke="currentColor" strokeWidth="1.5" />
              <line x1="16" y1="22" x2="48" y2="22" stroke="currentColor" strokeWidth="1.5" />
              <line x1="16" y1="30" x2="40" y2="30" stroke="currentColor" strokeWidth="1" opacity="0.5" />
              <line x1="16" y1="36" x2="44" y2="36" stroke="currentColor" strokeWidth="1" opacity="0.5" />
              <line x1="16" y1="42" x2="36" y2="42" stroke="currentColor" strokeWidth="1" opacity="0.5" />
            </svg>
            <h2 className="text-xl" style={{ color: "var(--fg-primary)", marginBottom: "var(--space-3)" }}>
              Awaiting First Edition
            </h2>
            <p className="text-base" style={{ color: "var(--fg-tertiary)", lineHeight: 1.6, marginBottom: "var(--space-4)" }}>
              The news pipeline hasn&apos;t run yet. Stories will appear here
              once articles are fetched and analyzed from 90 curated sources.
            </p>
            <p className="edition-meta">
              Scheduled: 6:00 AM &amp; 6:00 PM UTC daily
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
              No stories in this category.
            </p>
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
          </div>
        )}

        {/* Lead story */}
        {!isLoading && leadStory && (
          <section aria-label="Lead story">
            <LeadStory story={leadStory} onStoryClick={handleStoryClick} />
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

        {/* Compact stories — dense grid on desktop */}
        {!isLoading && compactStories.length > 0 && (
          <section aria-label="More stories" className="grid-compact">
            {compactStories.map((story, idx) => (
              <div key={story.id} className="grid-compact__item">
                <StoryCard
                  story={story}
                  index={idx + mediumStories.length + 1}
                  onStoryClick={handleStoryClick}
                />
              </div>
            ))}
          </section>
        )}

        {/* Edition line — newspaper tradition */}
        {!isLoading && filteredStories.length > 0 && (
          <div className="edition-line">
            <span className="edition-meta">
              {activeSection === "world" ? "World" : "US"} Edition /{" "}
              {filteredStories.length} stories
            </span>
            <span className="brand-name">void --news</span>
          </div>
        )}
      </main>

      {/* Footer */}
      {!isLoading && <Footer />}

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
