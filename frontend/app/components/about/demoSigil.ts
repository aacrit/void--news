import type { SigilData } from "../../lib/types";
import { DIVERGENT_SPREAD_MIN } from "../../lib/biasColors";

/* ---------------------------------------------------------------------------
   demoSigil — builds a fully-typed SigilData for the interactive Beat 2/4
   demos, so the onboarding teaches the REAL <Sigil> mark (beam = lean,
   ring = coverage, fan = divergence, strict-green = consensus) rather than a
   bespoke illustration that could drift from production.
   --------------------------------------------------------------------------- */

export function demoSigil(lean: number, leanSpread: number, sourceCount: number): SigilData {
  const l = Math.max(0, Math.min(100, Math.round(lean)));
  const spread = Math.max(0, Math.min(45, Math.round(leanSpread)));
  const sources = Math.max(1, Math.round(sourceCount));
  // Divergence flag mirrors the live derivation: high spread → divergent.
  const divergenceFlag: "divergent" | "consensus" | null =
    spread >= DIVERGENT_SPREAD_MIN ? "divergent" : spread <= 4 ? "consensus" : null;

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
    },
    pending: false,
    unscored: false,
    opinionLabel: "Reporting",
    divergenceFlag,
  };
}
