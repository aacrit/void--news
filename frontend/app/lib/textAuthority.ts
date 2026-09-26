/* ---------------------------------------------------------------------------
   textAuthority.ts — was this article's lean read, or was it assumed?

   WHAT THE PIPELINE ALREADY KNOWS. `political_lean` scores an article as

       score = baseline + clamp((text_score - 50), +/-delta_max) * confidence
       confidence = min(1.0, word_count / 150)

   so `confidence` is not a certainty. It is the share of the text's movement
   budget the article was long enough to earn. At 150 words or more it is 1.0
   and the whole of `delta_max` is available. At 11 words, the median of a
   Google-News-fed row, it is 0.07 and the published score is the outlet's
   baseline to within a rounding error.

   WHAT THE PAGE DID WITH IT. Nothing a reader could see. `confidence` is
   exported per article and reaches `DeepDive`, which folds it into a composite
   `coverage` number (60% rigor, 40% confidence) and hands the raw value to
   `DeepDiveSpectrum`, whose props declare it and whose body never reads it.
   `MobilePerspectivePeek` sorts by it. So a mark placed from a full article
   and a mark placed from a headline were drawn identically, at the same
   position, with the same tooltip.

   WHY THAT IS A RULE 1 PROBLEM AND NOT A POLISH ITEM. Measured 2026-09-23
   against run #375: 367 outlets have 20 or more articles and ZERO with 150
   words, and 13 of them are us_major. Associated Press, Reuters, the New York
   Times, the Washington Post, the Wall Street Journal, CNN, Bloomberg, USA
   Today, UPI, The Hill, Chicago Tribune, HuffPost and Newsmax all block
   non-browser clients, so Void holds their headlines and nothing else. 334 of
   the 367 reach the front page regularly. Every one of those marks was drawn
   as a measurement. The page asserted a reading it had not taken.

   THE CUT, and why it is where it is. Two states, not a gradient: the question
   a reader is actually asking is whether the score came from the article or
   from the outlet. At `confidence` 0.5 the article has earned half the
   movement available to it, which is 75 words, a headline plus a sentence.
   Below that the published score is the baseline with a nudge.

   The two states are named `article` and `headline` rather than `measured` and
   `placed`, because the Bench head already reads "N sources placed", meaning
   seated on a column. Reusing the word for a second, narrower claim in the
   same component would make both unreadable.

   One definition, three consumers (the Bench mark, its detail card, its
   screen-reader label), gated by `frontend/test/text-authority.test.mjs`.
   --------------------------------------------------------------------------- */

/** The `confidence` at which an article has earned half its movement budget.
 *  `min(1, words / 150)`, so this is 75 words. */
export const AUTHORITY_CUT = 0.5;

/** Words at which `confidence` reaches 1.0. Mirrors `_LENGTH_FULL_CONFIDENCE`
 *  in `pipeline/analyzers/political_lean.py`; the gate asserts they agree. */
export const FULL_CONFIDENCE_WORDS = 150;

export type TextAuthority = "article" | "headline";

/** A row with no stored confidence is NOT assumed to have been read. An older
 *  export that carries no value cannot support the claim that we had the
 *  article, so it reads as `headline` and says so. */
export function textAuthority(confidence?: number | null): TextAuthority {
  if (typeof confidence !== "number" || Number.isNaN(confidence)) return "headline";
  return confidence >= AUTHORITY_CUT ? "article" : "headline";
}

/** The phrase that goes in the detail card and the screen-reader label.
 *  Deliberately states the cause, not a confidence percentage: "62% confident"
 *  invites a reading of certainty that this number does not carry. */
export function authorityNote(confidence?: number | null): string | null {
  return textAuthority(confidence) === "headline"
    ? "Scored from the headline. This publisher does not serve us the article text, so this mark sits on its outlet's baseline."
    : null;
}

/** The count for the Bench head. */
export function headlineOnlyCount(rows: { confidence?: number | null }[]): number {
  return rows.filter((r) => textAuthority(r.confidence) === "headline").length;
}
