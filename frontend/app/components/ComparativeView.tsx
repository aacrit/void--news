"use client";

import { useMemo, useState } from "react";
import type { StorySource } from "../lib/types";

/* ---------------------------------------------------------------------------
   ComparativeView — "Read All Sides"
   Groups sources into Left / Center / Right buckets.
   Clean layout: source logo + first 2 headlines per bucket.
   --------------------------------------------------------------------------- */

interface ComparativeViewProps {
  sources: StorySource[];
  consensusPoints?: string[];
  divergencePoints?: string[];
}

interface LeanBucket {
  label: "Left" | "Center" | "Right";
  cssClass: string;
  min: number;
  max: number;
}

const BUCKETS: LeanBucket[] = [
  { label: "Left",   cssClass: "comp-view__col--left",   min: 0,  max: 40  },
  { label: "Center", cssClass: "comp-view__col--center", min: 41, max: 60  },
  { label: "Right",  cssClass: "comp-view__col--right",  min: 61, max: 100 },
];

function getFaviconUrl(url: string): string {
  try {
    const domain = new URL(url.startsWith("http") ? url : `https://${url}`).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return "";
  }
}

function AgreementIcon({ type }: { type: "agree" | "diverge" }) {
  if (type === "agree") {
    return (
      <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
        <circle cx="6" cy="6" r="5" stroke="var(--sense-low)" strokeWidth="1.5" fill="none" opacity="0.7" />
        <path d="M3.5 6L5.5 8L8.5 4" stroke="var(--sense-low)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <circle cx="6" cy="6" r="5" stroke="var(--sense-high)" strokeWidth="1.5" fill="none" opacity="0.7" />
      <path d="M4 4L8 8M8 4L4 8" stroke="var(--sense-high)" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

const VISIBLE_LIMIT = 3;

export default function ComparativeView({ sources, consensusPoints, divergencePoints }: ComparativeViewProps) {
  const [expandedBuckets, setExpandedBuckets] = useState<Record<string, boolean>>({});
  const [showInsights, setShowInsights] = useState(false);

  const buckets: Record<string, StorySource[]> = useMemo(() => {
    const result: Record<string, StorySource[]> = { Left: [], Center: [], Right: [] };
    for (const src of sources) {
      const lean = src.biasScores?.politicalLean ?? 50;
      if (lean <= 40) result.Left.push(src);
      else if (lean <= 60) result.Center.push(src);
      else result.Right.push(src);
    }
    return result;
  }, [sources]);

  const activeBuckets = BUCKETS.filter((b) => buckets[b.label].length > 0);

  if (activeBuckets.length < 2) {
    return (
      <div className="comp-view comp-view--empty">
        <p className="comp-view__empty-text">
          Sources do not span enough lean perspectives to compare.
        </p>
      </div>
    );
  }

  const hasConsensus = consensusPoints && consensusPoints.length > 0;
  const hasDivergence = divergencePoints && divergencePoints.length > 0;

  return (
    <div className="comp-view" role="region" aria-label="Read all sides: sources by perspective">
      <div className="comp-view__grid">
        {BUCKETS.map((bucket) => {
          const items = buckets[bucket.label];
          if (items.length === 0) return null;

          const isExpanded = !!expandedBuckets[bucket.label];
          const visibleItems = isExpanded ? items : items.slice(0, VISIBLE_LIMIT);
          const hasMore = items.length > VISIBLE_LIMIT;

          return (
            <div key={bucket.label} className={`comp-view__col ${bucket.cssClass}`}>
              {/* Column header */}
              <div className="comp-view__col-header">
                <span className="comp-view__lean-label">{bucket.label}</span>
                <span className="comp-view__source-count text-data">
                  {items.length} {items.length === 1 ? "source" : "sources"}
                </span>
              </div>

              {/* Source list — compact wire-ticker: logo + name + summary + arrow, all inline */}
              <div className="comp-view__items">
                {visibleItems.map((source, i) => {
                  const favicon = getFaviconUrl(source.url);
                  const title = source.articleTitle || source.name;

                  return (
                    <article key={`${source.name}-${i}`} className="comp-view__item comp-view__item--wire">
                      {source.url ? (
                        <a
                          href={source.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="comp-view__wire-link"
                          aria-label={`${source.name}: ${title}`}
                        >
                          {favicon && (
                            <span className="comp-view__favicon-wrap">
                              {/* eslint-disable-next-line @next/next/no-img-element */}
                              <img
                                src={favicon}
                                alt=""
                                width={14}
                                height={14}
                                className="comp-view__favicon"
                                loading="lazy"
                                onError={(e) => {
                                  const wrap = e.currentTarget.parentElement;
                                  if (wrap) wrap.style.display = "none";
                                }}
                              />
                            </span>
                          )}
                          <span className="comp-view__source-name text-data">{source.name}</span>
                          <span className="comp-view__wire-sep" aria-hidden="true">&mdash;</span>
                          <span className="comp-view__wire-title">{title}</span>
                          <span className="comp-view__wire-arrow" aria-hidden="true">&#8250;</span>
                        </a>
                      ) : (
                        <span className="comp-view__wire-link comp-view__wire-link--static">
                          {favicon && (
                            <span className="comp-view__favicon-wrap">
                              {/* eslint-disable-next-line @next/next/no-img-element */}
                              <img
                                src={favicon}
                                alt=""
                                width={14}
                                height={14}
                                className="comp-view__favicon"
                                loading="lazy"
                                onError={(e) => {
                                  const wrap = e.currentTarget.parentElement;
                                  if (wrap) wrap.style.display = "none";
                                }}
                              />
                            </span>
                          )}
                          <span className="comp-view__source-name text-data">{source.name}</span>
                          <span className="comp-view__wire-sep" aria-hidden="true">&mdash;</span>
                          <span className="comp-view__wire-title">{title}</span>
                        </span>
                      )}
                    </article>
                  );
                })}
              </div>

              {hasMore && (
                <button
                  className="comp-view__expand-btn"
                  onClick={() => setExpandedBuckets(prev => ({ ...prev, [bucket.label]: !isExpanded }))}
                  type="button"
                >
                  {isExpanded
                    ? "Show less"
                    : `+${items.length - VISIBLE_LIMIT} more`}
                </button>
              )}
            </div>
          );
        })}
      </div>

      {/* Convergence & Divergence — collapsed by default, below the grid */}
      {(hasConsensus || hasDivergence) && (
        <div className="comp-view__insights-disclosure">
          <button
            className="comp-view__insights-trigger"
            onClick={() => setShowInsights((prev) => !prev)}
            aria-expanded={showInsights}
            type="button"
          >
            Key agreements &amp; disagreements {showInsights ? "\u25BE" : "\u25B8"}
          </button>
          {showInsights && (
            <div className="comp-view__insights-content">
              {hasConsensus && (
                <div className="comp-view__insight-item">
                  <AgreementIcon type="agree" />
                  <div>
                    <span className="comp-view__insight-label">Where sources converge</span>
                    <ul className="comp-view__insight-list">
                      {consensusPoints.map((pt, i) => (
                        <li key={i}>{pt}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
              {hasDivergence && (
                <div className="comp-view__insight-item">
                  <AgreementIcon type="diverge" />
                  <div>
                    <span className="comp-view__insight-label">Where sources diverge</span>
                    <ul className="comp-view__insight-list">
                      {divergencePoints.map((pt, i) => (
                        <li key={i}>{pt}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
