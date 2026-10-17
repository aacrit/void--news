"use client";

import type { DisputedClaim } from "../lib/types";
import ClaimMark from "./ClaimMark";

/* ===========================================================================
   SummaryWithContradictions — void --verify
   Inline disputed-claim highlighting for the Deep Dive summary text.

   Scans the summary for phrases that match either side of a disputed claim and
   wraps each match in a <ClaimMark> (wavy underline + hover popover showing both
   versions). Falls back to the plain summary string when there is nothing to
   highlight. Ported verbatim out of DeepDive.tsx so it survives that modal's
   eventual deletion. Reuses the .claim-mark* classes from the globally-imported
   components.css (unchanged).
   =========================================================================== */

export interface DisputeMatch {
  start: number;
  end: number;
  dispute: DisputedClaim;
  text: string;
}

/** Where each disputed claim's phrase sits in the summary, first match only,
 *  no overlaps, sorted. Offsets are into `summary` as given. */
export function findDisputeMatches(summary: string, disputed?: DisputedClaim[]): DisputeMatch[] {
  if (!disputed?.length || !summary) return [];

  const targets: { phrase: string; dispute: DisputedClaim }[] = [];
  for (const d of disputed) {
    for (const version of [d.version_a, d.version_b]) {
      if (!version) continue;
      const phrases = version.split(/[.!?]+/).map((s) => s.trim()).filter((s) => s.length >= 12);
      for (const phrase of phrases) {
        if (summary.toLowerCase().includes(phrase.toLowerCase())) {
          targets.push({ phrase, dispute: d });
        }
      }
    }
    if (d.topic && d.topic.length >= 8 && summary.toLowerCase().includes(d.topic.toLowerCase())) {
      if (!targets.some((t) => t.dispute === d)) {
        targets.push({ phrase: d.topic, dispute: d });
      }
    }
  }

  const matches: DisputeMatch[] = [];
  const lower = summary.toLowerCase();
  for (const { phrase, dispute } of targets) {
    const idx = lower.indexOf(phrase.toLowerCase());
    if (idx >= 0) {
      const overlaps = matches.some(
        (m) => (idx >= m.start && idx < m.end) || (idx + phrase.length > m.start && idx + phrase.length <= m.end),
      );
      if (!overlaps) {
        matches.push({ start: idx, end: idx + phrase.length, dispute, text: summary.slice(idx, idx + phrase.length) });
      }
    }
  }
  return matches.sort((a, b) => a.start - b.start);
}

/** The text between `from` and `to` of `summary`, with every match inside it
 *  wrapped in a ClaimMark. */
export function markRange(summary: string, matches: DisputeMatch[], from: number, to: number, keyPrefix = ""): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  let cursor = from;
  matches.forEach((m, i) => {
    if (m.start < from || m.end > to) return;
    if (cursor < m.start) nodes.push(summary.slice(cursor, m.start));
    nodes.push(<ClaimMark key={`cm-${keyPrefix}${i}`} text={m.text} disputed={m.dispute} />);
    cursor = m.end;
  });
  if (cursor < to) nodes.push(summary.slice(cursor, to));
  return nodes;
}

export default function SummaryWithContradictions({
  summary,
  disputed,
}: {
  summary: string;
  disputed?: DisputedClaim[];
}): React.ReactNode {
  const matches = findDisputeMatches(summary, disputed);
  if (matches.length === 0) return summary;
  return <>{markRange(summary, matches, 0, summary.length)}</>;
}
