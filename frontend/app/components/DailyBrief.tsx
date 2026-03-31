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
  buffered: number;
  audioError: boolean;
  audioRef: React.RefObject<HTMLAudioElement | null>;
  audioCallbackRef: (el: HTMLAudioElement | null) => void;
  handlePlayPause: () => void;
  handleSeek: (e: React.ChangeEvent<HTMLInputElement>) => void;
  /** Current playback speed (1, 1.25, 1.5, 2) */
  playbackSpeed: number;
  /** Cycle to next speed */
  cycleSpeed: () => void;
  /** Skip forward 15 seconds */
  skipForward: () => void;
  /** SkipBackward 15 seconds */
  skipBackward: () => void;
  /** Direct seek to a time in seconds */
  seekTo: (seconds: number) => void;
  /** Whether the persistent bottom player is visible */
  isPlayerVisible: boolean;
  setPlayerVisible: (v: boolean) => void;
  /** Whether the player is expanded (full panel) */
  isExpanded: boolean;
  setExpanded: (v: boolean) => void;
}

export function useDailyBrief(edition: string): DailyBriefState {
  const [brief, setBrief] = useState<DailyBriefData | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [audioError, setAudioError] = useState(false);
  const [buffered, setBuffered] = useState(0);
  const [playbackSpeed, setPlaybackSpeed] = useState(() => {
    if (typeof window === "undefined") return 1;
    try { const s = localStorage.getItem("void-onair-speed"); return s ? Number(s) : 1; } catch { return 1; }
  });
  const [isPlayerVisible, setPlayerVisible] = useState(false);
  const [isExpanded, setExpanded] = useState(false);
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
    setBuffered(0);
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
    const onProgress = () => {
      if (el.buffered.length > 0 && el.duration > 0) {
        setBuffered((el.buffered.end(el.buffered.length - 1) / el.duration) * 100);
      }
    };

    el.addEventListener("timeupdate", onTime);
    el.addEventListener("loadedmetadata", onMeta);
    el.addEventListener("durationchange", onMeta);
    el.addEventListener("ended", onEnd);
    el.addEventListener("error", onError);
    el.addEventListener("progress", onProgress);
    if (el.duration && isFinite(el.duration)) setDuration(el.duration);

    listenerCleanupRef.current = () => {
      el.removeEventListener("timeupdate", onTime);
      el.removeEventListener("loadedmetadata", onMeta);
      el.removeEventListener("durationchange", onMeta);
      el.removeEventListener("ended", onEnd);
      el.removeEventListener("error", onError);
      el.removeEventListener("progress", onProgress);
    };
  }, []);

  const getAudio = useCallback((): HTMLAudioElement | null => {
    if (audioRef.current) return audioRef.current;
    // Fallback: grab by id if callback ref hasn't fired yet
    const el = document.getElementById("void-onair-audio") as HTMLAudioElement | null;
    if (el) {
      audioRef.current = el;
      // Attach listeners if not already attached
      if (!listenerCleanupRef.current) audioCallbackRef(el);
    }
    return el;
  }, [audioCallbackRef]);

  const handlePlayPause = useCallback(() => {
    const audio = getAudio();
    if (!audio) return;
    hapticMedium();
    if (isPlaying) {
      audio.pause();
      setIsPlaying(false);
    } else {
      if (audioError) {
        setAudioError(false);
        audio.load();
      }
      audio.play().catch(() => {
        setAudioError(true);
        setIsPlaying(false);
      });
      setIsPlaying(true);
    }
  }, [isPlaying, audioError, getAudio]);

  const lastSeekTick = useRef(0);
  const handleSeek = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const audio = getAudio();
    if (!audio) return;
    const t = Number(e.target.value);
    const tick = Math.floor(t / 5);
    if (tick !== lastSeekTick.current) {
      lastSeekTick.current = tick;
      hapticTick();
    }
    audio.currentTime = t;
    setCurrentTime(t);
  }, [getAudio]);

  const SPEEDS = [1, 1.25, 1.5, 2] as const;
  const cycleSpeed = useCallback(() => {
    setPlaybackSpeed((prev) => {
      const idx = SPEEDS.indexOf(prev as typeof SPEEDS[number]);
      const next = SPEEDS[(idx + 1) % SPEEDS.length];
      const audio = audioRef.current;
      if (audio) audio.playbackRate = next;
      try { localStorage.setItem("void-onair-speed", String(next)); } catch {}
      return next;
    });
  }, []);

  // Apply saved speed when audio loads
  useEffect(() => {
    const audio = audioRef.current;
    if (audio && playbackSpeed !== 1) audio.playbackRate = playbackSpeed;
  }, [brief, playbackSpeed]);

  const skipForward = useCallback(() => {
    const audio = getAudio();
    if (!audio) return;
    hapticTick();
    audio.currentTime = Math.min(audio.currentTime + 15, audio.duration || Infinity);
    setCurrentTime(audio.currentTime);
  }, [getAudio]);

  const skipBackward = useCallback(() => {
    const audio = getAudio();
    if (!audio) return;
    hapticTick();
    audio.currentTime = Math.max(audio.currentTime - 15, 0);
    setCurrentTime(audio.currentTime);
  }, [getAudio]);

  const seekTo = useCallback((seconds: number) => {
    const audio = getAudio();
    if (!audio) return;
    hapticLight();
    audio.currentTime = seconds;
    setCurrentTime(seconds);
    if (!isPlaying) {
      if (audioError) { setAudioError(false); audio.load(); }
      audio.play().catch(() => { setAudioError(true); setIsPlaying(false); });
      setIsPlaying(true);
    }
  }, [isPlaying, audioError]);

  // Auto-show player when brief has audio
  useEffect(() => {
    if (brief?.audio_url) setPlayerVisible(true);
  }, [brief]);

  return {
    brief, isPlaying, currentTime, duration, buffered, audioError, audioRef, audioCallbackRef,
    handlePlayPause, handleSeek, playbackSpeed, cycleSpeed, skipForward, skipBackward, seekTo,
    isPlayerVisible, setPlayerVisible, isExpanded, setExpanded,
  };
}

/* ---------------------------------------------------------------------------
   DailyBriefText — Banner with TL;DR + Opinion side by side.
   Both start collapsed (headline + preview + CTA). No audio here — that's
   handled by the standalone OnAirButton.
   --------------------------------------------------------------------------- */

export function DailyBriefText({ state }: { state: DailyBriefState }) {
  const { brief } = state;

  const [tldrExpanded, setTldrExpanded] = useState(false);
  const [opinionExpanded, setOpinionExpanded] = useState(false);

  if (!brief) return null;

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
      <div className="daily-brief-banner" role="complementary" aria-label="Daily Brief">

        <div className="db-banner-columns">

          {/* TL;DR Column */}
          <section className="db-col db-col--tldr" aria-label="void --tl;dr">
            <div className="db-col__label">
              <ScaleIcon size={12} animation="idle" />
              <span className="db-col__cmd">void --tl;dr</span>
              {brief.created_at && (
                <span className="db-col__time">{timeAgo(brief.created_at)}</span>
              )}
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
                  className="db-col__more"
                  onClick={handleTldrToggle}
                  type="button"
                  aria-expanded={tldrExpanded}
                >
                  {tldrExpanded ? "Less" : "Read more"}
                </button>
              </>
            )}
          </section>

          {/* Opinion Column */}
          {brief.opinion_text && (
            <section className="db-col db-col--opinion" aria-label="void --opinion">
              <div className="db-col__label">
                <ScaleIcon size={12} animation="idle" />
                <span className="db-col__cmd">void --opinion</span>
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
                className="db-col__more"
                onClick={handleOpinionToggle}
                type="button"
                aria-expanded={opinionExpanded}
              >
                {opinionExpanded ? "Less" : "Read more"}
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
  const { brief, isPlaying, currentTime, duration, buffered, audioError, audioRef, handlePlayPause, handleSeek } = state;

  if (!brief) return null;

  const hasAudio = !!brief.audio_url;
  const displayDuration = (hasAudio && brief.audio_duration_seconds) || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;

  // Section markers — opinion start position as percentage
  const opinionStart = brief.opinion_start_seconds ?? null;
  const hasOpinion = opinionStart !== null && displayDuration > 0;
  const opinionPct = hasOpinion ? (opinionStart / displayDuration) * 100 : 100;

  // Which section is the playhead in?
  const inOpinion = hasOpinion && currentTime >= opinionStart;

  // Snap-to-section handlers
  const seekTo = (seconds: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    hapticLight();
    audio.currentTime = seconds;
    if (!isPlaying) handlePlayPause();
  };

  return (
    <div className={`onair${isPlaying ? " onair--playing" : ""}`} role="region" aria-label="Audio Broadcast">
      {/* Header row */}
      <div className="onair__header">
        <ScaleIcon size={12} animation={isPlaying ? "analyzing" : "idle"} />
        {isPlaying && <span className="onair__live-dot" aria-hidden="true" />}
        <span className="onair__cmd">void --onair</span>
        {durationMin && !isPlaying && (
          <span className="onair__duration">{durationMin} min</span>
        )}
        {isPlaying && (
          <span className="onair__now-playing">Now Playing</span>
        )}
      </div>

      {/* Controls */}
      <div className="onair__controls">
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

        {/* Equalizer bars */}
        <div className={`onair__eq${isPlaying ? " onair__eq--active" : ""}`} aria-hidden="true">
          <span className="onair__eq-bar" style={{ animationDelay: "0ms" }} />
          <span className="onair__eq-bar" style={{ animationDelay: "150ms" }} />
          <span className="onair__eq-bar" style={{ animationDelay: "75ms" }} />
          <span className="onair__eq-bar" style={{ animationDelay: "200ms" }} />
          <span className="onair__eq-bar" style={{ animationDelay: "50ms" }} />
        </div>

        {/* CTA when idle, track when playing */}
        {isPlaying || currentTime > 0 ? (
          <div className="onair__track">
            {/* Section labels — clickable to snap */}
            <div className="onair__sections">
              <button
                className={`onair__section${!inOpinion ? " onair__section--active" : ""}`}
                onClick={() => seekTo(0)}
                type="button"
                style={hasOpinion ? { width: `${opinionPct}%` } : { width: "100%" }}
              >
                News
              </button>
              {hasOpinion && (
                <button
                  className={`onair__section${inOpinion ? " onair__section--active" : ""}`}
                  onClick={() => seekTo(opinionStart)}
                  type="button"
                  style={{ width: `${100 - opinionPct}%` }}
                >
                  Opinion
                </button>
              )}
            </div>

            {/* Seek bar with section divider */}
            <div className="onair__seek-wrap">
              <div className="onair__bar">
                <div className="onair__buffer" style={{ width: `${buffered}%` }} />
                <div className="onair__fill" style={{ width: `${progress}%` }} />
                {hasOpinion && (
                  <span
                    className="onair__section-mark"
                    style={{ left: `${opinionPct}%` }}
                    aria-hidden="true"
                  />
                )}
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
