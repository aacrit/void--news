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

/* ---------------------------------------------------------------------------
   First-encounter subtitles — show English labels once per browser session
   to teach the void -- branding, then fade away.
   --------------------------------------------------------------------------- */
const SUBTITLE_SEEN_KEY = "void-news-subtitles-seen";

function useFirstEncounterSubtitles(): boolean {
  const [show, setShow] = useState(false);
  useEffect(() => {
    try {
      if (!sessionStorage.getItem(SUBTITLE_SEEN_KEY)) {
        setShow(true);
        sessionStorage.setItem(SUBTITLE_SEEN_KEY, "1");
      }
    } catch { /* sessionStorage blocked */ }
  }, []);
  return show;
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
  audioCallbackRef: (el: HTMLAudioElement | null) => void;
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

  // Callback ref — attaches listeners the instant <audio> mounts in the DOM,
  // regardless of whether brief loaded before or after DailyBriefText renders.
  const listenerCleanupRef = useRef<(() => void) | null>(null);

  const audioCallbackRef = useCallback((el: HTMLAudioElement | null) => {
    if (listenerCleanupRef.current) {
      listenerCleanupRef.current();
      listenerCleanupRef.current = null;
    }
    audioRef.current = el;
    if (!el) return;

    const onTime = () => setCurrentTime(el.currentTime);
    const onMeta = () => {
      if (el.duration && isFinite(el.duration)) setDuration(el.duration);
    };
    const onEnd = () => setIsPlaying(false);
    const onError = () => { setAudioError(true); setIsPlaying(false); };

    el.addEventListener("timeupdate", onTime);
    el.addEventListener("loadedmetadata", onMeta);
    el.addEventListener("durationchange", onMeta);
    el.addEventListener("ended", onEnd);
    el.addEventListener("error", onError);
    if (el.duration && isFinite(el.duration)) setDuration(el.duration);

    listenerCleanupRef.current = () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("loadedmetadata", onMeta);
      el.removeEventListener("durationchange", onMeta);
      el.removeEventListener("ended", onEnd);
      el.removeEventListener("error", onError);
    };
  }, []);

  const handlePlayPause = useCallback(() => {
    const audio = audioRef.current;
    if (!audio || audioError) return;
    hapticMedium();
    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      audio.play().catch(() => {
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
    const tick = Math.floor(t / 5);
    if (tick !== lastSeekTick.current) {
      lastSeekTick.current = tick;
      hapticTick();
    }
    audio.currentTime = t;
    setCurrentTime(t);
  }, []);

  return { brief, isPlaying, currentTime, duration, audioError, audioRef, audioCallbackRef, handlePlayPause, handleSeek };
}

/* ---------------------------------------------------------------------------
   DailyBriefText — three CTA pills: tl;dr, opinion, onair.
   Each expands its panel on click. Headlines stay front and center.
   --------------------------------------------------------------------------- */

type ExpandedPanel = "tldr" | "opinion" | "onair" | null;

export function DailyBriefText({ state }: { state: DailyBriefState }) {
  const { brief, isPlaying, currentTime, duration, audioError, audioCallbackRef, handlePlayPause, handleSeek } = state;
  const [expanded, setExpanded] = useState<ExpandedPanel>("tldr");
  const showSubtitles = useFirstEncounterSubtitles();
  if (!brief) return null;

  const hasAudio = !!brief.audio_url && !audioError;
  const displayDuration = (hasAudio && brief.audio_duration_seconds) || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;

  const paragraphs = brief.tldr_text
    .split("\n")
    .map((p) => p.trim())
    .filter(Boolean);

  const togglePanel = (panel: ExpandedPanel) => {
    hapticLight();
    setExpanded((prev) => (prev === panel ? null : panel));
  };

  const handleOnairClick = () => {
    if (!hasAudio) return;
    // If panel is closed, open it and start playing
    if (expanded !== "onair") {
      setExpanded("onair");
      if (!isPlaying) handlePlayPause();
    } else {
      // If panel is open, toggle play/pause
      handlePlayPause();
    }
  };

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative"
    : "Pragmatic";

  return (
    <>
      {hasAudio && (
        <audio ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />
      )}

      <div className="daily-brief" role="complementary" aria-label="Daily Brief">
        {/* Pill row — three CTAs */}
        <div className="daily-brief__pills">
          {/* TL;DR pill */}
          <button
            className={`db-pill${expanded === "tldr" ? " db-pill--active" : ""}`}
            onClick={() => togglePanel("tldr")}
            type="button"
            aria-expanded={expanded === "tldr"}
            aria-controls="db-panel-tldr"
          >
            <ScaleIcon size={11} animation="idle" className="db-pill__icon" />
            <span className="db-pill__name">
              void --tl;dr
              {showSubtitles && <span className="db-pill__subtitle">The Daily Brief</span>}
            </span>
          </button>

          {/* Opinion pill */}
          {brief.opinion_text && (
            <button
              className={`db-pill${expanded === "opinion" ? " db-pill--active" : ""}`}
              onClick={() => togglePanel("opinion")}
              type="button"
              aria-expanded={expanded === "opinion"}
              aria-controls="db-panel-opinion"
            >
              <span className="db-pill__name">
                void --opinion
                {showSubtitles && <span className="db-pill__subtitle">The Board</span>}
              </span>
            </button>
          )}

          {/* On Air pill — expands inline into mini player when playing */}
          <button
            className={`db-pill db-pill--onair${isPlaying ? " db-pill--playing" : ""}${currentTime > 0 && !isPlaying ? " db-pill--has-progress" : ""}${expanded === "onair" ? " db-pill--active" : ""}${!hasAudio ? " db-pill--disabled" : ""}`}
            onClick={handleOnairClick}
            type="button"
            disabled={!hasAudio}
            aria-label={!hasAudio ? "Audio broadcast unavailable" : isPlaying ? "Pause broadcast" : "Play void onair"}
            title={!hasAudio ? "Audio broadcast generates twice daily" : undefined}
          >
            {isPlaying && <span className="db-pill__dot" />}
            <ScaleIcon
              size={11}
              animation={isPlaying ? "analyzing" : "idle"}
              className="db-pill__icon"
              aria-hidden
            />
            <span className="db-pill__name">
              void --onair
              {showSubtitles && <span className="db-pill__subtitle">Audio Broadcast</span>}
            </span>
            {/* Inline progress track — appears inside the pill when playing or paused mid-track */}
            {(isPlaying || currentTime > 0) && displayDuration > 0 && (
              <span className="db-pill__progress">
                <span className="db-pill__progress-track">
                  <span
                    className="db-pill__progress-fill"
                    style={{ transform: `scaleX(${progress / 100})` }}
                  />
                </span>
                <span className="db-pill__time">
                  {formatTime(currentTime)}/{formatTime(displayDuration)}
                </span>
              </span>
            )}
            <span className="db-pill__glyph" aria-hidden="true">
              {isPlaying ? "\u275A\u275A" : "\u25B6"}
            </span>
          </button>

          {/* Timestamp — right-aligned */}
          {brief.created_at && (
            <span className="daily-brief__timestamp">{timeAgo(brief.created_at)}</span>
          )}
        </div>

        {/* === Expandable panels === */}

        {/* TL;DR panel */}
        <div
          id="db-panel-tldr"
          className={`db-panel${expanded === "tldr" ? " db-panel--open" : ""}`}
        >
          <div className="db-panel__inner daily-brief__body">
            {paragraphs.map((p, i) => (
              <p key={i}>{p}</p>
            ))}
          </div>
        </div>

        {/* Opinion panel */}
        {brief.opinion_text && (
          <div
            id="db-panel-opinion"
            className={`db-panel${expanded === "opinion" ? " db-panel--open" : ""}`}
          >
            <div className="db-panel__inner daily-brief__opinion">
              <h3 className="daily-brief__opinion-headline">
                The Board
              </h3>
              <p>
                {brief.opinion_text}
                {brief.opinion_lean && (
                  <span className="opinion-lean-tag"> — {leanLabel} lens</span>
                )}
              </p>
            </div>
          </div>
        )}

        {/* On Air panel — progress bar + seek */}
        {hasAudio && (
          <div
            id="db-panel-onair"
            className={`db-panel${expanded === "onair" ? " db-panel--open" : ""}`}
          >
            <div className="db-panel__inner db-panel__onair">
              <div className="db-panel__onair-controls">
                <button
                  type="button"
                  className="db-onair__play-btn"
                  onClick={handlePlayPause}
                  aria-label={isPlaying ? "Pause" : "Play"}
                >
                  {isPlaying ? "\u275A\u275A" : "\u25B6"}
                </button>
                <div className="db-panel__onair-track-wrap">
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
                  <div className="db-panel__onair-meta">
                    <span className="db-panel__onair-status">
                      {isPlaying ? "Now playing" : "Paused"}
                    </span>
                    <span className="db-panel__onair-time">
                      {formatTime(currentTime)} / {formatTime(displayDuration)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
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
