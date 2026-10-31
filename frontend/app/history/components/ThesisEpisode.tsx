"use client";

import { useAudio } from "../../components/AudioProvider";
import { episodeFromHistory } from "../../lib/episode";
import type { AudioChapter } from "../../lib/types";

/* ===========================================================================
   ThesisEpisode — "From the episode", with the play glyph.

   A quotation of the programme, set in the editorial voice, spelled as
   spoken. The lines are server markup (the exporter copied them from the
   script, and T-10 asserts they are the script's). Only the glyph is a client
   island: it needs the shared player. It seeks the episode to the chapter's
   start, through the one `play(ep, {startAt})` press every play button in
   the product uses, so a second press pauses instead of restarting.

   With no episode in the manifest the block still renders, without the
   glyph: the page never waits on the audio (proposal §3).
   =========================================================================== */

/* Floor-based clock so a float start reads "4:12", not "4:12.3000001". */
function formatClock(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

interface ThesisEpisodeProps {
  chapter: number;
  title: string;
  kind: string;
  startTime: number | null;
  lines: { speaker: string; text: string }[];
  event: {
    id: string;
    title: string;
    subtitle: string;
    audioUrl: string | null;
    durationSeconds: number;
    chapters: AudioChapter[] | null;
  };
}

export default function ThesisEpisode({ chapter, title, kind, startTime, lines, event }: ThesisEpisodeProps) {
  const { play, nowPlaying, isPlaying, currentTime } = useAudio();
  const payload = event.audioUrl
    ? { id: event.id, title: event.title, subtitle: event.subtitle, audioUrl: event.audioUrl,
        durationSeconds: event.durationSeconds, chapters: event.chapters }
    : null;
  const ep = payload ? episodeFromHistory(payload) : null;
  const owns = !!ep && nowPlaying?.kind === "history" && nowPlaying.id === ep.id;
  const inChapter =
    owns && isPlaying && startTime !== null && currentTime >= startTime &&
    (event.chapters?.[chapter + 1]?.startTime === undefined || currentTime < (event.chapters?.[chapter + 1]?.startTime ?? Infinity));

  const where =
    kind === "scene" ? `Scene ${chapter}` : kind === "open" ? "the opening" : kind === "close" ? "the close" : title;
  const label = startTime !== null ? `Listen from ${where}, ${formatClock(startTime)}` : `Listen from ${where}`;

  return (
    <aside className="hist-th-episode" aria-label="From the episode">
      <p className="hist-th-episode__eyebrow">
        <span>From the episode</span>
        {title && <span className="hist-th-episode__chapter">{title}</span>}
      </p>
      <div className="hist-th-episode__body">
        {ep && startTime !== null && (
          <button
            type="button"
            className={`hist-th-episode__play${inChapter ? " hist-th-episode__play--playing" : ""}`}
            aria-label={inChapter ? `Pause ${event.title}` : label}
            onClick={() => play(ep, inChapter ? undefined : { startAt: startTime })}
          >
            <svg width="14" height="16" viewBox="0 0 12 14" fill="currentColor" aria-hidden="true">
              {inChapter
                ? <><rect x="1" y="1" width="3.5" height="12" /><rect x="7.5" y="1" width="3.5" height="12" /></>
                : <path d="M1 1.5v11l10-5.5z" />}
            </svg>
            <span className="hist-th-episode__play-label">{inChapter ? "Pause" : formatClock(startTime)}</span>
          </button>
        )}
        <div className="hist-th-episode__lines">
          {lines.map((l, i) => (
            <p key={i} className={`hist-th-episode__line${(l.speaker || "N").toUpperCase() !== "N" ? " hist-th-episode__line--voice" : ""}`}>
              {l.text}
            </p>
          ))}
        </div>
      </div>
    </aside>
  );
}
