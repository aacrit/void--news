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
   AudioPlayer — Persistent sticky bottom bar.
   ONE location for all audio controls. No CTA elsewhere.
   Shows automatically when brief has audio_url.
   --------------------------------------------------------------------------- */

export default function AudioPlayer({ state }: { state: DailyBriefState }) {
  const {
    brief, isPlaying, currentTime, duration, buffered, audioError,
    audioCallbackRef, handlePlayPause, handleSeek,
    playbackSpeed, cycleSpeed, skipForward, skipBackward, seekTo,
    isExpanded, setExpanded,
  } = state;

  const waveformBars = useMemo(() =>
    Array.from({ length: 32 }, (_, i) => 10 + Math.sin(i * 0.55) * 16 + Math.sin(i * 1.3) * 6),
  []);

  if (!brief) return null;

  const hasAudio = !!brief.audio_url;
  const displayDuration = brief.audio_duration_seconds || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;
  const effectiveOpinionStart = brief.opinion_start_seconds ?? (brief.opinion_text ? displayDuration * 0.6 : null);
  const hasOpinionSection = brief.opinion_text != null;
  const opinionPct = brief.opinion_start_seconds != null && displayDuration > 0
    ? (brief.opinion_start_seconds / displayDuration) * 100
    : hasOpinionSection ? 60 : 100;
  const inOpinion = hasOpinionSection && effectiveOpinionStart !== null && currentTime >= effectiveOpinionStart;
  const speedLabel = `${playbackSpeed}x`;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;


  return (
    <>
      {hasAudio && <audio ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />}

      <div
        className={`ap${isPlaying ? " ap--playing" : ""}${isExpanded ? " ap--expanded" : ""}${!hasAudio ? " ap--no-audio" : ""}`}
        role="region"
        aria-label="void --onair audio player"
      >
        {/* ── Expanded Panel ── */}
        {isExpanded && hasAudio && (
          <div className="ap__panel">
            <div className="ap__panel-header">
              <div className="ap__identity">
                <ScaleIcon size={14} animation={isPlaying ? "analyzing" : "idle"} />
                {isPlaying && <span className="ap__rec-dot" aria-hidden="true" />}
                <span className="ap__brand">void --onair</span>
              </div>
              <button className="ap__collapse" onClick={() => setExpanded(false)}
                type="button" aria-label="Collapse player">
                <svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
                  <path d="M5 8l5 5 5-5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            </div>

            {brief.audio_voice_label && (
              <div className="ap__voice-label">{brief.audio_voice_label}</div>
            )}

            <div className={`ap__waveform${isPlaying ? " ap__waveform--active" : ""}`} aria-hidden="true">
              {waveformBars.map((h, i) => (
                <div key={i} className="ap__waveform-bar"
                  style={{ height: `${h}px`, animationDelay: `${i * 55}ms` }} />
              ))}
            </div>

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
                type="button" aria-label={isPlaying ? "Pause" : "Play"}>
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

            <div className="ap__sections">
              <button className={`ap__section-btn${!inOpinion ? " ap__section-btn--active" : ""}`}
                onClick={() => seekTo(0)} type="button">News</button>
              {hasOpinionSection && (
                <button className={`ap__section-btn${inOpinion ? " ap__section-btn--active" : ""}`}
                  onClick={() => effectiveOpinionStart != null ? seekTo(effectiveOpinionStart) : null}
                  type="button">Opinion</button>
              )}
            </div>

            <div className="ap__seek-wrap">
              <div className="ap__bar">
                <div className="ap__buffer" style={{ width: `${buffered}%` }} />
                <div className="ap__fill" style={{ width: `${progress}%` }} />
                {hasOpinionSection && (
                  <span className="ap__section-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />
                )}
              </div>
              <input type="range" className="ap__seek-input" min={0}
                max={displayDuration || 100} value={currentTime} step={0.5}
                onChange={handleSeek} aria-label="Seek position"
                aria-valuetext={`${formatTime(currentTime)} of ${formatTime(displayDuration)}`} />
            </div>

            <div className="ap__panel-footer">
              <span className="ap__time">{formatTime(currentTime)} / {formatTime(displayDuration || 0)}</span>
              <button className="ap__speed" onClick={() => { hapticLight(); cycleSpeed(); }}
                type="button" aria-label={`Playback speed ${speedLabel}`}>{speedLabel}</button>
            </div>
          </div>
        )}

        {/* ── Mini Bar — always visible ── */}
        <div className="ap__mini">
          <button
            className={`ap__play${isPlaying ? " ap__play--active" : ""}`}
            onClick={() => { if (hasAudio) { hapticMedium(); handlePlayPause(); } }}
            type="button"
            disabled={!hasAudio}
            aria-label={!hasAudio ? "Audio broadcast unavailable" : isPlaying ? "Pause broadcast" : "Play broadcast"}>
            <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
          </button>

          <span className={`ap__section-label${audioError ? " ap__section-label--error" : ""}${!hasAudio ? " ap__section-label--disabled" : ""}`}>
            {!hasAudio ? "void --onair" : audioError ? "Unavailable" : isPlaying || currentTime > 0 ? (inOpinion ? "Opinion" : "News") : "void --onair"}
          </span>

          {!hasAudio && (
            <span className="ap__mini-hint">Audio generates twice daily</span>
          )}
          {hasAudio && !isPlaying && currentTime === 0 && durationMin && (
            <span className="ap__mini-hint">{durationMin} min</span>
          )}

          <div className="ap__mini-bar-wrap">
            <div className="ap__mini-bar">
              <div className="ap__mini-buffer" style={{ width: `${buffered}%` }} />
              <div className="ap__mini-fill" style={{ width: `${progress}%` }} />
              {hasOpinionSection && (
                <span className="ap__mini-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />
              )}
            </div>
            <input type="range" className="ap__mini-seek" min={0}
              max={displayDuration || 100} value={currentTime} step={0.5}
              onChange={handleSeek} aria-label="Seek position"
              aria-valuetext={`${formatTime(currentTime)} of ${formatTime(displayDuration)}`} />
          </div>

          <span className="ap__mini-time">
            {formatTime(currentTime)}<span className="ap__mini-dur"> / {formatTime(displayDuration || 0)}</span>
          </span>

          <button className="ap__mini-speed" onClick={() => { hapticLight(); cycleSpeed(); }}
            type="button" aria-label={`Speed ${speedLabel}`}>{speedLabel}</button>

          <button className="ap__expand" onClick={() => setExpanded(!isExpanded)}
            type="button" aria-label={isExpanded ? "Collapse player" : "Expand player"}>
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true">
              <path d={isExpanded ? "M4.5 7l4.5 4.5L13.5 7" : "M4.5 11l4.5-4.5L13.5 11"}
                stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </button>
        </div>
      </div>
    </>
  );
}
