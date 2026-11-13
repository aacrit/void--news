/* ===========================================================================
   verification.ts: whether a derived product's sentences were read against
   the stories they came from.

   The pipeline reads every TL;DR, Opinion and On Air sentence against its own
   story and cuts what that story does not carry
   (pipeline/editorial/derived_grounding.py). When that pass cannot complete,
   the product still ships, with a visible label (CEO, 2026-10-03: label
   rather than withhold). brief.json carries the flag per product as
   `grounding_ran: { tldr, opinion, onair }`.

   Only an explicit `false` labels. A missing flag is a brief written before
   the flag existed (2026-10-02 and earlier): unknown, and not claimed either
   way. tests/test_rigor.py F-3 fails a run that ships a product whose pass did
   not complete when this label is not wired to it.
   =========================================================================== */

export type VerifiedProduct = "tldr" | "opinion" | "onair";

export type GroundingFlags = Partial<Record<VerifiedProduct, boolean | null>>;

export const UNVERIFIED_LABEL = "Not yet verified";

export const UNVERIFIED_TITLE =
  "These sentences were not read against the stories they came from on this run.";

/** The flags off a brief, whatever shape the export handed us. */
export function groundingFlags(
  brief: { grounding_ran?: GroundingFlags | string | null } | null | undefined,
): GroundingFlags | null {
  const g = brief?.grounding_ran;
  if (!g) return null;
  if (typeof g === "string") {
    try {
      const parsed = JSON.parse(g);
      return parsed && typeof parsed === "object" ? (parsed as GroundingFlags) : null;
    } catch {
      return null;
    }
  }
  return typeof g === "object" ? g : null;
}

/** True only when the pipeline says the pass did NOT complete. */
export function isUnverified(
  brief: { grounding_ran?: GroundingFlags | string | null } | null | undefined,
  product: VerifiedProduct,
): boolean {
  return groundingFlags(brief)?.[product] === false;
}

/* ---------------------------------------------------------------------------
   When the text was WRITTEN. brief.json's created_at is when the row was
   stored; when the pipeline carries a brief or an opinion forward because
   no model answered, that is days after the text was written (Nov 4 to 7,
   2026: a three-day-old brief read "2h ago"). The pipeline writes
   `written_at` and `opinion_written_at` alongside; a brief from before the
   fields existed has neither and reads as written when stored.
   --------------------------------------------------------------------------- */

export type DatedBrief = {
  created_at?: string | null;
  written_at?: string | null;
  opinion_written_at?: string | null;
};

/** ISO time the TL;DR ("tldr") or the Opinion ("opinion") was written. */
export function writtenAt(brief: DatedBrief | null | undefined, product: "tldr" | "opinion"): string | null {
  if (!brief) return null;
  const own = product === "opinion" ? brief.opinion_written_at : brief.written_at;
  return own || brief.created_at || null;
}

/** True when the text was carried forward from an earlier edition: written
 *  more than 20 hours before this edition was stored. */
export function isCarried(brief: DatedBrief | null | undefined, product: "tldr" | "opinion"): boolean {
  if (!brief?.created_at) return false;
  const w = writtenAt(brief, product);
  if (!w) return false;
  const stored = new Date(brief.created_at).getTime();
  const written = new Date(w).getTime();
  if (!isFinite(stored) || !isFinite(written)) return false;
  return stored - written > 20 * 3600 * 1000;
}

/** "Written Wednesday": the label a carried text wears, or null. */
export function carriedLabel(brief: DatedBrief | null | undefined, product: "tldr" | "opinion"): string | null {
  if (!isCarried(brief, product)) return null;
  const w = writtenAt(brief, product);
  if (!w) return null;
  const d = new Date(w);
  if (!isFinite(d.getTime())) return null;
  return `Written ${d.toLocaleDateString("en-US", { weekday: "long", timeZone: "UTC" })}`;
}
