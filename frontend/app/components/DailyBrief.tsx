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
   DailyBriefText — editorial masthead with three tabs: tl;dr, opinion, onair.
   Always visible section. Tabs switch content panels in place.
   --------------------------------------------------------------------------- */

type ExpandedPanel = "tldr" | "opinion" | "onair" | null;

export function DailyBriefText({ state }: { state: DailyBriefState }) {
  const { brief, isPlaying, currentTime, duration, audioError, audioCallbackRef, handlePlayPause, handleSeek } = state;
  const [activeTab, setActiveTab] = useState<ExpandedPanel>("tldr");
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
    setActiveTab((prev) => (prev === panel ? "tldr" : panel));
  };

  const handleOnairClick = () => {
    if (!hasAudio) return;
    hapticLight();
    if (activeTab !== "onair") {
      setActiveTab("onair");
      if (!isPlaying) handlePlayPause();
    } else {
      handlePlayPause();
    }
  };

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative"
    : "Pragmatic";

  const leanMod = brief.opinion_lean === "left" ? "db-lean-badge--left"
    : brief.opinion_lean === "right" ? "db-lean-badge--right"
    : "db-lean-badge--center";

  const voiceLabel = brief.audio_url
    ? (brief.audio_url.includes("/india/") ? "Puck & Leda"
      : brief.audio_url.includes("/us/") ? "Enceladus & Kore"
      : "Charon & Aoede")
    : "Charon & Aoede";

  return (
    <>
      {hasAudio && (
        <audio ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />
      )}

      <div className="daily-brief" role="complementary" aria-label="Daily Brief">

        {/* Tab bar */}
        <div className="db-tabs" role="tablist" aria-label="Daily Brief sections">

          {/* TL;DR tab */}
          <button
            id="db-tab-tldr"
            className={`db-tab${activeTab === "tldr" ? " db-tab--active" : ""}`}
            role="tab"
            aria-selected={activeTab === "tldr"}
            aria-controls="db-panel-tldr"
            onClick={() => togglePanel("tldr")}
            type="button"
          >
            <span className="db-tab__icon">
              <ScaleIcon size={10} animation="idle" aria-hidden />
            </span>
            <span className="db-tab__cmd">
              <span className="db-tab__void">void </span>--tl;dr
            </span>
            {showSubtitles && (
              <span className="db-tab__subtitle">The Daily Brief</span>
            )}
          </button>

          {/* Opinion tab */}
          {brief.opinion_text && (
            <button
              id="db-tab-opinion"
              className={`db-tab${activeTab === "opinion" ? " db-tab--active" : ""}`}
              role="tab"
              aria-selected={activeTab === "opinion"}
              aria-controls="db-panel-opinion"
              onClick={() => togglePanel("opinion")}
              type="button"
            >
              <span className="db-tab__cmd">
                <span className="db-tab__void">void </span>--opinion
              </span>
              {showSubtitles && (
                <span className="db-tab__subtitle">The Board</span>
              )}
            </button>
          )}

          {/* Onair tab */}
          <button
            id="db-tab-onair"
            className={`db-tab db-tab--onair${activeTab === "onair" ? " db-tab--active" : ""}${isPlaying ? " db-tab--playing" : ""}${!hasAudio ? " db-tab--disabled" : ""}`}
            role="tab"
            aria-selected={activeTab === "onair"}
            aria-controls="db-panel-onair"
            onClick={handleOnairClick}
            type="button"
            disabled={!hasAudio}
            aria-label={!hasAudio ? "Audio broadcast unavailable" : isPlaying ? "Pause broadcast" : "Play void --onair"}
            title={!hasAudio ? "Audio broadcast generates twice daily" : undefined}
          >
            {isPlaying && <span className="db-tab__dot" aria-hidden="true" />}
            <span className="db-tab__icon">
              <ScaleIcon size={10} animation={isPlaying ? "analyzing" : "idle"} aria-hidden />
            </span>
            <span className="db-tab__cmd">
              <span className="db-tab__void">void </span>--onair
            </span>
            {showSubtitles && (
              <span className="db-tab__subtitle">Audio Broadcast</span>
            )}
            <span className="db-tab__glyph" aria-hidden="true">
              {isPlaying ? "\u275A\u275A" : "\u25B6"}
            </span>
          </button>

          {/* Timestamp — pushed to far right */}
          {brief.created_at && (
            <span className="daily-brief__timestamp" aria-label={`Updated ${timeAgo(brief.created_at)}`}>
              {timeAgo(brief.created_at)}
            </span>
          )}
        </div>

        {/* === Tab panels === */}

        {/* TL;DR panel */}
        <div
          id="db-panel-tldr"
          role="tabpanel"
          aria-labelledby="db-tab-tldr"
          className={`db-panel${activeTab === "tldr" ? " db-panel--open" : ""}`}
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
            role="tabpanel"
            aria-labelledby="db-tab-opinion"
            className={`db-panel${activeTab === "opinion" ? " db-panel--open" : ""}`}
          >
            <div className="db-panel__inner daily-brief__opinion">
              <h3 className="daily-brief__opinion-headline">
                {brief.opinion_headline || "The Board"}
              </h3>
              <p>
                {brief.opinion_text}
              </p>
              {brief.opinion_lean && (
                <span className={`db-lean-badge ${leanMod}`}>{leanLabel}</span>
              )}
            </div>
          </div>
        )}

        {/* Onair panel — full audio player */}
        <div
          id="db-panel-onair"
          role="tabpanel"
          aria-labelledby="db-tab-onair"
          className={`db-panel${activeTab === "onair" ? " db-panel--open" : ""}`}
        >
          <div className="db-panel__inner db-audio">
            {/* Play / pause button — 44px circle */}
            <button
              type="button"
              className={`db-audio__play${isPlaying ? " db-audio__play--active" : ""}`}
              onClick={handlePlayPause}
              disabled={!hasAudio}
              aria-label={isPlaying ? "Pause broadcast" : "Play broadcast"}
            >
              <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
            </button>

            {/* Track column — seek bar + meta */}
            <div className="db-audio__track-col">
              <div className="db-audio__seek-wrap">
                <div className="db-audio__bar">
                  <div
                    className="db-audio__fill"
                    style={{ width: `${progress}%` }}
                  />
                </div>
                <input
                  type="range"
                  className="db-audio__seek"
                  min={0}
                  max={displayDuration || 100}
                  value={currentTime}
                  step={0.5}
                  onChange={handleSeek}
                  disabled={!hasAudio}
                  aria-label="Broadcast seek position"
                  aria-valuetext={`${formatTime(currentTime)} of ${formatTime(displayDuration)}`}
                />
              </div>

              <div className="db-audio__meta">
                <span className="db-audio__status">
                  {isPlaying && <span className="db-audio__dot" aria-hidden="true" />}
                  {isPlaying ? `Now playing · ${voiceLabel}` : currentTime > 0 ? `Paused · ${voiceLabel}` : voiceLabel}
                </span>
                <span className="db-audio__time">
                  {formatTime(currentTime)} / {formatTime(displayDuration || 0)}
                </span>
              </div>
            </div>
          </div>
        </div>

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
