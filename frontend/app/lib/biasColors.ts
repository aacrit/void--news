/**
 * biasColors.ts — Single source of truth for bias color computation,
 * lean labels, lean buckets, and CSS variable caching.
 *
 * Replaces duplicated logic across BiasLens, BiasInspector, Sigil,
 * and DeepDiveSpectrum. One cache, one MutationObserver, one set of
 * thresholds.
 */

/* ── Lean bucket boundaries — used everywhere ───────────────────────────── */

export type LeanCategory =
  | "far-left"
  | "left"
  | "center-left"
  | "center"
  | "center-right"
  | "right"
  | "far-right";

/** The seven outlet baselines the analyzer anchors to, from
 *  `pipeline/analyzers/political_lean.py` BASELINE_MAP. A rung of this ladder
 *  is not an arbitrary number: it is what an outlet of that rating scores when
 *  its article's wording is unremarkable, which is most articles. Measured on
 *  the 2026-09-21 feed, 74% of all 668 measured articles sit EXACTLY on one of
 *  these seven values and 87% are within two points of one. The distribution
 *  is seven spikes, not a spread. */
export const LEAN_BASELINES: ReadonlyArray<readonly [LeanCategory, number]> = [
  ["far-left", 10], ["left", 20], ["center-left", 35], ["center", 50],
  ["center-right", 65], ["right", 80], ["far-right", 90],
] as const;

/** A score belongs to the baseline it is NEAREST. That places every boundary
 *  at the midpoint between two rungs (15, 27.5, 42.5, 57.5, 72.5, 85) without
 *  writing any of them down, and it makes the tie rule sayable: a score
 *  exactly between two rungs takes the one nearer the centre.
 *
 *  The tie rule has to be expressed in DISTANCE FROM CENTRE, not in score.
 *  Resolving a tie "upward" in score sends it toward the centre on the left of
 *  the ladder and away from it on the right, which is the same asymmetry this
 *  function was just fixed for: 15 landed on `left` while its mirror 85 landed
 *  on `far-right`. Caught by the symmetry check in test/labels.test.mjs. */

/**
 * Unified lean boundaries — identical for bucket placement AND labels.
 *
 * THE BOUNDARIES WERE WRONG UNTIL 2026-09-21, ASYMMETRICALLY.
 *
 * They were `<=20, <=35, <=45, <=55, <=65, <=80`, which put four of the seven
 * baselines on a bucket's upper EDGE. On the right that lands in the
 * correctly-named bucket by luck; on the left the upper edge of a bucket is
 * its LEAST extreme end, so it lands one rung too far out:
 *
 *     roster `left`        scores 20  ->  the page said FAR LEFT
 *     roster `center-left` scores 35  ->  the page said LEFT
 *
 * Both errors ran leftward, and the right-hand rungs were correct, so a
 * left-leaning outlet was displayed as more extreme than this product's own
 * roster rates it while a right-leaning one was not. For a product whose
 * whole claim is even-handed measurement that is the worst available bug.
 * `center-left` also held no baseline at all: it was a ten-point gap
 * populated only by the skirt of the 35 spike.
 *
 * Binning on the baselines fixes it and evens the widths (15/12.5/15/15/15/
 * 12.5/15, against 21/15/10/10/10/15/20). It moves 156 of 668 articles
 * (23.4%) into a different bucket, and only 11 of those (1.6%) change their
 * left/centre/right group, so cluster-level shape is barely touched.
 */
export function leanToBucket(v: number): LeanCategory {
  let best: LeanCategory = "center";
  let bestGap = Infinity;
  let bestPull = Infinity;
  for (const [name, base] of LEAN_BASELINES) {
    const gap = Math.abs(v - base);
    const pull = Math.abs(base - 50); // how extreme this rung is
    if (gap < bestGap - 1e-9 || (Math.abs(gap - bestGap) < 1e-9 && pull < bestPull)) {
      best = name;
      bestGap = gap;
      bestPull = pull;
    }
  }
  return best;
}

const LEAN_LABEL_TEXT: Record<LeanCategory, string> = {
  "far-left": "Far Left",
  left: "Left",
  "center-left": "Center-Left",
  center: "Center",
  "center-right": "Center-Right",
  right: "Right",
  "far-right": "Far Right",
};

/** The label and the bucket can never disagree: one derives from the other. */
export function leanLabel(v: number): string {
  return LEAN_LABEL_TEXT[leanToBucket(v)];
}

const LEAN_ABBR: Record<LeanCategory, string> = {
  "far-left": "FL", left: "L", "center-left": "CL", center: "C",
  "center-right": "CR", right: "R", "far-right": "FR",
};

/** Third consumer of the one ladder. It carried its own copy of the
 *  thresholds until 2026-09-21 and so inherited the same asymmetry; deriving
 *  it from the bucket is what makes "one ladder" true rather than asserted. */
export function leanLabelAbbr(v: number): string {
  return LEAN_ABBR[leanToBucket(v)];
}

export function senseLabel(v: number): string {
  if (v <= 25) return "Measured";
  if (v <= 50) return "Moderate";
  if (v <= 75) return "Elevated";
  return "Inflammatory";
}

export function rigorLabel(v: number): string {
  if (v >= 75) return "High rigor";
  if (v >= 50) return "Good rigor";
  if (v >= 25) return "Moderate rigor";
  return "Low rigor";
}

export function coverageLabel(v: number): string {
  if (v >= 75) return "Strongly sourced";
  if (v >= 50) return "Well sourced";
  if (v >= 25) return "Moderately sourced";
  return "Lightly sourced";
}

/* ── One lean ladder ───────────────────────────────────────────────────────
   There used to be three. leanToBucket / leanLabel cut at 20/35/45/55/65/80,
   tiltLabel cut at 29/46/53/72, and sigilLabelInfo had a fourth set of cuts of
   its own at 20/46/80. One number therefore produced three answers: a story at
   lean 60 read "Right" on the feed card, "Right Tilt" in the Sigil popup and
   "Center-Right" in the Deep Dive; at lean 30 it read "Left", "Far Left Tilt"
   and "Left". On the 2026-09-06 feed every confidently-labelled story
   disagreed with itself across surfaces.

   leanToBucket is now the only ladder. Everything below derives from it, so a
   surface may abbreviate the answer but can never give a different one.     ── */

export type TiltCategory = LeanCategory;

/** @deprecated Use leanToBucket. Kept as an alias so no caller silently
 *  switches ladders while the call sites are migrated. */
export const tiltToBucket = leanToBucket;

/** Human-readable descriptor for the Sigil popup. Derived from leanToBucket,
 *  so it cannot describe a band the label does not name. */
export function tiltDescriptor(v: number): string {
  switch (leanToBucket(v)) {
    case "far-left": return "Strong left lean in coverage language";
    case "left": return "Clear left lean in coverage framing";
    case "center-left": return "Slight left lean in text analysis";
    case "center": return "Balanced coverage from multiple perspectives";
    case "center-right": return "Slight right lean in text analysis";
    case "right": return "Clear right lean in coverage framing";
    default: return "Strong right lean in coverage language";
  }
}

/* ── Perceptual scale expansion — DISPLAY POSITION ONLY ────────────────────
   The cluster lean is a rigor-weighted mean; high-rigor wires (AP/Reuters≈50)
   plus genuinely two-sided coverage bunch most stories in ~40-62, so a LINEAR
   marker renders real center-left/center-right tilt nearly on top of dead
   center. This maps the TRUE lean (0-100) to a DISPLAY position (0-100) with
   high gain near center and saturation at the wings — a real 3-pt tilt becomes
   a ~7-8-pt visual offset — while staying strictly monotonic and side-
   preserving (a left story can never render right) and pinning the extremes
   (lean 0→0, 50→50, 100→100). The numeric score and label stay 100% TRUE;
   only on-screen distance from center is exaggerated for legibility.

   `confidence` (0-1) damps the amplification so low-signal thin clusters near
   50 aren't pushed out on noise; top stories (many sources) sit near 1.0 and
   get the full expansion. Tune sensitivity with DISPLAY_GAIN.                ── */

export const DISPLAY_GAIN = 3.2;

export function leanToDisplayPos(lean: number, confidence = 1): number {
  const d = (Math.max(0, Math.min(100, lean)) - 50) / 50; // -1..+1 true deviation
  const k = DISPLAY_GAIN * Math.max(0.4, Math.min(1, confidence));
  // tanh(k·d)/tanh(k): expands the middle, normalizes so the wings still reach
  // the rail (|d|=1 → ±1). Strictly increasing ⇒ order + side preserved.
  const expanded = Math.tanh(k * d) / Math.tanh(k);
  return 50 + 50 * expanded;
}

/** Display-space beam/needle angle in degrees for a lean, sharing the same
 *  expansion curve so every lean surface tilts consistently. */
export function leanToDisplayAngle(lean: number, confidence = 1, maxDeg = 24): number {
  return ((leanToDisplayPos(lean, confidence) - 50) / 50) * maxDeg;
}

/* ── Unscored gate — story lacks analytical signal for tilt label ───────── */

/**
 * Returns true when a story's lean falls in the balanced range (47-53)
 * but lacks enough analytical signal to genuinely call it "Balanced."
 * Three gates, any failure → unscored:
 *   A: all articles defaulted to 50 (no spread, no range, avg=50)
 *   B: single-source cluster (one voice isn't balance)
 *   C: low analytical confidence (<0.4)
 */
export function isUnscoredTilt(
  lean: number,
  sourceCount: number,
  leanSpread: number,
  leanRange: number,
  aggregateConfidence: number,
): boolean {
  if (lean < 47 || lean > 53) return false;
  const allDefault = lean === 50 && leanSpread === 0 && leanRange === 0;
  if (allDefault) return true;
  if (sourceCount < 2) return true;
  if (aggregateConfidence < 0.4) return true;
  return false;
}

/* ── Lean-label suppression — meaningful AND well-supported gate ────────────
   The aggregated cluster lean is a rigor-weighted mean. It bunches genuinely
   two-sided coverage and high-rigor wires in a false-center band, AND it drifts
   modestly off 50 on the WORD CHOICE of otherwise apolitical stories (a product
   recall, a wine harvest, a dead eagle), so a low-source / low-polarization
   story can read as a deliberate "Right" or "Left" editorial judgment when it is
   nothing of the sort.

   A glanceable partisan label is therefore asserted ONLY when it is
   WELL-SUPPORTED (enough sources, enough analytical confidence) AND the tilt
   shows up in one of two independent ways:
     1. the MEAN is clearly off center (large magnitude, backed by a real
        left/right split or strong enough to stand alone); or
     2. the ROSTER of coverage is lopsided (wing-share imbalance), with the mean
        agreeing in sign.
   Route 2 exists because route 1 alone is not reachable for the stories it is
   shown on. The mean averages sources sitting on both sides, so it is
   compressed toward 50 by construction: on 2026-08-13 the entire live top-50
   sat within |lean-50| <= 6 against a threshold of 8, and 52 of 52 cards
   rendered "Balanced". The wing counts are not compressed that way, so they carry
   the direction the mean loses. The gate stays fully symmetric: Left and Right
   are judged by the same thresholds on both routes. When a tilt fails the gate:
     - genuinely split (both wings present AND high polarization) -> "Contested".
     - otherwise -> "Balanced" when measured, "Not measured" when the gate fails.
   This changes label TEXT and numeric-score visibility ONLY; the Sigil beam
   angle, color, and fan geometry are untouched, and the Deep Dive spectrum still
   plots the full true distribution.                                          ── */

export const LEAN_BAND_LOW = 48;
export const LEAN_BAND_HIGH = 52;
/* The three measurement states a card can be in, said out loud. "Balanced"
   means measured and sitting at the centre; "Not measured" means the engine
   did not have enough measured articles or confidence to say anything, and
   the mark paints no direction. They used to share one word, "Flat". */
export const BALANCED_LABEL = "Balanced";
export const UNMEASURED_LABEL = "Not measured";
export const CONTESTED_LABEL = "Contested";

/** A directional partisan label needs at least this many sources behind it —
 *  a tilt carried by a handful of outlets is not a trustworthy editorial read. */
export const LABEL_MIN_SOURCES = 8;
/** ...and at least this much aggregate analytical confidence. */
export const LABEL_MIN_CONFIDENCE = 0.5;
/** ...and the lean must be MEASURED from at least this many articles.
 *
 *  Derived, not guessed. Per-article lean within a cluster has a standard
 *  deviation of 12 to 14 at every rank of the feed. A 7-point band is 10 points
 *  wide, so keeping the mean inside its own band with reasonable confidence
 *  asks for a standard error under 4, and at sd 12.5 that needs 10 measured
 *  articles (SE <= 3 would need 17). Below the top 20 the median cluster has
 *  10 to 15 measured articles and a maximum SE of 8 to 13, which is more than
 *  a band wide: those labels were noise wearing a direction.
 *
 *  Note this counts MEASURED articles, not sources. An article from an outlet
 *  with no left/right placement writing copy with no partisan signal scores 50
 *  as the ABSENCE of a measurement, and the pipeline already excludes those
 *  from the mean; they must not count toward its reliability either. */
export const LABEL_MIN_MEASURED = 10;
/** ...and a magnitude clear of dead center: |lean-50| must exceed this
 *  (i.e. lean <= 42 or >= 58), wider than the old false-center band. */
export const LABEL_MEANINGFUL_MARGIN = 8;
/** A very strong tilt (|lean-50| >= this) stands on its own without needing a
 *  measured left/right split behind it. */
export const LABEL_STRONG_MARGIN = 18;
/** Signed wing-share imbalance |R-L|/(L+C+R) at which the ROSTER of coverage is
 *  lopsided enough to assert a direction on its own.
 *
 *  Why a second route at all: the cluster lean is a MEAN, and a mean over
 *  sources that sit on both sides is compressed toward 50 by construction. It
 *  is the wrong statistic to threshold for "which way does this story lean" —
 *  a story carried 3:1 by right-leaning outlets can still average 55. The wing
 *  counts are not compressed that way, so they carry the direction the mean
 *  loses. The mean still has to AGREE in sign, so this only ever confirms a
 *  tilt the score already shows; it never invents one.
 *
 *  0.20 until 2026-09-21, against a denominator that included every centre
 *  article. On the wing-only denominator the same number would have called a
 *  3:2 split lopsided, so it was re-derived rather than carried over: 0.33 is
 *  roughly 2:1. Measured against the 2026-09-20 feed, the pair of changes
 *  moves 2 of 35 cards, both from Balanced to a direction, and both are real
 *  (12 left vs 5 right across 72 sources; 0 left vs 6 right across 24). */
export const LABEL_MIN_SHARE_TILT = 0.33;
/** Wing articles (left + right) a share tilt needs before it means anything.
 *  A proportion of two articles is not a roster. At five, the coarsest tilts
 *  the arithmetic can produce are 3:2 (0.20, correctly not lopsided), 4:1
 *  (0.60) and 5:0 (1.00), so the 0.33 threshold above lands between "split"
 *  and "one-sided" rather than inside rounding noise. */
export const LABEL_MIN_WING_ARTICLES = 5;
/** Otherwise a directional label needs genuine left/right divergence: the
 *  coverage's polarization must reach this. */
export const LABEL_MIN_SUPPORT_POLARIZATION = 35;
/** Polarization at/above which a suppressed tilt is surfaced as "Contested"
 *  rather than "Flat" — matches LeanCoverageBar's contested threshold. */
export const CONTESTED_MIN_POLARIZATION = 50;

export type LeanLabelState = "confident" | "contested" | "balanced" | "unmeasured";

export interface WingCounts {
  /** The seven bucket counts, far-left first. Already exported on every
   *  cluster as bias_diversity.lean_buckets and, until 2026-09-21, read by
   *  nothing. The register on the card and the bench in Deep Dive are both
   *  drawn from it. Sums to leanMeasuredCount. */
  leanBuckets?: readonly number[];
  leanLeftCount?: number;
  leanCenterCount?: number;
  leanRightCount?: number;
  /** Contestedness 0-100 (0 = one-sided/all-center, 100 = perfect L/R split). */
  polarization?: number;
  /** Aggregate analytical confidence 0-1. */
  aggregateConfidence?: number;
  /** Articles the lean was actually measured from (see LABEL_MIN_MEASURED). */
  leanMeasuredCount?: number;
}

/** Both wings genuinely present: left AND right coverage, with >=3 total.
 *  Matches LeanCoverageBar's contested gate exactly. */
export function bothWingsPresent(spread?: WingCounts | null): boolean {
  if (!spread) return false;
  const left = spread.leanLeftCount ?? 0;
  const center = spread.leanCenterCount ?? 0;
  const right = spread.leanRightCount ?? 0;
  return left > 0 && right > 0 && left + center + right >= 3;
}

/**
 * Signed wing-share imbalance in [-1, +1]: negative = the coverage roster
 * tilts left, positive = tilts right, 0 = symmetric, or too little wing
 * coverage to read a split from.
 *
 * The denominator is the WING coverage (left + right), not every analyzed
 * article. Dividing by left + center + right let neutral wire volume dilute a
 * real split out of existence: a story carried 14 left to 5 right landed at
 * 0.153 against a 0.20 threshold purely because 40 centre articles sat in the
 * denominator, while a nearly identical 16:6 story passed. What the number is
 * meant to answer is "of the outlets that took a side, how lopsided were
 * they", and that question does not involve the ones that did not.
 *
 * A proportion needs a denominator worth dividing by, so LABEL_MIN_WING_ARTICLES
 * is the floor. Without it the fix trades one lie for a worse one: measured on
 * the 2026-09-20 feed, a cluster with ONE left article out of six would have
 * read as a fully lopsided roster (tilt -1.0) and lit a confident Left label.
 * Five clusters on that feed had exactly that shape.
 */
export function leanShareTilt(spread?: WingCounts | null): number {
  if (!spread) return 0;
  const left = spread.leanLeftCount ?? 0;
  const center = spread.leanCenterCount ?? 0;
  const right = spread.leanRightCount ?? 0;
  /* Still gated on the full analyzed count: a three-article cluster has no
     roster to be lopsided, however its wings fall. */
  if (left + center + right < 3) return 0;
  const wings = left + right;
  if (wings < LABEL_MIN_WING_ARTICLES) return 0;
  return (right - left) / wings;
}

/* ── The shape of the roster ───────────────────────────────────────────────
   A point estimate has to be withheld when it is uncertain, which is why the
   old gate went quiet on 20 of 35 stories: it asked "which way does this
   lean" and suppressed the answer whenever the mean was not confident. A
   DISTRIBUTION never has to be withheld. If there is coverage there is a
   shape, and the shape is honest at any sample size.

   So the card reads the roster, not the mean. Five states, and every word is
   earned by the evidence that supports THAT word: Consensus is a claim about
   the centre and needs centre mass; Leans and Split are claims about the
   wings and need wing evidence. When neither is there the card states the
   count, which is true, rather than calling the story balanced.

   Measured on the 2026-09-21 feed: this speaks on 30 of 35 stories against
   15 of 35, and the five it stays quiet on have between 1 and 7 articles.

   A NOTE ON THE FALL-THROUGH, because the first draft of this rule got it
   wrong and would have shipped the exact lie the rest of this file removes.
   Falling through to "Balanced" labelled a story with 3 left, 4 centre and
   ZERO right-of-centre articles as balanced. Balanced is a finding, so it
   needs both wings present and enough of them to see.                      ── */

export type LeanShape = "leans" | "split" | "balanced" | "consensus" | "thin";

/** Articles that must have taken a side before the roster can be called
 *  lopsided or split. Same floor as LABEL_MIN_WING_ARTICLES, and for the same
 *  reason: a proportion of two articles is not a roster. */
export const SHAPE_MIN_WINGS = 5;
/** Total measured articles before any shape word is earned. */
export const SHAPE_MIN_TOTAL = 6;
/** Share of the roster in the centre bucket that counts as everyone agreeing. */
export const SHAPE_CONSENSUS_SHARE = 0.75;

export function leanShape(spread?: WingCounts | null): LeanShape {
  const left = spread?.leanLeftCount ?? 0;
  const center = spread?.leanCenterCount ?? 0;
  const right = spread?.leanRightCount ?? 0;
  const total = left + center + right;
  const wings = left + right;

  if (total < SHAPE_MIN_TOTAL) return "thin";
  if (center / total >= SHAPE_CONSENSUS_SHARE && total >= 8) return "consensus";
  if (wings < SHAPE_MIN_WINGS) return "thin";

  const tilt = (right - left) / wings;
  if (Math.abs(tilt) >= LABEL_MIN_SHARE_TILT) return "leans";
  // Both wings genuinely present, so "even" is a reading rather than an
  // absence. Whether the centre holds the mass is what separates a story the
  // coverage agrees on from one it has divided over.
  if (Math.min(left, right) >= 2) return center / total >= 0.5 ? "balanced" : "split";
  return "thin";
}

/** Which way a `leans` roster leans. Zero when the shape is not `leans`. */
export function leanShapeDirection(spread?: WingCounts | null): -1 | 0 | 1 {
  if (leanShape(spread) !== "leans") return 0;
  const left = spread?.leanLeftCount ?? 0;
  const right = spread?.leanRightCount ?? 0;
  return right > left ? 1 : -1;
}

/** The colour that word is printed in.
 *
 *  It has to come from the SAME rule as the word, and the card shipped for a
 *  day where it did not: the text came from `leanShapeLabel` while the colour
 *  still came from `storyLeanLabel`'s confidence-gated ramp, so one feed
 *  carried "Leans right" in crimson on one card and in muted grey on the next.
 *
 *  Five flat tokens, not a continuous ramp. Every one of them is tuned to
 *  clear AA on both papers on its own; a `color-mix` down the ramp is not,
 *  and one of its steps rendered 4.28:1 on the dark paper. The MAGNITUDE of
 *  the tilt is the register's job, drawn in the full seven-colour ramp
 *  directly above this line. The word only ever says which way. */
export function leanShapeColor(spread?: WingCounts | null): string {
  const shape = leanShape(spread);
  if (shape === "thin") return "var(--fg-muted)";
  /* Not --sense-high. That token is the sensationalism scale's top stop,
     drawn as dots and bars where 3:1 is the bar, and as TEXT on the light
     paper it measures 3.16:1. It had been the Contested label's colour since
     that label existed. Split is also the one shape with no direction to
     name, so plain ink is the honest choice as well as the legible one. */
  if (shape === "split") return "var(--fg-primary)";
  if (shape === "leans") {
    return leanShapeDirection(spread) > 0 ? "var(--bias-right)" : "var(--bias-left)";
  }
  return "var(--bias-center)";
}

/** The one line a card prints under the register. */
export function leanShapeLabel(spread?: WingCounts | null): string {
  const shape = leanShape(spread);
  if (shape === "thin") {
    const n = (spread?.leanLeftCount ?? 0) + (spread?.leanCenterCount ?? 0)
      + (spread?.leanRightCount ?? 0);
    return `${n} ${n === 1 ? "article" : "articles"}`;
  }
  if (shape === "leans") {
    return leanShapeDirection(spread) > 0 ? "Leans right" : "Leans left";
  }
  return shape === "split" ? "Split"
    : shape === "consensus" ? "Consensus" : "Balanced";
}

/** The shape word, its colour and its state, for every surface that names a
 *  story's coverage: the card's printed line, the Sigil's aria-label and
 *  popup, the Deep Dive masthead and Paper.
 *
 *  Before this, the printed word came from `leanShapeLabel` while the
 *  aria-label, the popup heading and the Deep Dive chip came from
 *  `storyLeanLabel`, the gated MEAN. On the 2026-09-25 edition that put
 *  "Leans left" on a card whose screen-reader label said "Not measured" and
 *  whose popup said "Not measured", "Balanced coverage" and "measured from 8
 *  of 12" in one box. A reader who hovered got a different answer from a
 *  reader who looked. One rule now feeds every one of them. */
export interface StoryShapeLabel {
  text: string;
  color: string;
  shape: LeanShape | "unscored";
}

export function storyShapeLabel(
  spread?: WingCounts | null,
  unscored = false,
): StoryShapeLabel {
  if (unscored) return { text: "Unscored", color: "var(--fg-muted)", shape: "unscored" };
  return { text: leanShapeLabel(spread), color: leanShapeColor(spread), shape: leanShape(spread) };
}

/** One sentence under the shape word in the Sigil popup. Counts, not a
 *  reading of the mean, so it cannot contradict the word above it. */
export function leanShapeDescriptor(spread?: WingCounts | null): string {
  const left = spread?.leanLeftCount ?? 0;
  const center = spread?.leanCenterCount ?? 0;
  const right = spread?.leanRightCount ?? 0;
  const counts = `${left} left of centre, ${center} centre, ${right} right of centre`;
  switch (leanShape(spread)) {
    case "consensus": return `Three quarters of the coverage sits in the centre: ${counts}`;
    case "balanced": return `Both sides covered this and neither outweighs the other: ${counts}`;
    case "split": return `Both sides covered this and the centre does not hold: ${counts}`;
    case "leans": return `One side carried most of the coverage: ${counts}`;
    default: return "Too few measured articles to read the coverage";
  }
}

/**
 * Decide how a story's lean LABEL should render:
 *   "confident"      well-supported tilt, shown either by the mean's magnitude
 *                    or by a lopsided coverage roster -> keep the directional label + score.
 *   "contested"      failed gate but genuinely split (both wings + high polarization) -> "Contested".
 *   "balanced"       measured, passed support, not split, mean at centre (score withheld).
 *   "unmeasured"     failed the support gate (measured count, sources, confidence).
 *
 * `sourceCount` defaults to +Infinity so callers that omit it keep the pre-gate
 * behavior for the source-count factor; pass the cluster's real source count to
 * suppress the arbitrary low-source tails.
 */
export function leanLabelState(
  lean: number,
  spread?: WingCounts | null,
  sourceCount = Number.POSITIVE_INFINITY,
): LeanLabelState {
  const margin = Math.abs(lean - 50);
  const pol = spread?.polarization ?? 0;
  const conf = spread?.aggregateConfidence ?? 1;
  const shareTilt = leanShareTilt(spread);

  // Support is common to both routes below: enough outlets behind the read,
  // enough analytical confidence in it, and enough MEASURED articles for the
  // mean to be worth a direction at all. measured is undefined on payloads
  // written before the field existed; those keep the old behaviour rather than
  // being suppressed wholesale.
  const measured = spread?.leanMeasuredCount;
  const enoughMeasured = measured === undefined || measured >= LABEL_MIN_MEASURED;
  const wellSupported =
    sourceCount >= LABEL_MIN_SOURCES &&
    conf >= LABEL_MIN_CONFIDENCE &&
    enoughMeasured;

  // Route 1 — the MEAN itself is clearly off center. Symmetric: the SAME
  // thresholds decide Left and Right, so a dead-eagle drift and an
  // eclipse-glasses recall are suppressed exactly the way the false center is.
  const meanIsMeaningful =
    margin >= LABEL_MEANINGFUL_MARGIN &&
    (pol >= LABEL_MIN_SUPPORT_POLARIZATION || margin >= LABEL_STRONG_MARGIN);

  // Route 2 — the ROSTER of coverage is lopsided. A mean over sources on both
  // sides is compressed toward 50 by construction, so a genuinely one-sided
  // story can sit at 55 and never clear Route 1. The wing counts still show it.
  // Requires the mean to agree in sign, so this confirms direction rather than
  // inventing it.
  const rosterIsLopsided =
    Math.abs(shareTilt) >= LABEL_MIN_SHARE_TILT &&
    Math.sign(shareTilt) === Math.sign(lean - 50);

  // Not enough measured articles, outlets or confidence: the engine has no
  // read, and the card says so rather than calling the story balanced.
  if (!wellSupported) return "unmeasured";

  if (meanIsMeaningful || rosterIsLopsided) return "confident";

  const genuinelyContested =
    bothWingsPresent(spread) && pol >= CONTESTED_MIN_POLARIZATION;
  return genuinelyContested ? "contested" : "balanced";
}

/* ── The one label a story gets ────────────────────────────────────────────
   Every surface that names a story's lean calls this: the feed card's Sigil,
   the Sigil popup, the Deep Dive's BiasSnapshot, the standalone /story page.
   Before it, three functions with three sets of cut points answered the same
   question three ways from the same number.

   The gate (leanLabelState) and the ladder (leanToBucket) are both applied
   here, so a caller cannot accidentally take one without the other, which is
   how the card once showed a confident direction for a story the Deep Dive was
   already calling Flat.                                                     ── */

export interface StoryLeanLabel {
  /** "Center-Right", or "Contested" / "Balanced" / "Not measured" / "Unscored" when suppressed. */
  text: string;
  /** "CR", or the same suppressed text (suppressed states are not abbreviated). */
  abbr: string;
  color: string;
  state: LeanLabelState | "unscored";
  /** True when the numeric score must NOT be shown alongside the label. */
  suppressed: boolean;
}

export function storyLeanLabel(
  lean: number,
  spread?: WingCounts & { leanSpread?: number } | null,
  sourceCount = Number.POSITIVE_INFINITY,
  unscored = false,
): StoryLeanLabel {
  if (unscored) {
    /* --fg-muted, not --fg-tertiary: the label is 8px on a card that sits at
       85% opacity while it settles, and tertiary read 3.7:1 there (2026-09-21). */
    return { text: "Unscored", abbr: "Unscored", color: "var(--fg-muted)",
             state: "unscored", suppressed: true };
  }
  const state = leanLabelState(lean, spread, sourceCount);
  if (state === "unmeasured") {
    return { text: UNMEASURED_LABEL, abbr: UNMEASURED_LABEL,
             color: "var(--fg-muted)", state, suppressed: true };
  }
  if (state === "balanced") {
    return { text: BALANCED_LABEL, abbr: BALANCED_LABEL,
             color: "var(--fg-muted)", state, suppressed: true };
  }
  if (state === "contested") {
    /* --fg-primary, not --sense-high: see leanShapeColor. #EF4444 is the
       sensationalism scale's top stop and measures 3.16:1 as text on the
       light paper. */
    return { text: CONTESTED_LABEL, abbr: CONTESTED_LABEL,
             color: "var(--fg-primary)", state, suppressed: true };
  }
  return {
    text: leanLabel(lean),
    abbr: leanLabelAbbr(lean),
    color: getSigilLeanColor(lean, spread?.leanSpread ?? 0,
                             spread?.aggregateConfidence ?? 1),
    state,
    suppressed: false,
  };
}

/* ── CSS variable cache — single observer ───────────────────────────────── */

const SSR_FALLBACK: Record<string, string> = {
  "--bias-far-left": "#0E2E70",
  "--bias-left": "#1B5298",
  "--bias-center-left": "#2E78B4",
  "--bias-center": "#2B784A",
  "--bias-center-right": "#C4503E",
  "--bias-right": "#9C2C22",
  "--bias-far-right": "#6E1610",
  "--sense-low": "#22C55E",
  "--sense-medium": "#EAB308",
  "--sense-high": "#EF4444",
  "--type-reporting": "#3B82F6",
  "--type-analysis": "#8B5CF6",
  "--type-opinion": "#F97316",
  "--rigor-high": "#22C55E",
  "--rigor-medium": "#EAB308",
  "--rigor-low": "#EF4444",
};

let cache: Record<string, string> | null = null;

export function getColors(): Record<string, string> {
  if (cache) return cache;
  if (typeof document === "undefined") return SSR_FALLBACK;
  const style = getComputedStyle(document.documentElement);
  cache = {};
  for (const v of Object.keys(SSR_FALLBACK)) {
    cache[v] = style.getPropertyValue(v).trim() || SSR_FALLBACK[v];
  }
  return cache;
}

// Single MutationObserver for theme changes
if (typeof window !== "undefined") {
  new MutationObserver((ms) => {
    for (const m of ms) {
      if (m.type === "attributes" && m.attributeName === "data-mode") {
        cache = null;
      }
    }
  }).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-mode"],
  });
}

/* ── Color interpolation ────────────────────────────────────────────────── */

export function lerpColor(a: string, b: string, t: number): string {
  const ah = parseInt(a.replace("#", ""), 16);
  const bh = parseInt(b.replace("#", ""), 16);
  const ar = (ah >> 16) & 0xff, ag = (ah >> 8) & 0xff, ab = ah & 0xff;
  const br = (bh >> 16) & 0xff, bg = (bh >> 8) & 0xff, bb = bh & 0xff;
  const r = Math.round(ar + (br - ar) * t);
  const g = Math.round(ag + (bg - ag) * t);
  const bl = Math.round(ab + (bb - ab) * t);
  return `#${((r << 16) | (g << 8) | bl).toString(16).padStart(6, "0")}`;
}

/* ── Semantic color getters ─────────────────────────────────────────────── */

/** Half-width of the green "strictly balanced" band, in the 0-100 space passed
 *  to getLeanColor. Green renders only within 50 ± this; everything else is a
 *  continuous light→dark blue (left) / red (right) ramp. */
export const GREEN_HALF = 3;

export function getLeanColor(v: number): string {
  /* A color-mix() of the tokens rather than a hex: the server has no
     stylesheet, so a hex computed there is the LIGHT palette baked into the
     HTML, which is what the About page's demo Sigil shipped in dark mode
     (rgb(17,54,121) on a dark ground, 1.5:1). A mix of var()s is the same
     string on both sides and takes the mode's value when painted. */
  const c = {
    "--bias-center": "var(--bias-center)",
    "--bias-center-left": "var(--bias-center-left)",
    "--bias-left": "var(--bias-left)",
    "--bias-far-left": "var(--bias-far-left)",
    "--bias-center-right": "var(--bias-center-right)",
    "--bias-right": "var(--bias-right)",
    "--bias-far-right": "var(--bias-far-right)",
  };
  const lerp = (a: string, b: string, t: number) =>
    `color-mix(in srgb, ${a} ${Math.round((1 - t) * 100)}%, ${b})`;
  // Green is reserved for STRICTLY balanced (50 ± GREEN_HALF). Outside that,
  // a continuous light→dark ramp: left = center-left → left → far-left (light
  // steel blue to navy); right = center-right → right → far-right (coral to
  // dark red). Magnitude of tilt drives darkness, so a slight tilt is a light
  // shade and an extreme tilt is the darkest. (Callers may pass an expanded
  // display position — see leanToDisplayPos — so near-center tilt is visible.)
  const d = v - 50;
  if (Math.abs(d) <= GREEN_HALF) return c["--bias-center"];
  const t = (Math.abs(d) - GREEN_HALF) / (50 - GREEN_HALF); // 0 (just off center) → 1 (extreme)
  if (d < 0) {
    // Left — light → dark blue across two stops.
    return t <= 0.5
      ? lerp(c["--bias-center-left"], c["--bias-left"], t / 0.5)
      : lerp(c["--bias-left"], c["--bias-far-left"], (t - 0.5) / 0.5);
  }
  // Right — light → dark red across two stops.
  return t <= 0.5
    ? lerp(c["--bias-center-right"], c["--bias-right"], t / 0.5)
    : lerp(c["--bias-right"], c["--bias-far-right"], (t - 0.5) / 0.5);
}

/** leanSpread (stddev) at/above which a cluster's coverage counts as divergent. */
export const DIVERGENT_SPREAD_MIN = 10;

/**
 * At-a-glance lean color for the Sigil. Identical to getLeanColor of the
 * expanded display position, EXCEPT a balanced-but-divergent story (a
 * contested standoff that merely averages to center) drops the green for a
 * neutral slate — green is reserved for GENUINE consensus (balanced AND
 * agreed). Tilted stories keep their blue/red hue regardless of spread; their
 * divergence is shown by the beam fan, not the color.
 */
export function getSigilLeanColor(lean: number, leanSpread: number, confidence = 1): string {
  const pos = leanToDisplayPos(lean, confidence);
  if (Math.abs(pos - 50) <= GREEN_HALF && leanSpread >= DIVERGENT_SPREAD_MIN) {
    return "var(--fg-secondary)";
  }
  return getLeanColor(pos);
}

export function getCoverageColor(v: number): string {
  const c = getColors();
  if (v >= 60) return c["--sense-low"];
  if (v >= 30) return c["--sense-medium"];
  return c["--sense-high"];
}

export function getSenseColor(v: number): string {
  const c = getColors();
  if (v <= 50) return lerpColor(c["--sense-low"], c["--sense-medium"], v / 50);
  return lerpColor(c["--sense-medium"], c["--sense-high"], (v - 50) / 50);
}

export function getRigorColor(v: number): string {
  const c = getColors();
  if (v <= 50) return lerpColor(c["--rigor-low"], c["--rigor-medium"], v / 50);
  return lerpColor(c["--rigor-medium"], c["--rigor-high"], (v - 50) / 50);
}

export function getFramingColor(v: number): string {
  return getSenseColor(v);
}
