"use client";

import { useMemo } from "react";
import type { Perspective } from "../types";

/* ===========================================================================
   PerspectiveComparison — Split-screen comparison of two perspectives
   Side by side on desktop, stacked on mobile. Vocabulary difference
   highlighting: unique words underlined in perspective colors.
   =========================================================================== */

interface PerspectiveComparisonProps {
  perspectiveA: Perspective;
  perspectiveB: Perspective;
}

/** Common English stop words to exclude from vocabulary highlighting. */
const STOP_WORDS = new Set([
  "about", "after", "again", "against", "almost", "along", "already", "also",
  "always", "among", "another", "around", "because", "become", "before",
  "began", "begin", "behind", "being", "below", "between", "beyond", "both",
  "bring", "brought", "called", "change", "could", "different", "does",
  "doing", "during", "each", "early", "either", "enough", "even", "every",
  "example", "first", "follow", "found", "from", "further", "given", "going",
  "great", "have", "having", "here", "however", "include", "including",
  "into", "just", "keep", "known", "large", "last", "later", "least",
  "leave", "left", "less", "like", "likely", "little", "long", "made",
  "make", "making", "many", "might", "more", "most", "much", "must",
  "need", "never", "next", "number", "often", "once", "only", "open",
  "order", "other", "over", "part", "people", "place", "point", "possible",
  "rather", "right", "said", "same", "several", "should", "show", "side",
  "since", "small", "some", "something", "still", "such", "take", "taken",
  "than", "that", "their", "them", "then", "there", "these", "they",
  "thing", "this", "those", "though", "thought", "three", "through",
  "time", "together", "under", "until", "upon", "used", "using", "very",
  "want", "well", "were", "what", "when", "where", "which", "while",
  "whole", "will", "with", "within", "without", "would", "year", "years",
]);

/** Extract a map of words (lowercased, 6+ characters, no stop words) to
 *  their frequency in the text. */
function extractWordCounts(text: string): Map<string, number> {
  const counts = new Map<string, number>();
  const words = text
    .toLowerCase()
    .replace(/[^a-z\s'-]/g, "")
    .split(/\s+/)
    .filter((w) => w.length >= 6 && !STOP_WORDS.has(w));
  for (const w of words) {
    counts.set(w, (counts.get(w) ?? 0) + 1);
  }
  return counts;
}

/** Find at most 10 distinctive words in textA that are absent from textB,
 *  ranked by frequency in textA (most repeated = most characteristic). */
function findUniqueWords(textA: string, textB: string): Set<string> {
  const countsA = extractWordCounts(textA);
  const wordsB = new Set(
    textB
      .toLowerCase()
      .replace(/[^a-z\s'-]/g, "")
      .split(/\s+/)
  );
  const candidates: [string, number][] = [];
  countsA.forEach((count, word) => {
    if (!wordsB.has(word)) candidates.push([word, count]);
  });
  /* Sort by frequency descending, then alphabetically for stability */
  candidates.sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]));
  return new Set(candidates.slice(0, 10).map(([w]) => w));
}

/** Highlight unique words in a text, wrapping them in spans.
 *  Stagger delay on each unique word for cascading highlight reveal. */
function highlightText(
  text: string,
  uniqueWords: Set<string>,
  colorClass: string
): React.ReactNode[] {
  // Split on word boundaries but keep the separators
  const parts = text.split(/(\s+)/);
  let uniqueIdx = 0;
  return parts.map((part, i) => {
    const clean = part.toLowerCase().replace(/[^a-z'-]/g, "");
    if (uniqueWords.has(clean)) {
      const delay = uniqueIdx * 30;
      uniqueIdx++;
      return (
        <span
          key={i}
          className={`hist-vocab-unique hist-vocab-stagger ${colorClass}`}
          style={{ animationDelay: `${delay}ms` }}
        >
          {part}
        </span>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export default function PerspectiveComparison({
  perspectiveA,
  perspectiveB,
}: PerspectiveComparisonProps) {
  const uniqueToA = useMemo(
    () => findUniqueWords(perspectiveA.narrative, perspectiveB.narrative),
    [perspectiveA.narrative, perspectiveB.narrative]
  );

  const uniqueToB = useMemo(
    () => findUniqueWords(perspectiveB.narrative, perspectiveA.narrative),
    [perspectiveA.narrative, perspectiveB.narrative]
  );

  return (
    <div className="hist-comparison" role="region" aria-label="Perspective comparison">
      {/* Panel A */}
      <div className="hist-comparison__panel">
        <div
          className="hist-comparison__header"
          style={{ borderBottomColor: `var(--hist-persp-${perspectiveA.color})` }}
        >
          {perspectiveA.viewpointName}
        </div>
        <div className="hist-comparison__text">
          {highlightText(
            perspectiveA.narrative,
            uniqueToA,
            `hist-vocab-unique--${perspectiveA.color}`
          )}
        </div>
      </div>

      {/* Divider */}
      <div className="hist-comparison__divider" aria-hidden="true">
        <div className="hist-comparison__divider-handle" />
      </div>

      {/* Panel B */}
      <div className="hist-comparison__panel">
        <div
          className="hist-comparison__header"
          style={{ borderBottomColor: `var(--hist-persp-${perspectiveB.color})` }}
        >
          {perspectiveB.viewpointName}
        </div>
        <div className="hist-comparison__text">
          {highlightText(
            perspectiveB.narrative,
            uniqueToB,
            `hist-vocab-unique--${perspectiveB.color}`
          )}
        </div>
      </div>
    </div>
  );
}
