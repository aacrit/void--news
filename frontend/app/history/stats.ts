/* ===========================================================================
   history/stats.ts — "By the Numbers"

   Lifted verbatim out of EventDetail when the event page became the Hearing,
   so one derivation serves both: the reel (still mounted from the landing
   overlay) and the Hearing's end matter, where the stat strip now lives. A
   second copy would drift, and two pages disagreeing about how many died is
   the one thing this section cannot afford.
   =========================================================================== */

import type { HistoricalEvent } from "./types";

export type StatVariant = "figure" | "text";
export interface StatCell {
  key: string;
  label: string;
  value: string;   // the large display string
  fine?: string;   // fine-print qualifier
  variant: StatVariant;
}

/* ===========================================================================
   "By the Numbers" — stat derivation
   Every value is derived from the existing fact strings; no data is invented.
   Each stat leads with a big, abbreviated magnitude (3.5 million -> "3.5M",
   ~21,000 -> "~21K", 46 years -> "46 yrs"); the full detail rides in a
   fine-print qualifier line below it. Prose-led or number-less strings fall
   back to a legible "text" cell so nothing renders as a giant wall of words.
   =========================================================================== */

/* Em / en dashes are banned in written output; normalize to commas. */
function tidy(s: string): string {
  return s
    .replace(/[—–]/g, ", ")
    .replace(/\s*\(/g, ", ")
    .replace(/\)/g, "")
    .replace(/,\s*,/g, ",")
    .replace(/\s+/g, " ")
    .replace(/\s+([,;:.])/g, "$1")
    .replace(/^[\s,;:.]+/, "")
    .trim();
}

function truncate(s: string, max: number): string {
  if (s.length <= max) return s;
  const cut = s.slice(0, max);
  const sp = cut.lastIndexOf(" ");
  return (sp > max * 0.6 ? cut.slice(0, sp) : cut).replace(/[\s,;:.]+$/, "") + "…";
}

/* Round to at most one decimal, dropping a trailing ".0". */
function shortNum(x: number): string {
  const r = Math.round(x * 10) / 10;
  return Number.isInteger(r) ? String(r) : r.toFixed(1);
}

function compact(n: number): string {
  const a = Math.abs(n);
  if (a >= 1e9) return shortNum(n / 1e9) + "B";
  if (a >= 1e6) return shortNum(n / 1e6) + "M";
  if (a >= 1e3) return shortNum(n / 1e3) + "K";
  return String(Math.round(n));
}

function scaleOf(word?: string): number {
  if (!word) return 1;
  const w = word.toLowerCase();
  if (w.startsWith("bill") || w === "bn") return 1e9;
  if (w.startsWith("mill")) return 1e6;
  if (w.startsWith("thou")) return 1e3;
  return 1;
}

function abbrevOne(numStr: string, scaleWord?: string): string {
  const n = parseFloat(numStr.replace(/,/g, ""));
  if (!isFinite(n)) return numStr;
  return compact(n * scaleOf(scaleWord));
}

/* Merge a range so a shared magnitude suffix isn't repeated: "75M"+"200M" -> "75-200M". */
function mergeRange(a: string, b: string, prefix: string): string {
  const sa = /[KMB]$/.exec(a);
  const sb = /[KMB]$/.exec(b);
  if (sa && sb && sa[0] === sb[0]) return `${prefix}${a.slice(0, -1)}-${b}`;
  return `${prefix}${a}-${b}`;
}

const _NUM = "\\d[\\d,]*(?:\\.\\d+)?";
const _SCALE = "(?:thousand|million|billion|bn)";
const _APPROX = /^(?:~|≈|about|around|approx(?:imately)?|over|nearly|est(?:imated)?|roughly|up to)\s*/i;

/* Pull a leading (or scale-qualified) magnitude out of a messy fact string.
   Returns null when no usable number is present (caller renders a text cell). */
function deriveMagnitude(raw: string): { value: string; fine: string } | null {
  let s = raw.trim();
  let prefix = "";
  const am = _APPROX.exec(s);
  if (am) { prefix = "~"; s = s.slice(am[0].length); }

  const rangeAnchored = new RegExp(`^(${_NUM})\\s*(${_SCALE})?\\s*(?:[-–—]|to)\\s*(${_NUM})\\s*(${_SCALE})?`, "i");
  const singleAnchored = new RegExp(`^(${_NUM})\\s*(${_SCALE})?`, "i");
  const rangeAnywhere = new RegExp(`(${_NUM})\\s*(${_SCALE})?\\s*(?:[-–—]|to)\\s*(${_NUM})\\s*(${_SCALE})`, "i");
  const singleAnywhere = new RegExp(`(${_NUM})\\s*(${_SCALE})`, "i");

  let m: RegExpExecArray | null;
  let value = "";
  let matchEnd = -1;

  if ((m = rangeAnchored.exec(s))) {
    const shared = m[4] || m[2];
    value = mergeRange(abbrevOne(m[1], m[2] || shared), abbrevOne(m[3], m[4] || shared), prefix);
    matchEnd = m[0].length;
  } else if (/^\d/.test(s) && (m = singleAnchored.exec(s))) {
    value = prefix + abbrevOne(m[1], m[2]);
    matchEnd = m[0].length;
  } else if ((m = rangeAnywhere.exec(s))) {
    const shared = m[4] || m[2];
    value = mergeRange(abbrevOne(m[1], m[2] || shared), abbrevOne(m[3], m[4] || shared), "");
  } else if ((m = singleAnywhere.exec(s))) {
    value = abbrevOne(m[1], m[2]);
  } else {
    return null;
  }

  const rest = matchEnd >= 0 ? s.slice(matchEnd) : s.replace(m[0], " ");
  const fine = truncate(
    tidy(rest).replace(/^(?:people|persons|killed|dead|deaths|of)\s+/i, ""),
    58
  );
  return { value, fine };
}

/* The Span cell: a duration count leads ("46 yrs"); the year range is fine print.
   Falls back to a bare year range or the raw date when no count is present. */
function deriveSpan(raw: string): { value: string; fine: string } {
  const s = raw.trim();
  const dur = /(\d[\d,.]*)\s*(year|yr|day|month|week|decade|centur)/i.exec(s);
  const yrRange = /(\d{1,4})\s*(BCE|BC|CE|AD)?\s*[-–—]\s*(\d{1,4})\s*(BCE|BC|CE|AD)?/i.exec(s);
  const paren = /\(([^)]+)\)/.exec(s);

  const yrText = yrRange
    ? tidy(`${yrRange[1]}${yrRange[2] ? " " + yrRange[2] : ""}-${yrRange[3]}${yrRange[4] ? " " + yrRange[4] : ""}`)
    : "";

  if (dur) {
    const u = dur[2].toLowerCase();
    const unit = /year|yr/.test(u) ? "yrs"
      : /day/.test(u) ? "days"
      : /month/.test(u) ? "mos"
      : /week/.test(u) ? "wks"
      : /decade/.test(u) ? "decades"
      : "centuries";
    const fine = yrText || (paren ? truncate(tidy(paren[1]), 32) : "");
    return { value: `${dur[1]} ${unit}`, fine };
  }
  if (yrRange) {
    return { value: yrText, fine: paren ? truncate(tidy(paren[1]), 32) : "" };
  }
  const singleYr = /\d{1,4}\s*(?:BCE|BC|CE|AD)\b|\d{3,4}/i.exec(s);
  if (singleYr) {
    return { value: singleYr[0].trim(), fine: paren ? truncate(tidy(paren[1]), 32) : "" };
  }
  return { value: truncate(tidy(s), 20), fine: "" };
}

function figureOrText(key: string, label: string, raw: string): StatCell {
  const m = deriveMagnitude(raw);
  if (m) return { key, label, value: m.value, fine: m.fine, variant: "figure" };
  return { key, label, value: truncate(tidy(raw), 40), variant: "text" };
}

/** The stat cells for one event, in reading order. Only facts that exist. */
export function deriveStats(event: HistoricalEvent): StatCell[] {
  const cells: StatCell[] = [];
  const dateRaw = event.dateRange || event.datePrimary;
  if (dateRaw) {
    const span = deriveSpan(dateRaw);
    cells.push({ key: "span", label: "Span", value: span.value, fine: span.fine, variant: "figure" });
  }
  if (event.deathToll && event.deathToll !== "N/A") {
    cells.push(figureOrText("killed", "Killed", event.deathToll));
  }
  if (event.displaced && event.displaced !== "N/A") {
    cells.push(figureOrText("displaced", "Displaced", event.displaced));
  }
  if (event.location) {
    cells.push({ key: "place", label: "Place", value: event.location, variant: "text" });
  }
  return cells;
}
