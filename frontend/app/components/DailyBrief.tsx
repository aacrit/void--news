"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { DailyBriefData } from "../lib/types";
import { fetchDailyBrief } from "../lib/supabase";
import { ScaleIcon } from "./ScaleIcon";

interface DailyBriefProps {
  edition: string;
}

/** Format seconds as MM:SS */
function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const remaining = s % 60;
  return `${m}:${remaining.toString().padStart(2, "0")}`;
}

/* ---------------------------------------------------------------------------
   Shared state shape — passed from useDailyBrief() to both sub-components
   --------------------------------------------------------------------------- */

export interface DailyBriefState {
  brief: DailyBriefData | null;
  isPlaying: boolean;
  showPlayer: boolean;
  currentTime: number;
  duration: number;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  handlePlayPause: () => void;
  handleSeek: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

/* ---------------------------------------------------------------------------
   useDailyBrief — fetch + audio state for an edition.
   Call once in HomeContent; pass the result to DailyBriefText + OnAirButton.
   --------------------------------------------------------------------------- */

export function useDailyBrief(edition: string): DailyBriefState {
  const [brief, setBrief] = useState<DailyBriefData | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showPlayer, setShowPlayer] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    setBrief(null);
    setIsPlaying(false);
    setShowPlayer(false);
    setCurrentTime(0);
    setDuration(0);

    fetchDailyBrief(edition).then((data) => {
      if (!cancelled) setBrief(data);
    });

    return () => { cancelled = true; };
  }, [edition]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => setCurrentTime(audio.currentTime);
    const onLoaded = () => setDuration(audio.duration || 0);
    const onEnded = () => { setIsPlaying(false); };

    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("loadedmetadata", onLoaded);
    audio.addEventListener("ended", onEnded);

    return () => {
      audio.removeEventListener("timeupdate", onTimeUpdate);
      audio.removeEventListener("loadedmetadata", onLoaded);
      audio.removeEventListener("ended", onEnded);
    };
  }, [brief]);

  const handlePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      setShowPlayer(true);
      audio.play().catch(() => {});
      setIsPlaying(true);
    }
  }, [isPlaying]);

  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;
    const t = Number(e.target.value);
    audio.currentTime = t;
    setCurrentTime(t);
  }, []);

  return { brief, isPlaying, showPlayer, currentTime, duration, audioRef, handlePlayPause, handleSeek };
}

/* ---------------------------------------------------------------------------
   DailyBriefText — newspaper editorial TL;DR box.
   Renders "on canvas" between FilterBar and the lead stories.
   Uses top + bottom rules for newspaper section-divider feel.
   --------------------------------------------------------------------------- */

export function DailyBriefText({ state }: { state: DailyBriefState }) {
  const { brief, audioRef } = state;
  const [expanded, setExpanded] = useState(false);
  if (!brief) return null;

  const hasAudio = !!brief.audio_url;

  const paragraphs = brief.tldr_text
    .split("\n")
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <>
      {/* Hidden audio element — lives here so it mounts with the text, not the button */}
      {hasAudio && (
        <audio
          ref={audioRef}
          src={brief.audio_url!}
          preload="metadata"
        />
      )}

      <div className="daily-brief" role="complementary" aria-label="Daily Brief">
        <div className="daily-brief__header">
          <ScaleIcon size={16} animation="idle" className="daily-brief__sigil" />
          <span className="daily-brief__label">Daily Brief</span>
        </div>
        <div className={`daily-brief__body${!expanded ? " daily-brief__body--collapsed" : ""}`}>
          {paragraphs.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>
        {/* "Read more" toggle — visible only on mobile via CSS */}
        <button
          className="daily-brief__toggle"
          onClick={() => setExpanded(!expanded)}
          type="button"
        >
          {expanded ? "Read less" : "Read more"}
        </button>
      </div>
    </>
  );
}

/* ---------------------------------------------------------------------------
   OnAirButton — compact pill CTA for the FilterBar row.
   ScaleIcon uses 'analyzing' when playing (deliberate 2s weigh cycle = broadcast).
   Progress bar reveals below on play.
   --------------------------------------------------------------------------- */

export function OnAirButton({ state }: { state: DailyBriefState }) {
  const { brief, isPlaying, showPlayer, currentTime, duration, handlePlayPause, handleSeek } = state;

  if (!brief?.audio_url) return null;

  const displayDuration = brief.audio_duration_seconds || duration;

  return (
    <div className="on-air-cta" data-playing={isPlaying ? "true" : undefined}>
      <button
        className={`on-air-cta__btn${isPlaying ? " on-air-cta__btn--active" : ""}`}
        onClick={handlePlayPause}
        aria-label={isPlaying ? "Pause broadcast" : "Play daily broadcast"}
        aria-pressed={isPlaying}
        type="button"
      >
        {/* ScaleIcon: pulse when playing, idle when not */}
        <ScaleIcon
          size={14}
          animation={isPlaying ? "analyzing" : "idle"}
          className="on-air-cta__icon"
          aria-hidden
        />

        {/* Red live dot — only when playing */}
        <span className="on-air-cta__dot" aria-hidden="true" />

        <span className="on-air-cta__label">On Air</span>

        {/* Play / pause SVG glyph */}
        <span className="on-air-cta__glyph" aria-hidden="true">
          {isPlaying ? (
            /* Pause bars */
            <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
              <rect x="1" y="1" width="3" height="8" rx="0.5" />
              <rect x="6" y="1" width="3" height="8" rx="0.5" />
            </svg>
          ) : (
            /* Play triangle */
            <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor">
              <path d="M2 1.5 L9 5 L2 8.5 Z" />
            </svg>
          )}
        </span>

        {/* Time display — only when player is open */}
        {showPlayer && (
          <span className="on-air-cta__time" aria-live="off">
            {formatTime(currentTime)} / {formatTime(displayDuration)}
          </span>
        )}
      </button>

      {/* Progress bar — expands below button when playing */}
      <div
        className={`on-air-cta__track${showPlayer ? " on-air-cta__track--visible" : ""}`}
        aria-hidden={!showPlayer}
      >
        <input
          type="range"
          className="on-air-cta__progress"
          min={0}
          max={displayDuration || 100}
          value={currentTime}
          step={0.5}
          onChange={handleSeek}
          role="slider"
          aria-valuemin={0}
          aria-valuemax={displayDuration || 100}
          aria-valuenow={Math.floor(currentTime)}
          aria-label="Broadcast progress"
          tabIndex={showPlayer ? 0 : -1}
        />
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------------
   DailyBrief — default export (self-contained, for backward compat).
   HomeContent now uses useDailyBrief + DailyBriefText + OnAirButton directly.
   --------------------------------------------------------------------------- */

export default function DailyBrief({ edition }: DailyBriefProps) {
  const state = useDailyBrief(edition);
  return (
    <>
      <DailyBriefText state={state} />
      {state.brief?.audio_url && (
        <OnAirButton state={state} />
      )}
    </>
  );
}
