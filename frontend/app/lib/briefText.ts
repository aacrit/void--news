/**
 * Daily-brief body text helpers.
 *
 * The pipeline writes the TL;DR and opinion bodies one STORY PER PARAGRAPH,
 * separated by a blank line (see daily_brief_generator._USER_PROMPT_TEMPLATE).
 * Interpolating that string straight into a single <p> collapses every break,
 * so each surface that renders a brief body splits it here first.
 */

/** Split a brief body into story paragraphs on blank-line breaks. */
export function splitBriefParagraphs(text: string | null | undefined): string[] {
  if (!text || typeof text !== "string") return [];
  return text
    .split(/\n\s*\n+/)
    .map((p) => p.trim())
    .filter(Boolean);
}

/* A period after one of these does not end a sentence ("Oct. 16", "Mr.
   Meeks", "U.S."). Splitting there left a teaser ending "on Friday, Oct." */
const NON_TERMINAL = /(?:\b(?:Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept?|Oct|Nov|Dec|Mr|Mrs|Ms|Dr|St|Sen|Rep|Gov|Gen|Lt|Col|Sgt|Capt|Prof|No|Jr|Sr|vs)|\b(?:[A-Z]\.)+[A-Z])\.$/;

/** Sentences of a brief body, closing quotes kept with their sentence. */
export function splitBriefSentences(text: string | null | undefined): string[] {
  if (!text || typeof text !== "string") return [];
  const out: string[] = [];
  for (const piece of text.split(/(?<=[.!?]["'”’)]?)\s+/)) {
    const s = piece.trim();
    if (!s) continue;
    if (out.length && NON_TERMINAL.test(out[out.length - 1])) out[out.length - 1] += ` ${s}`;
    else out.push(s);
  }
  return out;
}

/**
 * The collapsed teaser: whole sentences from the FIRST story paragraph, as
 * many as fit in `maxChars`, never fewer than one. A line clamp on the whole
 * body ended the teaser mid-sentence ("has publicly criticized President..."),
 * which read as a broken brief rather than a preview (2026-10-17).
 */
export function briefTeaser(text: string | null | undefined, maxChars: number): string {
  const first = splitBriefParagraphs(text)[0] ?? "";
  const sentences = splitBriefSentences(first);
  let out = sentences[0] ?? "";
  for (const s of sentences.slice(1)) {
    if (out.length + 1 + s.length > maxChars) break;
    out += ` ${s}`;
  }
  return out;
}

/** True when the body opens on an initialism ("US", "NATO"), where a drop
    cap would split it: "U" set large, then "S officials". */
export function opensOnInitialism(text: string | null | undefined): boolean {
  return /^[“"']?[A-Z]{2,}\b/.test((splitBriefParagraphs(text)[0] ?? "").trim());
}
