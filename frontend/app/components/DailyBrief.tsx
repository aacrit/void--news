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
    // Fetch edition-specific brief (pipeline generates distinct content per edition)
    fetchDailyBrief(edition).then((data) => {
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
   DailyBriefText — stacked sections: tl;dr (always visible), opinion
   (collapsible on mobile), onair (collapsible on mobile, auto-expands
   when playing). No tab system — sections always visible on desktop.
   --------------------------------------------------------------------------- */

export function DailyBriefText({ state }: { state: DailyBriefState }) {
  const { brief, isPlaying, currentTime, duration, audioError, audioCallbackRef, handlePlayPause, handleSeek } = state;

  // Mobile collapse state — opinion and onair start closed on mobile
  const [opinionOpen, setOpinionOpen] = useState(true);
  const [onairOpen, setOnairOpen] = useState(false);
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const mq = window.matchMedia("(max-width: 767px)");
    const update = (e: MediaQueryListEvent | MediaQueryList) => {
      setIsMobile(e.matches);
      if (e.matches) {
        setOpinionOpen(false);
        // Auto-expand onair when audio is available on mobile
        setOnairOpen(!!brief?.audio_url);
      } else {
        setOpinionOpen(true);
        setOnairOpen(true);
      }
    };
    update(mq);
    mq.addEventListener("change", update);
    return () => mq.removeEventListener("change", update);
  }, []);

  // Auto-expand onair section when playback starts or audio becomes available on mobile
  useEffect(() => {
    if (isMobile && (isPlaying || brief?.audio_url)) setOnairOpen(true);
  }, [isPlaying, isMobile, brief?.audio_url]);

  if (!brief) return null;

  const hasAudio = !!brief.audio_url && !audioError;
  const displayDuration = (hasAudio && brief.audio_duration_seconds) || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;

  const paragraphs = brief.tldr_text
    .split("\n")
    .map((p) => p.trim())
    .filter(Boolean);

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative"
    : "Pragmatic";

  const leanMod = brief.opinion_lean === "left" ? "db-lean-badge--left"
    : brief.opinion_lean === "right" ? "db-lean-badge--right"
    : "db-lean-badge--center";

  const voiceLabel = brief.audio_voice_label || "Two voices";

  const handleOpinionToggle = () => {
    if (!isMobile) return;
    hapticLight();
    setOpinionOpen((prev) => !prev);
  };

  const handleOnairToggle = () => {
    if (!isMobile) return;
    hapticLight();
    if (!hasAudio) return;
    if (!onairOpen) {
      setOnairOpen(true);
      if (!isPlaying) handlePlayPause();
    } else {
      setOnairOpen(false);
    }
  };

  // On desktop the onair label triggers play/pause directly
  const handleOnairLabelClick = () => {
    if (isMobile) {
      handleOnairToggle();
    } else {
      if (!hasAudio) return;
      hapticLight();
      handlePlayPause();
    }
  };

  // Collapsible is always "open" on desktop (CSS enforces 1fr via media query)
  // On mobile, the JS state controls the open class
  const opinionCollapsible = isMobile
    ? `db-block__collapsible${opinionOpen ? " db-block__collapsible--open" : ""}`
    : "db-block__collapsible db-block__collapsible--open";

  const onairCollapsible = isMobile
    ? `db-block__collapsible${(onairOpen || isPlaying) ? " db-block__collapsible--open" : ""}`
    : "db-block__collapsible db-block__collapsible--open";

  return (
    <>
      {hasAudio && (
        <audio ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />
      )}

      <div className="daily-brief" role="complementary" aria-label="Daily Brief">

        {/* Section header */}
        <div className="db-section-header">
          <span className="db-section-title">Daily Brief</span>
          {brief.created_at && (
            <span className="db-section-time" aria-label={`Updated ${timeAgo(brief.created_at)}`}>
              {timeAgo(brief.created_at)}
            </span>
          )}
        </div>

        {/* TL;DR — always visible, no collapse */}
        <section className="db-block db-block--tldr" aria-label="void --tl;dr The Daily Brief">
          <div className="db-block__label">
            <span className="db-block__cmd">void --tl;dr</span>
            <span className="db-block__subtitle">The Daily Brief</span>
          </div>
          <div className="db-block__collapsible db-block__collapsible--open">
            <div className="db-block__inner">
              <div className="db-block__body daily-brief__body">
                {paragraphs.map((p, i) => (
                  <p key={i}>{p}</p>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* Opinion — always visible on desktop, collapsible on mobile */}
        {brief.opinion_text && (
          <section className="db-block db-block--opinion" aria-label="void --opinion The Board">
            <button
              className={`db-block__label db-block__label--toggle${opinionOpen ? " db-block__label--open" : ""}`}
              onClick={handleOpinionToggle}
              type="button"
              aria-expanded={opinionOpen}
              aria-label={opinionOpen ? "Collapse opinion section" : "Expand opinion section"}
            >
              <span className="db-block__cmd">void --opinion</span>
              <span className="db-block__subtitle">The Board</span>
              {brief.opinion_lean && (
                <span className={`db-lean-badge ${leanMod}`}>{leanLabel}</span>
              )}
              <span className="db-block__chevron" aria-hidden="true">
                {opinionOpen ? "▴" : "▾"}
              </span>
            </button>
            <div className={opinionCollapsible}>
              <div className="db-block__inner">
                <div className="db-block__body daily-brief__opinion">
                  {brief.opinion_headline && (
                    <h3 className="daily-brief__opinion-headline">{brief.opinion_headline}</h3>
                  )}
                  <p>{brief.opinion_text}</p>
                </div>
              </div>
            </div>
          </section>
        )}

        {/* On Air — always visible on desktop, collapsible on mobile */}
        <section className="db-block db-block--onair" aria-label="void --onair Audio Broadcast">
          <button
            className={`db-block__label db-block__label--toggle${(onairOpen || isPlaying) ? " db-block__label--open" : ""}${!hasAudio ? " db-block__label--disabled" : ""}`}
            onClick={handleOnairLabelClick}
            type="button"
            disabled={!hasAudio}
            aria-expanded={onairOpen || isPlaying}
            aria-label={
              !hasAudio ? "Audio broadcast unavailable"
                : isMobile
                  ? (onairOpen ? "Collapse audio player" : "Expand audio player")
                  : isPlaying ? "Pause broadcast" : "Play void --onair"
            }
            title={!hasAudio ? "Audio broadcast generates twice daily" : undefined}
          >
            {isPlaying && <span className="db-block__live-dot" aria-hidden="true" />}
            <span className="db-block__cmd">
              <ScaleIcon size={10} animation={isPlaying ? "analyzing" : "idle"} aria-hidden />
              {" "}void --onair
            </span>
            <span className="db-block__subtitle">Audio Broadcast</span>
            <span className="db-block__chevron" aria-hidden="true">
              {isPlaying ? "\u275A\u275A" : "\u25B6"}
            </span>
          </button>
          <div className={onairCollapsible}>
            <div className="db-block__inner">
              <div className="db-block__body db-audio">
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
                      {isPlaying
                        ? `Now playing · ${voiceLabel}`
                        : currentTime > 0
                          ? `Paused · ${voiceLabel}`
                          : voiceLabel}
                    </span>
                    <span className="db-audio__time">
                      {formatTime(currentTime)} / {formatTime(displayDuration || 0)}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

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
