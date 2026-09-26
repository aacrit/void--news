"use client";

import { useMemo, useState } from "react";
import type { StorySource } from "../lib/types";
import { leanToBucket } from "../lib/biasColors";

/* ---------------------------------------------------------------------------
   ComparativeView — "Read All Sides"
   Groups sources into Left / Center / Right buckets. The three columns are
   the Bench's seven rungs folded (leanToBucket), so a source can never sit
   in a different place here than it does in the chart above it: Left used to
   be "lean <= 40", which put a centre-left outlet under Left in this list
   and in the centre-left column of the Bench. Unmeasured articles carry a
   stored 50 and are held out, as the Bench holds them out.
   Clean layout: source logo + first 2 headlines per bucket.
   --------------------------------------------------------------------------- */

interface ComparativeViewProps {
  sources: StorySource[];
  consensusPoints?: string[];
  divergencePoints?: string[];
  /** Suppress the embedded "Key agreements & disagreements" disclosure. Set
   *  true where the shared SpreadDisagreement panel already surfaces the same
   *  consensus/divergence up top, so this deeper "read all sides" view doesn't
   *  restate it. Defaults false (standalone callers keep the disclosure). */
  hideInsights?: boolean;
}

interface LeanBucket {
  label: "Left" | "Center" | "Right";
  cssClass: string;
  /** The rungs this column folds, printed under its label. */
  range: string;
}

const BUCKETS: LeanBucket[] = [
  { label: "Left",   cssClass: "comp-view__col--left",   range: "Far left to center-left" },
  { label: "Center", cssClass: "comp-view__col--center", range: "Center only" },
  { label: "Right",  cssClass: "comp-view__col--right",  range: "Center-right to far right" },
];

/** A syndicated headline often ends with its own masthead ("... - Outlook
 *  India"). The row already names the outlet, so the suffix is dropped when,
 *  and only when, it is that outlet's name. */
function stripOutletSuffix(title: string, outlet: string): string {
  const t = title.trim();
  const o = outlet.trim().toLowerCase();
  if (!o) return t;
  const m = t.match(/^(.*\S)\s+[-|:]\s+([^-|:]+)$/);
  if (m && m[2].trim().toLowerCase() === o) return m[1];
  return t;
}

function getFaviconUrl(_url: string): string {
  // Privacy: never call an external favicon service. Fetching a third-party
  // favicon would leak the reader's IP and which publisher they are viewing to
  // that host. The wire-ticker shows the full source name, so no logo is shown
  // when this returns empty.
  return "";
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

export default function ComparativeView({ sources, consensusPoints, divergencePoints, hideInsights = false }: ComparativeViewProps) {
  const [expandedBuckets, setExpandedBuckets] = useState<Record<string, boolean>>({});
  const [showInsights, setShowInsights] = useState(false);

  const { buckets, unmeasured } = useMemo(() => {
    const result: Record<string, StorySource[]> = { Left: [], Center: [], Right: [] };
    let held = 0;
    for (const src of sources) {
      const lean = src.biasScores?.politicalLean;
      if (src.leanUnscored || typeof lean !== "number") { held++; continue; }
      const rung = leanToBucket(lean);
      if (rung === "center") result.Center.push(src);
      else if (rung.endsWith("left")) result.Left.push(src);
      else result.Right.push(src);
    }
    return { buckets: result, unmeasured: held };
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
                <span className="comp-view__range text-data">{bucket.range}</span>
              </div>

              {/* Source list — compact wire-ticker: logo + name + summary + arrow, all inline */}
              <div className="comp-view__items">
                {visibleItems.map((source, i) => {
                  const favicon = getFaviconUrl(source.url);
                  const title = stripOutletSuffix(source.articleTitle || source.name, source.name);

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
      {unmeasured > 0 && (
        <p className="comp-view__unmeasured text-data">
          {unmeasured} {unmeasured === 1 ? "source" : "sources"} not measured, so not placed
        </p>
      )}

      {/* Convergence & Divergence — collapsed by default, below the grid.
          Suppressed when the SpreadDisagreement panel already shows this up top. */}
      {!hideInsights && (hasConsensus || hasDivergence) && (
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
                        <li key={i}>{typeof pt === "string" ? pt : String(pt)}</li>
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
                        <li key={i}>{typeof pt === "string" ? pt : String(pt)}</li>
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
