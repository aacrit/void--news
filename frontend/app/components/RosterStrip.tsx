"use client";

import { useMemo } from "react";
import { leanShape, type WingCounts } from "../lib/biasColors";

/* ---------------------------------------------------------------------------
   RosterStrip — seven hairline strokes on a rule, one per lean bucket.

   The card used to print a single 0-100 number and hide it whenever the
   engine was not confident, which on the 2026-09-21 feed was 20 stories out
   of 35: the product's differentiator silent on more than half the paper.

   The number was also the wrong summary. The real distributions are often
   bimodal, and a mean returns their empty middle: 7 left / 2 centre / 8 right
   and 0 left / 11 centre / 2 right both average to about 50, so a hollow
   centre and a genuine consensus printed the same figure.

   A distribution never has to be withheld. Where the ink stands is the
   direction, how tall the strip stands is how much coverage there is, and an
   empty bucket keeps a faint tick so absence reads as absence rather than as
   nothing. Register marks, not a chart: 1px strokes, no axis, no legend.

   Two independent encodings that do not destroy each other. Linear height
   with a cap flattened the biggest stories (a bucket of 26 and one of 11 both
   hit the ceiling); pure normalising made two articles stand as tall as
   twenty-six. So the strip's overall height comes from the sample size and
   the bars are normalised inside it.
   --------------------------------------------------------------------------- */

const TOKENS = [
  "--bias-far-left", "--bias-left", "--bias-center-left", "--bias-center",
  "--bias-center-right", "--bias-right", "--bias-far-right",
] as const;

const NAMES = [
  "far left", "left", "centre left", "centre",
  "centre right", "right", "far right",
] as const;

export interface RosterStripProps {
  spread?: WingCounts & { leanBuckets?: readonly number[] } | null;
  /** Stroke width in px. 1 on a card, 2 in a Deep Dive header. */
  weight?: 1 | 2;
  className?: string;
}

export default function RosterStrip({ spread, weight = 1, className }: RosterStripProps) {
  const counts = useMemo<number[]>(() => {
    const b = spread?.leanBuckets;
    return b && b.length === 7 ? b.map((n: number) => Math.max(0, Math.round(n))) : [];
  }, [spread]);

  const total = counts.reduce((a, b) => a + b, 0);
  if (total <= 0) return null;

  const gap = weight === 1 ? 7 : 12;
  const box = weight === 1 ? 16 : 26;
  const width = gap * 6 + weight;
  const peak = Math.max(3, Math.min(box, Math.round(2.6 * Math.sqrt(total))));
  const tallest = Math.max(...counts) || 1;
  const shape = leanShape(spread);

  /* Spoken in full, because the strip itself is decoration to a screen
     reader: the counts are the content. */
  const label = counts
    .map((n, i) => (n ? `${n} ${NAMES[i]}` : null))
    .filter(Boolean)
    .join(", ");

  return (
    <svg
      className={["roster", `roster--${shape}`, className].filter(Boolean).join(" ")}
      width={width}
      height={box + 5}
      viewBox={`0 0 ${width} ${box + 5}`}
      role="img"
      aria-label={`${total} measured ${total === 1 ? "article" : "articles"}: ${label}`}
    >
      <rect x={0} y={box + 2} width={width} height={0.75} className="roster__rule" />
      {counts.map((n, i) => {
        const x = i * gap;
        if (!n) {
          /* An empty bucket keeps a tick. Without it a gap reads as the strip
             ending rather than as no coverage at that position. */
          return (
            <rect key={i} x={x} y={box + 1.25} width={weight} height={1.5}
              className="roster__tick" />
          );
        }
        const h = Math.max(2.5, (peak * n) / tallest);
        return (
          <rect key={i} x={x} y={box + 2 - h} width={weight} height={h}
            style={{ fill: `var(${TOKENS[i]})` }} />
        );
      })}
    </svg>
  );
}
