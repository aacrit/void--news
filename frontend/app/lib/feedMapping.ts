/* ---------------------------------------------------------------------------
   feedMapping — shared, isomorphic cluster -> Story mapping.

   Extracted from HomeContent (2026-08-09) so the SAME code runs in two places:
     1. The build-time server fetch (app/lib/serverFeed.ts, used by the
        prerendered front page) that seeds `initialStories`.
     2. The client retry / pull-to-refresh path inside HomeContent.

   Sharing the exact mapping guarantees the server-rendered feed and any
   later client refetch produce identically-shaped Story objects. It is a
   PURE module (no "use client", no React, no Date.now / new Date at call
   time) so it is safe to import from a server component. Deterministic:
   same clusters in, same Story[] out.
   --------------------------------------------------------------------------- */

import type {
  Edition,
  Category,
  Story,
  BiasScores,
  BiasSpread,
  ThreeLensData,
  OpinionLabel,
  SigilData,
} from "./types";
import { isUnscoredTilt } from "./biasColors";
import { cleanFeedSummary } from "./summaryHygiene";

/** Map pipeline category slugs (both fine-grained and desk) to display names. */
export function capitalize(s: string): string {
  if (!s) return s;
  const map: Record<string, string> = {
    politics: "Politics", conflict: "Conflict", economy: "Economy",
    science: "Science", health: "Health", environment: "Environment",
    culture: "Culture",
    tech: "Science", technology: "Science", sports: "Culture",
  };
  return map[s.toLowerCase()] || s.charAt(0).toUpperCase() + s.slice(1);
}

/** Runtime guard for bias_diversity JSONB from Supabase. */
export function parseBiasDiversity(raw: unknown): Record<string, unknown> | null {
  if (raw == null) return null;
  if (typeof raw !== "object" || Array.isArray(raw)) return null;
  return raw as Record<string, unknown>;
}

/** Safely coerce a bias_diversity field to a number, with a fallback. */
export function safeNum(bd: Record<string, unknown>, key: string, fallback: number): number {
  const v = bd[key];
  if (typeof v === "number" && !Number.isNaN(v)) return v;
  return fallback;
}

/** Safely extract tier_breakdown as Record<string, number>. */
export function safeTierBreakdown(bd: Record<string, unknown>): Record<string, number> | undefined {
  const raw = bd["tier_breakdown"];
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return undefined;
  const result: Record<string, number> = {};
  for (const [k, v] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof v === "number" && Number.isFinite(v)) result[k] = v;
  }
  return Object.keys(result).length > 0 ? result : undefined;
}

export function deriveOpinionLabel(score: number): OpinionLabel {
  if (score <= 25) return "Reporting";
  if (score <= 50) return "Analysis";
  if (score <= 75) return "Opinion";
  return "Editorial";
}

export function deriveCoverageScore(sourceCount: number, factualRigor: number, confidence: number): number {
  const sourceNorm = Math.min(1.0, sourceCount / 10.0);
  const rigorNorm = factualRigor / 100.0;
  const confNorm = Math.min(1.0, confidence);
  return Math.round((sourceNorm * 0.35 + 0.2 + confNorm * 0.20 + rigorNorm * 0.25) * 100);
}

/** Field sets for the story_clusters feed query. Shared with serverFeed. */
export const FEED_ENRICHED_FIELDS =
  "id,title,summary,category,section,sections,importance_score,source_count,first_published,last_updated,divergence_score,headline_rank,coverage_velocity,bias_diversity,consensus_points,divergence_points,rank_world,claim_consensus,cached_image_url,is_international,is_headline,headline_confidence";
export const FEED_BASE_FIELDS =
  "id,title,summary,category,section,sections,importance_score,source_count,first_published,last_updated";

/**
 * Map raw story_clusters rows to Story[] and stamp divergence percentile
 * flags (top/bottom 10%). Isomorphic + deterministic.
 *
 * @param clusters   raw PostgREST rows
 * @param usingEnriched  whether the enriched field set was selected (older
 *                       schemas fall back to base and lack bias JSONB).
 */
export function mapClustersToStories(
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  clusters: any[],
  usingEnriched: boolean,
): Story[] {
  /* eslint-disable @typescript-eslint/no-explicit-any */
  const mappedStories: Story[] = clusters.map((cluster: any) => {
    const bd = usingEnriched ? parseBiasDiversity(cluster.bias_diversity) : null;
    const hasBiasData = !!(bd && bd["avg_political_lean"] != null);

    const biasScores: BiasScores = hasBiasData
      ? {
          politicalLean: safeNum(bd!, "avg_political_lean", 50),
          sensationalism: safeNum(bd!, "avg_sensationalism", 30),
          opinionFact: safeNum(bd!, "avg_opinion_fact", 25),
          factualRigor: safeNum(bd!, "avg_factual_rigor", 75),
          framing: safeNum(bd!, "avg_framing", 40),
        }
      : {
          politicalLean: 50,
          sensationalism: 30,
          opinionFact: 25,
          factualRigor: 75,
          framing: 40,
        };

    const biasSpread: BiasSpread | undefined = bd && bd["lean_spread"] != null
      ? {
          leanSpread: safeNum(bd, "lean_spread", 0),
          framingSpread: safeNum(bd, "framing_spread", 0),
          leanRange: safeNum(bd, "lean_range", 0),
          sensationalismSpread: safeNum(bd, "sensationalism_spread", 0),
          opinionSpread: safeNum(bd, "opinion_spread", 0),
          aggregateConfidence: safeNum(bd, "aggregate_confidence", 0),
          analyzedCount: safeNum(bd, "analyzed_count", 0),
          polarization: safeNum(bd, "polarization", 0),
          leanLeftCount: safeNum(bd, "lean_left_count", 0),
          leanCenterCount: safeNum(bd, "lean_center_count", 0),
          leanRightCount: safeNum(bd, "lean_right_count", 0),
        }
      : undefined;

    const sourceCount = cluster.source_count ?? 0;
    const opinionLabel = (bd?.["avg_opinion_label"] as OpinionLabel) ?? deriveOpinionLabel(biasScores.opinionFact);
    const lensData: ThreeLensData = {
      lean: biasScores.politicalLean,
      coverage: bd ? safeNum(bd, "coverage_score", deriveCoverageScore(
        sourceCount, biasScores.factualRigor, biasSpread?.aggregateConfidence ?? 0.5,
      )) : deriveCoverageScore(sourceCount, biasScores.factualRigor, 0.5),
      sourceCount,
      tierBreakdown: bd ? safeTierBreakdown(bd) : undefined,
      opinion: biasScores.opinionFact,
      opinionLabel,
      pending: !hasBiasData,
    };
    const claimCon = cluster.claim_consensus;
    const sigilData: SigilData = {
      politicalLean: biasScores.politicalLean,
      sensationalism: biasScores.sensationalism,
      opinionFact: biasScores.opinionFact,
      factualRigor: biasScores.factualRigor,
      framing: biasScores.framing,
      agreement: cluster.divergence_score || 0,
      sourceCount,
      tierBreakdown: bd ? safeTierBreakdown(bd) : undefined,
      biasSpread,
      pending: !hasBiasData,
      unscored: hasBiasData && isUnscoredTilt(
        biasScores.politicalLean,
        sourceCount,
        biasSpread?.leanSpread ?? 0,
        biasSpread?.leanRange ?? 0,
        biasSpread?.aggregateConfidence ?? 0,
      ),
      opinionLabel,
      consensusCorroborated: claimCon?.corroborated,
      consensusTotal: claimCon?.total_claims,
    };

    const rawConsensus = usingEnriched ? cluster.consensus_points : null;
    const rawDivergence = usingEnriched ? cluster.divergence_points : null;
    const consensusPoints: string[] = Array.isArray(rawConsensus)
      ? rawConsensus.map((p: unknown) => typeof p === "string" ? p : String(p ?? ""))
      : [];
    const divergencePoints: string[] = Array.isArray(rawDivergence)
      ? rawDivergence.map((p: unknown) => typeof p === "string" ? p : String(p ?? ""))
      : [];

    const safeTitle = typeof cluster.title === "string" ? cluster.title : String(cluster.title ?? "");
    const safeSummary = cleanFeedSummary(
      typeof cluster.summary === "string" ? cluster.summary : String(cluster.summary ?? ""),
      safeTitle,
    );

    return {
      id: cluster.id,
      title: safeTitle,
      summary: safeSummary,
      source: {
        name: "Multiple Sources",
        count: sourceCount,
      },
      category: capitalize(typeof cluster.category === "string" ? cluster.category : "politics") as Category,
      // Deterministic: NEVER default to new Date() here — an undated cluster
      // would serialize a build-time clock into the prerender and mismatch on
      // hydration. Feed cards do not render publishedAt, so an empty string is
      // safe; downstream Deep Dive formats its own dates client-side.
      publishedAt:
        cluster.first_published ||
        cluster.last_updated ||
        "",
      biasScores,
      biasSpread,
      lensData,
      sigilData,
      section: (cluster.section || "world") as Edition,
      sections: (cluster.sections || [cluster.section || "world"]) as Edition[],
      importance: cluster.rank_world || cluster.headline_rank || cluster.importance_score || 50,
      divergenceScore: cluster.divergence_score || 0,
      headlineRank: cluster.rank_world || cluster.headline_rank || cluster.importance_score || 50,
      coverageVelocity: cluster.coverage_velocity || 0,
      deepDive: consensusPoints.length > 0 || divergencePoints.length > 0 || cluster.claim_consensus
        ? {
            consensus: consensusPoints,
            divergence: divergencePoints,
            sources: [],
            claimConsensus: cluster.claim_consensus || undefined,
          }
        : undefined,
      cachedImageUrl: cluster.cached_image_url ?? null,
      is_international: Boolean(cluster.is_international),
    } as unknown as Story;
  });

  // Compute divergence percentiles (p10/p90) and flag top/bottom 10%.
  const divScores = mappedStories
    .map((s) => s.divergenceScore)
    .filter((d) => d > 0)
    .sort((a, b) => a - b);
  if (divScores.length >= 5) {
    const p10 = divScores[Math.floor(divScores.length * 0.1)];
    const p90 = divScores[Math.floor(divScores.length * 0.9)];
    for (const s of mappedStories) {
      if (s.divergenceScore > 0) {
        if (s.divergenceScore >= p90) {
          s.sigilData.divergenceFlag = "divergent";
        } else if (s.divergenceScore <= p10) {
          s.sigilData.divergenceFlag = "consensus";
        }
      }
    }
  }
  /* eslint-enable @typescript-eslint/no-explicit-any */

  return mappedStories;
}
