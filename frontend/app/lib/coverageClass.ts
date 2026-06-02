import type { Story } from "./types";

export interface CoverageVerdict {
  label: string;
  tone: "single" | "neutral";
}

/**
 * Returns the source-count line for a story card.
 *
 * v3 (2026-05-14): the multi-source "N sources" label is removed. The
 * Sigil already visualizes source count (ring + central number), so
 * repeating "23 sources" below each card was redundant noise that the
 * CEO flagged as cluttering the card meta row.
 *
 * The "single report" flag is preserved — a 1-source cluster is
 * editorially meaningful (op-eds, unverified breaking stories) and not
 * derivable from the Sigil's ring alone. This is the only state that
 * still returns a verdict.
 *
 * Multi-source (count >= 2): return null. The Sigil carries the signal.
 */
export function classifyCoverage(story: Story): CoverageVerdict | null {
  const count = story.source.count ?? 0;
  if (count < 1) return null;

  if (count === 1) {
    return { label: "single report", tone: "single" };
  }

  return null;
}
