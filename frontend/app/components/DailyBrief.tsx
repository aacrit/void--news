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
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isOutOfView, setIsOutOfView] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);

  // Fetch brief whenever edition changes
  useEffect(() => {
    let cancelled = false;
    setBrief(null);
    setIsPlaying(false);
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
    const onEnded = () => setIsPlaying(false);

    audio.addEventListener("timeupdate", onTimeUpdate);
    audio.addEventListener("loadedmetadata", onLoaded);
    audio.addEventListener("ended", onEnded);

    return () => {
      audio.removeEventListener("timeupdate", onTimeUpdate);
      audio.removeEventListener("loadedmetadata", onLoaded);
      audio.removeEventListener("ended", onEnded);
    };
  }, [brief]);

  // IntersectionObserver — track when container scrolls out of view (mobile sticky)
  useEffect(() => {
    const container = containerRef.current;
    if (!container || typeof IntersectionObserver === "undefined") return;

    const observer = new IntersectionObserver(
      ([entry]) => setIsOutOfView(!entry.isIntersecting),
      { threshold: 0 }
    );
    observer.observe(container);

    return () => observer.disconnect();
  }, [brief]);

  const togglePlay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play().catch(() => {
        // Autoplay blocked — silently fail, user already clicked
      });
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

  const PlayIcon = (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">
      <path d="M8 5v14l11-7z" />
    </svg>
  );

  const PauseIcon = (
    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor" aria-hidden="true">
      <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
    </svg>
  );

  return (
    <div className="daily-brief" ref={containerRef}>
      {/* Hidden audio element — no native controls */}
      {hasAudio && (
        <audio
          ref={audioRef}
          src={brief.audio_url!}
          preload="metadata"
        />
      )}

      <div className="daily-brief__content">
        {/* Text column */}
        <div className="daily-brief__text">
          <p className="daily-brief__label">Daily Brief</p>
          <div className="daily-brief__body">
            {paragraphs.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </div>

        {/* Audio player column — only when audio is available */}
        {hasAudio && (
          <div className="daily-brief__player">
            <button
              className="daily-brief__play-btn"
              onClick={togglePlay}
              aria-label={isPlaying ? "Pause daily brief" : "Play daily brief"}
              type="button"
            >
              {isPlaying ? PauseIcon : PlayIcon}
            </button>

            <input
              type="range"
              className="daily-brief__progress"
              min={0}
              max={displayDuration || 100}
              value={currentTime}
              step={1}
              onChange={handleSeek}
              role="slider"
              aria-valuemin={0}
              aria-valuemax={displayDuration || 100}
              aria-valuenow={Math.floor(currentTime)}
              aria-label="Audio progress"
            />

            <span className="daily-brief__time">
              {formatTime(currentTime)} / {formatTime(displayDuration)}
            </span>

            {brief.audio_voice_label && (
              <span className="daily-brief__voice-label">
                {brief.audio_voice_label}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Sticky mini-player — mobile only, visible when playing and scrolled past */}
      {isPlaying && isOutOfView && hasAudio && (
        <div className="daily-brief__sticky daily-brief__sticky--visible" role="region" aria-label="Audio mini-player">
          <button
            className="daily-brief__play-btn"
            onClick={togglePlay}
            aria-label="Pause daily brief"
            type="button"
          >
            {PauseIcon}
          </button>

          <input
            type="range"
            className="daily-brief__progress"
            min={0}
            max={displayDuration || 100}
            value={currentTime}
            step={1}
            onChange={handleSeek}
            role="slider"
            aria-valuemin={0}
            aria-valuemax={displayDuration || 100}
            aria-valuenow={Math.floor(currentTime)}
            aria-label="Audio progress"
          />

          <span className="daily-brief__time">
            {formatTime(currentTime)} / {formatTime(displayDuration)}
          </span>
        </div>
      )}
    </div>
  );
}
