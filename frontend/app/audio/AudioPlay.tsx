"use client";

import { useAudio } from "../components/AudioProvider";
import {
  type Episode,
  episodeFromBrief,
  episodeFromHistory,
  episodeFromWeekly,
  sameEpisode,
  type HistoryAudioPayload,
} from "../lib/episode";
import type { WeeklyDigestData } from "../lib/types";

/* ---------------------------------------------------------------------------
   AudioPlay: the one client island on /audio.

   Every button here calls the provider's `play(ep)`, which toggles when it
   already owns that episode and loads then plays when it does not. That one
   rule is why all three programmes now behave the same. Before it, this
   button played an already-loaded issue and merely LOADED a History episode,
   so a reader pressed Play and heard nothing (measured 2026-09-21).

   The label follows the element, not a guess: the button that owns the
   playing episode reads Pause.
   --------------------------------------------------------------------------- */

type Props =
  | { kind: "daily"; label: string; compact?: boolean }
  | { kind: "weekly"; label: string; compact?: boolean; issue: WeeklyDigestData }
  | { kind: "history"; label: string; compact?: boolean; payload: HistoryAudioPayload };

export default function AudioPlay(props: Props) {
  const a = useAudio();

  const episode: Episode | null =
    props.kind === "daily"
      ? episodeFromBrief(a.brief)
      : props.kind === "weekly"
        ? episodeFromWeekly(props.issue)
        : episodeFromHistory(props.payload);

  const mine = sameEpisode(a.nowPlaying, episode);
  const playing = mine && a.isPlaying;

  return (
    <button
      type="button"
      className={`audio-play${props.compact ? " audio-play--compact" : ""}${playing ? " audio-play--playing" : ""}`}
      data-kind={props.kind}
      data-state={playing ? "playing" : mine ? "loaded" : "idle"}
      disabled={!episode}
      onClick={() => episode && a.play(episode)}
      aria-label={playing ? props.label.replace(/^Play/, "Pause") : props.label}
    >
      <svg width="12" height="14" viewBox="0 0 12 14" fill="currentColor" aria-hidden="true" className="audio-play__icon">
        {playing
          ? <><rect x="1" y="1" width="3.5" height="12" /><rect x="7.5" y="1" width="3.5" height="12" /></>
          : <path d="M1 1.5v11l10-5.5z" />}
      </svg>
      <span className="audio-play__label">{playing ? "Pause" : props.compact ? "Play" : props.label}</span>
    </button>
  );
}
