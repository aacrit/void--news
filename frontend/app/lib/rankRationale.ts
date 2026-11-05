import type { Story } from "./types";

/**
 * Client-side derivation of the top signals that pushed a story to the top.
 * Pipeline-authoritative component scores are not yet persisted, so we
 * infer the salient contributions from fields that are: source_count,
 * divergence_score, coverage_velocity, bias spread, and cross-tier
 * distribution.  Returns up to 3 short phrases ordered by salience.
 */
export function deriveRankSignals(story: Story): string[] {
  const signals: { label: string; weight: number }[] = [];

  const count = story.source.count ?? 0;
  const velocity = story.coverageVelocity ?? 0;
  const divergence = story.divergenceScore ?? 0;
  const spread = story.sigilData?.biasSpread?.leanSpread ?? 0;
  const range = story.sigilData?.biasSpread?.leanRange ?? 0;
  const tiers = story.sigilData?.tierBreakdown ?? {};
  const tierCount = Object.values(tiers).filter((n) => (n ?? 0) > 0).length;

  if (count >= 15) signals.push({ label: "broad coverage", weight: count });
  else if (count >= 8) signals.push({ label: "wide reporting", weight: count * 0.7 });

  if (range >= 45) signals.push({ label: "cross-spectrum", weight: range * 0.9 });
  else if (spread >= 16) signals.push({ label: "contested framing", weight: spread });

  if (velocity >= 5) signals.push({ label: "fast-developing", weight: velocity * 1.2 });
  else if (velocity >= 2) signals.push({ label: "still developing", weight: velocity });

  if (tierCount >= 3) signals.push({ label: "tier-diverse", weight: 20 });

  if (divergence >= 50) signals.push({ label: "sharp disagreement", weight: divergence * 0.6 });

  signals.sort((a, b) => b.weight - a.weight);
  return signals.slice(0, 3).map((s) => s.label);
}
