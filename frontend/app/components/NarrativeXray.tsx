"use client";

import { useState, useMemo, useCallback, Fragment } from "react";
import type { FramingRationale, LeanRationale, ChargedMatch } from "../lib/types";

/* ---------------------------------------------------------------------------
   NarrativeXray — Per-sentence framing highlights
   Reveals charged synonyms, entity sentiment, and omissions inline.
   Progressive disclosure: count badge toggles highlights on/off.

   Uses cinematographer's `.nx-*` class system for staggered rack-focus
   reveal animation. Highlights resolve top-to-bottom when badge is toggled.
   --------------------------------------------------------------------------- */

interface NarrativeXrayProps {
  /** Article excerpt/summary text to annotate */
  text: string;
  /** Framing rationale with chargedMatches, entitiesFound/Missing */
  framingRationale?: FramingRationale;
  /** Lean rationale with entitySentiments */
  leanRationale?: LeanRationale;
}

/* --- SVG Icons ------------------------------------------------------------- */

function XrayIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="11" cy="11" r="7" />
      <line x1="16" y1="16" x2="21" y2="21" />
      <line x1="5.5" y1="5.5" x2="3.5" y2="3.5" />
      <line x1="4" y1="8" x2="2" y2="7.2" />
      <line x1="7.8" y1="4.2" x2="7" y2="2" />
    </svg>
  );
}

/* --- Tooltip sub-components ------------------------------------------------ */

interface ChargedSpanProps {
  text: string;
  match: ChargedMatch;
  index: number;
  active: boolean;
}

function ChargedSpan({ text, match, index, active }: ChargedSpanProps) {
  const [showTip, setShowTip] = useState(false);

  const toggle = useCallback(() => setShowTip((p) => !p), []);

  return (
    <span
      className="nx-highlight"
      style={{ "--nx-index": index } as React.CSSProperties}
      onClick={active ? toggle : undefined}
      onMouseEnter={active ? () => setShowTip(true) : undefined}
      onMouseLeave={active ? () => setShowTip(false) : undefined}
      tabIndex={active ? 0 : undefined}
      role={active ? "button" : undefined}
      onFocus={active ? () => setShowTip(true) : undefined}
      onBlur={active ? () => setShowTip(false) : undefined}
    >
      {text}
      {active && showTip && (
        <span className="nx-tooltip">
          <span className="nx-tooltip__label">Charged synonym</span>
          <span className="nx-tooltip__value">
            Neutral: {match.neutral}
          </span>
        </span>
      )}
    </span>
  );
}

interface EntitySpanProps {
  text: string;
  sentiment: number;
  index: number;
  active: boolean;
}

function EntitySpan({ text, sentiment, index, active }: EntitySpanProps) {
  const [showTip, setShowTip] = useState(false);
  const polarity = sentiment > 0.05 ? "warm" : sentiment < -0.05 ? "cool" : null;

  const toggle = useCallback(() => setShowTip((p) => !p), []);

  if (!polarity) return <>{text}</>;

  return (
    <span
      className={`nx-entity nx-entity--${polarity}`}
      style={{ "--nx-index": index } as React.CSSProperties}
      onClick={active ? toggle : undefined}
      onMouseEnter={active ? () => setShowTip(true) : undefined}
      onMouseLeave={active ? () => setShowTip(false) : undefined}
      tabIndex={active ? 0 : undefined}
      role={active ? "button" : undefined}
      onFocus={active ? () => setShowTip(true) : undefined}
      onBlur={active ? () => setShowTip(false) : undefined}
    >
      {text}
      {active && showTip && (
        <span className="nx-tooltip">
          <span className="nx-tooltip__label">Entity sentiment</span>
          <span className="nx-tooltip__value">
            {polarity === "warm" ? "Positive" : "Negative"} ({sentiment > 0 ? "+" : ""}{sentiment.toFixed(2)})
          </span>
        </span>
      )}
    </span>
  );
}

/* --- Build annotated text segments ----------------------------------------- */

interface Segment {
  text: string;
  type: "plain" | "charged" | "entity";
  match?: ChargedMatch;
  sentiment?: number;
  /** Global highlight index for stagger animation */
  highlightIndex?: number;
}

function buildSegments(
  text: string,
  chargedMatches: ChargedMatch[],
  entitySentiments: Record<string, number>,
): Segment[] {
  if (!text) return [];

  const annotations: Array<{
    start: number;
    end: number;
    type: "charged" | "entity";
    match?: ChargedMatch;
    sentiment?: number;
  }> = [];

  const textLower = text.toLowerCase();

  for (const match of chargedMatches) {
    const term = match.charged.toLowerCase();
    let searchFrom = 0;
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const idx = textLower.indexOf(term, searchFrom);
      if (idx === -1) break;
      if (!term.includes(" ")) {
        const before = idx > 0 ? textLower[idx - 1] : " ";
        const after = idx + term.length < textLower.length ? textLower[idx + term.length] : " ";
        if (/\w/.test(before) || /\w/.test(after)) {
          searchFrom = idx + 1;
          continue;
        }
      }
      annotations.push({ start: idx, end: idx + term.length, type: "charged", match });
      searchFrom = idx + term.length;
    }
  }

  for (const [entity, sentiment] of Object.entries(entitySentiments)) {
    if (Math.abs(sentiment) <= 0.05) continue;
    const entityLower = entity.toLowerCase();
    let searchFrom = 0;
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const idx = textLower.indexOf(entityLower, searchFrom);
      if (idx === -1) break;
      annotations.push({ start: idx, end: idx + entity.length, type: "entity", sentiment });
      searchFrom = idx + entity.length;
    }
  }

  if (annotations.length === 0) return [{ text, type: "plain" }];

  annotations.sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start));

  const filtered: typeof annotations = [];
  let lastEnd = 0;
  for (const ann of annotations) {
    if (ann.start >= lastEnd) {
      filtered.push(ann);
      lastEnd = ann.end;
    }
  }

  const segments: Segment[] = [];
  let cursor = 0;
  let highlightIdx = 0;

  for (const ann of filtered) {
    if (ann.start > cursor) {
      segments.push({ text: text.slice(cursor, ann.start), type: "plain" });
    }
    segments.push({
      text: text.slice(ann.start, ann.end),
      type: ann.type,
      match: ann.match,
      sentiment: ann.sentiment,
      highlightIndex: highlightIdx++,
    });
    cursor = ann.end;
  }

  if (cursor < text.length) {
    segments.push({ text: text.slice(cursor), type: "plain" });
  }

  return segments;
}

/* --- Main Component -------------------------------------------------------- */

export default function NarrativeXray({ text, framingRationale, leanRationale }: NarrativeXrayProps) {
  const [highlightsOn, setHighlightsOn] = useState(false);

  const chargedMatches = framingRationale?.chargedMatches ?? [];
  const entitiesFound = framingRationale?.entitiesFound ?? [];
  const entitiesMissing = framingRationale?.entitiesMissing ?? [];
  const entitySentiments = leanRationale?.entitySentiments ?? {};

  const signalCount = useMemo(() => {
    let count = 0;
    for (const m of chargedMatches) count += m.count;
    for (const s of Object.values(entitySentiments)) {
      if (Math.abs(s) > 0.05) count++;
    }
    return count;
  }, [chargedMatches, entitySentiments]);

  const hasOmissions = entitiesMissing.length > 0 && entitiesFound.length > 0;
  const totalEntities = entitiesFound.length + entitiesMissing.length;

  // Memoize segment computation — O(n*m) string scanning should not re-run
  // when parent re-renders without prop changes (e.g., sibling source expand).
  const segments = useMemo(
    () => buildSegments(text, chargedMatches, entitySentiments),
    [text, chargedMatches, entitySentiments],
  );

  const totalHighlights = segments.filter((s) => s.type !== "plain").length;

  if (signalCount === 0 && !hasOmissions) return null;

  return (
    <div
      className={highlightsOn ? "nx-active" : ""}
      style={{ "--nx-total-highlights": totalHighlights } as React.CSSProperties}
    >
      {/* Omission Banner — clip-path wipe entrance when active */}
      {hasOmissions && (
        <div className="nx-omission-banner" role="status">
          <div className="nx-omission-banner__headline">
            Covers {entitiesFound.length} of {totalEntities} key entities
          </div>
          <div className="nx-omission-banner__entities">
            Missing: {entitiesMissing.slice(0, 5).join(", ")}
            {entitiesMissing.length > 5 && ` +${entitiesMissing.length - 5} more`}
          </div>
        </div>
      )}

      {/* Count Badge — toggles .nx-active on wrapper */}
      {signalCount > 0 && (
        <button
          className={`nx-badge${highlightsOn ? " nx-badge--active" : ""}`}
          onClick={() => setHighlightsOn((prev) => !prev)}
          type="button"
          aria-pressed={highlightsOn}
          aria-label={`${signalCount} framing signals. ${highlightsOn ? "Hide" : "Show"} highlights.`}
        >
          <XrayIcon className="nx-badge__icon" />
          <span className="nx-badge__count">{signalCount}</span>
          <span className="nx-badge__label">
            framing signal{signalCount !== 1 ? "s" : ""}
          </span>
        </button>
      )}

      {/* Annotated Text — highlights stagger-resolve when .nx-active */}
      <p className="nx-source-body">
        {segments.map((seg, i) => {
          if (seg.type === "charged" && seg.match) {
            return (
              <ChargedSpan
                key={i}
                text={seg.text}
                match={seg.match}
                index={seg.highlightIndex ?? 0}
                active={highlightsOn}
              />
            );
          }
          if (seg.type === "entity" && seg.sentiment !== undefined) {
            return (
              <EntitySpan
                key={i}
                text={seg.text}
                sentiment={seg.sentiment}
                index={seg.highlightIndex ?? 0}
                active={highlightsOn}
              />
            );
          }
          return <Fragment key={i}>{seg.text}</Fragment>;
        })}
      </p>
    </div>
  );
}
