"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { DailyBriefData } from "../lib/types";
import { fetchDailyBrief } from "../lib/supabase";

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

export default function DailyBrief({ edition }: DailyBriefProps) {
  const [brief, setBrief] = useState<DailyBriefData | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [showPlayer, setShowPlayer] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);

  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Fetch brief whenever edition changes
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

  // Wire up audio element events
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
      // Reveal player on first play
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

  // Don't render until data is available
  if (!brief) return null;

  const paragraphs = brief.tldr_text
    .split("\n")
    .map((p) => p.trim())
    .filter(Boolean);

  const hasAudio = !!brief.audio_url;
  const displayDuration = hasAudio && brief.audio_duration_seconds
    ? brief.audio_duration_seconds
    : duration;

  return (
    <>
      {/* Hidden audio element */}
      {hasAudio && (
        <audio
          ref={audioRef}
          src={brief.audio_url!}
          preload="metadata"
        />
      )}

      {/* TL;DR Section — standalone editorial brief */}
      <div className="daily-brief">
        <div className="daily-brief__text">
          <p className="daily-brief__label">Daily Brief</p>
          <div className="daily-brief__body">
            {paragraphs.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </div>
      </div>

      {/* "On Air" CTA button — separate from TL;DR, below it */}
      {hasAudio && (
        <div className="on-air">
          <button
            className={`on-air__btn ${isPlaying ? "on-air__btn--active" : ""}`}
            onClick={handlePlayPause}
            aria-label={isPlaying ? "Pause broadcast" : "Listen to broadcast"}
            type="button"
          >
            <span className="on-air__dot" aria-hidden="true" />
            <span className="on-air__text">
              {isPlaying ? "On Air" : "On Air"}
            </span>
            {showPlayer && (
              <span className="on-air__time">
                {formatTime(currentTime)} / {formatTime(displayDuration)}
              </span>
            )}
          </button>

          {/* Progress slider — reveals smoothly on play */}
          <div className={`on-air__track ${showPlayer ? "on-air__track--visible" : ""}`}>
            <input
              type="range"
              className="on-air__progress"
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
            {brief.audio_voice_label && (
              <span className="on-air__voice">
                {brief.audio_voice_label}
              </span>
            )}
          </div>
        </div>
      )}
    </>
  );
}
