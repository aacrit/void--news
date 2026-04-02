"use client";

import { useState, useEffect, useMemo, useCallback, useRef } from "react";
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

const METHODOLOGY_AXES = [
  {
    name: "Political Lean",
    desc: "Keyword frequency, entity sentiment via NER, framing phrases, and source baseline blending. Score 0\u2013100.",
  },
  {
    name: "Sensationalism",
    desc: "Clickbait patterns, superlative density, emotional extremity, partisan attack frequency. Score 0\u2013100.",
  },
  {
    name: "Opinion vs Reporting",
    desc: "First-person pronouns, subjectivity markers, attribution density, rhetorical questions. Score 0\u2013100.",
  },
  {
    name: "Factual Rigor",
    desc: "Named sources via NER, organizational citations, data patterns, direct quotes, vague-source penalties. Score 0\u2013100.",
  },
  {
    name: "Framing",
    desc: "Charged synonym detection (50+ pairs), omission analysis across the cluster, headline\u2013body divergence. Score 0\u2013100.",
  },
  {
    name: "Outlet Tracking",
    desc: "Per-topic, per-outlet exponential moving average that adapts as outlets\u2019 coverage patterns evolve over time.",
  },
];

function ScoringMethodology() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="dd-methodology">
      <button
        className="dd-methodology__trigger"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-controls="sources-methodology-content"
      >
        How we score {isOpen ? "\u25BE" : "\u25B8"}
      </button>
      {isOpen && (
        <div
          className="dd-methodology__content"
          id="sources-methodology-content"
          role="region"
          aria-label="Scoring methodology"
        >
          <p className="dd-methodology__intro">
            Every article is analyzed by six independent rule-based algorithms.
            No AI makes scoring decisions &mdash; all analysis uses NLP heuristics,
            keyword lexicons, and statistical patterns.
          </p>
          <dl className="dd-methodology__axes">
            {METHODOLOGY_AXES.map((axis) => (
              <div className="dd-methodology__axis" key={axis.name}>
                <dt className="dd-methodology__axis-name">{axis.name}</dt>
                <dd className="dd-methodology__axis-desc">{axis.desc}</dd>
              </div>
            ))}
          </dl>
          <p className="dd-methodology__footer">
            419 sources. 42 ground-truth validation articles. 100% accuracy.
          </p>
        </div>
      )}
    </div>
  );
}

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
  const editionGroupRef = useRef<HTMLDivElement>(null);
  const leanGroupRef = useRef<HTMLDivElement>(null);

  // Defer date rendering to client to avoid SSG hydration mismatch (#310)
  const [mounted, setMounted] = useState(false);
  useEffect(() => { setMounted(true); }, []);

  /** Arrow-key navigation within a radiogroup container */
  const handleRadioGroupKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLDivElement>) => {
      if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;
      e.preventDefault();
      const container = e.currentTarget;
      const radios = Array.from(
        container.querySelectorAll<HTMLButtonElement>('[role="radio"]')
      );
      const idx = radios.indexOf(e.target as HTMLButtonElement);
      if (idx < 0) return;
      const next =
        e.key === "ArrowRight"
          ? radios[(idx + 1) % radios.length]
          : radios[(idx - 1 + radios.length) % radios.length];
      next.focus();
      next.click();
    },
    []
  );

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

          {/* Edition filter — radiogroup (filters content, not panel switch) */}
          <div
            className="nav-tabs"
            role="radiogroup"
            aria-label="Edition"
            ref={editionGroupRef}
            onKeyDown={handleRadioGroupKeyDown}
          >
            {EDITIONS.map((edition) => {
              const checked = activeEdition === edition.slug;
              return (
                <button
                  key={edition.slug}
                  role="radio"
                  aria-checked={checked}
                  tabIndex={checked ? 0 : -1}
                  className={`nav-tab${checked ? " nav-tab--active" : ""}`}
                  onClick={() => setActiveEdition(edition.slug)}
                >
                  <span className="nav-tab__inner">
                    <EditionIcon slug={edition.slug} size={14} />
                    {edition.label}
                  </span>
                </button>
              );
            })}
          </div>

          {/* Dateline — desktop only */}
          <span className="nav-dateline-inline" aria-hidden="true" suppressHydrationWarning>
            {mounted ? `${getEditionTimeOfDay(activeEdition)} Edition` : "Edition"}
            <span className="nav-dateline-inline__sep">&middot;</span>
            {mounted ? formatDateCompact() : ""}
            <span className="nav-dateline-inline__sep">&middot;</span>
            <span className="nav-dateline-inline__time">{mounted ? getEditionTimestamp(activeEdition) : ""}</span>
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
          <div
            className="sources-leans"
            role="radiogroup"
            aria-label="Filter by lean"
            ref={leanGroupRef}
            onKeyDown={handleRadioGroupKeyDown}
          >
            {LEAN_FILTERS.map((lean) => {
              const checked = activeLean === lean;
              return (
                <button
                  key={lean}
                  role="radio"
                  aria-checked={checked}
                  tabIndex={checked ? 0 : -1}
                  className={`sources-edition-chip${checked ? " sources-edition-chip--active" : ""}`}
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
            <h2 className="text-xl empty-state__title">
              Could not load sources
            </h2>
            <p className="text-base empty-state__body">
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
            <h2 className="text-xl empty-state__title">
              No sources found
            </h2>
            <p className="text-base empty-state__body--no-margin">
              Sources will appear once the pipeline syncs them to the database.
            </p>
          </div>
        )}

        {/* ---- Spectrum visualization ---- */}
        {!isLoading && !error && filteredSources.length > 0 && (
          <SpectrumChart sources={filteredSources} />
        )}

        {!isLoading && !error && filteredSources.length === 0 && sources.length > 0 && (
          <div className="empty-state empty-state--inline">
            <p className="text-base empty-state__body--no-margin">
              No sources match the current filters.
            </p>
            <button
              className="btn-secondary"
              onClick={() => { setActiveEdition("world"); setActiveLean("All"); }}
            >
              Clear filters
            </button>
          </div>
        )}

        {/* ---- Scoring Methodology ---- */}
        {!isLoading && !error && sources.length > 0 && (
          <ScoringMethodology />
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
