"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { supabase } from "../lib/supabase";
import SpectrumChart, { type SpectrumSource } from "../components/SpectrumChart";
import ThemeToggle from "../components/ThemeToggle";
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
  const [logoAnim, setLogoAnim] = useState<"draw" | "idle">("draw");

  useEffect(() => {
    const timer = setTimeout(() => setLogoAnim("idle"), 800);
    return () => clearTimeout(timer);
  }, []);

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
                <LogoIcon size={28} animation={logoAnim} />
              </span>
            </Link>
            <span className="nav-dateline">
              <span className="nav-dateline__full">Our Sources</span>
              <span className="nav-dateline__compact">Sources</span>
            </span>
          </div>

          <div className="nav-tabs">
            <Link
              href="/"
              className="nav-tab"
            >
              <span className="nav-tab__inner">News Feed</span>
            </Link>
            <span className="nav-tab nav-tab--active" aria-current="page">
              <span className="nav-tab__inner">Sources</span>
            </span>
          </div>

          <ThemeToggle />
        </nav>
      </header>

      <main id="main-content" className="page-main sources-page">
        {/* ---- Page header ---- */}
        <header className="sources-header">
          <div className="sources-header__text">
            <h1 className="sources-header__title">Our Sources</h1>
            <p className="sources-header__subtitle">
              Every source vetted for credibility before inclusion. Bias
              analysis runs per-article — not per-outlet — so a center-leaning
              outlet can still publish opinion pieces, and we&apos;ll flag them.
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

        {/* ---- Seven-point scale legend ---- */}
        {!isLoading && !error && sources.length > 0 && (
          <section className="spectrum-legend" aria-label="Political lean scale explanation">
            <h2 className="spectrum-legend__title">The Seven-Point Scale</h2>
            <div className="spectrum-legend__grid">
              {[
                {
                  lean: "far-left",
                  label: "Far Left",
                  desc: "Strongly progressive framing across most topics. Frequent use of left-coded language.",
                },
                {
                  lean: "left",
                  label: "Left",
                  desc: "Consistent left-leaning framing. Covers stories through a progressive lens.",
                },
                {
                  lean: "center-left",
                  label: "Center Left",
                  desc: "Leans progressive but maintains journalistic standards. Occasional conservative perspectives.",
                },
                {
                  lean: "center",
                  label: "Center",
                  desc: "Presents multiple perspectives. Aims for balance. Wire services often fall here.",
                },
                {
                  lean: "center-right",
                  label: "Center Right",
                  desc: "Leans conservative but covers diverse viewpoints. Strong editorial standards.",
                },
                {
                  lean: "right",
                  label: "Right",
                  desc: "Consistent right-leaning framing. Covers stories through a conservative lens.",
                },
                {
                  lean: "far-right",
                  label: "Far Right",
                  desc: "Strongly conservative framing. Frequent use of right-coded language and framing.",
                },
              ].map(({ lean, label, desc }) => (
                <div
                  key={lean}
                  className="spectrum-legend__item"
                  data-lean={lean}
                >
                  <div className="spectrum-legend__item-header">
                    <span
                      className="spectrum-legend__item-dot"
                      data-lean={lean}
                      aria-hidden="true"
                    />
                    <span className="spectrum-legend__item-label">{label}</span>
                  </div>
                  <p className="spectrum-legend__item-desc">{desc}</p>
                </div>
              ))}
            </div>
            <p className="spectrum-legend__caveat">
              These baselines are starting points for the analysis engine, not
              verdicts. Every article is scored independently. A right-leaning
              outlet can publish measured, factual reporting — and our engine
              will reflect that.
            </p>
          </section>
        )}
      </main>

      <Footer />
    </div>
  );
}
