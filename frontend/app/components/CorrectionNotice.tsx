/* ---------------------------------------------------------------------------
   CorrectionNotice: the page says it was corrected, and when.

   One line per correction, on the page that was corrected and nowhere else
   (CEO, 2026-10-03: corrections are internal at the site level, so there is
   no /corrections page, but a reader of a corrected story is told on it).
   The entries come from the export: pipeline/editorial/corrections.json for a
   published correction, and the archive repair for a card that carried a
   sentence from another story. Each reads "Corrected <date>: <reason>."

   Deterministic: the date is formatted from its ISO string in UTC, no clock.
   --------------------------------------------------------------------------- */

export interface CorrectionNote {
  /** ISO date of the correction (YYYY-MM-DD). */
  date: string;
  /** What was corrected: card, deepdive, brief, opinion or radio. */
  product?: string;
  /** The short public reason, lower case, no closing stop. */
  notice: string;
}

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

function longDate(iso: string): string {
  const [y, m, d] = (iso || "").slice(0, 10).split("-").map(Number);
  if (!y || !m || !d || m < 1 || m > 12) return "";
  return `${MONTHS[m - 1]} ${d}, ${y}`;
}

/** The notes worth printing, oldest first, each once. */
export function correctionLines(notes: readonly CorrectionNote[] | null | undefined): string[] {
  if (!Array.isArray(notes)) return [];
  const seen = new Set<string>();
  return [...notes]
    .filter((n) => n && typeof n.notice === "string" && n.notice.trim() && longDate(n.date))
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((n) => {
      const reason = n.notice.trim().replace(/[.\s]+$/, "");
      return `Corrected ${longDate(n.date)}: ${reason}.`;
    })
    .filter((line) => (seen.has(line) ? false : (seen.add(line), true)));
}

export default function CorrectionNotice({
  notes,
  className,
}: {
  notes: readonly CorrectionNote[] | null | undefined;
  className?: string;
}) {
  const lines = correctionLines(notes);
  if (lines.length === 0) return null;
  return (
    <aside className={`correction-notice${className ? ` ${className}` : ""}`} aria-label="Correction">
      {lines.map((line) => (
        <p key={line} className="correction-notice__line">{line}</p>
      ))}
    </aside>
  );
}
