"use client";

import { useAudio, type HistoryAudioPayload } from "../components/AudioProvider";
import type { WeeklyDigestData } from "../weekly/types";

/* ---------------------------------------------------------------------------
   AudioPlay: the one client island on /audio.

   Each programme is loaded into the SHARED player the way its own page does
   it, so the hub never grows a second transport: On Air through the daily
   flow (setEdition flips ownership back to the daily brief; the provider
   fetches it), The Argument through playWeekly, a History episode through
   playHistory. None of those autoplay; they reveal the player ready to
   start, and a second press toggles it. The label says which state the
   reader is in: the button that owns the playing episode reads Pause.
   --------------------------------------------------------------------------- */

type Props =
  | { kind: "daily"; id: string; label: string; compact?: boolean }
  | { kind: "weekly"; id: string; label: string; compact?: boolean; issue: Partial<WeeklyDigestData> }
  | { kind: "history"; id: string; label: string; compact?: boolean; payload: HistoryAudioPayload };

export default function AudioPlay(props: Props) {
  const a = useAudio();
  const mine = a.brief?.id === props.id && a.contentType === props.kind;
  const playing = mine && a.isPlaying;

  const onClick = () => {
    if (mine) { a.handlePlayPause(); return; }
    if (props.kind === "daily") {
      if (a.contentType === "daily" && a.brief?.audio_url) a.handlePlayPause();
      else a.setEdition("world");
      return;
    }
    if (props.kind === "weekly") { a.playWeekly(props.issue as WeeklyDigestData); return; }
    a.playHistory(props.payload);
  };

  return (
    <button
      type="button"
      className={`audio-play${props.compact ? " audio-play--compact" : ""}${playing ? " audio-play--playing" : ""}`}
      data-kind={props.kind}
      data-state={playing ? "playing" : mine ? "loaded" : "idle"}
      onClick={onClick}
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
