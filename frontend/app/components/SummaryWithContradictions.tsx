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

export default function SummaryWithContradictions({
  summary,
  disputed,
}: {
  summary: string;
  disputed?: DisputedClaim[];
}): React.ReactNode {
  if (!disputed?.length || !summary) return summary;

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

  if (targets.length === 0) return summary;

  const matches: { start: number; end: number; dispute: DisputedClaim; text: string }[] = [];
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

  if (matches.length === 0) return summary;
  matches.sort((a, b) => a.start - b.start);

  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  for (let i = 0; i < matches.length; i++) {
    const m = matches[i];
    if (cursor < m.start) nodes.push(summary.slice(cursor, m.start));
    nodes.push(<ClaimMark key={`cm-${i}`} text={m.text} disputed={m.dispute} />);
    cursor = m.end;
  }
  if (cursor < summary.length) nodes.push(summary.slice(cursor));
  return <>{nodes}</>;
}
