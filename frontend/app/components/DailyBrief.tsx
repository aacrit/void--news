"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import type { DailyBriefData } from "../lib/types";
import { fetchDailyBrief } from "../lib/supabase";
import { ScaleIcon } from "./ScaleIcon";
import { hapticMedium, hapticLight, hapticTick } from "../lib/haptics";
import { timeAgo } from "../lib/utils";

interface DailyBriefProps {
  edition: string;
}

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

/* ---------------------------------------------------------------------------
   Shared state — call once in HomeContent, pass to DailyBriefText.
   --------------------------------------------------------------------------- */

export interface DailyBriefState {
  brief: DailyBriefData | null;
  isPlaying: boolean;
  currentTime: number;
  duration: number;
  audioError: boolean;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  handlePlayPause: () => void;
  handleSeek: (e: React.ChangeEvent<HTMLInputElement>) => void;
}

export function useDailyBrief(edition: string): DailyBriefState {
  const [brief, setBrief] = useState<DailyBriefData | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [audioError, setAudioError] = useState(false);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  useEffect(() => {
    let cancelled = false;

    // Pause and detach audio before switching briefs to prevent a race
    // where audio.play() is still pending when src changes.
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      audio.src = "";
      audio.load();
    }

    setBrief(null);
    setIsPlaying(false);
    setCurrentTime(0);
    setDuration(0);
    setAudioError(false);
    // Single daily brief — always world, edition-agnostic
    fetchDailyBrief("world").then((data) => {
      if (!cancelled) setBrief(data);
    });
    return () => { cancelled = true; };
  }, [edition]);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;
    const onTime = () => setCurrentTime(audio.currentTime);
    const onMeta = () => setDuration(audio.duration || 0);
    const onEnd = () => setIsPlaying(false);
    // Graceful degradation: when the audio URL 404s or fails to load, mark
    // the error state so the play button is disabled. No disruptive alert —
    // the brief text remains fully readable.
    const onError = () => {
      setAudioError(true);
      setIsPlaying(false);
    };
    audio.addEventListener("timeupdate", onTime);
    audio.addEventListener("loadedmetadata", onMeta);
    audio.addEventListener("ended", onEnd);
    audio.addEventListener("error", onError);
    return () => {
      audio.removeEventListener("timeupdate", onTime);
      audio.removeEventListener("loadedmetadata", onMeta);
      audio.removeEventListener("ended", onEnd);
      audio.removeEventListener("error", onError);
    };
  }, [brief]);

  const handlePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || audioError) return;
    hapticMedium();
    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play().catch(() => {
        // play() rejection (e.g. browser autoplay policy) — mark error so the
        // button disables gracefully rather than appearing stuck in a play state.
        setAudioError(true);
        setIsPlaying(false);
      });
      setIsPlaying(true);
    }
  }, [isPlaying, audioError]);

  const lastSeekTick = useRef(0);
  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = audioRef.current;
    if (!audio) return;
    const t = Number(e.target.value);
    // Detent haptic every 5 seconds of scrub distance
    const tick = Math.floor(t / 5);
    if (tick !== lastSeekTick.current) {
      lastSeekTick.current = tick;
      hapticTick();
    }
    audio.currentTime = t;
    setCurrentTime(t);
  }, []);

  return { brief, isPlaying, currentTime, duration, audioError, audioRef, handlePlayPause, handleSeek };
}

/* ---------------------------------------------------------------------------
   DailyBriefText — editorial TL;DR + void --onair player.
   --------------------------------------------------------------------------- */

export function DailyBriefText({ state }: { state: DailyBriefState }) {
  const { brief, isPlaying, currentTime, duration, audioError, audioRef, handlePlayPause, handleSeek } = state;
  const [expanded, setExpanded] = useState(false);
  if (!brief) return null;

  const hasAudio = !!brief.audio_url && !audioError;
  const displayDuration = (hasAudio && brief.audio_duration_seconds) || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;

  const paragraphs = brief.tldr_text
    .split("\n")
    .map((p) => p.trim())
    .filter(Boolean);

  return (
    <>
      {hasAudio && (
        <audio ref={audioRef} src={brief.audio_url!} preload="metadata" />
      )}

      <div className="daily-brief" role="complementary" aria-label="Daily Brief">
        {/* Header: label + onair pill */}
        <div className="daily-brief__header">
          <ScaleIcon size={16} animation="idle" className="daily-brief__sigil" />
          <span className="daily-brief__label">Daily Brief</span>
          {brief.created_at && (
            <span className="daily-brief__timestamp">{timeAgo(brief.created_at)}</span>
          )}

          {hasAudio && (
            <button
              className={`void-onair${isPlaying ? " void-onair--playing" : ""}`}
              onClick={handlePlayPause}
              aria-label={isPlaying ? "Pause broadcast" : "Play void onair"}
              type="button"
            >
              <ScaleIcon
                size={12}
                animation={isPlaying ? "analyzing" : "idle"}
                aria-hidden
              />
              {isPlaying && <span className="void-onair__dot" />}
              <span className="void-onair__name">void --onair</span>
              <span className="void-onair__glyph" aria-hidden="true">
                {isPlaying ? "\u275A\u275A" : "\u25B6"}
              </span>
              {isPlaying && (
                <span className="void-onair__time">
                  {formatTime(currentTime)}/{formatTime(displayDuration)}
                </span>
              )}
            </button>
          )}
        </div>

        {/* Progress bar — thin line below header, visible when playing */}
        {hasAudio && isPlaying && (
          <div className="void-onair__track">
            <div
              className="void-onair__fill"
              style={{ width: `${progress}%` }}
            />
            <input
              type="range"
              className="void-onair__seek"
              min={0}
              max={displayDuration || 100}
              value={currentTime}
              step={0.5}
              onChange={handleSeek}
              aria-label="Broadcast progress"
            />
          </div>
        )}

        {/* TL;DR body */}
        <div
          id="daily-brief-body"
          className={`daily-brief__body${!expanded ? " daily-brief__body--mobile-clamp" : ""}`}
        >
          {paragraphs.map((p, i) => (
            <p key={i}>{p}</p>
          ))}
        </div>

        {/* Opinion section — editorial board's take */}
        {brief.opinion_text && expanded && (
          <div className="daily-brief__opinion">
            <div className="daily-brief__opinion-label">The Board</div>
            <p>{brief.opinion_text}</p>
          </div>
        )}

        <button
          className="daily-brief__toggle"
          onClick={() => { hapticLight(); setExpanded(!expanded); }}
          type="button"
          aria-expanded={expanded}
          aria-controls="daily-brief-body"
        >
          {expanded ? "Read less" : "Read more"}
        </button>
      </div>
    </>
  );
}

/* ---------------------------------------------------------------------------
   Default export — backward compat.
   --------------------------------------------------------------------------- */

export default function DailyBrief({ edition }: DailyBriefProps) {
  const state = useDailyBrief(edition);
  return <DailyBriefText state={state} />;
}
