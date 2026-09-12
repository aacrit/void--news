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
