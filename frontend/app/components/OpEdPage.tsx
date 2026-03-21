"use client";

import { useState, useEffect, useMemo } from "react";
import type { Edition } from "../lib/types";
import type { OpinionArticle } from "../lib/types";
import type { LeanRange } from "./LeanFilter";
import { fetchOpinionArticles } from "../lib/supabase";
import OpinionCard from "./OpinionCard";
import LoadingSkeleton from "./LoadingSkeleton";

/* --------------------------------------------------------------------------
   OpEdPage — The Op-Ed Page
   Fetches individual opinion articles directly (not clusters).
   No deep dive, no consensus/divergence, no Gemini summaries.
   Featured first article; remaining in 2-col desktop / 1-col mobile grid.
   -------------------------------------------------------------------------- */

interface OpEdPageProps {
  edition: Edition;
  leanRange?: LeanRange | null;
}

export default function OpEdPage({ edition, leanRange }: OpEdPageProps) {
  const [articles, setArticles] = useState<OpinionArticle[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    setIsLoading(true);
    setError(null);

    fetchOpinionArticles(edition)
      .then((data) => {
        if (controller.signal.aborted) return;
        setArticles(data as OpinionArticle[]);
        setIsLoading(false);
      })
      .catch((err) => {
        if (controller.signal.aborted) return;
        setError(err instanceof Error ? err.message : "Failed to load opinion articles");
        setIsLoading(false);
      });

    return () => controller.abort();
  }, [edition]);

  // Universal lean filter — applied to opinion articles by their politicalLean score
  const filteredArticles = useMemo(() => {
    if (!leanRange) return articles;
    return articles.filter(
      (a) => a.politicalLean >= leanRange.min && a.politicalLean <= leanRange.max,
    );
  }, [articles, leanRange]);

  const featured = filteredArticles[0] ?? null;
  const rest = filteredArticles.slice(1);

  return (
    <div className="oped-page">
      {/* Section header */}
      <header className="oped-page__header">
        <div className="oped-page__header-rule" />
        <div className="oped-page__header-inner">
          <h2 className="oped-page__title">The Op-Ed Page</h2>
          <p className="oped-page__subtitle">
            Opinion, analysis, and editorial &mdash; ranked by recency, balanced across the spectrum.
          </p>
        </div>
        <div className="oped-page__header-rule" />
      </header>

      {/* Loading state */}
      {isLoading && <LoadingSkeleton />}

      {/* Error state */}
      {error && !isLoading && (
        <div className="empty-state">
          <p style={{ fontFamily: "var(--font-structural)", fontSize: "var(--text-lg)", color: "var(--fg-tertiary)" }}>
            Unable to load opinion articles.
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && articles.length === 0 && (
        <div className="empty-state">
          <p style={{ fontFamily: "var(--font-structural)", fontSize: "var(--text-lg)", color: "var(--fg-tertiary)", lineHeight: 1.6 }}>
            No opinion pieces found for this edition.<br />
            Try the morning or evening pipeline run.
          </p>
        </div>
      )}

      {/* Featured editorial — first article, larger treatment */}
      {!isLoading && featured && (
        <section className="oped-page__featured" aria-label="Featured editorial">
          <OpinionCard article={featured} featured={true} />
        </section>
      )}

      {/* Remaining articles — 2-col desktop, 1-col mobile */}
      {!isLoading && rest.length > 0 && (
        <section className="oped-page__grid" aria-label="Opinion articles">
          {rest.map((article) => (
            <OpinionCard key={article.id} article={article} />
          ))}
        </section>
      )}

      {/* Empty state when lean filter hides everything */}
      {!isLoading && !error && articles.length > 0 && filteredArticles.length === 0 && (
        <div className="lean-filter-empty">
          <p className="lean-filter-empty__text">No opinion pieces in this lean range.</p>
          <p className="lean-filter-empty__hint">Try widening the range or clearing the lean filter.</p>
        </div>
      )}

      {/* Count line */}
      {!isLoading && filteredArticles.length > 0 && (
        <p className="oped-page__count">
          {filteredArticles.length} opinion piece{filteredArticles.length !== 1 ? "s" : ""}
          {leanRange ? " (filtered)" : ""} &mdash; curated from {edition === "world" ? "world" : "US"} sources
        </p>
      )}
    </div>
  );
}
