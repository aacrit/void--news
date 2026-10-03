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
