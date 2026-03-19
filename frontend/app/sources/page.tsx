"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { supabase } from "../lib/supabase";
import SpectrumChart, { type SpectrumSource } from "../components/SpectrumChart";
import ThemeToggle from "../components/ThemeToggle";
import PageToggle from "../components/PageToggle";
import LogoFull from "../components/LogoFull";
import LogoIcon from "../components/LogoIcon";
import Footer from "../components/Footer";

/* ---------------------------------------------------------------------------
   Sources Page — /sources
   Visualizes all curated news sources on a political lean spectrum.
   Desktop: horizontal spectrum bar with logos above/below.
   Mobile: vertical lean zones with source lists.
   --------------------------------------------------------------------------- */

export default function SourcesPage() {
  const [sources, setSources] = useState<SpectrumSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadSources() {
      try {
        const { data, error: fetchError } = await supabase
          .from("sources")
          .select(
            "name, slug, url, tier, country, political_lean_baseline, credibility_notes"
          )
          .order("name");

        if (controller.signal.aborted) return;

        if (fetchError) {
          setError(fetchError.message);
          setIsLoading(false);
          return;
        }

        setSources((data as SpectrumSource[]) || []);
        setIsLoading(false);
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error ? err.message : "Failed to load sources"
          );
          setIsLoading(false);
        }
      }
    }

    loadSources();
    return () => controller.abort();
  }, []);

  const totalCount = sources.length;

  return (
    <div className="page-container">
      {/* ---- Nav ---- */}
      <header className="nav-header">
        <nav className="nav-inner" aria-label="Main navigation">
          <div className="nav-left">
            <Link
              href="/"
              aria-label="void --news — home"
              className="nav-logo si-hoverable"
            >
              <span className="nav-logo-desktop">
                <LogoFull height={36} />
              </span>
              <span className="nav-logo-mobile">
                <LogoFull height={22} />
              </span>
            </Link>
            <span className="nav-dateline">
              <span className="nav-dateline__full">Our Sources</span>
              <span className="nav-dateline__medium">Sources</span>
            </span>
          </div>

          <div className="nav-right">
            <PageToggle activePage="sources" />
            <ThemeToggle />
          </div>
        </nav>
      </header>

      <main id="main-content" className="page-main sources-page">
        {/* ---- Page header ---- */}
        <header className="sources-header">
          <div className="sources-header__text">
            <h1 className="sources-header__title">Our Sources</h1>
            <p className="sources-header__subtitle">
              Every source vetted for credibility. Bias runs per-article, not per-outlet.
              These baselines are starting points &mdash; a right-leaning outlet can publish
              measured reporting, and our engine will reflect that.
            </p>
          </div>
          <div className="sources-header__stat" aria-live="polite">
            {isLoading ? (
              <span
                className="skeleton sources-header__stat-skeleton"
                aria-label="Loading source count"
              />
            ) : (
              <span className="sources-header__count">
                <span className="sources-header__count-num">{totalCount}</span>
                <span className="sources-header__count-label">
                  curated sources
                </span>
              </span>
            )}
          </div>
        </header>

        {/* ---- Tier legend ---- */}
        <div className="sources-tier-legend" aria-label="Tier breakdown">
          <div className="sources-tier-legend__item">
            <span className="sources-tier-legend__dot sources-tier-legend__dot--above" />
            <span className="sources-tier-legend__name">
              US Major
            </span>
            <span className="sources-tier-legend__note">Above the bar</span>
          </div>
          <div className="sources-tier-legend__item">
            <span className="sources-tier-legend__dot sources-tier-legend__dot--below" />
            <span className="sources-tier-legend__name">
              International &amp; Independent
            </span>
            <span className="sources-tier-legend__note">Below the bar</span>
          </div>
        </div>

        {/* ---- Loading state ---- */}
        {isLoading && (
          <div className="sources-loading" aria-label="Loading sources">
            <div className="sources-loading__bar skeleton" />
            <div className="sources-loading__logos">
              {Array.from({ length: 12 }).map((_, i) => (
                <div
                  key={i}
                  className="sources-loading__logo skeleton"
                  style={{ animationDelay: `${i * 60}ms` }}
                />
              ))}
            </div>
          </div>
        )}

        {/* ---- Error state ---- */}
        {error && !isLoading && (
          <div className="empty-state">
            <h2
              className="text-xl"
              style={{
                color: "var(--fg-primary)",
                marginBottom: "var(--space-3)",
              }}
            >
              Could not load sources
            </h2>
            <p
              className="text-base"
              style={{
                color: "var(--fg-tertiary)",
                marginBottom: "var(--space-4)",
              }}
            >
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

        {/* ---- Empty state ---- */}
        {!isLoading && !error && sources.length === 0 && (
          <div className="empty-state">
            <LogoIcon size={48} animation="analyzing" />
            <h2
              className="text-xl"
              style={{
                color: "var(--fg-primary)",
                marginBottom: "var(--space-3)",
              }}
            >
              No sources found
            </h2>
            <p
              className="text-base"
              style={{ color: "var(--fg-tertiary)" }}
            >
              Sources will appear once the pipeline syncs them to the database.
            </p>
          </div>
        )}

        {/* ---- Spectrum visualization ---- */}
        {!isLoading && !error && sources.length > 0 && (
          <SpectrumChart sources={sources} />
        )}

        {/* Seven-point scale is now inline in the SpectrumChart component */}
      </main>

      <Footer />
    </div>
  );
}
