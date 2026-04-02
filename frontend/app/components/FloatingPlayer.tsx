"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import type { DailyBriefState } from "./DailyBrief";
import LogoIcon from "./LogoIcon";
import { hapticLight, hapticMedium, hapticConfirm } from "../lib/haptics";

const PlayIcon = () => (
  <svg width="11" height="13" viewBox="0 0 11 13" fill="currentColor" aria-hidden="true">
    <path d="M1 1.5v10l9-5z" />
  </svg>
);

const PauseIcon = () => (
  <svg width="10" height="12" viewBox="0 0 10 12" fill="currentColor" aria-hidden="true">
    <rect x="1" y="1" width="2.5" height="10" rx="0.5" />
    <rect x="6.5" y="1" width="2.5" height="10" rx="0.5" />
  </svg>
);

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

  /* ---- Swipe-down gesture (expanded → minimize) ---- */
  // IMPORTANT: All hooks must be called before any conditional return.
  // Moving these above the early return fixes React error #310:
  // "Rendered more hooks than during the previous render."
  const dragYRef = useRef<{ startY: number; current: number } | null>(null);
  const [dragOffset, setDragOffset] = useState(0);

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

  const handleBarTouchStart = (e: React.TouchEvent) => {
    dragYRef.current = { startY: e.touches[0].clientY, current: 0 };
  };

  const handleBarTouchMove = (e: React.TouchEvent) => {
    if (!dragYRef.current) return;
    const dy = e.touches[0].clientY - dragYRef.current.startY;
    if (dy > 0) {
      dragYRef.current.current = dy;
      setDragOffset(dy * 0.6);
    }
  };

  const handleBarTouchEnd = () => {
    if (!dragYRef.current) return;
    const dy = dragYRef.current.current;
    dragYRef.current = null;
    setDragOffset(0);
    if (dy > 80) {
      hapticLight();
      setExpanded(false);
    }
  };

  return (
    <div
      ref={playerRef}
      className={[
        "fp",
        expanded ? "fp--expanded" : "fp--compact",
        isPlaying ? "fp--playing" : "",
      ].filter(Boolean).join(" ")}
      style={dragOffset > 0 ? { transform: `translateY(${dragOffset}px)`, transition: "none" } : undefined}
      role="region"
      aria-label="Audio player"
    >
      {/* ── COMPACT PILL ── */}
      {!expanded && (
        <div className="fp__pill" onClick={toggleExpand}>
          {/* Void logo */}
          <LogoIcon size={16} animation={isPlaying ? "analyzing" : "idle"} className="fp__logo" />

          {/* Mini equalizer bars — visible when playing */}
          {isPlaying && (
            <div className="fp__pill-eq" aria-hidden="true">
              <div className="fp__pill-eq-bar" style={{ height: 10 }} />
              <div className="fp__pill-eq-bar" style={{ height: 14 }} />
              <div className="fp__pill-eq-bar" style={{ height: 8 }} />
              <div className="fp__pill-eq-bar" style={{ height: 12 }} />
            </div>
          )}

          {/* Play/Pause */}
          <button
            className={`fp__play${isPlaying ? " fp__play--active" : ""}`}
            onClick={(e) => { e.stopPropagation(); hapticConfirm(); handlePlayPause(); }}
            type="button"
            aria-label={isPlaying ? "Pause" : "Play"}
          >
            {isPlaying ? <PauseIcon /> : <PlayIcon />}
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
        <div
          className="fp__bar"
          onTouchStart={handleBarTouchStart}
          onTouchMove={handleBarTouchMove}
          onTouchEnd={handleBarTouchEnd}
        >
          {/* Drag indicator */}
          <div className="fp__drag-indicator" aria-hidden="true" />
          {/* Header — drag handle for swipe-down-to-minimize */}
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
              {isPlaying ? <PauseIcon /> : <PlayIcon />}
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
