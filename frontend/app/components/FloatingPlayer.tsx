"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import type { DailyBriefState } from "./DailyBrief";
import LogoIcon from "./LogoIcon";
import { hapticLight, hapticMedium, hapticConfirm } from "../lib/haptics";

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

export default function FloatingPlayer({ state }: { state: DailyBriefState }) {
  const {
    brief, isPlaying, currentTime, duration, buffered, audioError,
    handlePlayPause, handleSeek,
    playbackSpeed, cycleSpeed, skipForward, skipBackward, seekTo,
    isPlayerVisible, setPlayerVisible,
  } = state;

  const [expanded, setExpanded] = useState(false);
  const playerRef = useRef<HTMLDivElement>(null);

  const waveformBars = useMemo(() =>
    Array.from({ length: 24 }, (_, i) => Math.min(28, 8 + Math.sin(i * 0.6) * 14 + Math.sin(i * 1.4) * 5)),
  []);

  if (!brief || !brief.audio_url || !isPlayerVisible) return null;

  const displayDuration = brief.audio_duration_seconds || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;
  const durationMin = displayDuration ? Math.ceil(displayDuration / 60) : null;
  const speedLabel = `${playbackSpeed}x`;

  const opinionStart = brief.opinion_start_seconds ?? null;
  const effectiveOpinionStart = opinionStart ?? (brief.opinion_text ? displayDuration * 0.6 : null);
  const hasOpinionSection = brief.opinion_text != null;
  const opinionPct = opinionStart !== null && displayDuration > 0
    ? (opinionStart / displayDuration) * 100
    : hasOpinionSection ? 60 : 100;
  const inOpinion = hasOpinionSection && effectiveOpinionStart !== null && currentTime >= effectiveOpinionStart;

  const toggleExpand = () => {
    hapticLight();
    setExpanded(v => !v);
  };

  const dismiss = () => {
    hapticLight();
    setPlayerVisible(false);
    setExpanded(false);
  };

  return (
    <div
      ref={playerRef}
      className={[
        "fp",
        expanded ? "fp--expanded" : "fp--compact",
        isPlaying ? "fp--playing" : "",
      ].filter(Boolean).join(" ")}
      role="region"
      aria-label="Audio player"
    >
      {/* ── COMPACT PILL ── */}
      {!expanded && (
        <div className="fp__pill" onClick={toggleExpand}>
          {/* Void logo */}
          <LogoIcon size={16} animation={isPlaying ? "analyzing" : "idle"} className="fp__logo" />

          {/* Play/Pause */}
          <button
            className={`fp__play${isPlaying ? " fp__play--active" : ""}`}
            onClick={(e) => { e.stopPropagation(); hapticConfirm(); handlePlayPause(); }}
            type="button"
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
          </button>

          {/* Track info */}
          <div className="fp__info">
            {isPlaying && <span className="fp__rec-dot" aria-hidden="true" />}
            <span className="fp__title">void --onair</span>
            <span className="fp__section">{inOpinion ? "Opinion" : "News"}</span>
          </div>

          {/* Time */}
          <span className="fp__time">
            {isPlaying || currentTime > 0 ? formatTime(currentTime) : durationMin ? `${durationMin}m` : ""}
          </span>

          {/* Mini progress bar */}
          <div className="fp__mini-progress" aria-hidden="true">
            <div className="fp__mini-progress-fill" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}

      {/* ── EXPANDED BAR ── */}
      {expanded && (
        <div className="fp__bar">
          {/* Header */}
          <div className="fp__bar-header">
            <div className="fp__bar-brand">
              <LogoIcon size={16} animation={isPlaying ? "analyzing" : "idle"} />
              <span className="fp__bar-title">void --onair</span>
              {audioError && <span className="fp__bar-error">Unavailable</span>}
            </div>
            <div className="fp__bar-actions">
              <button className="fp__speed" onClick={() => { hapticLight(); cycleSpeed(); }}
                type="button" aria-label={`Speed ${speedLabel}`}>{speedLabel}</button>
              <button className="fp__minimize" onClick={toggleExpand} type="button" aria-label="Minimize player">
                <span aria-hidden="true">&#9662;</span>
              </button>
              <button className="fp__dismiss" onClick={dismiss} type="button" aria-label="Close player">
                <span aria-hidden="true">&times;</span>
              </button>
            </div>
          </div>

          {/* Waveform */}
          <div className={`fp__waveform${isPlaying ? " fp__waveform--active" : ""}`} aria-hidden="true">
            {waveformBars.map((h, i) => (
              <div key={i} className="fp__waveform-bar" style={{ height: `${h}px`, animationDelay: `${i * 50}ms` }} />
            ))}
          </div>

          {/* Transport */}
          <div className="fp__transport">
            <button className="fp__skip" onClick={() => skipBackward()} type="button" aria-label="Back 15s">-15</button>
            <button
              className={`fp__play-lg${isPlaying ? " fp__play-lg--active" : ""}`}
              onClick={() => { hapticMedium(); handlePlayPause(); }}
              type="button" aria-label={isPlaying ? "Pause" : "Play"}
            >
              <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
            </button>
            <button className="fp__skip" onClick={() => skipForward()} type="button" aria-label="Forward 15s">+15</button>
          </div>

          {/* Seek bar */}
          <div className="fp__seek">
            <div className="fp__seek-sections">
              <button className={`fp__seek-sec${!inOpinion ? " fp__seek-sec--active" : ""}`}
                onClick={() => seekTo(0)} type="button">News</button>
              {hasOpinionSection && (
                <button className={`fp__seek-sec${inOpinion ? " fp__seek-sec--active" : ""}`}
                  onClick={() => effectiveOpinionStart != null ? seekTo(effectiveOpinionStart) : null}
                  type="button">Opinion</button>
              )}
            </div>
            <div className="fp__seek-bar-wrap">
              <div className="fp__seek-bar">
                <div className="fp__seek-buffer" style={{ width: `${buffered}%` }} />
                <div className="fp__seek-fill" style={{ width: `${progress}%` }} />
                {hasOpinionSection && <span className="fp__seek-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />}
              </div>
              <input type="range" className="fp__seek-input" min={0} max={displayDuration || 100}
                value={currentTime} step={0.5} onChange={handleSeek} aria-label="Seek"
                aria-valuetext={`${formatTime(currentTime)} of ${formatTime(displayDuration)}`} />
            </div>
            <div className="fp__seek-time">
              <span>{formatTime(currentTime)}</span>
              <span>{formatTime(displayDuration || 0)}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
