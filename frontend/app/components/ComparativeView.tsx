"use client";

import { useMemo } from "react";
import type { StorySource } from "../lib/types";

/* ---------------------------------------------------------------------------
   ComparativeView — "Read All Sides"
   Groups sources into Left / Center / Right buckets and shows summaries
   side-by-side with word-level diff highlighting.

   Left:   politicalLean 0–40
   Center: politicalLean 41–60
   Right:  politicalLean 61–100
   --------------------------------------------------------------------------- */

interface ComparativeViewProps {
  sources: StorySource[];
  /** Pipeline-generated consensus points — what all sources agree on */
  consensusPoints?: string[];
  /** Pipeline-generated divergence points — where sources disagree */
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

interface BucketSource {
  source: StorySource;
  excerpt: string;
}

/** Tokenise text into lowercase words (letters only). */
function tokenise(text: string): string[] {
  return text.toLowerCase().match(/[a-z']+/g) ?? [];
}

/** Return which words are exclusive to `side` vs `others`. */
function exclusiveWords(side: string[], others: string[][]): Set<string> {
  const otherUnion = new Set(others.flat());
  const exclusive = new Set<string>();
  for (const w of side) {
    if (!otherUnion.has(w)) exclusive.add(w);
  }
  return exclusive;
}

interface HighlightedWord {
  word: string;
  /** "left" | "right" | null (shared/center) */
  highlight: "left" | "right" | null;
}

/**
 * Word-level diff: marks words unique to left sources in blue,
 * unique to right sources in red, and shared words as neutral.
 */
function diffWords(
  text: string,
  sideLabel: "Left" | "Center" | "Right",
  leftTexts: string[],
  rightTexts: string[],
): HighlightedWord[] {
  const words = text.split(/(\s+)/);
  const leftTokens = leftTexts.flatMap(tokenise);
  const rightTokens = rightTexts.flatMap(tokenise);
  const excLeft = exclusiveWords(leftTokens, [rightTokens]);
  const excRight = exclusiveWords(rightTokens, [leftTokens]);

  return words.map((chunk) => {
    // Preserve whitespace chunks verbatim
    if (/^\s+$/.test(chunk)) return { word: chunk, highlight: null };
    const lower = chunk.toLowerCase().replace(/[^a-z']/g, "");
    let highlight: "left" | "right" | null = null;
    if (sideLabel !== "Left" && excLeft.has(lower)) highlight = "left";
    if (sideLabel !== "Right" && excRight.has(lower)) highlight = "right";
    return { word: chunk, highlight };
  });
}

/** Get favicon URL from a source URL. */
function getFaviconUrl(url: string): string {
  try {
    const domain = new URL(url.startsWith("http") ? url : `https://${url}`).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return "";
  }
}

/** SVG icon for agreement/divergence points */
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

export default function ComparativeView({ sources, consensusPoints, divergencePoints }: ComparativeViewProps) {
  const buckets: Record<string, BucketSource[]> = useMemo(() => {
    const result: Record<string, BucketSource[]> = { Left: [], Center: [], Right: [] };
    for (const src of sources) {
      const lean = src.biasScores?.politicalLean ?? 50;
      // Use actual article content when available, fall back to structured metadata
      const excerpt = src.articleSummary
        ? src.articleSummary.slice(0, 300)
        : src.articleTitle
          ? src.articleTitle
          : `${src.name} coverage. Lean: ${lean}/100.`;
      if (lean <= 40) result.Left.push({ source: src, excerpt });
      else if (lean <= 60) result.Center.push({ source: src, excerpt });
      else result.Right.push({ source: src, excerpt });
    }
    return result;
  }, [sources]);

  // Collect texts per side for word-diff
  const leftTexts  = buckets.Left.map(b => b.excerpt);
  const rightTexts = buckets.Right.map(b => b.excerpt);

  // Extract key framing terms per lean side from rationale data.
  // These surface what vocabulary each perspective emphasizes.
  const keyTerms = useMemo(() => {
    const left = new Set<string>();
    const right = new Set<string>();
    for (const src of sources) {
      const rat = src.lensData?.leanRationale;
      if (!rat) continue;
      for (const kw of rat.topLeftKeywords ?? []) left.add(kw);
      for (const kw of rat.topRightKeywords ?? []) right.add(kw);
    }
    return {
      Left: [...left].slice(0, 4),
      Center: [] as string[],
      Right: [...right].slice(0, 4),
    };
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
      {/* Convergence & Divergence — embedded at top of All Sides */}
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

          return (
            <div key={bucket.label} className={`comp-view__col ${bucket.cssClass}`}>
              {/* Column header */}
              <div className="comp-view__col-header">
                <span className="comp-view__lean-label">{bucket.label}</span>
                <span className="comp-view__source-count text-data">
                  {items.length} {items.length === 1 ? "source" : "sources"}
                </span>
              </div>

              {/* Key framing terms — vocabulary this side emphasizes */}
              {keyTerms[bucket.label].length > 0 && (
                <div className="comp-view__key-terms">
                  {keyTerms[bucket.label].map((term) => (
                    <span key={term} className="comp-view__term">{term}</span>
                  ))}
                </div>
              )}

              {/* Source summaries */}
              <div className="comp-view__items">
                {items.map(({ source }, i) => {
                  const favicon = getFaviconUrl(source.url);
                  const lean = source.biasScores?.politicalLean ?? 50;
                  const rigor = source.biasScores?.factualRigor ?? 50;
                  const sensationalism = source.biasScores?.sensationalism ?? 30;
                  const opinionLabel = source.lensData?.opinionLabel ?? "Reporting";
                  const confidence = source.confidence ?? 0.5;

                  // Build diff-highlighted text from actual article content
                  const titleText = source.name;
                  const bodyText = source.articleSummary
                    ? source.articleSummary.slice(0, 300)
                    : source.articleTitle ?? `Coverage from ${source.name}`;
                  const highlighted = diffWords(bodyText, bucket.label, leftTexts, rightTexts);

                  return (
                    <article key={`${source.name}-${i}`} className="comp-view__item">
                      {/* Source meta */}
                      <div className="comp-view__item-meta">
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
                                // Remove the wrapper entirely to avoid gap
                                const wrap = e.currentTarget.parentElement;
                                if (wrap) wrap.style.display = "none";
                              }}
                            />
                          </span>
                        )}
                        <span className="comp-view__source-name text-data">{titleText}</span>
                        <span className="comp-view__lean-score text-data">
                          {lean}
                        </span>
                      </div>

                      {/* Source credibility signals — surfaces existing unused data */}
                      <div className="comp-view__signals">
                        <span className={`comp-view__type-badge comp-view__type-badge--${opinionLabel.toLowerCase()}`}>
                          {opinionLabel}
                        </span>
                        <span className="comp-view__rigor-bar" aria-label={`Factual rigor: ${rigor}/100`}>
                          <span className="comp-view__rigor-fill" style={{ width: `${rigor}%` }} />
                        </span>
                        <span className="comp-view__rigor-val text-data">{rigor}</span>
                        {sensationalism > 60 && (
                          <span className="comp-view__warn" title="High sensationalism detected" aria-label="High sensationalism">
                            <svg width="10" height="10" viewBox="0 0 10 10" fill="none" aria-hidden="true">
                              <path d="M5 1L9 9H1L5 1Z" stroke="var(--sense-high)" strokeWidth="1.2" fill="none"/>
                              <circle cx="5" cy="7" r="0.6" fill="var(--sense-high)"/>
                              <line x1="5" y1="4" x2="5" y2="6" stroke="var(--sense-high)" strokeWidth="1"/>
                            </svg>
                          </span>
                        )}
                      </div>

                      {/* Diff-highlighted body */}
                      <p className="comp-view__body">
                        {highlighted.map((hw, j) => {
                          if (hw.highlight === "left") {
                            return (
                              <mark key={j} className="comp-view__mark comp-view__mark--left">
                                {hw.word}
                              </mark>
                            );
                          }
                          if (hw.highlight === "right") {
                            return (
                              <mark key={j} className="comp-view__mark comp-view__mark--right">
                                {hw.word}
                              </mark>
                            );
                          }
                          return <span key={j}>{hw.word}</span>;
                        })}
                      </p>

                      {/* Read article link */}
                      <a
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="comp-view__read-link"
                        aria-label={`Read full article from ${source.name}`}
                      >
                        Read article
                        <span aria-hidden="true"> &#8594;</span>
                      </a>
                    </article>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Diff key */}
      <div className="comp-view__key" aria-label="Colour key">
        <span className="comp-view__key-item">
          <mark className="comp-view__mark comp-view__mark--left">Blue</mark> words unique to left sources
        </span>
        <span className="comp-view__key-item">
          <mark className="comp-view__mark comp-view__mark--right">Red</mark> words unique to right sources
        </span>
      </div>
    </div>
  );
}
