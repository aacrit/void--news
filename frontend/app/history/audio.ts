import manifest from "../../public/data/history-audio.json";
import { BASE_PATH } from "../lib/utils";
import { coerceChapters } from "../lib/chapters";
import type { AudioChapter } from "../lib/types";

/* ---------------------------------------------------------------------------
   history/audio.ts — which History events have an audio edition.

   Every event that has been produced as a mini audio documentary appears in
   `public/data/history-audio.json`, written by `pipeline/history/publish_audio.py`
   when the episode is published. The manifest is imported at BUILD time, not
   fetched: History is a static export, the file is committed with the audio it
   describes, and a fetch would mean the Listen button appearing a beat after
   the page settles.

   This module is deliberately the only thing that knows where the audio lives.
   The catalogue moves to R2 when all 78 episodes exist (docs/HISTORY-AUDIO.md);
   that is a change to the `url` strings in the manifest and nothing here.
   --------------------------------------------------------------------------- */

export interface HistoryEpisode {
  /** Ready to play: base path applied, fingerprint kept. */
  url: string;
  title: string;
  durationSeconds: number;
  chapters: AudioChapter[] | null;
}

interface RawEpisode {
  url?: string;
  title?: string;
  durationSeconds?: number;
  chapters?: unknown;
}

const EPISODES: Record<string, RawEpisode> =
  (manifest as { episodes?: Record<string, RawEpisode> })?.episodes ?? {};

/** The published episode for an event slug, or null when none exists yet. */
export function historyEpisode(slug: string): HistoryEpisode | null {
  const raw = slug ? EPISODES[slug] : undefined;
  if (!raw?.url || typeof raw.durationSeconds !== "number") return null;
  return {
    // Manifest urls are site-relative and never carry the base path, so this
    // is correct both on the custom domain (base "") and under /void--news.
    url: `${BASE_PATH}${raw.url}`,
    title: raw.title ?? "",
    durationSeconds: raw.durationSeconds,
    chapters: coerceChapters(raw.chapters),
  };
}

/** How many events currently have an audio edition. */
export function publishedEpisodeCount(): number {
  return Object.keys(EPISODES).length;
}

/**
 * Fill in an event's audio fields from the manifest.
 *
 * Applied wherever events are built, whichever source won: the manifest is the
 * record of what was actually published, so it takes precedence over a stale
 * `audio_url` left behind by the retired Supabase column. An event with no
 * episode keeps its existing values and the Listen button stays hidden.
 */
export function withHistoryAudio<T extends {
  slug: string;
  audioUrl?: string | null;
  audioDuration?: number | null;
  audioChapters?: AudioChapter[] | null;
}>(event: T): T {
  const ep = historyEpisode(event.slug);
  if (!ep) return event;
  return { ...event, audioUrl: ep.url, audioDuration: ep.durationSeconds,
           audioChapters: ep.chapters };
}

/** Same, for a list. */
export function withHistoryAudioAll<T extends Parameters<typeof withHistoryAudio>[0]>(
  events: T[]
): T[] {
  return events.map((e) => withHistoryAudio(e));
}
