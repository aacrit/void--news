import type { Story } from "./types";

export interface CoverageVerdict {
  label: string;
  tone: "single" | "neutral";
}

/**
 * Returns the source-count line for a story card.
 *
 * Used to be a 5-bucket editorial classifier ("left-right split",
 * "center-weighted", "in agreement"…) appended to the count. Removed
 * 2026-04-29: the Sigil already encodes lean (color), divergence (ring
 * class), and consensus visually — adding text classification on the
 * card violated `feedback_bias_indicator_priorities.md` (Sigil is the
 * brand mark; secondary axes belong in Deep Dive). The full breakdown
 * remains available in DeepDive's SixLenses + ComparativeView.
 *
 * Returns just `"N sources"` (or `"single report"` for 1-source clusters
 * since "1 source" is editorially meaningful — flags op-eds and
 * unverified reporting).
 */
export function classifyCoverage(story: Story): CoverageVerdict | null {
  const count = story.source.count ?? 0;
  if (count < 1) return null;

  if (count === 1) {
    return { label: "single report", tone: "single" };
  }

  const noun = count === 1 ? "source" : "sources";
  return { label: `${count} ${noun}`, tone: "neutral" };
}
