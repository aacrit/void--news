"use client";

import { useState, useMemo } from "react";
import type { Section, Category } from "./lib/types";
import { mockStories } from "./lib/mockData";
import NavBar from "./components/NavBar";
import FilterBar from "./components/FilterBar";
import LeadStory from "./components/LeadStory";
import StoryCard from "./components/StoryCard";
import RefreshButton from "./components/RefreshButton";

/* ---------------------------------------------------------------------------
   Homepage — News Feed
   Desktop: broadsheet grid — lead story + asymmetric layout + dense compact
   Mobile: single-column tabloid stack
   --------------------------------------------------------------------------- */

export default function Home() {
  const [activeSection, setActiveSection] = useState<Section>("world");
  const [activeCategory, setActiveCategory] = useState<"All" | Category>(
    "All"
  );

  const filteredStories = useMemo(() => {
    let stories = mockStories.filter((s) => s.section === activeSection);
    if (activeCategory !== "All") {
      stories = stories.filter((s) => s.category === activeCategory);
    }
    return stories.sort((a, b) => b.importance - a.importance);
  }, [activeSection, activeCategory]);

  const leadStory = filteredStories[0];
  const mediumStories = filteredStories.slice(1, 4);
  const compactStories = filteredStories.slice(4);

  return (
    <div
      style={{
        minHeight: "100vh",
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
        style={{
          maxWidth: 1280,
          margin: "0 auto",
          padding: "0 var(--space-7)",
          paddingBottom: "var(--space-7)",
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
          <div style={{ display: "flex", alignItems: "center", gap: "var(--space-3)" }}>
            <RefreshButton />
          </div>
        </div>

        {/* Filter bar */}
        <FilterBar
          activeCategory={activeCategory}
          onCategoryChange={setActiveCategory}
        />

        {/* Empty state */}
        {filteredStories.length === 0 && (
          <div
            style={{
              padding: "var(--space-7) 0",
              textAlign: "center",
            }}
          >
            <p
              style={{
                fontFamily: "var(--font-structural)",
                fontSize: "var(--text-lg)",
                color: "var(--fg-tertiary)",
              }}
            >
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
        {leadStory && (
          <section aria-label="Lead story">
            <LeadStory story={leadStory} />
          </section>
        )}

        {/* Medium stories — broadsheet grid on desktop */}
        {mediumStories.length > 0 && (
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
                <StoryCard story={story} index={idx + 1} />
              </div>
            ))}
          </section>
        )}

        {/* Compact stories — dense grid on desktop */}
        {compactStories.length > 0 && (
          <section
            aria-label="More stories"
            className="grid-compact"
          >
            {compactStories.map((story, idx) => (
              <div
                key={story.id}
                className="grid-compact__item"
              >
                <StoryCard story={story} index={idx + mediumStories.length + 1} />
              </div>
            ))}
          </section>
        )}

        {/* Edition line — newspaper tradition */}
        <footer
          style={{
            borderTop: "2px solid var(--fg-primary)",
            marginTop: "var(--space-6)",
            paddingTop: "var(--space-3)",
            paddingBottom: "var(--space-6)",
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
        </footer>
      </main>

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
