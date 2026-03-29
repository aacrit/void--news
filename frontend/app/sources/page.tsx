"use client";

import { useState, useEffect, useMemo } from "react";
import Link from "next/link";
import type { Edition } from "../lib/types";
import { supabase, supabaseError } from "../lib/supabase";
import SpectrumChart, { type SpectrumSource, normalizeLean } from "../components/SpectrumChart";
import ThemeToggle from "../components/ThemeToggle";
import PageToggle from "../components/PageToggle";
import EditionIcon from "../components/EditionIcon";
import LogoFull from "../components/LogoFull";
import LogoIcon from "../components/LogoIcon";
import Footer from "../components/Footer";
import { getEditionTimeOfDay, getEditionTimestamp } from "../lib/utils";
import ErrorBoundary from "../components/ErrorBoundary";

/* ---------------------------------------------------------------------------
   Sources Page — /sources
   Visualizes all curated news sources on a political lean spectrum.
   Desktop: horizontal spectrum bar with logos above/below.
   Mobile: horizontal swipeable card strip with scroll-snap.
   --------------------------------------------------------------------------- */

type LeanCategory =
  | "far-left" | "left" | "center-left" | "center"
  | "center-right" | "right" | "far-right";

type LeanFilter = "All" | "Left" | "Center" | "Right";

const EDITIONS: { slug: Edition; label: string }[] = [
  { slug: "world", label: "World" },
  { slug: "us", label: "US" },
  { slug: "india", label: "India" },
];

const EDITION_COUNTRIES: Record<Edition, string[] | null> = {
  world: null,
  us: ["US"],
  india: ["IN"],
};

const LEAN_FILTERS: LeanFilter[] = ["Left", "Center", "Right"];

const LEAN_ALLOWED: Record<LeanFilter, LeanCategory[] | null> = {
  All: null,
  Left: ["far-left", "left", "center-left"],
  Center: ["center"],
  Right: ["center-right", "right", "far-right"],
};

const LEAN_DOT_COLOR: Record<string, string> = {
  Left: "var(--bias-left)",
  Center: "var(--bias-center)",
  Right: "var(--bias-right)",
};

function formatDateCompact(): string {
  return new Date().toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function SourcesPageInner() {
  const [sources, setSources] = useState<SpectrumSource[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeEdition, setActiveEdition] = useState<Edition>("world");
  const [activeLean, setActiveLean] = useState<LeanFilter>("All");

  useEffect(() => {
    const controller = new AbortController();

    async function loadSources() {
      if (!supabase) {
        setError(supabaseError ?? "Unable to connect to data source.");
        setIsLoading(false);
        return;
      }
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
    let result = sources;
    const countries = EDITION_COUNTRIES[activeEdition];
    if (countries) result = result.filter((s) => countries.includes(s.country));
    const allowed = LEAN_ALLOWED[activeLean];
    if (allowed) result = result.filter((s) => allowed.includes(normalizeLean(s.political_lean_baseline)));
    return result;
  }, [sources, activeEdition, activeLean]);

  const totalCount = filteredSources.length;

  const handleLeanTap = (lean: LeanFilter) => {
    if (typeof navigator !== "undefined" && navigator.vibrate) navigator.vibrate(10);
    setActiveLean(lean === activeLean ? "All" : lean);
  };

  return (
    <div className="page-container">
      {/* ---- Nav header — matches NavBar layout ---- */}
      <header className="nav-header">
        <nav className="nav-inner" aria-label="Main navigation">
          <div className="nav-left">
            <Link
              href="/"
              aria-label="void --news — home"
              className="nav-logo si-hoverable"
            >
              <span className="nav-logo-desktop">
                <LogoFull height={32} />
              </span>
              <span className="nav-logo-mobile">
                <LogoFull height={22} />
              </span>
            </Link>
          </div>

          {/* Edition tabs — local state, visually identical to NavBar */}
          <div className="nav-tabs" role="tablist" aria-label="Edition selector">
            {EDITIONS.map((edition) => (
              <button
                key={edition.slug}
                role="tab"
                aria-selected={activeEdition === edition.slug}
                className={`nav-tab${activeEdition === edition.slug ? " nav-tab--active" : ""}`}
                onClick={() => setActiveEdition(edition.slug)}
              >
                <span className="nav-tab__inner">
                  <EditionIcon slug={edition.slug} size={14} />
                  {edition.label}
                </span>
              </button>
            ))}
          </div>

          {/* Dateline — desktop only */}
          <span className="nav-dateline-inline" aria-hidden="true">
            {getEditionTimeOfDay(activeEdition)} Edition
            <span className="nav-dateline-inline__sep">&middot;</span>
            {formatDateCompact()}
            <span className="nav-dateline-inline__sep">&middot;</span>
            <span className="nav-dateline-inline__time">{getEditionTimestamp(activeEdition)}</span>
          </span>

          <div className="nav-right">
            <PageToggle activePage="sources" />
            <ThemeToggle />
          </div>
        </nav>
      </header>

      {/* Mobile bottom nav — edition switching */}
      <nav className="nav-bottom" aria-label="Edition navigation">
        {EDITIONS.map((edition) => (
          <button
            key={`mobile-${edition.slug}`}
            aria-current={activeEdition === edition.slug ? "page" : undefined}
            className={`nav-bottom-tab${activeEdition === edition.slug ? " nav-bottom-tab--active" : ""}`}
            onClick={() => setActiveEdition(edition.slug)}
          >
            <span className="nav-tab__inner">
              <EditionIcon slug={edition.slug} size={18} />
              {edition.label}
            </span>
          </button>
        ))}
      </nav>

      <main id="main-content" className="page-main sources-page">
        {/* ---- Toolbar: title + lean filter ---- */}
        <div className="sources-toolbar">
          <div className="sources-toolbar__text">
            <h1 className="sources-toolbar__title" title="void --sources">
              <span className="sources-toolbar__count">{totalCount}</span> Sources
            </h1>
          </div>
          <div className="sources-leans" role="tablist" aria-label="Filter by lean">
            {LEAN_FILTERS.map((lean) => {
              const isActive = activeLean === lean;
              return (
                <button
                  key={lean}
                  role="tab"
                  aria-selected={isActive}
                  className={`sources-edition-chip${isActive ? " sources-edition-chip--active" : ""}`}
                  onClick={() => handleLeanTap(lean)}
                >
                  <span
                    className="filter-chip__dot"
                    style={{ backgroundColor: LEAN_DOT_COLOR[lean] }}
                    aria-hidden="true"
                  />
                  {lean}
                </button>
              );
            })}
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
              No sources match the current filters.
            </p>
            <button
              className="btn-secondary"
              onClick={() => { setActiveEdition("world"); setActiveLean("All"); }}
              style={{ marginTop: "var(--space-3)" }}
            >
              Clear filters
            </button>
          </div>
        )}
      </main>

      <Footer />
    </div>
  );
}

export default function SourcesPage() {
  return (
    <ErrorBoundary>
      <SourcesPageInner />
    </ErrorBoundary>
  );
}
