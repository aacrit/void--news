import type { AudioChapter } from "./types";

/* ---------------------------------------------------------------------------
   chapters.ts — pure helpers for the On Air chapter rail.

   The daily brief is produced as a radio show with real chapters (ident and
   sign-on, the headlines menu, one chapter per story, the "also today" briefs,
   the closer, the editorial). The pipeline emits their start times; everything
   the player needs to turn a playhead position into "you are in chapter 3 of 8"
   lives here, with no React and no DOM, so it can be asserted offline.

   Rules the rest of the player relies on:
   - A null / empty / malformed chapter list is the LEGACY case. Every helper
     degrades to "no chapters" (-1, 0, []) rather than throwing, so an old
     episode, a weekly issue or a history account renders the original
     News / Opinion transport untouched.
   - Chapters are not trusted to be sorted or complete. `findChapterIndex`
     scans for the latest start at or before the playhead, and a chapter that
     declares an `endTime` is honoured: past it, the reader is between
     chapters (-1), not still inside the last one.
   --------------------------------------------------------------------------- */

/** A chapter is usable only if it carries a finite, non-negative start. */
function isUsable(c: unknown): c is AudioChapter {
  if (!c || typeof c !== "object") return false;
  const s = (c as AudioChapter).startTime;
  return typeof s === "number" && isFinite(s) && s >= 0;
}

/**
 * Coerce whatever arrived on the wire into a chapter array or null.
 *
 * `audio_chapters` is a JSONB column exported to static JSON. Depending on the
 * export path it can arrive as a real array, as a JSON string, or as null on
 * every legacy episode. Anything that is not a usable array of chapters
 * becomes null, which every consumer reads as "no chapters".
 */
export function coerceChapters(raw: unknown): AudioChapter[] | null {
  if (raw == null) return null;
  let value = raw;
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return null;
    try {
      value = JSON.parse(trimmed);
    } catch {
      return null;
    }
  }
  if (!Array.isArray(value)) return null;
  const clean = value.filter(isUsable).map((c) => ({
    ...c,
    title: typeof c.title === "string" ? c.title : "",
  }));
  return clean.length > 0 ? clean : null;
}

/**
 * Which chapter contains `t` (seconds), or -1.
 *
 * -1 means "no chapter here": before the first chapter starts (the ident and
 * sign-on run ahead of chapter 1), inside a declared gap, or past a final
 * chapter that declares its own end.
 */
export function findChapterIndex(
  chapters: AudioChapter[] | null | undefined,
  t: number
): number {
  if (!chapters || chapters.length === 0) return -1;
  if (typeof t !== "number" || !isFinite(t) || t < 0) return -1;

  let best = -1;
  let bestStart = -1;
  for (let i = 0; i < chapters.length; i++) {
    const c = chapters[i];
    if (!isUsable(c)) continue;
    // >= bestStart, not >, so a later entry wins an exact tie: the pipeline
    // emits chapters in play order and the second of two identical starts is
    // the one the listener is actually hearing.
    if (c.startTime <= t && c.startTime >= bestStart) {
      best = i;
      bestStart = c.startTime;
    }
  }
  if (best === -1) return -1;

  const end = chapters[best].endTime;
  if (typeof end === "number" && isFinite(end) && t >= end) return -1;
  return best;
}

/**
 * Where chapter `index` ends, in seconds.
 *
 * Preference order: its own `endTime`, then the next chapter's start, then the
 * episode duration. Returns null when none of those is known.
 */
export function chapterEnd(
  chapters: AudioChapter[] | null | undefined,
  index: number,
  duration?: number | null
): number | null {
  if (!chapters || index < 0 || index >= chapters.length) return null;
  const own = chapters[index].endTime;
  if (typeof own === "number" && isFinite(own) && own > chapters[index].startTime) {
    return own;
  }
  for (let i = index + 1; i < chapters.length; i++) {
    const s = chapters[i]?.startTime;
    if (typeof s === "number" && isFinite(s) && s > chapters[index].startTime) return s;
  }
  if (typeof duration === "number" && isFinite(duration) && duration > chapters[index].startTime) {
    return duration;
  }
  return null;
}

/**
 * How far through chapter `index` the playhead sits, 0..1.
 *
 * 0 when the chapter has not started or its length is unknown; 1 once the
 * playhead is at or past its end. Drives the fill on the current rail segment.
 */
export function chapterProgress(
  chapters: AudioChapter[] | null | undefined,
  index: number,
  t: number,
  duration?: number | null
): number {
  if (!chapters || index < 0 || index >= chapters.length) return 0;
  if (typeof t !== "number" || !isFinite(t)) return 0;
  const start = chapters[index].startTime;
  const end = chapterEnd(chapters, index, duration);
  if (end == null || end <= start) return 0;
  if (t <= start) return 0;
  if (t >= end) return 1;
  return (t - start) / (end - start);
}

/** One seek mark per chapter, as a percentage of the episode. */
export interface ChapterMark {
  index: number;
  pct: number;
  chapter: AudioChapter;
}

/**
 * Positions for the marks drawn on the progress bar. Chapters beyond the known
 * duration are dropped rather than clamped onto the end of the bar, where they
 * would stack into one unreadable smudge.
 */
export function chapterMarks(
  chapters: AudioChapter[] | null | undefined,
  duration: number | null | undefined
): ChapterMark[] {
  if (!chapters || !duration || !isFinite(duration) || duration <= 0) return [];
  const marks: ChapterMark[] = [];
  for (let i = 0; i < chapters.length; i++) {
    const c = chapters[i];
    if (!isUsable(c)) continue;
    if (c.startTime > duration) continue;
    marks.push({ index: i, pct: (c.startTime / duration) * 100, chapter: c });
  }
  return marks;
}

/** Index of the Opinion chapter, or -1. The "Opinion" jump reads this.
 * Episodes rendered before 2026-09-19 carry kind "editorial"; both resolve. */
export function findOpinionIndex(
  chapters: AudioChapter[] | null | undefined
): number {
  if (!chapters) return -1;
  return chapters.findIndex(
    (c) => isUsable(c) && (c.kind === "opinion" || c.kind === "editorial"),
  );
}

/** Short uppercase rail label for a chapter kind. Story rows show their rank. */
export function chapterKindLabel(c: AudioChapter): string {
  switch (c.kind) {
    case "headlines":
      return "Headlines";
    case "story":
      return typeof c.rank === "number" && isFinite(c.rank) ? `No. ${c.rank}` : "Story";
    case "briefs":
      return "In brief";
    case "finally":
      return "Finally";
    case "opinion":
    case "editorial":
      return "Opinion";
    // A History documentary chapter is named by its title alone ("Twenty five
    // seconds", "The Soviet programme"); a badge beside it would say nothing.
    // Explicit rather than left to the default, so the silence is a decision.
    case "segment":
      return "";
    // "The Argument", the weekly edition. The badge names the MOVEMENT, which
    // is what a magazine's reader is navigating by; the chapter's own title
    // carries the subject. "topic" is the argument itself, badged as such,
    // because it is the one movement a listener comes back for.
    case "topic":
      return "The Argument";
    case "cover":
      return "Cover";
    case "second":
      return "Feature";
    case "department":
      return "Department";
    case "numbers":
      return "Measured";
    case "contents":
      return "Contents";
    case "open":
    case "close":
      return "";
    default:
      return "";
  }
}

/** m:ss for a chapter timecode. Shared by every rail surface. */
export function formatChapterTime(seconds: number): string {
  if (typeof seconds !== "number" || !isFinite(seconds) || seconds < 0) seconds = 0;
  const s = Math.floor(seconds);
  return `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;
}
