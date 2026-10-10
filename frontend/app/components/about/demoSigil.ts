import type { SigilData } from "../../lib/types";
import { DIVERGENT_SPREAD_MIN, LEAN_BASELINES, leanToBucket } from "../../lib/biasColors";

/* ---------------------------------------------------------------------------
   demoSigil — builds a fully-typed SigilData for the interactive Beat 2/4
   demos, so the onboarding teaches the REAL <Sigil> mark (beam = lean,
   ring = coverage, fan = divergence, strict-green = consensus) rather than a
   bespoke illustration that could drift from production.

   The demo carries a real roster (P1-12, 2026-10-02). It passed no wing
   counts, so the real Sigil read an empty roster and printed "0 measured"
   beside a lean word on /about. Each demo source is now placed: spread
   evenly across lean ± 1.5 × spread and binned on the same seven rungs the
   pipeline uses, so the word under the mark is the word the product would
   print for that roster, and every printed count is a count of something.
   --------------------------------------------------------------------------- */

/** Where the demo's `sources` outlets sit, evenly across the spread. */
export function demoPositions(lean: number, spread: number, sources: number): number[] {
  const n = Math.max(1, Math.round(sources));
  const reach = 1.5 * spread;
  return Array.from({ length: n }, (_, i) => {
    const z = n === 1 ? 0 : -1 + (2 * i) / (n - 1);
    return Math.max(0, Math.min(100, lean + z * reach));
  });
}

export function demoSigil(lean: number, leanSpread: number, sourceCount: number): SigilData {
  const l = Math.max(0, Math.min(100, Math.round(lean)));
  const spread = Math.max(0, Math.min(45, Math.round(leanSpread)));
  const sources = Math.max(1, Math.round(sourceCount));
  // Divergence flag mirrors the live derivation: high spread → divergent.
  const divergenceFlag: "divergent" | "consensus" | null =
    spread >= DIVERGENT_SPREAD_MIN ? "divergent" : spread <= 4 ? "consensus" : null;

  /* The roster: one placed outlet per demo source, on the real ladder. */
  const names = LEAN_BASELINES.map(([n]) => n);
  const buckets = names.map(() => 0);
  for (const p of demoPositions(l, spread, sources)) buckets[names.indexOf(leanToBucket(p))] += 1;
  const left = buckets[0] + buckets[1] + buckets[2];
  const center = buckets[3];
  const right = buckets[4] + buckets[5] + buckets[6];

  return {
    politicalLean: l,
    sensationalism: 30,
    opinionFact: 20,
    factualRigor: 78,
    framing: 28,
    agreement: spread, // 0 = unanimous, higher = more disagreement
    sourceCount: sources,
    tierBreakdown: { us_major: 2, international: 3, independent: Math.max(0, sources - 5) },
    biasSpread: {
      leanSpread: spread,
      framingSpread: 10,
      leanRange: Math.min(100, spread * 2),
      sensationalismSpread: 8,
      opinionSpread: 10,
      aggregateConfidence: 1,
      analyzedCount: sources,
      leanBuckets: buckets,
      leanLeftCount: left,
      leanCenterCount: center,
      leanRightCount: right,
      polarization: Math.round((100 * 2 * Math.min(left, right)) / sources),
      leanMeasuredCount: sources,
      leanTotalCount: sources,
      leanVote: "outlet",
    },
    pending: false,
    unscored: false,
    opinionLabel: "Reporting",
    divergenceFlag,
  };
}
