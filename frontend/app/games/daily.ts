/* ==========================================================================
   Games: the daily rotation, one definition.

   Every daily game holds a FIXED bank of puzzles and serves them in order,
   one per UTC day, wrapping when the bank runs out. The bank is not keyed to
   calendar dates, so it cannot "run out" and leave a blank day: day N is
   puzzle (N mod size). The pages say so in their copy ("No. 7 of 29. The set
   repeats."), because a rotation dressed as a fresh daily puzzle would be a
   claim the bank cannot support.

   The day turns at midnight UTC, the same instant the hub's "daily reset"
   countdown names.
   ========================================================================== */

const MS_PER_DAY = 86_400_000;

/** Whole UTC days since 1970-01-01 for the given instant. */
export function utcDayNumber(now: Date = new Date()): number {
  return Math.floor(now.getTime() / MS_PER_DAY);
}

/** Today's position in a bank of `size` puzzles. Deterministic by UTC date. */
export function rotationIndex(size: number, now: Date = new Date()): number {
  if (!Number.isInteger(size) || size <= 0) {
    throw new Error(`rotationIndex: bank size must be a positive integer, got ${size}`);
  }
  const day = utcDayNumber(now);
  return ((day % size) + size) % size;
}

/** "October 2, 2026" for the UTC day, independent of the reader's zone. */
export function utcDateLabel(now: Date = new Date()): string {
  return now.toLocaleDateString("en-US", {
    month: "long",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  });
}
