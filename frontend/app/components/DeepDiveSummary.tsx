"use client";

import type { DisputedClaim } from "../lib/types";
import { summaryParagraphs } from "../lib/summaryParagraphs";
import { findDisputeMatches, markRange } from "./SummaryWithContradictions";

/* ---------------------------------------------------------------------------
   DeepDiveSummary: "The Story", set as a lede and paragraphs at a reading
   measure, with disputed claims marked. One component for the three Deep Dive
   shells, which each printed the summary as a single <p> (audit 2026-09-26,
   finding 7). The split never changes the text (lib/summaryParagraphs.ts) and
   never cuts a disputed-claim mark across two paragraphs.
   --------------------------------------------------------------------------- */

export default function DeepDiveSummary({
  summary,
  disputed,
}: {
  summary: string;
  disputed?: DisputedClaim[];
}) {
  const matches = findDisputeMatches(summary, disputed);
  const { paragraphs, offsets } = summaryParagraphs(
    summary,
    matches.map((m) => ({ start: m.start, end: m.end })),
  );
  return (
    <div className="dd-summary">
      {paragraphs.map((p, i) => {
        const from = offsets[i];
        const to = from + p.length;
        return (
          <p key={i} className={i === 0 ? "dd-summary__lede" : undefined}>
            {markRange(summary, matches, from, to, `${i}-`)}
          </p>
        );
      })}
    </div>
  );
}
