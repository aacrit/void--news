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
   Shared state — call once in HomeContent, pass to DailyBriefText + OnAirButton.
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
   DailyBriefText — Banner with TL;DR + Opinion side by side.
   Both start collapsed (headline + preview + CTA). No audio here — that's
   handled by the standalone OnAirButton.
   --------------------------------------------------------------------------- */

export function DailyBriefText({ state }: { state: DailyBriefState }) {
  const { brief, audioError, audioCallbackRef } = state;

  const [tldrExpanded, setTldrExpanded] = useState(false);
  const [opinionExpanded, setOpinionExpanded] = useState(false);

  if (!brief) return null;

  const hasAudio = !!brief.audio_url && !audioError;

  const paragraphs = brief.tldr_text
    .split("\n")
    .map((p) => p.trim())
    .filter(Boolean);

  // Preview: first 2 lines, rest hidden behind expand
  const previewLines = paragraphs.slice(0, 2);
  const expandedLines = paragraphs.slice(2);

  const opinionPreview = brief.opinion_text
    ? brief.opinion_text.split(/[.!?]\s/).slice(0, 2).join(". ").trim()
    : "";
  // Ensure preview ends with punctuation
  const opinionPreviewText = opinionPreview && !opinionPreview.match(/[.!?]$/)
    ? opinionPreview + "."
    : opinionPreview;

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative"
    : "Pragmatic";

  const leanMod = brief.opinion_lean === "left" ? "db-lean-badge--left"
    : brief.opinion_lean === "right" ? "db-lean-badge--right"
    : "db-lean-badge--center";

  const handleTldrToggle = () => {
    hapticLight();
    setTldrExpanded((prev) => !prev);
  };

  const handleOpinionToggle = () => {
    hapticLight();
    setOpinionExpanded((prev) => !prev);
  };

  return (
    <>
      {hasAudio && (
        <audio ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />
      )}

      <div className="daily-brief-banner" role="complementary" aria-label="Daily Brief">

        {/* Banner header */}
        <div className="db-banner-header">
          <span className="db-banner-title">Daily Brief</span>
          {brief.created_at && (
            <span className="db-banner-time" aria-label={`Updated ${timeAgo(brief.created_at)}`}>
              {timeAgo(brief.created_at)}
            </span>
          )}
        </div>

        <div className="db-banner-columns">

          {/* TL;DR Column */}
          <section className="db-col db-col--tldr" aria-label="void --tl;dr The Daily Brief">
            <div className="db-col__label">
              <span className="db-col__cmd">void --tl;dr</span>
              <span className="db-col__subtitle">The Daily Brief</span>
            </div>

            {brief.tldr_headline && (
              <h3 className="db-col__headline db-col__headline--accent">{brief.tldr_headline}</h3>
            )}

            <div className="db-col__preview">
              {previewLines.map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>

            {expandedLines.length > 0 && (
              <>
                <div className={`db-col__expand${tldrExpanded ? " db-col__expand--open" : ""}`}>
                  <div className="db-col__expand-inner">
                    {expandedLines.map((p, i) => (
                      <p key={i}>{p}</p>
                    ))}
                  </div>
                </div>
                <button
                  className="db-col__cta"
                  onClick={handleTldrToggle}
                  type="button"
                  aria-expanded={tldrExpanded}
                  aria-label={tldrExpanded ? "Collapse brief" : "Read full brief"}
                >
                  {tldrExpanded ? "Collapse" : "Read full brief"}
                </button>
              </>
            )}
          </section>

          {/* Opinion Column */}
          {brief.opinion_text && (
            <section className="db-col db-col--opinion" aria-label="void --opinion The Board">
              <div className="db-col__label">
                <span className="db-col__cmd">void --opinion</span>
                <span className="db-col__subtitle">The Board</span>
                {brief.opinion_lean && (
                  <span className={`db-lean-badge ${leanMod}`}>{leanLabel}</span>
                )}
              </div>

              {brief.opinion_headline && (
                <h3 className="db-col__headline">{brief.opinion_headline}</h3>
              )}

              <p className="db-col__preview">{opinionPreviewText}</p>

              <div className={`db-col__expand${opinionExpanded ? " db-col__expand--open" : ""}`}>
                <div className="db-col__expand-inner">
                  <p>{brief.opinion_text}</p>
                </div>
              </div>

              <button
                className="db-col__cta"
                onClick={handleOpinionToggle}
                type="button"
                aria-expanded={opinionExpanded}
                aria-label={opinionExpanded ? "Collapse opinion" : "Read full opinion"}
              >
                {opinionExpanded ? "Collapse" : "Read full opinion"}
              </button>
            </section>
          )}

        </div>
      </div>
    </>
  );
}

/* ---------------------------------------------------------------------------
   OnAirButton — standalone audio pill, rendered separately from the banner.
   --------------------------------------------------------------------------- */

export function OnAirButton({ state }: { state: DailyBriefState }) {
  const { brief, isPlaying, currentTime, duration, audioError, handlePlayPause, handleSeek } = state;

  if (!brief) return null;

  const hasAudio = !!brief.audio_url && !audioError;
  const displayDuration = (hasAudio && brief.audio_duration_seconds) || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;

  return (
    <div className={`onair${isPlaying ? " onair--playing" : ""}`} role="region" aria-label="Audio Broadcast">
      {/* Broadcast header row */}
      <div className="onair__header">
        {isPlaying && <span className="onair__live-dot" aria-hidden="true" />}
        <span className="onair__cmd">void --onair</span>
        <span className="onair__tagline">Audio Broadcast</span>
        {durationMin && !isPlaying && (
          <span className="onair__duration">{durationMin} min</span>
        )}
        {isPlaying && (
          <span className="onair__now-playing">Now Playing</span>
        )}
      </div>

      {/* Main control area */}
      <div className="onair__controls">
        {/* Play/pause button */}
        <button
          className={`onair__play${isPlaying ? " onair__play--active" : ""}`}
          onClick={handlePlayPause}
          disabled={!hasAudio}
          type="button"
          aria-label={
            !hasAudio ? "Audio broadcast unavailable"
              : isPlaying ? "Pause broadcast" : "Play broadcast"
          }
          title={!hasAudio ? "Audio broadcast generates twice daily" : undefined}
        >
          <span className="onair__play-icon" aria-hidden="true">
            {isPlaying ? "\u275A\u275A" : "\u25B6"}
          </span>
        </button>

        {/* Equalizer bars — always visible, animate when playing */}
        <div className={`onair__eq${isPlaying ? " onair__eq--active" : ""}`} aria-hidden="true">
          <span className="onair__eq-bar" style={{ animationDelay: "0ms" }} />
          <span className="onair__eq-bar" style={{ animationDelay: "150ms" }} />
          <span className="onair__eq-bar" style={{ animationDelay: "75ms" }} />
          <span className="onair__eq-bar" style={{ animationDelay: "200ms" }} />
          <span className="onair__eq-bar" style={{ animationDelay: "50ms" }} />
        </div>

        {/* CTA or seek bar */}
        {isPlaying ? (
          <div className="onair__track">
            <div className="onair__seek-wrap">
              <div className="onair__bar">
                <div className="onair__fill" style={{ width: `${progress}%` }} />
              </div>
              <input
                type="range"
                className="onair__seek"
                min={0}
                max={displayDuration || 100}
                value={currentTime}
                step={0.5}
                onChange={handleSeek}
                aria-label="Broadcast seek position"
                aria-valuetext={`${formatTime(currentTime)} of ${formatTime(displayDuration)}`}
              />
            </div>
            <span className="onair__time">
              {formatTime(currentTime)} / {formatTime(displayDuration || 0)}
            </span>
          </div>
        ) : hasAudio ? (
          <button
            className="onair__cta"
            onClick={handlePlayPause}
            type="button"
          >
            Listen to today&rsquo;s broadcast
          </button>
        ) : (
          <span className="onair__unavailable">Broadcast generates twice daily</span>
        )}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------------------
   Default export — backward compat.
   --------------------------------------------------------------------------- */

export default function DailyBrief({ edition }: DailyBriefProps) {
  const state = useDailyBrief(edition);
  return <DailyBriefText state={state} />;
}
