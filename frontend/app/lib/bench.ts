/* ---------------------------------------------------------------------------
   bench.ts — the packing arithmetic behind the Bench.

   The Bench is a unit histogram: one mark per source, marks stacked inside the
   column of the lean rung that source sits on, so the height of a column IS
   the count in that bucket. That only reads as a histogram if the marks are
   the same size in every column, and it only fits on a page if that size is
   chosen from the data rather than fixed.

   Measured on the 2026-09-21 feed (35 clusters, one entry per source name,
   unscored rows excluded), the tallest bucket in a story runs from 2 to 40
   with a median of 11. A fixed 20px mark in a single file would need 880px of
   height for the worst story, and a cap low enough to fit would bite on 22 of
   the 35. So a column is multi-file: marks flow in sub-rows of `perRow`, and
   the mark shrinks only as far as it must.

   The search is the whole of the design decision, in one place, pure, so
   `test/bench.test.mjs` can hold it to the sizes above.

   WHAT IT OPTIMISES, and this is the part the first draft got wrong: the
   FEWEST marks per sub-row, not the largest mark. Taking the widest sub-row
   the column allowed packed a bucket of 4 and a bucket of 5 into one row
   each, so both columns stood exactly one mark high, and a bucket of 1, 2, 3,
   4 and 5 all drew the same height. The height had stopped being the count,
   which is the only claim the Bench makes. Measured on the 2026-09-21 feed at
   1440px, that collapsed five distinct counts into one bar on every story.

   So the search walks `perRow` up from 1 and takes the biggest mark that fits
   at the first width that works. `perRow` is the histogram's resolution: at 1
   a column is a true single file and every count has its own height; at 2 the
   heights step in pairs. Marks shrink before the resolution is given up.

     - Never go below `markMin`: past it a favicon is a smudge and the mark
       stops naming anything.
     - When nothing fits, cap the column and report `capPerColumn`, which is
       what puts the "Show all N sources" toggle on the page. The toggle
       re-packs against a taller box rather than revealing a hidden layer, so
       nothing is ever drawn that the collapsed view lied about.
   --------------------------------------------------------------------------- */

export interface BenchPack {
  /** Mark diameter in px. Uniform across every column, by definition. */
  mark: number;
  /** Marks per sub-row inside one column. */
  perRow: number;
  /** Sub-rows the tallest column occupies. */
  rows: number;
  /** Most marks one column may draw. Infinity when nothing is cut. */
  capPerColumn: number;
}

export interface BenchPackOptions {
  /** Usable width of ONE column in px. */
  colWidth: number;
  /** Height budget for the stacks, in px. */
  maxHeight: number;
  /** Marks in the busiest bucket. */
  tallest: number;
  markMax?: number;
  markMin?: number;
  /** Space between marks, both axes. */
  gap?: number;
}

export const BENCH_MARK_MAX = 20;
export const BENCH_MARK_MIN = 10;
export const BENCH_GAP = 2;
/** Below this diameter a favicon is not readable, so the mark draws as a
 *  plain lean-coloured disc instead of pretending to carry a logo. */
export const BENCH_FAVICON_MIN = 13;

export function packBench(opts: BenchPackOptions): BenchPack {
  const gap = opts.gap ?? BENCH_GAP;
  const markMax = opts.markMax ?? BENCH_MARK_MAX;
  const markMin = opts.markMin ?? BENCH_MARK_MIN;
  const colWidth = Math.max(0, opts.colWidth);
  const maxHeight = Math.max(0, opts.maxHeight);
  const tallest = Math.max(0, Math.floor(opts.tallest));

  if (tallest <= 0) {
    return { mark: markMax, perRow: 1, rows: 0, capPerColumn: Infinity };
  }

  /* Widest a column can go at the smallest mark: past this no candidate can
     fit the column, whatever the height budget allows. */
  const perRowMax = Math.max(1, Math.floor(colWidth / (markMin + gap)));

  for (let perRow = 1; perRow <= perRowMax; perRow++) {
    const rows = Math.ceil(tallest / perRow);
    for (let mark = markMax; mark >= markMin; mark--) {
      const pitch = mark + gap;
      if (rows * pitch <= maxHeight && perRow * pitch <= colWidth) {
        return { mark, perRow, rows, capPerColumn: Infinity };
      }
    }
  }

  /* Nothing fits: draw as many whole sub-rows of the smallest mark as the box
     holds, at the widest the column allows, and report the cut. */
  const pitch = markMin + gap;
  const rowsThatFit = Math.max(1, Math.floor(maxHeight / pitch));
  return {
    mark: markMin,
    perRow: perRowMax,
    rows: rowsThatFit,
    capPerColumn: rowsThatFit * perRowMax,
  };
}

/** Chunk a column's marks into sub-rows, bottom row first. */
export function benchRows<T>(items: readonly T[], perRow: number): T[][] {
  const n = Math.max(1, Math.floor(perRow));
  const out: T[][] = [];
  for (let i = 0; i < items.length; i += n) out.push(items.slice(i, i + n));
  return out;
}
