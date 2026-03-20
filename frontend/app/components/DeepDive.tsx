"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  ArrowLeft,
  X,
  Check,
  Warning,
} from "@phosphor-icons/react";
import type { Story, StorySource, DeepDiveData, ThreeLensData, OpinionLabel } from "../lib/types";
import { fetchDeepDiveData } from "../lib/supabase";
import { timeAgo } from "../lib/utils";
import Sigil from "./Sigil";
import LogoIcon from "./LogoIcon";

/* ---------------------------------------------------------------------------
   DeepDive — Slide-in panel showing unified summary of a story cluster.
   Desktop (1024px+): 50% width panel sliding from the right.
   Mobile: full-screen modal sliding up from the bottom.
   --------------------------------------------------------------------------- */

interface DeepDiveProps {
  story: Story;
  onClose: () => void;
}

/* --- Favicon helper ------------------------------------------------------ */

function getDomain(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ""); }
  catch { return ""; }
}

function faviconUrl(articleUrl: string): string {
  const domain = getDomain(articleUrl);
  if (!domain) return "";
  return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
}

/* --- Lean label helper --------------------------------------------------- */

function leanLabel(lean: number): string {
  if (lean <= 20) return "Far Left";
  if (lean <= 35) return "Left";
  if (lean <= 45) return "Center-Left";
  if (lean <= 55) return "Center";
  if (lean <= 65) return "Center-Right";
  if (lean <= 80) return "Right";
  return "Far Right";
}

/* --- Main DeepDive component --------------------------------------------- */

export default function DeepDive({ story, onClose }: DeepDiveProps) {
  const [isVisible, setIsVisible] = useState(false);
  const [contentVisible, setContentVisible] = useState(false);
  const [liveData, setLiveData] = useState<DeepDiveData | null>(null);
  const [isLoadingData, setIsLoadingData] = useState(false);
  const [isDesktop, setIsDesktop] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const previousFocusRef = useRef<HTMLElement | null>(null);

  const deepDive: DeepDiveData | undefined = liveData ?? story.deepDive;

  const sources = useMemo(() => deepDive?.sources ?? [], [deepDive]);

  /* ---- Compute lean spectrum positions (max 3 rows, overflow collapses) -- */
  const leanPositions = useMemo(() => {
    const MAX_VISIBLE_ROWS = 3;
    const items = sources
      .map((src, idx) => ({ src, idx, lean: src.biasScores.politicalLean }))
      .sort((a, b) => a.lean - b.lean);

    const placed: { lean: number; row: number }[] = [];
    return items.map((item) => {
      let row = 0;
      for (const p of placed) {
        if (Math.abs(item.lean - p.lean) < 7 && p.row === row) {
          row++;
        }
      }
      placed.push({ lean: item.lean, row });
      // If row exceeds max, collapse into the last visible row (will overlap)
      const visibleRow = Math.min(row, MAX_VISIBLE_ROWS - 1);
      const isOverflow = row >= MAX_VISIBLE_ROWS;
      return { ...item, row: visibleRow, isOverflow };
    });
  }, [sources]);

  /* ---- Detect desktop vs mobile for directional animation -------------- */
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 1024px)");
    setIsDesktop(mq.matches);

    function handleChange(e: MediaQueryListEvent) {
      setIsDesktop(e.matches);
    }

    mq.addEventListener("change", handleChange);
    return () => mq.removeEventListener("change", handleChange);
  }, []);

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
          // bias_scores may be object (one-to-one) or array (one-to-many)
          const biasRaw = article.bias_scores;
          const bias = Array.isArray(biasRaw)
            ? (biasRaw.length > 0 ? biasRaw[0] : null)
            : (biasRaw ?? null);

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
          // Use pipeline-generated consensus/divergence from the cluster,
          // falling back only when no data has been computed yet.
          const rawConsensus = Array.isArray(story.deepDive?.consensus) ? story.deepDive.consensus : [];
          const rawDivergence = Array.isArray(story.deepDive?.divergence) ? story.deepDive.divergence : [];
          const consensus = rawConsensus.length > 0
            ? rawConsensus
            : ["Sources broadly agree on the key facts of this story"];
          const divergenceData = rawDivergence.length > 0
            ? rawDivergence
            : ["Some differences in framing and emphasis were detected across sources"];

          setLiveData({
            consensus,
            divergence: divergenceData,
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
          /* Desktop: slide from right (translateX). Mobile: slide from bottom (translateY).
             Both open and close use the same axis — symmetric animation. */
          transform: isVisible
            ? "translate(0, 0)"
            : isDesktop ? "translateX(100%)" : "translateY(100%)",
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

          {/* Cluster-level bias indicator */}
          {story.sigilData && !story.sigilData.pending && (
            <div style={{ marginTop: "var(--space-3)" }}>
              <Sigil data={story.sigilData} size="lg" />
            </div>
          )}

          {/* Source spectrum — merged lean visualization + clickable source links.
              No section header. Favicons positioned on spectrum by lean score.
              Max 3 rows; overflow sources overlap and expand on hover. */}
          {sources.length > 0 && (
            <div className="dd-spectrum" style={{ marginTop: "var(--space-4)" }}>
              {/* Gradient track */}
              <div className="dd-spectrum__track" />

              {/* Center tick */}
              <div className="dd-spectrum__center-tick" />

              {/* Source dots positioned by lean, max 3 rows */}
              <div className="dd-spectrum__dots" style={{ height: (leanPositions.length > 0 ? Math.min(3, Math.max(...leanPositions.map(p => p.row + 1))) : 1) * 30 + 4 }}>
                {leanPositions.map(({ src, idx, lean, row, isOverflow }) => {
                  const favicon = faviconUrl(src.url);
                  return (
                    <a
                      key={`${src.name}-${idx}`}
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      title={`${src.name} — ${leanLabel(lean)} (${lean})`}
                      aria-label={`${src.name}: ${leanLabel(lean)}`}
                      className={`dd-spectrum__dot${isOverflow ? " dd-spectrum__dot--overflow" : ""}`}
                      style={{
                        left: `${lean}%`,
                        top: row * 30,
                        zIndex: isOverflow ? 1 : sources.length - row,
                      }}
                    >
                      {favicon ? (
                        <img src={favicon} alt="" width={14} height={14} style={{ borderRadius: 2 }} loading="lazy" />
                      ) : (
                        <span className="dd-spectrum__dot-initial">
                          {src.name.charAt(0)}
                        </span>
                      )}
                    </a>
                  );
                })}
              </div>

              {/* Axis labels */}
              <div className="dd-spectrum__labels">
                <span>Left</span>
                <span>Center</span>
                <span>Right</span>
              </div>
            </div>
          )}
        </header>

        {/* ---- Content (fades in after panel) ----------------------------- */}
        <div
          className="deep-dive-panel__content"
          style={{
            opacity: contentVisible ? 1 : 0,
            transition: "opacity 300ms var(--ease-out)",
          }}
        >
          {/* Loading indicator — analyzing animation while fetching deep dive data */}
          {isLoadingData && !deepDive && (
            <div style={{ padding: "var(--space-5) 0", display: "flex", flexDirection: "column", alignItems: "center", gap: "var(--space-3)" }}>
              <LogoIcon size={32} animation="analyzing" />
              <span className="text-data" style={{ color: "var(--fg-tertiary)" }}>
                Analyzing coverage...
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

          {/* Source lean spectrum removed — merged into header spectrum above */}

          {/* ---- Section: Where sources agree ----------------------------- */}
          {deepDive && Array.isArray(deepDive.consensus) && deepDive.consensus.length > 0 && (
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
          {deepDive && Array.isArray(deepDive.divergence) && deepDive.divergence.length > 0 && (
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
