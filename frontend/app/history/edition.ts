/* ---------------------------------------------------------------------------
   history/edition.ts — which History recordings are marked as new.

   A manifest entry (public/data/history-audio.json) may carry `edition`. The
   one value today is "first-listener": a re-made episode, a new script
   written for a listener meeting the event for the first time and a new
   render, set by `pipeline/history/publish_audio.py --edition`. The pages
   mark it with the plain words below and nothing more: the manifest vouches
   that the recording is new, not that it is better.

   Kept apart from audio.ts so a client component can read the label without
   pulling the whole manifest into its bundle. tests/test_history_audio.py
   holds this set to publish_audio.EDITIONS.
   --------------------------------------------------------------------------- */

const NEW_RECORDING_EDITIONS: ReadonlySet<string> = new Set(["first-listener"]);

/** True when a manifest entry's `edition` is one the pages mark as new. */
export function isNewRecording(edition: unknown): boolean {
  return typeof edition === "string" && NEW_RECORDING_EDITIONS.has(edition);
}

/** The visible words of the mark, one string for every surface. */
export const NEW_RECORDING_LABEL = "New recording";
