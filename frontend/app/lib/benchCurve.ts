/* ---------------------------------------------------------------------------
   benchCurve.ts — the spectrum line over the Bench, and the room it leaves.

   TWO THINGS, both pure, both here so `test/bench-curve.test.mjs` can hold
   them to the one rule that matters.

   1. THE LINE. A hairline that rides the top of every column, so seven
      discrete counts read as one silhouette without stopping being counts.

      THE TRAP, and it is this project's own: the Bench exists because a
      kernel density estimate was removed on 2026-09-21 for "drawing hills
      between spikes that nothing stands on". A smoothed curve over the same
      seven numbers is the same mistake wearing a thinner stroke, unless it
      is built so that it CANNOT invent a peak.

      So every segment is a cubic whose two control points carry the y of its
      own endpoints:

          C  x0 + dx/3, y0    x1 - dx/3, y1    x1, y1

      A cubic Bezier is a convex combination of its four control y values, so
      with y0, y0, y1, y1 the curve's y is confined to [min(y0,y1),
      max(y0,y1)] for the whole segment. It is monotone by construction, not
      by a tolerance. It touches every column top exactly, it can never rise
      above the taller of two neighbours, and it can never dip below the
      shorter. A hill between two spikes is unrepresentable.

      The curve therefore adds no information and removes none. It is the
      shape of the distribution, drawn over the counts that are the claim.

   2. THE ROOM. Where a distribution leans, the far side of the Bench is
      empty, and that emptiness is the same fact the line is stating. So it
      is given to the mark instead of being padding: `whitespace` returns the
      widest low run, which is where the coverage is not.

      It returns null rather than a cramped box. A mark squeezed into 14px of
      a flat distribution is worse than no mark, and the caller falls back to
      the head.
   --------------------------------------------------------------------------- */

export interface BenchGeometry {
  /** Marks in each of the seven buckets, far left to far right. */
  counts: readonly number[];
  /** Mark diameter, uniform across columns (`BenchPack.mark`). */
  mark: number;
  /** Marks per sub-row (`BenchPack.perRow`). */
  perRow: number;
  /** Space between marks (`BENCH_GAP`). */
  gap: number;
  /** Most marks a column may draw (`BenchPack.capPerColumn`). */
  cap?: number;
  /** Usable width of one column. */
  colWidth: number;
  /** Space between columns. */
  colGap: number;
  /** Height budget for the stacks. */
  boxH: number;
}

/** Stack height in px for each column, measured the way the DOM stacks it. */
export function columnHeights(g: BenchGeometry): number[] {
  const cap = g.cap && Number.isFinite(g.cap) ? g.cap : Infinity;
  return g.counts.map((n) => {
    const drawn = Math.min(n, cap);
    if (drawn <= 0) return 0;
    const rows = Math.ceil(drawn / Math.max(1, g.perRow));
    return Math.max(0, rows * (g.mark + g.gap) - g.gap);
  });
}

/** Centre x of column i. */
export function columnCentre(i: number, g: BenchGeometry): number {
  return i * (g.colWidth + g.colGap) + g.colWidth / 2;
}

export interface Envelope {
  /** The open line across the column tops. */
  line: string;
  /** The same line closed down to the baseline, for a wash under it. */
  area: string;
  /** The vertices, which sit exactly on the column tops. */
  points: [number, number][];
  /** Total width the path is drawn in. */
  width: number;
}

export function envelope(g: BenchGeometry): Envelope | null {
  return envelopeFrom(columnHeights(g), g);
}

/** The same line over heights someone else computed.
 *
 *  The card's register (`RosterStrip`) sizes its seven strokes differently
 *  from the Bench: its overall height comes from the sample size and the bars
 *  are normalised inside it, because at 16px a row-based stack would be one
 *  row for everything. Different heights, same silhouette, ONE path builder,
 *  so the shape a reader learns on a card is the shape they meet in the Deep
 *  Dive rather than a second drawing that happens to look similar. */
export function envelopeFrom(
  heights: readonly number[],
  g: Omit<BenchGeometry, "counts" | "mark" | "perRow" | "gap"> & { counts?: readonly number[] },
): Envelope | null {
  if (!heights.some((h) => h > 0)) return null;
  const geo = { ...g, counts: heights } as BenchGeometry;
  return trace(heights, geo);
}

/** The monotone cubic through a list of points. Both edges of the ink ribbon
 *  are built with it, so neither edge can invent a peak either. */
function through(points: readonly [number, number][]): string {
  let d = `M ${round(points[0][0])} ${round(points[0][1])}`;
  for (let i = 1; i < points.length; i += 1) {
    const [x0, y0] = points[i - 1];
    const [x1, y1] = points[i];
    const dx = (x1 - x0) / 3;
    d += ` C ${round(x0 + dx)} ${round(y0)} ${round(x1 - dx)} ${round(y1)} ` +
         `${round(x1)} ${round(y1)}`;
  }
  return d;
}

/** The same curve as a PEN STROKE rather than a stroked line: a filled ribbon
 *  whose width follows the count in each bucket, heavy where the coverage is
 *  and tapering to a hairline where it is not.
 *
 *  THIS IS WHAT REPLACED THE WASH. A flat tint under a curve is a chart
 *  convention and the one element on the panel that was not ink; it was also
 *  redundant, because the area under the Bench's curve is already filled with
 *  the source marks themselves. Pressure variation says the same thing the
 *  wash was saying, in the house's own hand (see `InkUnderline`: a faint
 *  blurred bleed under a pen stroke that thickens at the press), and it says
 *  it on the line instead of behind it.
 *
 *  The ribbon's CENTRELINE is still exactly the envelope, so the reading is
 *  unchanged. Width is a second rendering of the count that height already
 *  carries, never a third number. */
export function inkRibbon(
  env: Envelope,
  weights: readonly number[],
  { minHalf = 0.35, maxHalf = 2.2 }: { minHalf?: number; maxHalf?: number } = {},
): string {
  const peak = Math.max(...weights, 0) || 1;
  /* The two outer anchors sit on the baseline and carry no count, so the
     stroke enters and leaves the page at its thinnest. */
  const halves = [minHalf, ...weights.map(
    (w) => minHalf + (maxHalf - minHalf) * Math.min(1, Math.max(0, w) / peak)), minHalf];
  const top = env.points.map(([x, y], i) => [x, y - halves[i]] as [number, number]);
  const bottom = env.points.map(([x, y], i) => [x, y + halves[i]] as [number, number]);
  const back = [...bottom].reverse();
  return `${through(top)} L ${round(back[0][0])} ${round(back[0][1])} ` +
         `${through(back).slice(through(back).indexOf("C") - 1)} Z`;
}

function trace(heights: readonly number[], g: BenchGeometry): Envelope | null {

  const width = columnCentre(heights.length - 1, g) + g.colWidth / 2;
  /* The line starts and ends ON the baseline at the outer edges, so a
     distribution that reaches the last column does not appear to run off the
     page, and one that does not reaches the floor where its count is zero. */
  const points: [number, number][] = [
    [0, g.boxH],
    ...heights.map((h, i) => [columnCentre(i, g), g.boxH - h] as [number, number]),
    [width, g.boxH],
  ];

  /* Control points carry their own endpoint's y. See the header: this is what
     makes overshoot unrepresentable rather than merely unlikely. */
  const line = through(points);
  const area = `${line} L ${round(width)} ${round(g.boxH)} L 0 ${round(g.boxH)} Z`;
  return { line, area, points, width };
}

export interface Room {
  x: number;
  y: number;
  width: number;
  height: number;
  /** Inclusive column indices the room spans. */
  from: number;
  to: number;
}

/** The widest run of low columns, and the space above it.
 *
 *  `lowShare` is the fraction of the tallest column below which a column
 *  counts as leaving room. `minSide` is the smallest square worth putting a
 *  mark in; below it this returns null and the caller does something else. */
export function whitespace(
  g: BenchGeometry,
  { lowShare = 0.34, minSide = 44 }: { lowShare?: number; minSide?: number } = {},
): Room | null {
  const heights = columnHeights(g);
  const tallest = Math.max(...heights, 0);
  if (tallest <= 0) return null;
  const ceiling = tallest * lowShare;

  let best: Room | null = null;
  let i = 0;
  while (i < heights.length) {
    if (heights[i] > ceiling) { i += 1; continue; }
    let j = i;
    while (j + 1 < heights.length && heights[j + 1] <= ceiling) j += 1;
    const left = columnCentre(i, g) - g.colWidth / 2;
    const right = columnCentre(j, g) + g.colWidth / 2;
    const runTop = Math.max(...heights.slice(i, j + 1));
    const room: Room = {
      x: left,
      y: 0,
      width: right - left,
      /* Stops at the tallest column IN THE RUN, so the mark never overlaps a
         mark, and clears the line by a hair. */
      height: g.boxH - runTop,
      from: i,
      to: j,
    };
    const side = Math.min(room.width, room.height);
    const bestSide = best ? Math.min(best.width, best.height) : 0;
    if (side > bestSide) best = room;
    i = j + 1;
  }
  if (!best) return null;
  if (Math.min(best.width, best.height) < minSide) return null;
  return best;
}

function round(n: number): number {
  return Math.round(n * 100) / 100;
}
