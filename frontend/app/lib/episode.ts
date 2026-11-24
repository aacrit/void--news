/* ===========================================================================
   episode.ts: the one shape the player plays, and the one rule for a press.

   Until 2026-09-21 the provider held a single `brief` slot that three
   programmes wrote into, and every surface read it as if it were always the
   daily edition. Measured consequences, all in a browser: /onair announced a
   History documentary as "World Edition, ON AIR"; opening the Weekly issue
   paused a playing brief mid-sentence and swapped the source; returning home
   detached a playing documentary; a tab resume replaced the issue with the
   daily brief while every label still said Weekly.

   An Episode is what is playing, whoever made it. The daily brief keeps its
   own slot and no programme may write it, so "today's edition" and "what is
   playing" can never be confused again.

   Pure: no React, no DOM, no fetch. That is what lets test/episode.test.mjs
   assert the press rule without a browser.
   =========================================================================== */
import type { AudioChapter, DailyBriefData, WeeklyDigestData } from "./types";
import { coerceChapters } from "./chapters";

/** Which programme made this episode. Drives the accent, the label and the
 *  dateline grammar on every surface. */
export type ProgrammeKind = "daily" | "weekly" | "history";

export interface Episode {
  kind: ProgrammeKind;
  /** Stable per episode: the brief id, the issue id, the event slug. */
  id: string;
  /** What is playing, in the programme's own words. */
  title: string;
  /** One line under the title, or null. */
  subtitle: string | null;
  audioUrl: string;
  /** From the row that produced the file, so a readout settles before the
   *  element has loaded its metadata. 0 when unknown. */
  durationSeconds: number;
  /** Already coerced, so `coerceChapters` runs exactly once per episode. */
  chapters: AudioChapter[];
  /** ISO. The publication date of THIS episode, never "now". */
  publishedAt: string | null;
  /** "On Air" / "The Argument" / "History". What the chrome calls it. */
  programmeLabel: string;
  /** Only the daily programme has an edition; the others must not print one. */
  editionLabel: string | null;
  voiceLabel: string | null;
  /** The daily brief's opinion firewall. null on the other programmes, which
   *  is what makes their transport a single continuous read. */
  opinionStartSeconds: number | null;
}

export const PROGRAMME_LABEL: Record<ProgrammeKind, string> = {
  daily: "On Air",
  weekly: "The Argument",
  history: "History",
};

const EDITION_LABEL: Record<string, string> = {
  world: "World",
  us: "US",
  europe: "Europe",
  "south-asia": "South Asia",
};

export function editionLabelFor(edition: string | null | undefined): string {
  return EDITION_LABEL[edition ?? "world"] ?? "World";
}

/** Today's broadcast. The only episode allowed to carry an edition label. */
export function episodeFromBrief(brief: DailyBriefData | null): Episode | null {
  if (!brief?.audio_url) return null;
  return {
    kind: "daily",
    id: brief.id,
    title: brief.tldr_headline ?? "Today's broadcast",
    subtitle: null,
    audioUrl: brief.audio_url,
    durationSeconds: Number(brief.audio_duration_seconds) || 0,
    chapters: coerceChapters(brief.audio_chapters ?? null) ?? [],
    publishedAt: brief.created_at ?? null,
    programmeLabel: PROGRAMME_LABEL.daily,
    editionLabel: editionLabelFor(brief.edition),
    voiceLabel: brief.audio_voice_label ?? null,
    opinionStartSeconds: brief.opinion_start_seconds ?? null,
  };
}

/** The Sunday edition. A scored programme with movements, not an edition of
 *  the daily broadcast, so editionLabel is null however the row is labelled. */
export function episodeFromWeekly(digest: WeeklyDigestData | null): Episode | null {
  if (!digest?.audio_url) return null;
  const lead =
    Array.isArray(digest.cover_text) && digest.cover_text.length > 0
      ? digest.cover_text[0]?.text ?? null
      : null;
  return {
    kind: "weekly",
    id: digest.id,
    title: digest.cover_headline ?? "This week's Argument",
    subtitle: lead,
    audioUrl: digest.audio_url,
    durationSeconds: Number(digest.audio_duration_seconds) || 0,
    chapters: coerceChapters(digest.audio_chapters ?? null) ?? [],
    publishedAt: digest.created_at ?? digest.week_start ?? null,
    programmeLabel: PROGRAMME_LABEL.weekly,
    editionLabel: null,
    voiceLabel: digest.audio_voice_label ?? null,
    opinionStartSeconds: digest.opinion_start_seconds ?? null,
  };
}

export interface HistoryAudioPayload {
  id: string;
  title: string;
  subtitle?: string | null;
  audioUrl: string;
  durationSeconds: number;
  chapters?: AudioChapter[] | null;
  /** When the EVENT happened is not when the episode was published, and
   *  neither is "now": the lock screen used to date a 1258 documentary today. */
  publishedAt?: string | null;
}

export function episodeFromHistory(payload: HistoryAudioPayload | null): Episode | null {
  if (!payload?.audioUrl) return null;
  return {
    kind: "history",
    id: payload.id,
    title: payload.title,
    subtitle: payload.subtitle ?? null,
    audioUrl: payload.audioUrl,
    durationSeconds: Number(payload.durationSeconds) || 0,
    chapters: coerceChapters(payload.chapters ?? null) ?? [],
    publishedAt: payload.publishedAt ?? null,
    programmeLabel: PROGRAMME_LABEL.history,
    editionLabel: null,
    voiceLabel: null,
    opinionStartSeconds: null,
  };
}

/** Two references to the same audio. Compared on the URL as well as the id,
 *  because the archive rows carry a brief id that a later refetch can reissue
 *  (which is how a play button lost track of its own episode). */
export function sameEpisode(a: Episode | null, b: Episode | null): boolean {
  if (!a || !b) return false;
  if (a.kind !== b.kind) return false;
  return a.id === b.id || stripCacheBust(a.audioUrl) === stripCacheBust(b.audioUrl);
}

/** `/audio/world/x.mp3?v=42d5b960` and the same file without the query are the
 *  same episode; the pipeline appends a content hash on every run. */
export function stripCacheBust(url: string): string {
  return url.split("?")[0];
}

/** What a press on a play button must do. One rule, so that every button in
 *  the product behaves the same: the hub, the pill, the page, the panel, the
 *  History hero. Before this, pressing Play on a History episode loaded it and
 *  played nothing, while the same button on an already-loaded issue toggled. */
export type PressAction = "toggle" | "load-and-play";

export function decidePress(
  nowPlaying: Episode | null,
  target: Episode,
): PressAction {
  return sameEpisode(nowPlaying, target) ? "toggle" : "load-and-play";
}

/** Whether a surface may replace what is loaded without being asked. A page
 *  that merely renders (the Weekly issue on mount) may offer its programme
 *  when the player is idle, and may never interrupt one that is playing. */
export function mayTakeOver(
  nowPlaying: Episode | null,
  isPlaying: boolean,
  target: Episode,
): boolean {
  if (sameEpisode(nowPlaying, target)) return false;
  return !isPlaying;
}
