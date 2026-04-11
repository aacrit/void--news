"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import type { Perspective } from "../types";

/* ===========================================================================
   HistoryAudioCue — void --history companion audio player

   A self-contained audio component for history event pages.
   Two zones:

   1. In-flow cue strip (between Stage 1 Scene and Stage 2 Crack):
      Document annotation — dashed rules, play button, perspective dots, duration.

   2. Sticky archive bar (appears at bottom of page once audio has started):
      Minimal transport with title, play/pause, progress strip, time.
      Disappears when audio ends.
   =========================================================================== */

const PERSP_COLORS = ["a", "b", "c", "d", "e"] as const;

/* ── Icons ── */
const PlayIcon = () => (
  <svg width="12" height="14" viewBox="0 0 12 14" fill="currentColor" aria-hidden="true">
    <path d="M1 1.5v11l10-5.5z" />
  </svg>
);

const PauseIcon = () => (
  <svg width="11" height="14" viewBox="0 0 11 14" fill="currentColor" aria-hidden="true">
    <rect x="1" y="1" width="3" height="12" rx="0.5" />
    <rect x="7" y="1" width="3" height="12" rx="0.5" />
  </svg>
);

const ArchiveIcon = () => (
  <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true">
    <rect x="1" y="1" width="10" height="2" rx="0.5" />
    <rect x="2" y="4.5" width="8" height="6.5" rx="0.5" fill="none" stroke="currentColor" strokeWidth="1" />
    <rect x="4" y="6.5" width="4" height="1" rx="0.3" />
  </svg>
);

function formatDuration(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

interface HistoryAudioCueProps {
  audioUrl: string;
  durationSeconds: number;
  eventTitle: string;
  perspectives: Perspective[];
}

export default function HistoryAudioCue({
  audioUrl,
  durationSeconds,
  eventTitle,
  perspectives,
}: HistoryAudioCueProps) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(durationSeconds);
  const [hasStarted, setHasStarted] = useState(false);
  const [error, setError] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const progressBarRef = useRef<HTMLDivElement>(null);

  /* ── Audio event listeners ── */
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTime = () => setCurrentTime(audio.currentTime);
    const onMeta = () => {
      if (audio.duration && isFinite(audio.duration)) setDuration(audio.duration);
    };
    const onEnd = () => { setIsPlaying(false); };
    const onError = () => { setError(true); setIsPlaying(false); setIsLoading(false); };
    const onCanPlay = () => setIsLoading(false);
    const onWaiting = () => setIsLoading(true);
    const onPlaying = () => setIsLoading(false);

    audio.addEventListener("timeupdate", onTime);
    audio.addEventListener("loadedmetadata", onMeta);
    audio.addEventListener("durationchange", onMeta);
    audio.addEventListener("ended", onEnd);
    audio.addEventListener("error", onError);
    audio.addEventListener("canplay", onCanPlay);
    audio.addEventListener("waiting", onWaiting);
    audio.addEventListener("playing", onPlaying);

    return () => {
      audio.removeEventListener("timeupdate", onTime);
      audio.removeEventListener("loadedmetadata", onMeta);
      audio.removeEventListener("durationchange", onMeta);
      audio.removeEventListener("ended", onEnd);
      audio.removeEventListener("error", onError);
      audio.removeEventListener("canplay", onCanPlay);
      audio.removeEventListener("waiting", onWaiting);
      audio.removeEventListener("playing", onPlaying);
    };
  }, []);

  /* ── Play / Pause ── */
  const handlePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || error) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      setIsLoading(true);
      audio.play().then(() => {
        setIsPlaying(true);
        setHasStarted(true);
        setIsLoading(false);
      }).catch(() => {
        setError(true);
        setIsPlaying(false);
        setIsLoading(false);
      });
    }
  }, [isPlaying, error]);

  /* ── Progress bar click / drag seek ── */
  const handleSeek = useCallback((e: React.MouseEvent<HTMLDivElement>) => {
    const audio = audioRef.current;
    const bar = progressBarRef.current;
    if (!audio || !bar || duration <= 0) return;

    const rect = bar.getBoundingClientRect();
    const x = Math.max(0, Math.min(e.clientX - rect.left, rect.width));
    const ratio = x / rect.width;
    const seekTo = ratio * duration;
    audio.currentTime = seekTo;
    setCurrentTime(seekTo);
  }, [duration]);

  const progressPct = duration > 0 ? (currentTime / duration) * 100 : 0;
  const perspCount = Math.min(perspectives.length, 5);

  return (
    <>
      {/* ── In-flow cue strip ── */}
      <div
        className="hist-audio-cue hist-reveal"
        role="region"
        aria-label="Audio companion for this event"
        data-playing={isPlaying}
        data-started={hasStarted}
      >
        <audio
          ref={audioRef}
          src={audioUrl}
          preload="metadata"
          crossOrigin="anonymous"
          hidden
          aria-hidden="true"
        />

        {/* Play button */}
        <button
          className="hist-audio-cue__play"
          onClick={handlePlayPause}
          aria-label={isPlaying ? "Pause audio companion" : "Play audio companion"}
          disabled={error}
          data-loading={isLoading}
        >
          <span className="hist-audio-cue__play-ring" aria-hidden="true" />
          {isLoading ? (
            <span className="hist-audio-cue__spinner" aria-hidden="true" />
          ) : isPlaying ? (
            <PauseIcon />
          ) : (
            <PlayIcon />
          )}
        </button>

        {/* Label + perspective dots */}
        <div className="hist-audio-cue__meta">
          <span className="hist-audio-cue__label">
            <ArchiveIcon />
            <span>Listen to this event</span>
          </span>
          <span className="hist-audio-cue__persp" aria-label={`${perspCount} perspectives in dialogue`}>
            {Array.from({ length: perspCount }, (_, i) => (
              <span
                key={i}
                className={`hist-audio-cue__dot hist-audio-cue__dot--${PERSP_COLORS[i]}`}
                aria-hidden="true"
              />
            ))}
            <span className="hist-audio-cue__persp-count">{perspCount} perspectives</span>
          </span>
        </div>

        {/* Duration */}
        <span className="hist-audio-cue__duration" aria-label={`Duration: ${formatDuration(duration)}`}>
          {formatDuration(duration)}
        </span>

        {/* Thin progress strip (inside cue, becomes active once started) */}
        {hasStarted && (
          <div
            className="hist-audio-cue__progress"
            role="progressbar"
            aria-valuenow={Math.round(progressPct)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Playback progress"
          >
            <div
              className="hist-audio-cue__progress-fill"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        )}
      </div>

      {/* ── Sticky archive bar — appears once audio has started ── */}
      {hasStarted && (
        <div
          className="hist-audio-bar"
          role="complementary"
          aria-label="Audio playback controls"
          data-playing={isPlaying}
        >
          <div className="hist-audio-bar__inner">
            {/* Brand mark */}
            <span className="hist-audio-bar__brand" aria-hidden="true">
              void <span className="hist-audio-bar__brand-cmd">--history</span>
            </span>

            {/* Transport */}
            <button
              className="hist-audio-bar__play"
              onClick={handlePlayPause}
              aria-label={isPlaying ? "Pause" : "Play"}
              disabled={error}
            >
              {isPlaying ? <PauseIcon /> : <PlayIcon />}
            </button>

            {/* Progress strip (interactive) */}
            <div
              className="hist-audio-bar__progress"
              ref={progressBarRef}
              onClick={handleSeek}
              role="presentation"
              title={`${formatDuration(currentTime)} / ${formatDuration(duration)}`}
            >
              <div
                className="hist-audio-bar__fill"
                style={{ width: `${progressPct}%` }}
              />
            </div>

            {/* Time */}
            <span className="hist-audio-bar__time" aria-live="off">
              {formatDuration(currentTime)}
              <span className="hist-audio-bar__sep" aria-hidden="true"> / </span>
              <span className="hist-audio-bar__total">{formatDuration(duration)}</span>
            </span>
          </div>
        </div>
      )}
    </>
  );
}
