/* ---------------------------------------------------------------------------
   void --weekly — pure formatting. No React, no Date.now(), no locale.

   Every date string here is built from the ISO parts by hand. The previous
   helpers did `new Date(start + "T00:00:00").toLocaleDateString("en-US", ...)`,
   which is only ACCIDENTALLY hydration-safe: the local parse and the local read
   happen to cancel out. serverFeed.ts sets the house rule (bake a
   UTC-deterministic string at build, never call new Date() for a rendered value
   during render), and now that these pages prerender, following it removes a
   whole class of React #418.
   --------------------------------------------------------------------------- */

const MONTHS = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];
const MONTHS_SHORT = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

/** "2026-09-14" -> [2026, 9, 14], or null when unparseable. */
function parts(iso: string): [number, number, number] | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec((iso || "").trim());
  if (!m) return null;
  const [y, mo, d] = [Number(m[1]), Number(m[2]), Number(m[3])];
  if (mo < 1 || mo > 12 || d < 1 || d > 31) return null;
  return [y, mo, d];
}

/** "September 14 to 20, 2026" — collapsed when the week stays in one month. */
export function formatWeekRange(start: string, end: string): string {
  const a = parts(start);
  const b = parts(end);
  if (!a || !b) return "";
  const [ay, am, ad] = a;
  const [by, bm, bd] = b;
  if (ay === by && am === bm) return `${MONTHS[am - 1]} ${ad} to ${bd}, ${ay}`;
  if (ay === by) return `${MONTHS[am - 1]} ${ad} to ${MONTHS[bm - 1]} ${bd}, ${ay}`;
  return `${MONTHS[am - 1]} ${ad}, ${ay} to ${MONTHS[bm - 1]} ${bd}, ${by}`;
}

/** "Sep 14 to 20" for the compact back-issue list. No en dash: the
    dash ban in CLAUDE.md covers frontend microcopy, and this string renders
    in every Back Issues row. */
export function formatArchiveRange(start: string, end: string): string {
  const a = parts(start);
  const b = parts(end);
  if (!a || !b) return "";
  const [, am, ad] = a;
  const [, bm, bd] = b;
  if (am === bm) return `${MONTHS_SHORT[am - 1]} ${ad} to ${bd}`;
  return `${MONTHS_SHORT[am - 1]} ${ad} to ${MONTHS_SHORT[bm - 1]} ${bd}`;
}

/* The DB issue number counts from the generator's 2026-03-22 epoch, but the
   section only launched publicly at issue 19, so #19 is the reader's #1. */
export const WEEKLY_LAUNCH_ISSUE = 19;

export function weeklyDisplayNo(n: number): number {
  return Math.max(1, (n ?? 0) - WEEKLY_LAUNCH_ISSUE + 1);
}

/** "08" — the folio number on every department plate. */
export function issueFolio(n: number): string {
  return String(weeklyDisplayNo(n)).padStart(2, "0");
}

/* The three lenses, named the way the section names them. */
export function leanBadgeLabel(lean: string): string {
  const l = (lean || "").toLowerCase();
  if (l.startsWith("left")) return "Progressive";
  if (l.startsWith("right")) return "Conservative";
  if (l === "center-left") return "Center-Left";
  if (l === "center-right") return "Center-Right";
  return "Pragmatic";
}

export function leanToBiasVar(lean: string): string {
  const l = (lean || "").toLowerCase();
  if (l.startsWith("left")) return "var(--bias-left)";
  if (l.startsWith("right")) return "var(--bias-right)";
  if (l === "center-left") return "var(--bias-center-left)";
  if (l === "center-right") return "var(--bias-center-right)";
  return "var(--bias-center)";
}

/* Defensive scrubber: early generator versions baked a bulleted TIMELINE block
   into the essay body. The prompt forbids it now, but published rows still
   carry it. */
export function stripTimelineFromText(text: string): string {
  if (!text) return "";
  return text
    .split("\n\n")
    .filter((block) => {
      const t = block.trim();
      if (/^#{0,3}\s*\**\s*TIMELINE\b/i.test(t)) return false;
      const lines = t.split("\n").filter(Boolean);
      return !(lines.length > 1 && lines.every((l) => /^\s*[-*•]/.test(l)));
    })
    .join("\n\n");
}

/** Paragraphs of an essay, with the timeline block scrubbed. */
export function essayParagraphs(text: string): string[] {
  return stripTimelineFromText(text || "")
    .split("\n\n")
    .map((p) => p.trim())
    .filter(Boolean);
}

/** One sentence worth setting large. Skips the lede, which is already set. */
export function pickPullQuote(text: string): string {
  const paras = essayParagraphs(text);
  if (paras.length < 2) return "";
  const sentences = paras
    .slice(1)
    .join(" ")
    .split(/(?<=[.!?])\s+/)
    .map((s) => s.trim())
    .filter(Boolean);
  return (
    sentences.find((s) => s.length >= 70 && s.length <= 150) ||
    sentences.find((s) => s.length >= 45 && s.length <= 200) ||
    ""
  );
}

/** A number the way a magazine sets one: "2,637". */
export function groupDigits(n: number | null | undefined): string {
  if (n === null || n === undefined || !Number.isFinite(n)) return "n/a";
  return Math.round(n).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/** First ~n characters on a word boundary, for meta descriptions. */
export function clip(text: string, n = 160): string {
  const t = (text || "").replace(/\s+/g, " ").trim();
  if (t.length <= n) return t;
  const cut = t.slice(0, n);
  return cut.slice(0, cut.lastIndexOf(" ")).replace(/[,;:]$/, "") + "…";
}
