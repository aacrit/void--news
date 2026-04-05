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

/** Extract a set of unique words (lowercased, 4+ characters) from text. */
function extractWords(text: string): Set<string> {
  const words = text
    .toLowerCase()
    .replace(/[^a-z\s'-]/g, "")
    .split(/\s+/)
    .filter((w) => w.length >= 4);
  return new Set(words);
}

/** Find words unique to textA that are absent from textB. */
function findUniqueWords(textA: string, textB: string): Set<string> {
  const wordsA = extractWords(textA);
  const wordsB = extractWords(textB);
  const unique = new Set<string>();
  wordsA.forEach((w) => {
    if (!wordsB.has(w)) unique.add(w);
  });
  return unique;
}

/** Highlight unique words in a text, wrapping them in spans. */
function highlightText(
  text: string,
  uniqueWords: Set<string>,
  colorClass: string
): React.ReactNode[] {
  // Split on word boundaries but keep the separators
  const parts = text.split(/(\s+)/);
  return parts.map((part, i) => {
    const clean = part.toLowerCase().replace(/[^a-z'-]/g, "");
    if (uniqueWords.has(clean)) {
      return (
        <span key={i} className={`hist-vocab-unique ${colorClass}`}>
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
