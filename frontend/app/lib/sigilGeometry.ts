/* ---------------------------------------------------------------------------
   sigilGeometry.ts — the one set of numbers the mark is drawn from.

   The mark appears at three scales now: the Sigil on a card, the Sigil's
   popup, and the Bench, where it stands in the room the distribution leaves.
   Three drawings of one mark drift unless the numbers live in one place, and
   a mark that is 11 units across on a card and 10 in the Deep Dive is the
   same class of defect as a lean ladder with two implementations.

   `test/bench-curve.test.mjs` asserts Sigil.tsx still draws these exact
   values, by reading the file, so a change to one has to be a change to both.
   --------------------------------------------------------------------------- */

/** Every drawing of the mark is authored in this box. */
export const SIGIL_VIEWBOX = "0 0 32 32";
/** The pivot: the circle's centre, and the point the beam rotates about. */
export const SIGIL_CX = 16;
export const SIGIL_CY = 14;
export const SIGIL_R = 11;
/** The beam spans the circle, edge to edge. */
export const SIGIL_BEAM_X1 = 4;
export const SIGIL_BEAM_X2 = 28;
export const SIGIL_STROKE = 1.8;
/** Where a parted beam's two arms begin and end. The hollow is 14 to 18. */
export const SIGIL_ARM_L: [number, number] = [4, 14];
export const SIGIL_ARM_R: [number, number] = [18, 28];
/** Degrees at which the beam saturates. Past this a steeper angle says
 *  nothing more and starts to read as a graphic rather than a reading. */
export const SIGIL_MAX_TILT = 24;

/** Beam angle in degrees from a tilt in -1..+1. Positive is right-heavy,
 *  which in SVG is a positive rotation: the right end of the beam goes down. */
export function beamAngle(tilt: number): number {
  const t = Math.max(-1, Math.min(1, tilt || 0));
  return t * SIGIL_MAX_TILT;
}

/** The two arm angles for a parted beam, from the wing counts. A wing that
 *  outweighs the other drops further, so the parting leans as it opens. */
export function splitAngles(left: number, right: number): { left: number; right: number } {
  const total = left + right;
  if (total <= 0) return { left: 0, right: 0 };
  return {
    left: -SIGIL_MAX_TILT * (left / total),
    right: SIGIL_MAX_TILT * (right / total),
  };
}
