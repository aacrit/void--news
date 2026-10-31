/* ===========================================================================
   summaryParagraphs: a Deep Dive summary set as paragraphs.

   The pipeline writes each story's summary as ONE string of 160 to 350 words
   with no breaks, and every Deep Dive printed it as one <p>: about 25 lines on
   a phone and 150 characters a line on a desktop (audit 2026-09-26, finding
   7). This splits it at sentence ends into a lede and paragraphs of about 55
   to 90 words, in the renderer, so it works for every summary already in the
   archive too.

   It never changes text. The paragraphs, joined with single spaces, are the
   input with its whitespace runs collapsed, character for character: a bad
   break is a readability defect, never a factual one (Rule 1), and
   test/summary-paragraphs.test.mjs holds that over the real feed.

   A break is never placed:
     - after a short capitalised token or an initial ("U.S.", "Dr.", "Lt.",
       "Ihor M."): see sentenceEnds;
     - inside an open quotation;
     - inside a protected range (a disputed-claim mark), so a mark is never
       cut across two paragraphs.
   =========================================================================== */

/** Offsets just past each sentence end in `text` (after the closing quote or
 *  bracket, before the whitespace), skipping abbreviations and initials. */
export function sentenceEnds(text: string): number[] {
  const ends: number[] = [];
  const re = /[.!?]["”’)]?(?=\s+["“‘(]?[A-Z0-9])/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    const before = text.slice(0, m.index).match(/(\S+)$/)?.[1] ?? "";
    if (/^(?:[A-Z][a-z]{0,2}|(?:[A-Za-z]\.)+[A-Za-z]|No|Nos|vs|etc)$/.test(before)) continue;
    ends.push(m.index + m[0].length);
  }
  return ends;
}

/** True when `pos` sits inside an open quotation in `text`. */
function insideQuote(text: string, pos: number): boolean {
  const head = text.slice(0, pos);
  const straight = (head.match(/"/g) ?? []).length;
  if (straight % 2 === 1) return true;
  const open = (head.match(/“/g) ?? []).length;
  const close = (head.match(/”/g) ?? []).length;
  return open > close;
}

const words = (s: string) => (s.match(/\S+/g) ?? []).length;

export interface SummaryParagraphs {
  paragraphs: string[];
  /** Start offset of each paragraph in the ORIGINAL (untrimmed) text. */
  offsets: number[];
}

export const PARA_TARGET_WORDS = 55;
export const PARA_MIN_TAIL_WORDS = 25;

export function summaryParagraphs(
  text: string | null | undefined,
  protect: Array<{ start: number; end: number }> = [],
): SummaryParagraphs {
  const src = text ?? "";
  const lead = src.length - src.trimStart().length;
  const body = src.trim();
  if (!body) return { paragraphs: [], offsets: [] };

  // Candidate breaks, as offsets into src: the whitespace after a sentence.
  const ok = (end: number) =>
    !insideQuote(src, end) && !protect.some((r) => end > r.start && end < r.end);
  const ends = sentenceEnds(src).filter((e) => e > lead && e < lead + body.length && ok(e));

  // Sentences, as [start, end) offsets into src.
  const spans: Array<[number, number]> = [];
  let start = lead;
  for (const e of ends) {
    spans.push([start, e]);
    start = e;
    while (start < src.length && /\s/.test(src[start])) start++;
  }
  spans.push([start, lead + body.length]);

  // Short summaries stay one paragraph.
  if (words(body) <= 80 || spans.length < 3) {
    return { paragraphs: [body], offsets: [lead] };
  }

  // The lede: one sentence, two when the first is very short.
  const groups: Array<[number, number]> = [];
  let i = 0;
  let ledeEnd = spans[0][1];
  i = 1;
  if (words(src.slice(spans[0][0], spans[0][1])) < 15 && spans.length > 3) {
    ledeEnd = spans[1][1];
    i = 2;
  }
  groups.push([spans[0][0], ledeEnd]);

  // The rest in paragraphs of about PARA_TARGET_WORDS.
  let gStart = spans[i]?.[0] ?? -1;
  let count = 0;
  for (; i < spans.length; i++) {
    count += words(src.slice(spans[i][0], spans[i][1]));
    if (count >= PARA_TARGET_WORDS && i < spans.length - 1) {
      groups.push([gStart, spans[i][1]]);
      gStart = spans[i + 1][0];
      count = 0;
    }
  }
  if (gStart >= 0 && gStart < lead + body.length) groups.push([gStart, spans[spans.length - 1][1]]);

  // A short last paragraph goes back into the one before it (never into the lede).
  if (groups.length > 2) {
    const last = groups[groups.length - 1];
    if (words(src.slice(last[0], last[1])) < PARA_MIN_TAIL_WORDS) {
      groups.pop();
      groups[groups.length - 1] = [groups[groups.length - 1][0], last[1]];
    }
  }

  return {
    paragraphs: groups.map(([a, b]) => src.slice(a, b).trim()),
    offsets: groups.map(([a]) => a),
  };
}
