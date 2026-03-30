"use client";

import { useMemo } from "react";
import type { DailyBriefState } from "./DailyBrief";
import { ScaleIcon } from "./ScaleIcon";
import { hapticMedium, hapticLight, hapticTick } from "../lib/haptics";

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

/* ---------------------------------------------------------------------------
   AudioPlayer — Persistent bottom bar + expandable broadcast console

   Mini bar (56px): play/pause, progress, time, speed, expand chevron
   Expanded: waveform, skip 15s, section nav, seek bar, voice label
   Renders once in HomeContent, outside scroll container.
   The <audio> element always mounts when audio_url exists (independent
   of player visibility) so the callback ref fires immediately.
   --------------------------------------------------------------------------- */

export default function AudioPlayer({ state }: { state: DailyBriefState }) {
  const {
    brief, isPlaying, currentTime, duration, buffered,
    audioCallbackRef, handlePlayPause, handleSeek,
    playbackSpeed, cycleSpeed, skipForward, skipBackward, seekTo,
    isPlayerVisible, isExpanded, setExpanded,
  } = state;

  // Waveform bar heights — 32 desktop, 20 mobile (CSS hides extras)
  const waveformBars = useMemo(() =>
    Array.from({ length: 32 }, (_, i) => 10 + Math.sin(i * 0.55) * 16 + Math.sin(i * 1.3) * 6),
  []);

  const hasAudio = !!brief?.audio_url;

  // Audio element must mount as soon as URL is available — before player is visible
  if (!brief || !hasAudio) return null;

  const displayDuration = brief.audio_duration_seconds || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;

  // Section markers
  const opinionStart = brief.opinion_start_seconds ?? null;
  const hasOpinionTimestamp = opinionStart !== null && displayDuration > 0;
  const effectiveOpinionStart = opinionStart ?? (brief.opinion_text ? displayDuration * 0.6 : null);
  const hasOpinionSection = brief.opinion_text != null;
  const opinionPct = hasOpinionTimestamp ? (opinionStart / displayDuration) * 100
    : hasOpinionSection ? 60 : 100;
  const inOpinion = hasOpinionSection && effectiveOpinionStart !== null && currentTime >= effectiveOpinionStart;

  const speedLabel = playbackSpeed === 1 ? "1x"
    : playbackSpeed === 1.25 ? "1.25x"
    : playbackSpeed === 1.5 ? "1.5x" : "2x";

  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;

  return (
    <>
      {/* Audio element — always in DOM when URL exists */}
      <audio ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />

      {/* Player bar — visible once isPlayerVisible is true */}
      {isPlayerVisible && (
        <div
          className={`ap${isPlaying ? " ap--playing" : ""}${isExpanded ? " ap--expanded" : ""}`}
          role="region"
          aria-label="Audio player"
        >
          {/* ── Expanded Panel ── */}
          {isExpanded && (
            <div className="ap__panel">
              {/* Header */}
              <div className="ap__panel-header">
                <div className="ap__identity">
                  <ScaleIcon size={14} animation={isPlaying ? "analyzing" : "idle"} />
                  {isPlaying && <span className="ap__rec-dot" aria-hidden="true" />}
                  <span className="ap__brand">void --onair</span>
                </div>
                <button
                  className="ap__collapse"
                  onClick={() => setExpanded(false)}
                  type="button"
                  aria-label="Collapse player"
                >
                  <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                    <path d="M5 8l5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </button>
              </div>

              {/* Voice label */}
              {brief.audio_voice_label && (
                <div className="ap__voice-label">{brief.audio_voice_label}</div>
              )}

              {/* Waveform */}
              <div className={`ap__waveform${isPlaying ? " ap__waveform--active" : ""}`} aria-hidden="true">
                {waveformBars.map((h, i) => (
                  <div key={i} className="ap__waveform-bar"
                    style={{ height: `${h}px`, animationDelay: `${i * 55}ms` }} />
                ))}
              </div>

              {/* Transport — skip back, play/pause, skip forward */}
              <div className="ap__transport">
                <button className="ap__skip" onClick={() => { hapticTick(); skipBackward(); }}
                  type="button" aria-label="Skip back 15 seconds">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z" fill="currentColor"/>
                    <text x="12" y="15.5" textAnchor="middle" fontSize="7" fontWeight="600" fill="currentColor" fontFamily="var(--font-data)">15</text>
                  </svg>
                </button>
                <button
                  className={`ap__play-lg${isPlaying ? " ap__play-lg--active" : ""}`}
                  onClick={() => { hapticMedium(); handlePlayPause(); }}
                  type="button"
                  aria-label={isPlaying ? "Pause" : "Play"}
                >
                  <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
                </button>
                <button className="ap__skip" onClick={() => { hapticTick(); skipForward(); }}
                  type="button" aria-label="Skip forward 15 seconds">
                  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                    <path d="M12 5V1l5 5-5 5V7c-3.31 0-6 2.69-6 6s2.69 6 6 6 6-2.69 6-6h2c0 4.42-3.58 8-8 8s-8-3.58-8-8 3.58-8 8-8z" fill="currentColor"/>
                    <text x="12" y="15.5" textAnchor="middle" fontSize="7" fontWeight="600" fill="currentColor" fontFamily="var(--font-data)">15</text>
                  </svg>
                </button>
              </div>

              {/* Section nav */}
              <div className="ap__sections">
                <button
                  className={`ap__section-btn${!inOpinion ? " ap__section-btn--active" : ""}`}
                  onClick={() => seekTo(0)}
                  type="button"
                >
                  News
                </button>
                {hasOpinionSection && (
                  <button
                    className={`ap__section-btn${inOpinion ? " ap__section-btn--active" : ""}`}
                    onClick={() => effectiveOpinionStart != null ? seekTo(effectiveOpinionStart) : null}
                    type="button"
                  >
                    Opinion
                  </button>
                )}
              </div>

              {/* Seek bar */}
              <div className="ap__seek-wrap">
                <div className="ap__bar">
                  <div className="ap__buffer" style={{ width: `${buffered}%` }} />
                  <div className="ap__fill" style={{ width: `${progress}%` }} />
                  {hasOpinionSection && (
                    <span className="ap__section-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />
                  )}
                </div>
                <input
                  type="range"
                  className="ap__seek-input"
                  min={0}
                  max={displayDuration || 100}
                  value={currentTime}
                  step={0.5}
                  onChange={handleSeek}
                  aria-label="Seek position"
                  aria-valuetext={`${formatTime(currentTime)} of ${formatTime(displayDuration)}`}
                />
              </div>

              {/* Time + speed */}
              <div className="ap__panel-footer">
                <span className="ap__time">
                  {formatTime(currentTime)} / {formatTime(displayDuration || 0)}
                </span>
                <button className="ap__speed" onClick={() => { hapticLight(); cycleSpeed(); }}
                  type="button" aria-label={`Playback speed ${speedLabel}`}>
                  {speedLabel}
                </button>
              </div>
            </div>
          )}

          {/* ── Mini Bar ── */}
          <div className="ap__mini">
            {/* Play/Pause */}
            <button
              className={`ap__play${isPlaying ? " ap__play--active" : ""}`}
              onClick={() => { hapticMedium(); handlePlayPause(); }}
              type="button"
              aria-label={isPlaying ? "Pause broadcast" : "Play broadcast"}
            >
              <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
            </button>

            {/* Section label */}
            <span className="ap__section-label">
              {isPlaying || currentTime > 0
                ? (inOpinion ? "Opinion" : "News")
                : "void --onair"
              }
            </span>

            {/* Duration hint when idle */}
            {!isPlaying && currentTime === 0 && durationMin && (
              <span className="ap__mini-hint">{durationMin} min</span>
            )}

            {/* Progress bar */}
            <div className="ap__mini-bar-wrap">
              <div className="ap__mini-bar">
                <div className="ap__mini-buffer" style={{ width: `${buffered}%` }} />
                <div className="ap__mini-fill" style={{ width: `${progress}%` }} />
                {hasOpinionSection && (
                  <span className="ap__mini-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />
                )}
              </div>
              <input
                type="range"
                className="ap__mini-seek"
                min={0}
                max={displayDuration || 100}
                value={currentTime}
                step={0.5}
                onChange={handleSeek}
                aria-label="Seek position"
              />
            </div>

            {/* Time */}
            <span className="ap__mini-time">
              {formatTime(currentTime)}<span className="ap__mini-dur"> / {formatTime(displayDuration || 0)}</span>
            </span>

            {/* Speed (desktop only) */}
            <button className="ap__mini-speed" onClick={() => { hapticLight(); cycleSpeed(); }}
              type="button" aria-label={`Speed ${speedLabel}`}>
              {speedLabel}
            </button>

            {/* Expand */}
            <button
              className="ap__expand"
              onClick={() => setExpanded(!isExpanded)}
              type="button"
              aria-label={isExpanded ? "Collapse player" : "Expand player"}
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
                <path d={isExpanded ? "M4.5 7l4.5 4.5L13.5 7" : "M4.5 11l4.5-4.5L13.5 11"}
                  stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      )}
    </>
  );
}
