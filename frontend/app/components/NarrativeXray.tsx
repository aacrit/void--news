"use client";

import { useState, useMemo, useCallback, Fragment } from "react";
import type { FramingRationale, LeanRationale, ChargedMatch } from "../lib/types";

/* ---------------------------------------------------------------------------
   NarrativeXray — Per-sentence framing highlights
   Reveals charged synonyms, entity sentiment, and omissions inline.
   Progressive disclosure: count badge toggles highlights on/off.
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
    <svg className={className} width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <circle cx="6" cy="6" r="5" stroke="currentColor" strokeWidth="1.2" fill="none" />
      <path d="M4 6h4M6 4v4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}

function OmissionIcon({ className }: { className?: string }) {
  return (
    <svg className={className} width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
      <rect x="1.5" y="1.5" width="11" height="11" rx="1.5" stroke="currentColor" strokeWidth="1.2" fill="none" strokeDasharray="2 2" />
      <path d="M5 7h4" stroke="currentColor" strokeWidth="1.2" strokeLinecap="round" />
    </svg>
  );
}

/* --- Intensity Dots -------------------------------------------------------- */

function IntensityDots({ level }: { level: number }) {
  return (
    <span className="xray__tip-intensity" aria-label={`Intensity ${level} of 3`}>
      {[1, 2, 3].map((i) => (
        <span
          key={i}
          className={`xray__tip-intensity-dot${i <= level ? " xray__tip-intensity-dot--filled" : ""}`}
        />
      ))}
    </span>
  );
}

/* --- Highlight a single charged match inline ------------------------------- */

interface ChargedSpanProps {
  text: string;
  match: ChargedMatch;
  showTooltips: boolean;
}

function ChargedSpan({ text, match, showTooltips }: ChargedSpanProps) {
  const [tapped, setTapped] = useState(false);

  const handleClick = useCallback(() => {
    if (showTooltips) setTapped((prev) => !prev);
  }, [showTooltips]);

  if (!showTooltips) return <>{text}</>;

  return (
    <span
      className="xray__charged"
      onClick={handleClick}
      tabIndex={0}
      role="button"
      aria-describedby={undefined}
    >
      {text}
      <span className={`xray__tip${tapped ? " xray__tip--visible" : ""}`}>
        <span className="xray__tip-label">Charged synonym</span>
        Neutral: <span className="xray__tip-neutral">{match.neutral}</span>
        <IntensityDots level={match.intensity} />
      </span>
    </span>
  );
}

/* --- Highlight a single entity with sentiment ------------------------------ */

interface EntitySpanProps {
  text: string;
  sentiment: number;
  showTooltips: boolean;
}

function EntitySpan({ text, sentiment, showTooltips }: EntitySpanProps) {
  const [tapped, setTapped] = useState(false);
  const polarity = sentiment > 0.05 ? "pos" : sentiment < -0.05 ? "neg" : null;

  const handleClick = useCallback(() => {
    if (showTooltips) setTapped((prev) => !prev);
  }, [showTooltips]);

  if (!showTooltips || !polarity) return <>{text}</>;

  const label = polarity === "pos" ? "Positive framing" : "Negative framing";

  return (
    <span
      className={`xray__entity xray__entity--${polarity}`}
      onClick={handleClick}
      tabIndex={0}
      role="button"
    >
      {text}
      <span className={`xray__tip${tapped ? " xray__tip--visible" : ""}`}>
        <span className="xray__tip-label">Entity sentiment</span>
        {label} ({sentiment > 0 ? "+" : ""}{sentiment.toFixed(2)})
      </span>
    </span>
  );
}

/* --- Build annotated text segments ----------------------------------------- */

interface Segment {
  text: string;
  type: "plain" | "charged" | "entity";
  match?: ChargedMatch;
  sentiment?: number;
}

function buildSegments(
  text: string,
  chargedMatches: ChargedMatch[],
  entitySentiments: Record<string, number>,
): Segment[] {
  if (!text) return [];

  // Build a list of all matches with their positions
  const annotations: Array<{
    start: number;
    end: number;
    type: "charged" | "entity";
    match?: ChargedMatch;
    sentiment?: number;
  }> = [];

  const textLower = text.toLowerCase();

  // Find charged synonym positions
  for (const match of chargedMatches) {
    const term = match.charged.toLowerCase();
    let searchFrom = 0;
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const idx = textLower.indexOf(term, searchFrom);
      if (idx === -1) break;
      // Word boundary check for single-word terms
      if (!term.includes(" ")) {
        const before = idx > 0 ? textLower[idx - 1] : " ";
        const after = idx + term.length < textLower.length ? textLower[idx + term.length] : " ";
        if (/\w/.test(before) || /\w/.test(after)) {
          searchFrom = idx + 1;
          continue;
        }
      }
      annotations.push({
        start: idx,
        end: idx + term.length,
        type: "charged",
        match,
      });
      searchFrom = idx + term.length;
    }
  }

  // Find entity positions
  for (const [entity, sentiment] of Object.entries(entitySentiments)) {
    if (Math.abs(sentiment) <= 0.05) continue; // Skip near-neutral
    const entityLower = entity.toLowerCase();
    let searchFrom = 0;
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const idx = textLower.indexOf(entityLower, searchFrom);
      if (idx === -1) break;
      annotations.push({
        start: idx,
        end: idx + entity.length,
        type: "entity",
        sentiment,
      });
      searchFrom = idx + entity.length;
    }
  }

  if (annotations.length === 0) {
    return [{ text, type: "plain" }];
  }

  // Sort by position, longer matches first for overlaps
  annotations.sort((a, b) => a.start - b.start || (b.end - b.start) - (a.end - a.start));

  // Remove overlapping annotations (keep first/longest)
  const filtered: typeof annotations = [];
  let lastEnd = 0;
  for (const ann of annotations) {
    if (ann.start >= lastEnd) {
      filtered.push(ann);
      lastEnd = ann.end;
    }
  }

  // Build segments
  const segments: Segment[] = [];
  let cursor = 0;

  for (const ann of filtered) {
    if (ann.start > cursor) {
      segments.push({ text: text.slice(cursor, ann.start), type: "plain" });
    }
    segments.push({
      text: text.slice(ann.start, ann.end),
      type: ann.type,
      match: ann.match,
      sentiment: ann.sentiment,
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

  // Count total signals for the badge
  const signalCount = useMemo(() => {
    let count = 0;
    for (const m of chargedMatches) count += m.count;
    // Count entities with non-neutral sentiment
    for (const s of Object.values(entitySentiments)) {
      if (Math.abs(s) > 0.05) count++;
    }
    return count;
  }, [chargedMatches, entitySentiments]);

  const hasOmissions = entitiesMissing.length > 0 && entitiesFound.length > 0;
  const totalEntities = entitiesFound.length + entitiesMissing.length;

  // Don't render if no signals at all
  if (signalCount === 0 && !hasOmissions) return null;

  const segments = buildSegments(
    text,
    highlightsOn ? chargedMatches : [],
    highlightsOn ? entitySentiments : {},
  );

  return (
    <div className="xray">
      {/* Omission Banner */}
      {hasOmissions && (
        <div className="xray__omission" role="status">
          <OmissionIcon className="xray__omission-icon" />
          <span>
            <span className="xray__omission-stat">
              Covers {entitiesFound.length} of {totalEntities} key entities.
            </span>
            {" "}
            <span className="xray__omission-missing">
              Missing: {entitiesMissing.slice(0, 5).join(", ")}
              {entitiesMissing.length > 5 && ` +${entitiesMissing.length - 5} more`}
            </span>
          </span>
        </div>
      )}

      {/* Count Badge Toggle */}
      {signalCount > 0 && (
        <button
          className={`xray__badge${highlightsOn ? " xray__badge--active" : ""}`}
          onClick={() => setHighlightsOn((prev) => !prev)}
          type="button"
          aria-pressed={highlightsOn}
          aria-label={`${signalCount} framing signals. ${highlightsOn ? "Hide" : "Show"} highlights.`}
        >
          <XrayIcon className="xray__badge-icon" />
          {signalCount} framing signal{signalCount !== 1 ? "s" : ""}
        </button>
      )}

      {/* Annotated Text */}
      <p className="xray__text">
        {segments.map((seg, i) => {
          if (seg.type === "charged" && seg.match) {
            return (
              <ChargedSpan
                key={i}
                text={seg.text}
                match={seg.match}
                showTooltips={highlightsOn}
              />
            );
          }
          if (seg.type === "entity" && seg.sentiment !== undefined) {
            return (
              <EntitySpan
                key={i}
                text={seg.text}
                sentiment={seg.sentiment}
                showTooltips={highlightsOn}
              />
            );
          }
          return <Fragment key={i}>{seg.text}</Fragment>;
        })}
      </p>
    </div>
  );
}
