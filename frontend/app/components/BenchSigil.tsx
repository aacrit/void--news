"use client";

import {
  leanShape,
  leanShapeColor,
  leanShapeLabel,
  leanShareTilt,
  type WingCounts,
} from "../lib/biasColors";
import {
  SIGIL_VIEWBOX, SIGIL_CX, SIGIL_CY, SIGIL_R,
  SIGIL_BEAM_X1, SIGIL_BEAM_X2, SIGIL_STROKE,
  SIGIL_ARM_L, SIGIL_ARM_R,
  beamAngle, splitAngles,
} from "../lib/sigilGeometry";

/* ---------------------------------------------------------------------------
   BenchSigil — the mark, standing in the room the distribution leaves.

   WHAT IT REPLACES. The Bench printed its verdict as a line of text above the
   columns: "Leans Right". A word set in a heading is the one thing on this
   panel that is not drawn from the data in front of it, and next to a
   silhouette that already says which way the weight falls it is a caption for
   a picture the reader can see.

   So the word goes to the screen reader, where it is the content, and the
   space goes to the mark, where the shape is.

   WHY THE ROOM IS THE RIGHT PLACE, and not a corner. Where a roster leans,
   the far side of the Bench is empty, and that emptiness is the same fact the
   columns are stating. Putting the mark there means its POSITION carries the
   reading too: on a right-leaning story it sits out on the left, over nothing,
   with the mass to its right. `benchCurve.whitespace` finds that room, and
   returns null rather than a cramped box, so a flat distribution gets the mark
   back in the head instead of a 14px smudge between two columns.

   IT IS THE SAME MARK, not a second one. State comes from `leanShape` and
   colour from `leanShapeColor`, which is what the card's Sigil and its
   register already read, so the four states mean the same thing on every
   surface. The geometry is `lib/sigilGeometry.ts`, shared with the Sigil and
   asserted against it. The tilt is `leanShareTilt`, the roster's own tilt over
   its wings, never a mean: the Bench's whole argument is that a mean returns
   the empty middle of a bimodal roster.

   It is decoration to a screen reader. The columns carry the counts, the
   Bench's own label carries the shape word, and this repeats both.
   --------------------------------------------------------------------------- */

export interface BenchSigilProps {
  spread?: WingCounts | null;
  /** Rendered side in px. The mark is square. */
  size: number;
  className?: string;
}

export default function BenchSigil({ spread, size, className }: BenchSigilProps) {
  const shape = leanShape(spread);
  const ink = leanShapeColor(spread);
  const label = leanShapeLabel(spread);

  const left = spread?.leanLeftCount ?? 0;
  const right = spread?.leanRightCount ?? 0;
  const arms = splitAngles(left, right);
  const angle = shape === "leans" ? beamAngle(leanShareTilt(spread)) : 0;

  const pivot = `${SIGIL_CX}px ${SIGIL_CY}px`;

  return (
    <svg
      className={["bsig", `bsig--${shape}`, className].filter(Boolean).join(" ")}
      width={size}
      height={size}
      viewBox={SIGIL_VIEWBOX}
      fill="none"
      strokeLinecap="round"
      aria-hidden="true"
      focusable="false"
      data-shape={shape}
      data-label={label}
      style={{ color: ink }}
    >
      {/* The void. Held back, because it is the room the mark sits in, not
          the reading: the beam is the reading. */}
      <circle
        className="bsig__ring"
        cx={SIGIL_CX}
        cy={SIGIL_CY}
        r={SIGIL_R}
        strokeWidth={SIGIL_STROKE}
      />

      {shape === "split" ? (
        <g className="bsig__split">
          <g style={{ transformOrigin: pivot, transform: `rotate(${arms.left}deg)` }}>
            <line
              x1={SIGIL_ARM_L[0]} y1={SIGIL_CY} x2={SIGIL_ARM_L[1]} y2={SIGIL_CY}
              stroke="var(--bias-left)" strokeWidth={SIGIL_STROKE}
            />
          </g>
          <g style={{ transformOrigin: pivot, transform: `rotate(${arms.right}deg)` }}>
            <line
              x1={SIGIL_ARM_R[0]} y1={SIGIL_CY} x2={SIGIL_ARM_R[1]} y2={SIGIL_CY}
              stroke="var(--bias-right)" strokeWidth={SIGIL_STROKE}
            />
          </g>
          {/* The hollow, stated rather than left blank: a parted beam with
              nothing between the arms reads as a broken one. */}
          <line
            className="bsig__hollow"
            x1={SIGIL_ARM_L[1] + 0.6} y1={SIGIL_CY}
            x2={SIGIL_ARM_R[0] - 0.6} y2={SIGIL_CY}
            strokeWidth={1}
          />
        </g>
      ) : (
        <g
          className="bsig__beam"
          style={{ transformOrigin: pivot, transform: `rotate(${angle}deg)` }}
        >
          <line
            x1={SIGIL_BEAM_X1} y1={SIGIL_CY} x2={SIGIL_BEAM_X2} y2={SIGIL_CY}
            stroke="currentcolor"
            strokeWidth={SIGIL_STROKE}
            /* Thin is not a reading, and it does not pretend to be one. */
            strokeDasharray={shape === "thin" ? "3 2.5" : undefined}
          />
        </g>
      )}

      {/* Consensus is a claim about the centre, so the centre is marked. */}
      {shape === "consensus" && (
        <circle
          className="bsig__centre"
          cx={SIGIL_CX} cy={SIGIL_CY} r={1.9}
          fill="currentcolor" stroke="none"
        />
      )}
    </svg>
  );
}
