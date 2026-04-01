"use client";

import { useMemo, useState } from "react";
import type { StorySource } from "../lib/types";
import NarrativeXray from "./NarrativeXray";

/* ---------------------------------------------------------------------------
   ComparativeView — "Read All Sides"
   Groups sources into Left / Center / Right buckets.
   Clean layout: source logo + first 2 headlines per bucket.
   Expandable Narrative X-Ray per source (charged synonyms, entity sentiment, omissions).
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

const VISIBLE_LIMIT = 5;

export default function ComparativeView({ sources, consensusPoints, divergencePoints }: ComparativeViewProps) {
  const [expandedBuckets, setExpandedBuckets] = useState<Record<string, boolean>>({});
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

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
      {/* Convergence & Divergence */}
      {(hasConsensus || hasDivergence) && (
        <div className="comp-view__insights">
          {hasConsensus && (
            <div className="comp-view__insight-col comp-view__insight-col--agree">
              <div className="comp-view__insight-header">
                <AgreementIcon type="agree" />
                <span className="comp-view__insight-label">Where sources converge</span>
              </div>
              <ul className="comp-view__insight-list">
                {consensusPoints.map((pt, i) => (
                  <li key={i}>{pt}</li>
                ))}
              </ul>
            </div>
          )}
          {hasDivergence && (
            <div className="comp-view__insight-col comp-view__insight-col--diverge">
              <div className="comp-view__insight-header">
                <AgreementIcon type="diverge" />
                <span className="comp-view__insight-label">Where sources diverge</span>
              </div>
              <ul className="comp-view__insight-list">
                {divergencePoints.map((pt, i) => (
                  <li key={i}>{pt}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

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
                  const sourceKey = `${source.name}-${i}`;
                  const isSourceExpanded = !!expandedSources[sourceKey];
                  const hasXrayData = source.lensData?.framingRationale?.chargedMatches?.length
                    || source.lensData?.framingRationale?.entitiesMissing?.length
                    || (source.lensData?.leanRationale?.entitySentiments
                      && Object.values(source.lensData.leanRationale.entitySentiments).some((s) => Math.abs(s) > 0.05));
                  const hasExpandableContent = !!source.articleSummary && hasXrayData;

                  return (
                    <article key={sourceKey} className="comp-view__item comp-view__item--wire">
                      <div
                        className="comp-view__wire-link"
                        role={hasExpandableContent ? "button" : undefined}
                        tabIndex={hasExpandableContent ? 0 : undefined}
                        aria-expanded={hasExpandableContent ? isSourceExpanded : undefined}
                        aria-label={`${source.name}: ${title}`}
                        onClick={(e) => {
                          if (hasExpandableContent) {
                            e.preventDefault();
                            setExpandedSources((prev) => ({ ...prev, [sourceKey]: !prev[sourceKey] }));
                          }
                        }}
                        onKeyDown={(e) => {
                          if (hasExpandableContent && (e.key === "Enter" || e.key === " ")) {
                            e.preventDefault();
                            setExpandedSources((prev) => ({ ...prev, [sourceKey]: !prev[sourceKey] }));
                          }
                        }}
                        style={hasExpandableContent ? { cursor: "pointer" } : undefined}
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
                        {hasExpandableContent ? (
                          <span
                            className="comp-view__wire-arrow"
                            aria-hidden="true"
                            style={{
                              display: "inline-block",
                              transform: isSourceExpanded ? "rotate(90deg)" : "none",
                              transition: "transform 150ms var(--ease-out)",
                            }}
                          >
                            &#8250;
                          </span>
                        ) : source.url ? (
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="comp-view__wire-arrow"
                            aria-label={`Open ${source.name} article`}
                            onClick={(e) => e.stopPropagation()}
                          >
                            &#8250;
                          </a>
                        ) : null}
                      </div>

                      {/* Expanded X-Ray view */}
                      {isSourceExpanded && source.articleSummary && (
                        <div className="comp-view__xray-wrap">
                          <NarrativeXray
                            text={source.articleSummary}
                            framingRationale={source.lensData?.framingRationale}
                            leanRationale={source.lensData?.leanRationale}
                          />
                          {source.url && (
                            <a
                              href={source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="comp-view__expand-btn"
                              style={{ display: "inline-block", marginTop: "var(--space-2)" }}
                            >
                              Read full article &#8250;
                            </a>
                          )}
                        </div>
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
    </div>
  );
}
