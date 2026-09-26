"use client";

import { useMemo } from "react";
import "../styles/bench.css";
import Bench, { type BenchSource } from "./Bench";

/* ---------------------------------------------------------------------------
   DeepDiveSpectrum — the Deep Dive's lean panel.

   Since 2026-09-21 this is a thin wrapper: it filters the rows that were never
   measured and hands the rest to the Bench, which draws one mark per source in
   the column of the lean rung that source sits on.

   What it used to be, and why that went: a kernel density estimate over the
   0-100 lean axis, drawn as an ink wave with favicon pins strung along a line
   beneath it, plus an amber plumb line at the tier-weighted mean. Three things
   were wrong with it.

   The distribution is not continuous. The engine anchors every article on its
   outlet's baseline and moves it by what the text does, so 74% of measured
   articles land EXACTLY on one of the seven baselines and 87% within two
   points. A KDE over seven spikes paints hills between them that no article
   stands on, and the reader cannot count anything off a smoothed curve.

   The plumb line answered the wrong question. A mean returns the empty middle
   of a bimodal roster: 7 left / 2 centre / 8 right and 0 left / 11 centre /
   2 right both come out near 50, so a hollow centre and a genuine consensus
   drew the same line in the same place.

   And the pins were a second, disagreeing view of the same numbers: they sat
   at continuous lean positions on a strip under a curve, so nothing in the
   panel could be read as a count.

   The props are unchanged apart from the retired `aggregateLean`, which fed
   the plumb line and nothing else.
   --------------------------------------------------------------------------- */

export interface DeepDiveSpectrumSource {
  name: string;
  articleUrl: string;
  sourceUrl: string;
  tier: string;
  politicalLean: number;
  /** Factual rigor score 0-100 (from bias_scores) */
  factualRigor?: number;
  /** Raw confidence 0-1 from pipeline */
  confidence?: number;
  /** The article's own headline, where the calling surface carries one. */
  headline?: string;
  /** The engine did not measure this article's lean. Its stored value is 50,
   *  so it must not be placed on a column: see the filter below. */
  leanUnscored?: boolean;
}

interface DeepDiveSpectrumProps {
  sources: DeepDiveSpectrumSource[];
  /** Mount already-drawn: no entrance choreography. Used where a parent owns
      the one continuous open motion (the inline Deep Dive accordion). */
  settled?: boolean;
}

export default function DeepDiveSpectrum({
  sources: allSources,
  settled = false,
}: DeepDiveSpectrumProps) {
  /* One filter, in the one component that places sources on the ladder. An
     article whose lean was never measured carries the stored 50, so seating it
     in the centre column is a count of a reading nobody took, and enough of
     them build a centre spike out of nothing: 595 of the 737 rows on the
     2026-09-20 export were unmeasured. It is still a source that covered the
     story, so it keeps its place in the roster, the source count and the tier
     breakdown, and the Bench says out loud how many are being held back. */
  const measured = useMemo<BenchSource[]>(
    () =>
      allSources
        .filter((s) => !s.leanUnscored)
        .map((s) => ({
          name: s.name,
          articleUrl: s.articleUrl,
          tier: s.tier,
          politicalLean: s.politicalLean,
          headline: s.headline,
          /* Carried through, not dropped. This component declared `confidence`
             on its props and never read it, so a mark placed from a headline
             and one read off a full article drew identically. */
          confidence: s.confidence,
        })),
    [allSources],
  );

  const unscoredCount = allSources.length - measured.length;

  return (
    <Bench sources={measured} unscoredCount={unscoredCount} settled={settled} />
  );
}
