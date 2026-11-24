/* ---------------------------------------------------------------------------
   outletVotes: one vote per OUTLET, the rule the card and the Bench share.

   CEO decision 3 (2026-10-02). The card's histogram used to count ARTICLES
   (`compute_lean_histogram` over every measured row) while the Deep Dive
   Bench kept the first article per source name and drew one mark per outlet.
   On the 2026-10-01 feed that was 417 article votes from 347 outlets, and 3
   of the 20 cards printed a different word from their own Deep Dive.

   The histogram is now computed ONCE, in the pipeline
   (`pipeline/utils/bias_aggregation.py: compute_outlet_lean_histogram`), and
   this file is its mirror for the one place that has to draw the outlets
   individually: an outlet sits at the MEAN of its measured articles in the
   story, keyed by source name. `tests/test_bias_bins.py` and
   `test/labels.test.mjs` re-derive the committed export through both and
   assert they agree with what the card was given, on every story.

   Pure: no DOM, no React, so the node tests can import it.
   --------------------------------------------------------------------------- */

import { leanToBucket, LEAN_BASELINES, type WingCounts } from "./biasColors";

export interface VoteRow {
  name: string;
  politicalLean: number;
  /** The engine did not measure this article's lean: it casts no vote. */
  leanUnscored?: boolean;
}

export interface OutletVote<T extends VoteRow> {
  /** The outlet's article nearest its mean, first on a tie: the one a mark
   *  links to and whose working its card shows. */
  row: T;
  name: string;
  /** Mean of the outlet's measured articles in this story. */
  lean: number;
  /** Measured articles behind that mean. */
  articles: number;
}

const keyOf = (name: string) => name.toLowerCase().trim();

/** Measured rows -> one entry per outlet, in first-seen order. */
export function outletVotes<T extends VoteRow>(rows: readonly T[]): OutletVote<T>[] {
  const order: string[] = [];
  const by = new Map<string, T[]>();
  for (const r of rows) {
    if (r.leanUnscored) continue;
    if (typeof r.politicalLean !== "number" || Number.isNaN(r.politicalLean)) continue;
    const k = keyOf(r.name);
    if (!k) continue;
    if (!by.has(k)) { by.set(k, []); order.push(k); }
    by.get(k)!.push(r);
  }
  return order.map((k) => {
    const group = by.get(k)!;
    let sum = 0;
    for (const g of group) sum += g.politicalLean;
    const lean = sum / group.length;
    let row = group[0];
    for (const g of group) {
      if (Math.abs(g.politicalLean - lean) < Math.abs(row.politicalLean - lean)) row = g;
    }
    return { row, name: row.name, lean, articles: group.length };
  });
}

/** The seven counts and L/C/R split those outlets make. */
export function outletSpread(leans: readonly number[]): WingCounts {
  const buckets = LEAN_BASELINES.map(() => 0);
  const names = LEAN_BASELINES.map(([n]) => n);
  for (const v of leans) buckets[names.indexOf(leanToBucket(v))] += 1;
  return {
    leanBuckets: buckets,
    leanLeftCount: buckets[0] + buckets[1] + buckets[2],
    leanCenterCount: buckets[3],
    leanRightCount: buckets[4] + buckets[5] + buckets[6],
    leanMeasuredCount: leans.length,
    leanVote: "outlet",
  };
}
