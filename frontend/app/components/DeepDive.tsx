"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  ArrowLeft,
  X,
  Check,
  Warning,
  ArrowSquareOut,
} from "@phosphor-icons/react";
import type { Story, StorySource, DeepDiveData, ThreeLensData, OpinionLabel } from "../lib/types";
import { fetchDeepDiveData } from "../lib/supabase";
import { timeAgo } from "../lib/utils";
import BiasLens from "./BiasLens";

/* ---------------------------------------------------------------------------
   DeepDive — Slide-in panel showing unified summary of a story cluster.
   Desktop (1024px+): 50% width panel sliding from the right.
   Mobile: full-screen modal sliding up from the bottom.
   --------------------------------------------------------------------------- */

interface DeepDiveProps {
  story: Story;
  onClose: () => void;
}

const TIER_LABELS: Record<StorySource["tier"], string> = {
  us_major: "US",
  international: "Intl",
  independent: "Ind",
};

const TIER_FULL_LABELS: Record<StorySource["tier"], string> = {
  us_major: "US Major",
  international: "International",
  independent: "Independent",
};

const TIER_COLORS: Record<StorySource["tier"], string> = {
  us_major: "var(--bias-center)",
  international: "var(--type-reporting)",
  independent: "var(--sense-low)",
};

/* --- Coverage breakdown bar component ------------------------------------ */

function CoverageBar({
  label,
  count,
  total,
  color,
}: {
  label: string;
  count: number;
  total: number;
  color: string;
}) {
  const pct = total > 0 ? (count / total) * 100 : 0;

  return (
    <div className="coverage-bar">
      <div className="coverage-bar__header">
        <span className="coverage-bar__label">{label}</span>
        <span className="coverage-bar__count">{count}</span>
      </div>
      <div className="coverage-bar__track">
        <div
          className="coverage-bar__fill"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

/* --- Main DeepDive component --------------------------------------------- */

export default function DeepDive({ story, onClose }: DeepDiveProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [contentVisible, setContentVisible] = useState(false);
  const [liveData, setLiveData] = useState<DeepDiveData | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const deepDive: DeepDiveData | undefined = liveData ?? story.deepDive;

  const sources = useMemo(() => deepDive?.sources ?? [], [deepDive]);

  const tierCounts = useMemo(() => {
    const counts = { us_major: 0, international: 0, independent: 0 };
    for (const s of sources) {
      counts[s.tier]++;
    }
    return counts;
  }, [sources]);

  /* ---- Fetch live data from Supabase ----------------------------------- */
  useEffect(() => {
    let cancelled = false;

    async function loadClusterData() {
      setIsLoadingData(true);
      try {
        const raw = await fetchDeepDiveData(story.id);
        if (cancelled || !raw || raw.length === 0) {
          setIsLoadingData(false);
          return;
        }

        const storySourceList: StorySource[] = [];
        for (const row of raw) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const article = row.article as any;
          if (!article) continue;

          const source = article.source;
          const biasArr = article.bias_scores;
          const bias = Array.isArray(biasArr) && biasArr.length > 0 ? biasArr[0] : null;

          const lean = (bias?.political_lean as number) ?? 50;
          const opinionVal = (bias?.opinion_fact as number) ?? 25;
          const rigor = (bias?.factual_rigor as number) ?? 75;

          // Parse rationale if available
          let rationale: Record<string, unknown> | null = null;
          if (bias?.rationale && typeof bias.rationale === "object") {
            rationale = bias.rationale;
          }

          // Derive opinion label
          let opinionLabel: OpinionLabel = "Reporting";
          if (opinionVal > 75) opinionLabel = "Editorial";
          else if (opinionVal > 50) opinionLabel = "Opinion";
          else if (opinionVal > 25) opinionLabel = "Analysis";

          // Per-article coverage: based on rigor + confidence (no cluster source count)
          const confidence = (bias?.confidence as number) ?? 0.5;
          const coverageScore = Math.round((rigor / 100) * 60 + confidence * 40);

          const lensData: ThreeLensData = {
            lean,
            coverage: coverageScore,
            sourceCount: 1,
            opinion: opinionVal,
            opinionLabel,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            leanRationale: (rationale?.lean as any) ?? undefined,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            opinionRationale: (rationale?.opinion as any) ?? undefined,
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            coverageRationale: (rationale?.coverage as any) ?? undefined,
          };

          storySourceList.push({
            name: (source?.name as string) ?? "Unknown",
            url: (article.url as string) ?? (source?.url as string) ?? "#",
            tier: ((source?.tier as string) as StorySource["tier"]) ?? "us_major",
            biasScores: {
              politicalLean: lean,
              sensationalism: (bias?.sensationalism as number) ?? 30,
              opinionFact: opinionVal,
              factualRigor: rigor,
              framing: (bias?.framing as number) ?? 40,
            },
            lensData,
          });
        }

        if (!cancelled && storySourceList.length > 0) {
          setLiveData({
            consensus: story.deepDive?.consensus ?? [
              "Sources broadly agree on the key facts of this story",
            ],
            divergence: story.deepDive?.divergence ?? [
              "Some differences in framing and emphasis were detected across sources",
            ],
            sources: storySourceList,
          });
        }
      } catch {
        /* Silently fall back to mock deepDive data */
      } finally {
        if (!cancelled) setIsLoadingData(false);
      }
    }

    loadClusterData();
    return () => { cancelled = true; };
  }, [story.id, story.deepDive]);

  /* ---- Open animation sequence ----------------------------------------- */
  useEffect(() => {
    previousFocusRef.current = document.activeElement as HTMLElement;
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    requestAnimationFrame(() => {
      setIsVisible(true);
      setTimeout(() => setContentVisible(true), 200);
    });

    return () => {
      document.body.style.overflow = originalOverflow;
    };
  }, []);

  /* ---- Focus trap + Escape key ----------------------------------------- */
  useEffect(() => {
    if (!isVisible) return;
    panelRef.current?.focus();

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        handleClose();
        return;
      }

      if (e.key === "Tab" && panelRef.current) {
        const focusable = panelRef.current.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    }

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isVisible]);

  /* ---- Close with animation -------------------------------------------- */
  const handleClose = useCallback(() => {
    setContentVisible(false);
    setIsVisible(false);
    setTimeout(() => {
      previousFocusRef.current?.focus();
      onClose();
    }, 400);
  }, [onClose]);

  return (
    <>
      {/* Backdrop */}
      <div
        aria-hidden="true"
        onClick={handleClose}
        className="deep-dive-backdrop"
        style={{
          opacity: isVisible ? 1 : 0,
          transition: "opacity 300ms var(--ease-out)",
        }}
      />

      {/* Panel */}
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Deep dive: ${story.title}`}
        tabIndex={-1}
        className="deep-dive-panel"
        style={{
          transform: isVisible ? "translateY(0)" : "translateY(100%)",
          transition: "transform 400ms var(--ease-out)",
        }}
      >
        {/* ---- Header --------------------------------------------------- */}
        <header className="deep-dive-panel__header">
          <div className="deep-dive-header-bar">
            <button onClick={handleClose} aria-label="Back to feed" className="deep-dive-back">
              <ArrowLeft size={18} weight="regular" aria-hidden="true" />
              <span className="deep-dive-back-label">Back to feed</span>
            </button>

            <button onClick={handleClose} aria-label="Close deep dive" className="deep-dive-close">
              <X size={20} weight="regular" aria-hidden="true" />
            </button>
          </div>

          <h2 className="text-xl" style={{ color: "var(--fg-primary)", marginTop: "var(--space-3)" }}>
            {story.title}
          </h2>

          <div className="deep-dive-meta">
            <span className="category-tag">{story.category}</span>
            <span className="dot-separator" aria-hidden="true" />
            <span className="time-tag" style={{ color: "var(--fg-tertiary)" }}>
              {sources.length > 0 ? sources.length : story.source.count} sources
            </span>
            <span className="dot-separator" aria-hidden="true" />
            <span className="time-tag">{timeAgo(story.publishedAt)}</span>
          </div>
        </header>

        {/* ---- Content (fades in after panel) ----------------------------- */}
        <div
          className="deep-dive-panel__content"
          style={{
            opacity: contentVisible ? 1 : 0,
            transition: "opacity 300ms var(--ease-out)",
          }}
        >
          {/* Loading indicator */}
          {isLoadingData && !deepDive && (
            <div style={{ padding: "var(--space-5) 0", textAlign: "center" }}>
              <span className="text-data" style={{ color: "var(--fg-tertiary)" }}>
                Loading coverage data...
              </span>
            </div>
          )}

          {/* ---- Section: What Happened --------------------------------- */}
          <section aria-labelledby="dd-summary" style={{ marginBottom: "var(--space-6)" }}>
            <h3 id="dd-summary" className="section-heading">What happened</h3>
            <p className="text-base" style={{ lineHeight: 1.7, color: "var(--fg-secondary)" }}>
              {story.summary}
            </p>
          </section>

          {/* ---- Section: Where sources agree ----------------------------- */}
          {deepDive && deepDive.consensus.length > 0 && (
            <section aria-labelledby="dd-consensus" style={{ marginBottom: "var(--space-6)" }}>
              <h3 id="dd-consensus" className="section-heading">Where sources agree</h3>
              <ul className="evidence-list">
                {deepDive.consensus.map((point, i) => (
                  <li key={i} className="evidence-item">
                    <Check size={18} weight="bold" aria-hidden="true" className="evidence-item__icon" style={{ color: "var(--sense-low)" }} />
                    <span className="evidence-item__text">{point}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* ---- Section: Where sources diverge -------------------------- */}
          {deepDive && deepDive.divergence.length > 0 && (
            <section aria-labelledby="dd-divergence" style={{ marginBottom: "var(--space-6)" }}>
              <h3 id="dd-divergence" className="section-heading">Where sources diverge</h3>
              <ul className="evidence-list">
                {deepDive.divergence.map((point, i) => (
                  <li key={i} className="evidence-item">
                    <Warning size={18} weight="bold" aria-hidden="true" className="evidence-item__icon" style={{ color: "var(--sense-medium)" }} />
                    <span className="evidence-item__text">{point}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* ---- Section: Source Coverage List ----------------------------- */}
          {sources.length > 0 && (
            <section aria-labelledby="dd-sources" style={{ marginBottom: "var(--space-6)" }}>
              <h3 id="dd-sources" className="section-heading">Source coverage</h3>
              <div role="list" aria-label="Sources covering this story">
                {sources.map((src, i) => (
                  <div key={`${src.name}-${i}`} role="listitem" className="source-row">
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="source-link"
                    >
                      {src.name}
                    </a>

                    <span
                      className="tier-badge"
                      style={{ color: TIER_COLORS[src.tier], border: `1px solid ${TIER_COLORS[src.tier]}` }}
                      title={TIER_FULL_LABELS[src.tier]}
                    >
                      {TIER_LABELS[src.tier]}
                    </span>

                    {src.lensData && <BiasLens lensData={src.lensData} size="sm" />}

                    <a
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Open ${src.name} article in new tab`}
                      className="external-link-icon"
                    >
                      <ArrowSquareOut size={16} weight="regular" aria-hidden="true" />
                    </a>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ---- Section: Coverage Breakdown ------------------------------ */}
          {sources.length > 0 && (
            <section aria-labelledby="dd-breakdown" style={{ marginBottom: "var(--space-6)" }}>
              <h3 id="dd-breakdown" className="section-heading">Coverage breakdown</h3>
              <CoverageBar label={TIER_FULL_LABELS.us_major} count={tierCounts.us_major} total={sources.length} color={TIER_COLORS.us_major} />
              <CoverageBar label={TIER_FULL_LABELS.international} count={tierCounts.international} total={sources.length} color={TIER_COLORS.international} />
              <CoverageBar label={TIER_FULL_LABELS.independent} count={tierCounts.independent} total={sources.length} color={TIER_COLORS.independent} />
            </section>
          )}

          {/* No deep dive data at all */}
          {!deepDive && !isLoadingData && (
            <div style={{ padding: "var(--space-6) 0", textAlign: "center" }}>
              <p className="text-base" style={{ color: "var(--fg-tertiary)", lineHeight: 1.6 }}>
                Detailed coverage data is not yet available for this story.
                Check back after the next pipeline run.
              </p>
            </div>
          )}
        </div>
      </div>
    </>
  );
}
