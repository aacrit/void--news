"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  ArrowLeft,
  X,
  Check,
  Warning,
  ArrowSquareOut,
} from "@phosphor-icons/react";
import type { Story, StorySource, DeepDiveData } from "../lib/types";
import { fetchDeepDiveData } from "../lib/supabase";
import { timeAgo } from "../lib/mockData";
import BiasBars from "./BiasBars";

/* ---------------------------------------------------------------------------
   DeepDive — Slide-in panel showing unified summary of a story cluster.
   Desktop: 50% width panel sliding from the right with dark backdrop.
   Mobile: full-screen modal sliding up from the bottom.
   Accessibility: focus trap, Escape to close, role="dialog", aria-modal.
   --------------------------------------------------------------------------- */

interface DeepDiveProps {
  story: Story;
  onClose: () => void;
}

/* --- Tier display helpers ------------------------------------------------- */

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
    <div style={{ marginBottom: "var(--space-3)" }}>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "baseline",
          marginBottom: "var(--space-1)",
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-structural)",
            fontSize: "var(--text-sm)",
            fontWeight: 500,
            color: "var(--fg-secondary)",
          }}
        >
          {label}
        </span>
        <span
          style={{
            fontFamily: "var(--font-data)",
            fontSize: "var(--text-xs)",
            color: "var(--fg-tertiary)",
            fontFeatureSettings: '"tnum" 1',
          }}
        >
          {count}
        </span>
      </div>
      <div
        style={{
          height: 6,
          backgroundColor: "var(--bg-secondary)",
          width: "100%",
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${pct}%`,
            backgroundColor: color,
            transition: "width var(--dur-morph) var(--ease-out)",
          }}
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

  /* The data to render: prefer live Supabase data, fall back to story.deepDive */
  const deepDive: DeepDiveData | undefined = liveData ?? story.deepDive;

  const sources = deepDive?.sources ?? [];

  /* Tier counts */
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

        /* Transform raw Supabase data into DeepDiveData shape */
        const storySourceList: StorySource[] = [];
        for (const row of raw) {
          const article = row.article as Record<string, unknown> | null;
          if (!article) continue;

          const source = article.source as Record<string, unknown> | null;
          const biasArr = article.bias_scores as
            | Record<string, unknown>[]
            | null;
          const bias = biasArr && biasArr.length > 0 ? biasArr[0] : null;

          storySourceList.push({
            name: (source?.name as string) ?? "Unknown",
            url: (article.url as string) ?? (source?.url as string) ?? "#",
            tier:
              ((source?.tier as string) as StorySource["tier"]) ?? "us_major",
            biasScores: {
              politicalLean: (bias?.political_lean as number) ?? 50,
              sensationalism: (bias?.sensationalism as number) ?? 30,
              opinionFact: (bias?.opinion_fact as number) ?? 25,
              factualRigor: (bias?.factual_rigor as number) ?? 75,
              framing: (bias?.framing as number) ?? 40,
            },
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
    return () => {
      cancelled = true;
    };
  }, [story.id, story.deepDive]);

  /* ---- Open animation sequence ----------------------------------------- */
  useEffect(() => {
    /* Store the element that had focus before opening */
    previousFocusRef.current = document.activeElement as HTMLElement;

    /* Prevent body scroll */
    const originalOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    /* Trigger enter animations on next frame */
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

    /* Focus the panel on open */
    panelRef.current?.focus();

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        handleClose();
        return;
      }

      /* Tab trap */
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
      /* Restore focus */
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
        style={{
          position: "fixed",
          inset: 0,
          backgroundColor: "rgba(0, 0, 0, 0.5)",
          zIndex: "var(--z-overlay)",
          opacity: isVisible ? 1 : 0,
          transition: `opacity 300ms var(--ease-out)`,
          cursor: "pointer",
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
          position: "fixed",
          zIndex: "var(--z-modal)",
          backgroundColor: "var(--bg-primary)",
          boxShadow: "var(--shadow-e3)",
          overflowY: "auto",
          overflowX: "hidden",
          outline: "none",
          /* Default (mobile): full-screen from bottom */
          inset: 0,
          transform: isVisible ? "translateY(0)" : "translateY(100%)",
          transition: `transform 400ms var(--ease-out)`,
        }}
      >
        {/* ---- Header --------------------------------------------------- */}
        <header
          style={{
            position: "sticky",
            top: 0,
            backgroundColor: "var(--bg-primary)",
            zIndex: 2,
            borderBottom: "var(--rule-thin)",
            padding: "var(--space-4) var(--space-5)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: "var(--space-3)",
            }}
          >
            {/* Back button */}
            <button
              onClick={handleClose}
              aria-label="Back to feed"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "var(--space-2)",
                fontFamily: "var(--font-structural)",
                fontSize: "var(--text-sm)",
                fontWeight: 500,
                color: "var(--fg-secondary)",
                padding: "var(--space-2)",
                marginLeft: "calc(-1 * var(--space-2))",
                minWidth: 44,
                minHeight: 44,
              }}
            >
              <ArrowLeft size={18} weight="regular" aria-hidden="true" />
              <span className="deep-dive-back-label">Back to feed</span>
            </button>

            {/* Close button — more prominent on mobile */}
            <button
              onClick={handleClose}
              aria-label="Close deep dive"
              className="deep-dive-close-btn"
              style={{
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                width: 44,
                height: 44,
                color: "var(--fg-secondary)",
                flexShrink: 0,
              }}
            >
              <X size={20} weight="regular" aria-hidden="true" />
            </button>
          </div>

          {/* Headline */}
          <h2
            style={{
              fontFamily: "var(--font-editorial)",
              fontSize: "var(--text-xl)",
              fontWeight: 700,
              lineHeight: 1.15,
              letterSpacing: "-0.005em",
              color: "var(--fg-primary)",
              marginTop: "var(--space-3)",
            }}
          >
            {story.title}
          </h2>

          {/* Meta row: category + source count + time */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "var(--space-3)",
              marginTop: "var(--space-2)",
              flexWrap: "wrap",
            }}
          >
            <span
              style={{
                fontFamily: "var(--font-structural)",
                fontSize: "var(--text-xs)",
                fontWeight: 500,
                letterSpacing: "0.06em",
                textTransform: "uppercase",
                color: "var(--fg-tertiary)",
              }}
            >
              {story.category}
            </span>
            <span
              style={{
                width: 3,
                height: 3,
                borderRadius: "50%",
                backgroundColor: "var(--fg-muted)",
                flexShrink: 0,
              }}
              aria-hidden="true"
            />
            <span
              style={{
                fontFamily: "var(--font-data)",
                fontSize: "var(--text-xs)",
                color: "var(--fg-tertiary)",
                fontFeatureSettings: '"tnum" 1',
              }}
            >
              {sources.length > 0 ? sources.length : story.source.count} sources
            </span>
            <span
              style={{
                width: 3,
                height: 3,
                borderRadius: "50%",
                backgroundColor: "var(--fg-muted)",
                flexShrink: 0,
              }}
              aria-hidden="true"
            />
            <span
              style={{
                fontFamily: "var(--font-data)",
                fontSize: "var(--text-xs)",
                color: "var(--fg-muted)",
                fontFeatureSettings: '"tnum" 1',
              }}
            >
              {timeAgo(story.publishedAt)}
            </span>
          </div>
        </header>

        {/* ---- Content (fades in after panel) ----------------------------- */}
        <div
          style={{
            padding: "var(--space-5)",
            opacity: contentVisible ? 1 : 0,
            transition: `opacity 300ms var(--ease-out)`,
          }}
        >
          {/* Loading indicator */}
          {isLoadingData && !deepDive && (
            <div
              style={{
                padding: "var(--space-5) 0",
                textAlign: "center",
              }}
            >
              <span
                style={{
                  fontFamily: "var(--font-data)",
                  fontSize: "var(--text-sm)",
                  color: "var(--fg-tertiary)",
                }}
              >
                Loading coverage data...
              </span>
            </div>
          )}

          {/* ---- Section: What Happened --------------------------------- */}
          <section aria-labelledby="dd-summary" style={{ marginBottom: "var(--space-6)" }}>
            <h3
              id="dd-summary"
              style={{
                fontFamily: "var(--font-editorial)",
                fontSize: "var(--text-lg)",
                fontWeight: 700,
                color: "var(--fg-primary)",
                marginBottom: "var(--space-3)",
                paddingBottom: "var(--space-2)",
                borderBottom: "var(--rule-thin)",
              }}
            >
              What happened
            </h3>
            <p
              style={{
                fontFamily: "var(--font-structural)",
                fontSize: "var(--text-base)",
                lineHeight: 1.7,
                color: "var(--fg-secondary)",
                maxWidth: "65ch",
              }}
            >
              {story.summary}
            </p>
          </section>

          {/* ---- Section: Where sources agree ----------------------------- */}
          {deepDive && deepDive.consensus.length > 0 && (
            <section
              aria-labelledby="dd-consensus"
              style={{ marginBottom: "var(--space-6)" }}
            >
              <h3
                id="dd-consensus"
                style={{
                  fontFamily: "var(--font-editorial)",
                  fontSize: "var(--text-lg)",
                  fontWeight: 700,
                  color: "var(--fg-primary)",
                  marginBottom: "var(--space-3)",
                  paddingBottom: "var(--space-2)",
                  borderBottom: "var(--rule-thin)",
                }}
              >
                Where sources agree
              </h3>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {deepDive.consensus.map((point, i) => (
                  <li
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "var(--space-3)",
                      padding: "var(--space-2) 0",
                    }}
                  >
                    <Check
                      size={18}
                      weight="bold"
                      aria-hidden="true"
                      style={{
                        color: "var(--sense-low)",
                        flexShrink: 0,
                        marginTop: 2,
                      }}
                    />
                    <span
                      style={{
                        fontFamily: "var(--font-structural)",
                        fontSize: "var(--text-base)",
                        lineHeight: 1.6,
                        color: "var(--fg-secondary)",
                      }}
                    >
                      {point}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* ---- Section: Where sources diverge -------------------------- */}
          {deepDive && deepDive.divergence.length > 0 && (
            <section
              aria-labelledby="dd-divergence"
              style={{ marginBottom: "var(--space-6)" }}
            >
              <h3
                id="dd-divergence"
                style={{
                  fontFamily: "var(--font-editorial)",
                  fontSize: "var(--text-lg)",
                  fontWeight: 700,
                  color: "var(--fg-primary)",
                  marginBottom: "var(--space-3)",
                  paddingBottom: "var(--space-2)",
                  borderBottom: "var(--rule-thin)",
                }}
              >
                Where sources diverge
              </h3>
              <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {deepDive.divergence.map((point, i) => (
                  <li
                    key={i}
                    style={{
                      display: "flex",
                      alignItems: "flex-start",
                      gap: "var(--space-3)",
                      padding: "var(--space-2) 0",
                    }}
                  >
                    <Warning
                      size={18}
                      weight="bold"
                      aria-hidden="true"
                      style={{
                        color: "var(--sense-medium)",
                        flexShrink: 0,
                        marginTop: 2,
                      }}
                    />
                    <span
                      style={{
                        fontFamily: "var(--font-structural)",
                        fontSize: "var(--text-base)",
                        lineHeight: 1.6,
                        color: "var(--fg-secondary)",
                      }}
                    >
                      {point}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* ---- Section: Source Coverage List ----------------------------- */}
          {sources.length > 0 && (
            <section
              aria-labelledby="dd-sources"
              style={{ marginBottom: "var(--space-6)" }}
            >
              <h3
                id="dd-sources"
                style={{
                  fontFamily: "var(--font-editorial)",
                  fontSize: "var(--text-lg)",
                  fontWeight: 700,
                  color: "var(--fg-primary)",
                  marginBottom: "var(--space-3)",
                  paddingBottom: "var(--space-2)",
                  borderBottom: "var(--rule-thin)",
                }}
              >
                Source coverage
              </h3>
              <div role="list" aria-label="Sources covering this story">
                {sources.map((src, i) => (
                  <div
                    key={`${src.name}-${i}`}
                    role="listitem"
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "var(--space-3)",
                      padding: "var(--space-3) var(--space-3)",
                      backgroundColor:
                        i % 2 === 1 ? "var(--bg-secondary)" : "transparent",
                      transition:
                        "background-color var(--dur-fast) var(--ease-out)",
                    }}
                  >
                    {/* Source name — clickable */}
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        fontFamily: "var(--font-structural)",
                        fontSize: "var(--text-base)",
                        fontWeight: 500,
                        color: "var(--fg-primary)",
                        textDecoration: "none",
                        flex: 1,
                        minWidth: 0,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {src.name}
                    </a>

                    {/* Tier badge */}
                    <span
                      style={{
                        fontFamily: "var(--font-data)",
                        fontSize: "var(--text-xs)",
                        fontWeight: 500,
                        color: TIER_COLORS[src.tier],
                        border: `1px solid ${TIER_COLORS[src.tier]}`,
                        padding: "1px 6px",
                        letterSpacing: "0.04em",
                        textTransform: "uppercase",
                        flexShrink: 0,
                        lineHeight: 1.5,
                      }}
                      title={TIER_FULL_LABELS[src.tier]}
                    >
                      {TIER_LABELS[src.tier]}
                    </span>

                    {/* Bias bars */}
                    <BiasBars scores={src.biasScores} size="sm" />

                    {/* External link */}
                    <a
                      href={src.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      aria-label={`Open ${src.name} article in new tab`}
                      style={{
                        display: "inline-flex",
                        alignItems: "center",
                        justifyContent: "center",
                        width: 32,
                        height: 32,
                        color: "var(--fg-muted)",
                        flexShrink: 0,
                        transition: "color var(--dur-fast) var(--ease-out)",
                      }}
                    >
                      <ArrowSquareOut
                        size={16}
                        weight="regular"
                        aria-hidden="true"
                      />
                    </a>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* ---- Section: Coverage Breakdown ------------------------------ */}
          {sources.length > 0 && (
            <section
              aria-labelledby="dd-breakdown"
              style={{ marginBottom: "var(--space-6)" }}
            >
              <h3
                id="dd-breakdown"
                style={{
                  fontFamily: "var(--font-editorial)",
                  fontSize: "var(--text-lg)",
                  fontWeight: 700,
                  color: "var(--fg-primary)",
                  marginBottom: "var(--space-3)",
                  paddingBottom: "var(--space-2)",
                  borderBottom: "var(--rule-thin)",
                }}
              >
                Coverage breakdown
              </h3>
              <CoverageBar
                label={TIER_FULL_LABELS.us_major}
                count={tierCounts.us_major}
                total={sources.length}
                color={TIER_COLORS.us_major}
              />
              <CoverageBar
                label={TIER_FULL_LABELS.international}
                count={tierCounts.international}
                total={sources.length}
                color={TIER_COLORS.international}
              />
              <CoverageBar
                label={TIER_FULL_LABELS.independent}
                count={tierCounts.independent}
                total={sources.length}
                color={TIER_COLORS.independent}
              />
            </section>
          )}

          {/* No deep dive data at all */}
          {!deepDive && !isLoadingData && (
            <div
              style={{
                padding: "var(--space-6) 0",
                textAlign: "center",
              }}
            >
              <p
                style={{
                  fontFamily: "var(--font-structural)",
                  fontSize: "var(--text-base)",
                  color: "var(--fg-tertiary)",
                  lineHeight: 1.6,
                }}
              >
                Detailed coverage data is not yet available for this story.
                Check back after the next pipeline run.
              </p>
            </div>
          )}
        </div>

        {/* ---- Responsive styles ---------------------------------------- */}
        <style>{`
          /* Mobile: full-screen modal from bottom (default above) */

          /* Desktop: 50% width panel from right */
          @media (min-width: 768px) {
            .deep-dive-panel {
              left: auto !important;
              right: 0 !important;
              top: 0 !important;
              bottom: 0 !important;
              width: 50% !important;
              min-width: 420px !important;
              max-width: 720px !important;
              transform: ${isVisible ? "translateX(0)" : "translateX(100%)"} !important;
              border-left: var(--rule-thin) !important;
            }

            .deep-dive-close-btn {
              display: none !important;
            }
          }

          /* Very wide screens — cap width */
          @media (min-width: 1440px) {
            .deep-dive-panel {
              width: 40% !important;
              max-width: 640px !important;
            }
          }

          /* Mobile: hide "Back to feed" text, keep arrow */
          @media (max-width: 767px) {
            .deep-dive-back-label {
              display: none !important;
            }
          }
        `}</style>
      </div>
    </>
  );
}
