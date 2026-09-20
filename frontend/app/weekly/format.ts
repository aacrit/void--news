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

/* ---------------------------------------------------------------------------
   Volume and number.

   The DB `issue_number` counts weeks from the generator's 2026-03-22 epoch and
   is the sort key. It is NOT what a reader sees.

   Void Weekly launched as a Sunday magazine on 2026-09-20 with the week of
   September 14, which is epoch issue 26. That issue is Vol. I, No. 1. A volume
   is a year of publication, so numbers run 1 to 52 inside it and the volume
   turns over rather than the number climbing to 147.

   Issues published BEFORE the launch are pilots. They are kept and readable —
   the work was real and the archive should not lie about what exists — but
   they sit outside the volume numbering, because pretending the run started
   earlier than it did would be the same kind of unearned claim the section
   exists to catch. The old `weeklyDisplayNo` clamped with Math.max(1, ...),
   which would have collapsed every pilot onto No. 1 alongside the launch.
   --------------------------------------------------------------------------- */

/** Epoch issue number of Vol. I, No. 1: the week of 2026-09-14. */
export const WEEKLY_LAUNCH_ISSUE = 26;
export const WEEKS_PER_VOLUME = 52;

export interface IssueRef {
  /** Published before the volume system began. */
  pilot: boolean;
  /** 1-based volume; 0 for a pilot. */
  volume: number;
  /** 1-based number within the volume; 0 for a pilot. */
  number: number;
  /** Position in the whole run, 1-based; 0 for a pilot. Sorting only. */
  serial: number;
}

export function issueRef(raw: number | null | undefined): IssueRef {
  // `NaN < 1` is false, so a non-finite issue number would fall through to the
  // volume branch and print "Vol. NaN, No. NaN" on a cover. Checked first.
  const n = Number(raw);
  if (!Number.isFinite(n)) return { pilot: true, volume: 0, number: 0, serial: 0 };
  const serial = n - WEEKLY_LAUNCH_ISSUE + 1;
  if (serial < 1) return { pilot: true, volume: 0, number: 0, serial: 0 };
  return {
    pilot: false,
    volume: Math.floor((serial - 1) / WEEKS_PER_VOLUME) + 1,
    number: ((serial - 1) % WEEKS_PER_VOLUME) + 1,
    serial,
  };
}

const ROMAN: Array<[number, string]> = [
  [1000, "M"], [900, "CM"], [500, "D"], [400, "CD"], [100, "C"], [90, "XC"],
  [50, "L"], [40, "XL"], [10, "X"], [9, "IX"], [5, "V"], [4, "IV"], [1, "I"],
];

/** Volumes are set in roman, numbers in arabic. That is the convention, and it
    is also what stops "Vol. 1, No. 1" from reading as a version string. */
export function romanNumeral(n: number): string {
  if (!Number.isFinite(n) || n < 1) return "";
  let out = "";
  let left = Math.floor(n);
  for (const [v, sym] of ROMAN) {
    while (left >= v) {
      out += sym;
      left -= v;
    }
  }
  return out;
}

/** "Vol. I, No. 1" — the full label, for the cover and the share card. */
export function issueLabel(raw: number | null | undefined): string {
  const r = issueRef(raw);
  if (r.pilot) return "Pilot issue";
  return `Vol. ${romanNumeral(r.volume)}, No. ${r.number}`;
}

/** "I.01" — the folio on every department plate, where space is one line. */
export function issueFolio(raw: number | null | undefined): string {
  const r = issueRef(raw);
  if (r.pilot) return "Pilot";
  return `${romanNumeral(r.volume)}.${String(r.number).padStart(2, "0")}`;
}

/** "No. 1" / "Pilot" — the compact form for an index row or a back-issue line. */
export function issueShort(raw: number | null | undefined): string {
  const r = issueRef(raw);
  return r.pilot ? "Pilot" : `No. ${r.number}`;
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
