/* ---------------------------------------------------------------------------
   weeklyAudio: is an issue's recording withdrawn?

   A pure reader over the corrections file (build-data/weekly-corrections.json,
   hand-maintained), shared by /audio (a server component) and the Weekly issue
   (a client component), so the two can never disagree about the same issue.

   The corrections file is the record of the withdrawal. A row may say so in
   structure (`audio: "withdrawn"`), and the one written on 2026-10-01 says so
   in its prose ("The audio edition is withdrawn"), which is read as well, so
   the page states what the correction states and nothing a hand typed beside
   it. Until 2026-10-02 /audio printed "No issue has been recorded yet" over
   an issue that had been recorded and then withdrawn (audit 2 F3).
   --------------------------------------------------------------------------- */

export interface CorrectionLike {
  week_start: string;
  corrected_on?: string;
  text: string;
  audio?: string;
}

const WITHDRAWN = /\b(audio|recording)\b[^.]*\bwithdrawn\b/i;

/** The correction that withdrew this week's recording, or null. */
export function audioWithdrawal<T extends CorrectionLike>(corrections: readonly T[], week: string): T | null {
  return (
    corrections.find(
      (c) => c.week_start === week && (c.audio === "withdrawn" || WITHDRAWN.test(c.text)),
    ) ?? null
  );
}
