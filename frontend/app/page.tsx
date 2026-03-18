"use client";

import { useState, useEffect, useMemo, useCallback } from "react";
import type { Section, Category, Story } from "./lib/types";
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

/* ---------------------------------------------------------------------------
   Homepage — News Feed
   Desktop: broadsheet grid — lead story + asymmetric layout + dense compact
   Mobile: single-column tabloid stack
   Fetches live data from Supabase. Shows loading skeleton, then content.
   Wrapped in ErrorBoundary for graceful error handling.
   --------------------------------------------------------------------------- */

function HomeContent() {
  const [stories, setStories] = useState<Story[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<Section>("world");
  const [activeCategory, setActiveCategory] = useState<"All" | Category>(
    "All"
  );
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);

  const handleStoryClick = useCallback((story: Story) => {
    setSelectedStory(story);
  }, []);

  const handleDeepDiveClose = useCallback(() => {
    setSelectedStory(null);
  }, []);

  useEffect(() => {
    async function loadFromSupabase() {
      try {
        const { data: clusters, error } = await supabase
          .from("story_clusters")
          .select(
            `
            id,
            title,
            summary,
            category,
            section,
            importance_score,
            source_count,
            first_published,
            last_updated
          `
          )
          .order("importance_score", { ascending: false })
          .limit(30);

        if (error || !clusters || clusters.length === 0) {
          setIsLoading(false);
          return;
        }

        // Transform clusters into Story format for the components
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
          }) => ({
            id: cluster.id,
            title: cluster.title,
            summary: cluster.summary || "",
            source: {
              name: "Multiple Sources",
              count: cluster.source_count || 1,
            },
            category: (cluster.category || "Politics") as Category,
            publishedAt:
              cluster.first_published ||
              cluster.last_updated ||
              new Date().toISOString(),
            // TODO(m-6): Bias scores are hardcoded placeholders. To show real
            // data, join cluster_articles + bias_scores in the Supabase query
            // and compute per-cluster averages. Deferred to avoid N+1 queries
            // on page load — consider a database view or RPC for this.
            biasScores: {
              politicalLean: 50,
              sensationalism: 30,
              opinionFact: 25,
              factualRigor: 75,
              framing: 40,
            },
            section: (cluster.section || "world") as Section,
            importance: cluster.importance_score || 50,
          })
        );

        setStories(liveStories);
        setIsLoading(false);

        // Get last pipeline run time
        const { data: run } = await supabase
          .from("pipeline_runs")
          .select("completed_at")
          .eq("status", "completed")
          .order("completed_at", { ascending: false })
          .limit(1)
          .single();

        if (run?.completed_at) {
          setLastUpdated(run.completed_at);
        }
      } catch {
        setIsLoading(false);
      }
    }

    loadFromSupabase();
  }, []);

  const filteredStories = useMemo(() => {
    let filtered = stories.filter((s) => s.section === activeSection);
    if (activeCategory !== "All") {
      filtered = filtered.filter((s) => s.category === activeCategory);
    }
    return filtered.sort((a, b) => b.importance - a.importance);
  }, [stories, activeSection, activeCategory]);

  const leadStory = filteredStories[0];
  const mediumStories = filteredStories.slice(1, 4);
  const compactStories = filteredStories.slice(4);

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        backgroundColor: "var(--bg-primary)",
        transition: "background-color var(--dur-morph) var(--ease-out)",
      }}
    >
      <NavBar
        activeSection={activeSection}
        onSectionChange={(s) => {
          setActiveSection(s);
          setActiveCategory("All");
        }}
      />

      <main
        id="main-content"
        style={{
          flex: 1,
          maxWidth: 1280,
          margin: "0 auto",
          padding: "0 var(--space-7)",
          paddingBottom: "var(--space-7)",
          width: "100%",
        }}
      >
        {/* Section title — newspaper tradition */}
        <div
          style={{
            borderBottom: "2px solid var(--fg-primary)",
            paddingTop: "var(--space-5)",
            paddingBottom: "var(--space-2)",
            marginBottom: "var(--space-2)",
            display: "flex",
            alignItems: "baseline",
            justifyContent: "space-between",
          }}
        >
          <h1
            style={{
              fontFamily: "var(--font-editorial)",
              fontSize: "var(--text-lg)",
              fontWeight: 700,
              letterSpacing: "0.02em",
              textTransform: "uppercase",
              color: "var(--fg-primary)",
            }}
          >
            {activeSection === "world" ? "World News" : "US News"}
          </h1>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-3)",
            }}
          >
            <RefreshButton externalLastUpdated={lastUpdated} />
          </div>
        </div>

        {/* Filter bar */}
        <FilterBar
          activeCategory={activeCategory}
          onCategoryChange={setActiveCategory}
        />

        {/* Loading skeleton */}
        {isLoading && <LoadingSkeleton />}

        {/* Empty state — no data from pipeline yet */}
        {!isLoading && stories.length === 0 && (
          <div style={{
            padding: "var(--space-7) var(--space-5)",
            textAlign: "center",
            maxWidth: 480,
            margin: "0 auto",
          }}>
            <svg width="64" height="64" viewBox="0 0 64 64" fill="none" style={{ margin: "0 auto var(--space-5)", opacity: 0.35, color: "var(--fg-tertiary)" }}>
              <rect x="8" y="12" width="48" height="40" rx="1" stroke="currentColor" strokeWidth="1.5" />
              <line x1="16" y1="22" x2="48" y2="22" stroke="currentColor" strokeWidth="1.5" />
              <line x1="16" y1="30" x2="40" y2="30" stroke="currentColor" strokeWidth="1" opacity="0.5" />
              <line x1="16" y1="36" x2="44" y2="36" stroke="currentColor" strokeWidth="1" opacity="0.5" />
              <line x1="16" y1="42" x2="36" y2="42" stroke="currentColor" strokeWidth="1" opacity="0.5" />
            </svg>
            <h2 style={{
              fontFamily: "var(--font-editorial)",
              fontSize: "var(--text-xl)",
              fontWeight: 700,
              color: "var(--fg-primary)",
              marginBottom: "var(--space-3)",
            }}>
              Awaiting First Edition
            </h2>
            <p style={{
              fontFamily: "var(--font-structural)",
              fontSize: "var(--text-base)",
              color: "var(--fg-tertiary)",
              lineHeight: 1.6,
              marginBottom: "var(--space-4)",
            }}>
              The news pipeline hasn&apos;t run yet. Stories will appear here
              once articles are fetched and analyzed from 90 curated sources.
            </p>
            <p style={{
              fontFamily: "var(--font-data)",
              fontSize: "var(--text-xs)",
              color: "var(--fg-muted)",
              letterSpacing: "0.02em",
            }}>
              Scheduled: 6:00 AM &amp; 6:00 PM UTC daily
            </p>
          </div>
        )}

        {/* No stories in selected filter */}
        {!isLoading && stories.length > 0 && filteredStories.length === 0 && (
          <div style={{ padding: "var(--space-7) 0", textAlign: "center" }}>
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
          <section
            aria-label="Top stories"
            className="grid-medium"
            style={{
              borderBottom: "var(--rule-thin)",
            }}
          >
            {mediumStories.map((story, idx) => (
              <div
                key={story.id}
                className="grid-medium__item"
                style={{
                  borderRight:
                    idx < mediumStories.length - 1
                      ? "var(--rule-thin)"
                      : "none",
                }}
              >
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
        {!isLoading && (
          <div
            style={{
              borderTop: "2px solid var(--fg-primary)",
              marginTop: "var(--space-6)",
              paddingTop: "var(--space-3)",
              paddingBottom: "var(--space-3)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexWrap: "wrap",
              gap: "var(--space-3)",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-data)",
                fontSize: "var(--text-xs)",
                color: "var(--fg-muted)",
                fontFeatureSettings: '"tnum" 1',
              }}
            >
              {activeSection === "world" ? "World" : "US"} Edition /{" "}
              {filteredStories.length} stories
            </span>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: "var(--space-3)",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-editorial)",
                  fontSize: "var(--text-xs)",
                  color: "var(--fg-muted)",
                  letterSpacing: "0.01em",
                }}
              >
                void --news
              </span>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      {!isLoading && <Footer />}

      {/* Deep Dive panel — slides in when a story is selected */}
      {selectedStory && (
        <DeepDive story={selectedStory} onClose={handleDeepDiveClose} />
      )}

      {/* Page-level responsive styles */}
      <style>{`
        /* ---- Medium stories grid (desktop: 3 columns with newspaper rules) ---- */
        .grid-medium {
          display: grid;
          grid-template-columns: 1fr;
        }

        .grid-medium__item {
          padding-right: 0;
          padding-left: 0;
        }

        @media (min-width: 768px) {
          .grid-medium {
            grid-template-columns: repeat(2, 1fr);
            gap: 0 var(--space-5);
          }
          .grid-medium__item {
            padding-right: var(--space-5);
          }
          .grid-medium__item:nth-child(2n) {
            border-right: none !important;
            padding-right: 0;
          }
        }

        @media (min-width: 1024px) {
          .grid-medium {
            grid-template-columns: repeat(3, 1fr);
            gap: 0 var(--space-5);
          }
          .grid-medium__item:nth-child(2n) {
            border-right: var(--rule-thin) !important;
            padding-right: var(--space-5);
          }
          .grid-medium__item:nth-child(3n) {
            border-right: none !important;
            padding-right: 0;
          }
        }

        /* ---- Compact stories grid ---- */
        .grid-compact {
          display: grid;
          grid-template-columns: 1fr;
        }

        @media (min-width: 768px) {
          .grid-compact {
            grid-template-columns: repeat(2, 1fr);
            gap: 0 var(--space-5);
          }
        }

        @media (min-width: 1024px) {
          .grid-compact {
            grid-template-columns: repeat(3, 1fr);
            gap: 0 var(--space-5);
          }
        }

        @media (min-width: 1280px) {
          .grid-compact {
            grid-template-columns: repeat(4, 1fr);
            gap: 0 var(--space-5);
          }
        }

        /* Compact story cards: reduce typography */
        .grid-compact .grid-compact__item h3 {
          font-size: var(--text-lg) !important;
        }

        /* ---- Mobile bottom nav visibility ---- */
        @media (max-width: 767px) {
          .nav-bottom-mobile {
            display: flex !important;
          }
          .nav-tabs-desktop {
            display: none !important;
          }
          /* Mobile: show icon, hide full logo */
          .nav-logo-desktop {
            display: none !important;
          }
          .nav-logo-mobile {
            display: block !important;
          }
          /* Extra padding at bottom for mobile nav */
          main {
            padding-bottom: 80px !important;
          }
        }

        /* ---- Scrollbar hide for filter bar ---- */
        [role="tablist"]::-webkit-scrollbar {
          display: none;
        }

        /* ---- Medium grid column rules on desktop ---- */
        @media (min-width: 1024px) {
          .grid-medium__item {
            padding-left: var(--space-5);
          }
          .grid-medium__item:first-child {
            padding-left: 0;
          }
        }
      `}</style>
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
