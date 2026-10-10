/* ---------------------------------------------------------------------------
   historyThesis — build-time reader for a History event's thesis.

   `pipeline/history/export_thesis.py` writes `build-data/history-theses/
   <slug>.json` for a thesis whose front matter is `published` and whose
   every check passes. The route reads it here, at build, and renders the
   Thesis instead of the Hearing when one exists. Nothing is fetched in the
   browser.

   The switch is `status: published` and nothing else. A draft can be
   exported for a local preview with `--include-drafts`, and this reader
   renders it only when NEXT_PUBLIC_HISTORY_DRAFTS=1 is set at build, so a
   preview export in a working tree cannot reach the served site.

   Mirrors lib/historyScript.ts: readFileSync, memoised, no network.
   --------------------------------------------------------------------------- */

import { readFileSync } from "fs";
import { join } from "path";
import type { ThesisDoc } from "../history/thesis";

const _theses = new Map<string, ThesisDoc | null>();

function looksUsable(blob: unknown): blob is ThesisDoc {
  const t = blob as Partial<ThesisDoc> | null;
  return !!(
    t && typeof t === "object" && typeof t.slug === "string" &&
    Array.isArray(t.sections) && Array.isArray(t.notes) && typeof t.status === "string"
  );
}

/** The published thesis for an event, or null when the event is still the Hearing. */
export function getHistoryThesis(slug: string): ThesisDoc | null {
  if (!slug) return null;
  const cached = _theses.get(slug);
  if (cached !== undefined) return cached;

  let parsed: ThesisDoc | null = null;
  try {
    const raw = readFileSync(
      join(process.cwd(), "build-data", "history-theses", `${slug}.json`),
      "utf8",
    );
    const blob = JSON.parse(raw) as unknown;
    if (looksUsable(blob)) {
      const drafts = process.env.NEXT_PUBLIC_HISTORY_DRAFTS === "1";
      parsed = blob.status === "published" || drafts ? blob : null;
    }
  } catch {
    parsed = null;
  }
  _theses.set(slug, parsed);
  return parsed;
}
