/* ---------------------------------------------------------------------------
   historyScript — build-time reader for a History event's parsed script.

   `pipeline/history/export_scripts.py` parses each of the 78 committed scripts
   with the same `script_format.parse_script` the synthesiser uses and writes
   `frontend/build-data/history-scripts/<slug>.json`. The Hearing renders that
   structure directly, so the reader on /history/<slug> gets the episode's own
   running order in the served HTML rather than a client fetch and a line of
   loading copy.

   Build-data, not public/data: the server component reads it at build and the
   HTML carries the words, so the browser never fetches 12 KB per event and
   history.json (which the landing loads whole) does not grow by 78 files.

   Mirrors lib/historyCatalog.ts: readFileSync, memoised, no network, no dates.
   A slug with no script returns null and the page renders the hero and the end
   matter without a spine, which is what a missing export should look like.
   --------------------------------------------------------------------------- */

import { readFileSync } from "fs";
import { join } from "path";

/** One spoken line. `speaker` is "N" for the narrator; anything else (M, F)
 *  is someone else's words, and the page sets those in a different face. */
export interface ScriptLine {
  speaker: string;
  text: string;
}

export type ScriptKind =
  | "OPEN"
  | "TITLE"
  | "SCENE"
  | "DOCUMENT"
  | "ASIDE"
  | "PERSPECTIVE"
  | "TURN"
  | "REST"
  | "CLOSE";

export interface ScriptSegment {
  kind: ScriptKind | string;
  lines: ScriptLine[];
  /** SCENE / PERSPECTIVE / TURN title; "short" on a short REST. */
  title?: string;
  /** DOCUMENT only. */
  author?: string;
  work?: string;
  date?: string;
  /** PERSPECTIVE only: the index into the event YAML's `perspectives` array
   *  that this segment argues. Resolved by the exporter with H-09's own stem
   *  rule. Never re-derived here: two rules that disagreed about which account
   *  is which would print an argument under the name of the side that did not
   *  make it. */
  account?: number | null;
}

export interface HistoryScript {
  slug: string;
  words: number;
  segments: ScriptSegment[];
  say: Record<string, string>;
}

const _scripts = new Map<string, HistoryScript | null>();

function looksUsable(blob: unknown): blob is HistoryScript {
  const s = blob as Partial<HistoryScript> | null;
  return !!(s && typeof s === "object" && typeof s.slug === "string" && Array.isArray(s.segments));
}

/** The parsed script for an event, or null when none was exported. */
export function getHistoryScript(slug: string): HistoryScript | null {
  if (!slug) return null;
  const cached = _scripts.get(slug);
  if (cached !== undefined) return cached;

  let parsed: HistoryScript | null = null;
  try {
    const raw = readFileSync(
      join(process.cwd(), "build-data", "history-scripts", `${slug}.json`),
      "utf8",
    );
    const blob = JSON.parse(raw) as unknown;
    if (looksUsable(blob)) {
      parsed = {
        slug: blob.slug,
        words: typeof blob.words === "number" ? blob.words : 0,
        segments: blob.segments.filter((s) => s && typeof s.kind === "string").map((s) => ({
          ...s,
          lines: Array.isArray(s.lines) ? s.lines : [],
        })),
        say: (blob.say ?? {}) as Record<string, string>,
      };
    }
  } catch {
    parsed = null;
  }
  _scripts.set(slug, parsed);
  return parsed;
}
