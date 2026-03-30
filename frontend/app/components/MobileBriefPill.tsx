"use client";

import { useState, useRef, useEffect } from "react";
import type { DailyBriefState } from "./DailyBrief";
import { ScaleIcon } from "./ScaleIcon";
import { hapticLight, hapticMedium, hapticTick } from "../lib/haptics";
import { timeAgo } from "../lib/utils";

function formatTime(seconds: number): string {
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  const r = s % 60;
  return `${m}:${r.toString().padStart(2, "0")}`;
}

/* ---------------------------------------------------------------------------
   MobileBriefPill — Collapsed 44px pill that expands inline.

   Collapsed: "void --tl;dr · 3h ago    [▶] void --onair"
   Expanded: Full TL;DR + dotted rule + full Opinion + audio player
   Spring-snappy expand (300ms), ease-out collapse (200ms).
   --------------------------------------------------------------------------- */

export default function MobileBriefPill({ state }: { state: DailyBriefState }) {
  const { brief, isPlaying, currentTime, duration, audioError, audioRef, audioCallbackRef, handlePlayPause, handleSeek } = state;
  const [expanded, setExpanded] = useState(false);
  const contentRef = useRef<HTMLDivElement>(null);
  const [contentHeight, setContentHeight] = useState(0);
  const pillRef = useRef<HTMLDivElement>(null);

  // Measure content height for smooth expand/collapse
  useEffect(() => {
    if (!contentRef.current) return;
    const ro = new ResizeObserver(([entry]) => {
      setContentHeight(entry.contentRect.height);
    });
    ro.observe(contentRef.current);
    return () => ro.disconnect();
  }, [expanded]);

  if (!brief) return null;

  const hasAudio = !!brief.audio_url && !audioError;
  const displayDuration = (hasAudio && brief.audio_duration_seconds) || duration;
  const progress = displayDuration > 0 ? (currentTime / displayDuration) * 100 : 0;

  // Opinion section data
  const opinionStart = brief.opinion_start_seconds ?? null;
  const hasOpinion = opinionStart !== null && displayDuration > 0;
  const opinionPct = hasOpinion ? (opinionStart / displayDuration) * 100 : 100;
  const inOpinion = hasOpinion && currentTime >= opinionStart;

  const seekTo = (seconds: number) => {
    const audio = audioRef.current;
    if (!audio) return;
    hapticLight();
    audio.currentTime = seconds;
    if (!isPlaying) handlePlayPause();
  };

  const leanLabel = brief.opinion_lean === "left" ? "Progressive"
    : brief.opinion_lean === "right" ? "Conservative"
    : "Pragmatic";

  const leanMod = brief.opinion_lean === "left" ? "mbp-lean--left"
    : brief.opinion_lean === "right" ? "mbp-lean--right"
    : "mbp-lean--center";

  const paragraphs = brief.tldr_text
    .split("\n")
    .map((p) => p.trim())
    .filter(Boolean);

  const handleToggle = () => {
    hapticLight();
    setExpanded((prev) => !prev);
  };

  return (
    <div className={`mbp${expanded ? " mbp--expanded" : ""}`} ref={pillRef} role="complementary" aria-label="Daily Brief">
      {hasAudio && (
        <audio ref={audioCallbackRef} src={brief.audio_url!} preload="metadata" />
      )}

      {/* Collapsed pill header — always visible */}
      <button
        className="mbp__header"
        onClick={handleToggle}
        type="button"
        aria-expanded={expanded}
      >
        <div className="mbp__left">
          <ScaleIcon size={12} animation="idle" />
          <span className="mbp__cmd">void --tl;dr</span>
          {brief.created_at && (
            <span className="mbp__time">{timeAgo(brief.created_at)}</span>
          )}
        </div>
        <div className="mbp__right">
          {hasAudio && !expanded && (
            <button
              className={`mbp__play${isPlaying ? " mbp__play--active" : ""}`}
              onClick={(e) => { e.stopPropagation(); hapticMedium(); handlePlayPause(); }}
              type="button"
              aria-label={isPlaying ? "Pause broadcast" : "Play broadcast"}
            >
              <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
            </button>
          )}
          <span className="mbp__toggle" aria-hidden="true">
            {expanded ? "Less" : "Read"}
          </span>
        </div>
      </button>

      {/* Expandable content */}
      <div
        className="mbp__expand"
        style={{
          height: expanded ? contentHeight : 0,
          transition: expanded
            ? "height 300ms var(--spring-snappy)"
            : "height 200ms var(--ease-out)",
        }}
      >
        <div ref={contentRef} className="mbp__content">
          {/* TL;DR section */}
          <section className="mbp__section" aria-label="void --tl;dr">
            {brief.tldr_headline && (
              <h3 className="mbp__headline mbp__headline--accent">{brief.tldr_headline}</h3>
            )}
            <div className="mbp__text">
              {paragraphs.map((p, i) => (
                <p key={i}>{p}</p>
              ))}
            </div>
          </section>

          {/* Dotted firewall rule */}
          {brief.opinion_text && <hr className="mbp__rule" />}

          {/* Opinion section */}
          {brief.opinion_text && (
            <section className="mbp__section" aria-label="void --opinion">
              <div className="mbp__opinion-label">
                <ScaleIcon size={12} animation="idle" />
                <span className="mbp__cmd">void --opinion</span>
                {brief.opinion_lean && (
                  <span className={`mbp__lean ${leanMod}`}>{leanLabel}</span>
                )}
              </div>
              {brief.opinion_headline && (
                <h3 className="mbp__headline">{brief.opinion_headline}</h3>
              )}
              <div className="mbp__text">
                <p>{brief.opinion_text}</p>
              </div>
            </section>
          )}

          {/* Audio player (inline when expanded) */}
          {hasAudio && (
            <div className="mbp__audio">
              <div className="mbp__audio-header">
                <button
                  className={`mbp__play mbp__play--lg${isPlaying ? " mbp__play--active" : ""}`}
                  onClick={() => { hapticMedium(); handlePlayPause(); }}
                  type="button"
                  aria-label={isPlaying ? "Pause broadcast" : "Play broadcast"}
                >
                  <span aria-hidden="true">{isPlaying ? "\u275A\u275A" : "\u25B6"}</span>
                </button>
                <span className="mbp__cmd">void --onair</span>
                <span className="mbp__audio-time">
                  {formatTime(currentTime)} / {formatTime(displayDuration || 0)}
                </span>
              </div>

              {/* Section labels */}
              <div className="mbp__sections">
                <button
                  className={`mbp__section-btn${!inOpinion ? " mbp__section-btn--active" : ""}`}
                  onClick={() => seekTo(0)}
                  type="button"
                  style={hasOpinion ? { width: `${opinionPct}%` } : { width: "100%" }}
                >
                  News
                </button>
                {hasOpinion && (
                  <button
                    className={`mbp__section-btn${inOpinion ? " mbp__section-btn--active" : ""}`}
                    onClick={() => seekTo(opinionStart)}
                    type="button"
                    style={{ width: `${100 - opinionPct}%` }}
                  >
                    Opinion
                  </button>
                )}
              </div>

              {/* Seek bar */}
              <div className="mbp__seek-wrap">
                <div className="mbp__bar">
                  <div className="mbp__fill" style={{ width: `${progress}%` }} />
                  {hasOpinion && (
                    <span className="mbp__section-mark" style={{ left: `${opinionPct}%` }} aria-hidden="true" />
                  )}
                </div>
                <input
                  type="range"
                  className="mbp__seek"
                  min={0}
                  max={displayDuration || 100}
                  value={currentTime}
                  step={0.5}
                  onChange={handleSeek}
                  aria-label="Broadcast seek position"
                />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
