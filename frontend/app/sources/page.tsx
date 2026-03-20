"use client";

import { useState, useEffect, useMemo } from "react";
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

type Edition = "world" | "us" | "india";

const EDITIONS: { slug: Edition; label: string }[] = [
  { slug: "world", label: "All" },
  { slug: "us", label: "US" },
  { slug: "india", label: "India" },
];

const EDITION_COUNTRIES: Record<Edition, string[] | null> = {
  world: null,
  us: ["US"],
  india: ["IN"],
};

export default function SourcesPage() {
  const [sources, setSources] = useState<SpectrumSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeEdition, setActiveEdition] = useState<Edition>("world");

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

  const filteredSources = useMemo(() => {
    const countries = EDITION_COUNTRIES[activeEdition];
    if (!countries) return sources;
    return sources.filter((s) => countries.includes(s.country));
  }, [sources, activeEdition]);

  const editionLabel = EDITIONS.find((e) => e.slug === activeEdition)?.label ?? "All";
  const totalCount = filteredSources.length;

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
        {/* ---- Compact toolbar with edition filter ---- */}
        <div className="sources-toolbar">
          <div className="sources-toolbar__text">
            <h1 className="sources-toolbar__title">
              {totalCount} Sources &middot; {editionLabel}
            </h1>
          </div>
          <div className="sources-editions" role="tablist" aria-label="Filter by edition">
            {EDITIONS.map((edition) => (
              <button
                key={edition.slug}
                role="tab"
                aria-selected={activeEdition === edition.slug}
                className={`sources-edition-chip${activeEdition === edition.slug ? " sources-edition-chip--active" : ""}`}
                onClick={() => setActiveEdition(edition.slug)}
              >
                {edition.label}
              </button>
            ))}
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
        {!isLoading && !error && filteredSources.length > 0 && (
          <SpectrumChart sources={filteredSources} />
        )}

        {!isLoading && !error && filteredSources.length === 0 && sources.length > 0 && (
          <div className="empty-state" style={{ padding: "var(--space-6) 0" }}>
            <p className="text-base" style={{ color: "var(--fg-tertiary)" }}>
              No sources for {editionLabel} edition.
            </p>
            <button className="btn-secondary" onClick={() => setActiveEdition("world")} style={{ marginTop: "var(--space-3)" }}>
              View all sources
            </button>
          </div>
        )}

        {/* Seven-point scale is now inline in the SpectrumChart component */}
      </main>

      <Footer />
    </div>
  );
}
